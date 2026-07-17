"""임베딩 인코더 학습.

클래스(단어) 수에 비해 단어당 영상이 적어서(단어DB 유래는 5개=5각도, 문장클립
유래는 최대 20개), 전체 학습셋을 통째로 한 배치로 넣는다 (매 배치에 모든 단어가
다 들어가야 Supervised Contrastive Loss가 제대로 작동하기 때문).

절차:
  1. 5개 각도(D/F/L/R/U)를 돌아가며 하나씩 검증용으로 떼어놓는 "leave-one-angle-out"
     교차검증을 5번 돌려서, 안 본 각도에 대한 일반화 성능을 신뢰성 있게 추정한다.
  2. 교차검증에서 성능이 가장 좋았던 시점의 평균 에폭 수를 확인한 뒤,
     실제 배포용 모델은 5개 각도를 전부 학습에 써서 (검증용으로 떼어두지 않고)
     그 에폭 수만큼 학습해 최대한 많은 데이터를 활용한다.

실행:
    conda activate coss
    python ai/sign_recognition/train.py
"""
import os
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from dataset import SignWordDataset, augment, CACHE_DIR
from model import SignEncoder, supervised_contrastive_loss

# wandb 로그인이 안 되어 있으면(~/.netrc 없고 WANDB_API_KEY도 없으면) wandb.init()이
# 터미널 로그인 프롬프트를 띄우다 백그라운드 실행을 멈춰버릴 수 있어서, 로그인
# 여부를 먼저 확인하고 안 되어 있으면 조용히 wandb 없이(콘솔 출력만) 돈다.
# Windows에서 wandb login은 인증정보를 `.netrc`가 아니라 `_netrc`에 저장하므로 둘 다 확인한다.
WANDB_ENABLED = (
    bool(os.environ.get("WANDB_API_KEY"))
    or Path.home().joinpath(".netrc").exists()
    or Path.home().joinpath("_netrc").exists()
)
if WANDB_ENABLED:
    import wandb
else:
    print("[wandb] 로그인 안 되어 있어서 wandb 로깅 없이 진행합니다 (터미널에서 `wandb login` 실행 후 재실행하면 활성화됨)")

MODEL_OUT = Path(__file__).resolve().parent.parent / "models" / "sign_encoder.pt"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS = 300
LR = 1e-3
# 21->78단어로 늘면서 모델 용량(model.py hidden/embed_dim)도 키웠는데, 파라미터가
# 늘면 이 정도(단어당 1~20개) 데이터량에서는 과적합 위험도 같이 커지므로
# weight decay를 조금 더 준다.
WEIGHT_DECAY = 2e-4
ALL_ANGLES = ("D", "F", "L", "R", "U")
# 78단어로 늘면서 fold별 최고 정확도 시점이 epoch 100~280으로 넓게 퍼졌다
# (20단위로는 최적 지점을 놓칠 수 있음) -- 10단위로 더 촘촘히 확인한다.
EVAL_EVERY = 10


def make_model_and_optim():
    model = SignEncoder().to(DEVICE)
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=EPOCHS)
    return model, optim, sched


@torch.no_grad()
def eval_holdout(model: SignEncoder, word_to_idx: dict, holdout_angle: str) -> float:
    """holdout_angle 클립들이, 나머지 각도 클립들 중 같은 단어를 1등으로 찾는 비율."""
    model.eval()
    gallery_emb, gallery_label, query_emb, query_label = [], [], [], []

    for word_dir in sorted(CACHE_DIR.iterdir()):
        if not word_dir.is_dir():
            continue
        label = word_to_idx[word_dir.name]
        for npy_path in sorted(word_dir.glob("*.npy")):
            angle = npy_path.stem.split("_")[-1]
            seq = augment(np.load(npy_path), train=False)
            x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
            emb = model(x).cpu().numpy()[0]
            if angle == holdout_angle:
                query_emb.append(emb)
                query_label.append(label)
            else:
                gallery_emb.append(emb)
                gallery_label.append(label)

    gallery_emb = np.stack(gallery_emb)
    gallery_label = np.array(gallery_label)
    correct = sum(
        gallery_label[(gallery_emb @ e).argmax()] == l
        for e, l in zip(query_emb, query_label)
    )
    model.train()
    return correct / max(1, len(query_label))


def run_fold(holdout_angle: str, word_to_idx: dict):
    train_ds = SignWordDataset(train=True, val_angles=(holdout_angle,))
    loader = DataLoader(train_ds, batch_size=len(train_ds), shuffle=True)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="keypoint-cv",
            name=f"keypoint-fold-{holdout_angle}",
            config={"epochs": EPOCHS, "lr": LR, "n_words": len(word_to_idx), "holdout_angle": holdout_angle},
            reinit=True,
        )

    history = []  # (epoch, acc)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
            epoch_loss = loss.item()  # 배치가 하나뿐(full-batch)이라 그대로 씀
        sched.step()

        log = {"epoch": epoch, "train_loss": epoch_loss}
        if epoch % EVAL_EVERY == 0 or epoch == EPOCHS:
            acc = eval_holdout(model, word_to_idx, holdout_angle)
            history.append((epoch, acc))
            log["val_acc"] = acc
            print(f"    [holdout={holdout_angle}] epoch {epoch:3d}/{EPOCHS}  loss {epoch_loss:.4f}  acc {acc:.1%}")
        if run is not None:
            run.log(log)

    best_epoch, best_acc = max(history, key=lambda h: h[1])
    print(f"  [holdout={holdout_angle}] best acc {best_acc:.1%} @ epoch {best_epoch}")
    if run is not None:
        run.summary["best_acc"] = best_acc
        run.summary["best_epoch"] = best_epoch
        run.finish()
    return best_epoch, best_acc


def train_final(word_to_idx: dict, n_epochs: int):
    """검증용으로 각도를 떼어두지 않고 5개 각도 전부로 최종 배포 모델을 학습."""
    train_ds = SignWordDataset(train=True, val_angles=())  # 아무 각도도 안 뺌 = 전부 학습
    loader = DataLoader(train_ds, batch_size=len(train_ds), shuffle=True)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="keypoint-cv",
            name="keypoint-final",
            config={"epochs": n_epochs, "lr": LR, "n_words": len(word_to_idx)},
            reinit=True,
        )

    for epoch in range(1, n_epochs + 1):
        model.train()
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
        sched.step()
        if run is not None:
            run.log({"epoch": epoch, "train_loss": loss.item()})
        if epoch % EVAL_EVERY == 0 or epoch == n_epochs:
            print(f"  final epoch {epoch:4d}  loss {loss.item():.4f}")

    if run is not None:
        run.finish()

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "word_to_idx": word_to_idx}, MODEL_OUT)
    print(f"최종 모델 저장 -> {MODEL_OUT}")


def main():
    probe_ds = SignWordDataset(train=True, val_angles=("U",))
    word_to_idx = probe_ds.word_to_idx
    probe_ds.save_label_map()
    print(f"단어 {len(word_to_idx)}개, device: {DEVICE}\n")

    print("=== 1) leave-one-angle-out 5-fold 교차검증 ===")
    results = []
    for i, angle in enumerate(ALL_ANGLES, 1):
        print(f"\n-- fold {i}/{len(ALL_ANGLES)} (holdout={angle}) 시작 --")
        results.append(run_fold(angle, word_to_idx))

    accs = [r[1] for r in results]
    epochs_at_best = [r[0] for r in results]
    print(f"\n교차검증 평균 정확도: {np.mean(accs):.1%}  (fold별: {[f'{a:.0%}' for a in accs]})")
    chosen_epochs = int(np.median(epochs_at_best))
    print(f"최종 학습 에폭 수 결정: {chosen_epochs} (각 fold에서 제일 좋았던 에폭의 중앙값)")

    print("\n=== 2) 전체 데이터(5각도 전부)로 최종 배포 모델 학습 ===")
    train_final(word_to_idx, chosen_epochs)


if __name__ == "__main__":
    main()
