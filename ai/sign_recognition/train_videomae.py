"""VideoMAE 전이학습 기반 임베딩 인코더 학습 (train.py의 VideoMAE 버전).

keypoint 버전과 똑같은 절차를 따른다:
  1. 5개 각도(D/F/L/R/U)를 돌아가며 하나씩 검증용으로 떼어놓는 leave-one-angle-out
     교차검증을 5번 돌려서 일반화 성능을 추정한다.
  2. 교차검증에서 성능이 가장 좋았던 시점의 평균 에폭 수를 확인한 뒤,
     실제 배포용 모델은 5개 각도를 전부 학습에 써서 그 에폭 수만큼 학습한다.

keypoint 버전과 다른 점:
  - backbone(VideoMAE)은 대부분 얼려있으므로 optim은 model.trainable_parameters()
    (마지막 n_unfrozen개 트랜스포머 층 + head)만 학습한다.
  - 사전학습된 표현을 이미 갖고 있으므로 학습률은 훨씬 작게(1e-4), 에폭 수도
    훨씬 적게(과적합/파괴적 망각 방지) 잡는다.
  - 영상 텐서라 배치당 메모리 비용이 커서 EPOCHS를 keypoint판보다 낮춘다.

실행:
    conda activate coss
    python ai/sign_recognition/train_videomae.py
"""
import os
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from video_dataset import SignWordVideoDataset, PKBatchSampler
from video_frames import load_video_as_tensor
from model import VideoMAEEncoder, supervised_contrastive_loss

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

MODEL_OUT = Path(__file__).resolve().parent.parent / "models" / "sign_encoder_videomae.pt"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# 첫 시도(EPOCHS=60, N_UNFROZEN=2)에서 epoch 15(19.0%)를 정점으로 val_acc가
# 계속 나빠지는데 train_loss는 계속 좋아지는 전형적 과적합 패턴이 나와서
# (학습에 쓴 4개 각도의 뷰 특이적 패턴을 외우고, 못 본 각도로는 일반화 실패),
# unfreeze 범위/에폭 수를 줄이고 정규화를 강화한다.
EPOCHS = 30
LR = 1e-4
WEIGHT_DECAY = 3e-4
DROPOUT = 0.4
ALL_ANGLES = ("D", "F", "L", "R", "U")
EVAL_EVERY = 5
N_UNFROZEN = 1

# 실측 결과 8GB VRAM 기준: 84(full batch) 배치는 gradient checkpointing을 켜도
# 11.7GB가 필요해 못 돌아간다 (어텐션 시퀀스 길이가 1568토큰이라 배치에 선형
# 비례해서 메모리를 먹음). 배치 32는 4.23GB로 여유 있게 들어가서 이 값을 쓴다.
# 대신 한 에폭에 여러 미니배치를 도는 구조가 되어 SupCon이 매 스텝 21개 단어를
# 전부 못 보긴 하지만, 에폭 수가 넉넉하고 매번 랜덤 셔플되니 데이터 활용에는
# 문제 없다.
BATCH_SIZE = 32

# 매 __getitem__마다 영상을 캐싱 없이 새로 디코딩하느라 CPU가 병목이라(GPU 사용률
# 17% 수준), 워커 여러 개로 디코딩을 병렬화한다. persistent_workers=True로
# 에폭마다 워커를 새로 안 띄우고 재사용(같은 loader를 여러 epoch 동안 재사용하는
# 구조라 워커 재시작 비용이 누적되면 손해가 크다).
NUM_WORKERS = 4


def make_loader(ds, batch_size):
    sampler = PKBatchSampler(ds.labels(), batch_size)
    return DataLoader(
        ds,
        batch_sampler=sampler,
        num_workers=NUM_WORKERS,
        persistent_workers=NUM_WORKERS > 0,
        pin_memory=True,
    )


def make_model_and_optim():
    model = VideoMAEEncoder(n_unfrozen=N_UNFROZEN, dropout=DROPOUT).to(DEVICE)
    optim = torch.optim.Adam(model.trainable_parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=EPOCHS)
    return model, optim, sched


@torch.no_grad()
def eval_holdout(model: VideoMAEEncoder, word_to_idx: dict, holdout_angle: str) -> float:
    """holdout_angle 클립들이, 나머지 각도 클립들 중 같은 단어를 1등으로 찾는 비율."""
    model.eval()
    from video_dataset import DATA_DIR

    gallery_emb, gallery_label, query_emb, query_label = [], [], [], []

    for word_dir in sorted(DATA_DIR.iterdir()):
        if not word_dir.is_dir():
            continue
        label = word_to_idx[word_dir.name]
        for mp4_path in sorted(word_dir.glob("*.mp4")):
            angle = mp4_path.stem.split("_")[-1]
            tensor = load_video_as_tensor(str(mp4_path), jitter=False)
            x = tensor.unsqueeze(0).to(DEVICE)
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
    train_ds = SignWordVideoDataset(train=True, val_angles=(holdout_angle,))
    loader = make_loader(train_ds, BATCH_SIZE)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="videomae-cv",
            name=f"videomae-fold-{holdout_angle}",
            config={"batch_size": BATCH_SIZE, "lr": LR, "n_unfrozen": N_UNFROZEN, "epochs": EPOCHS, "holdout_angle": holdout_angle},
            reinit=True,
        )

    history = []  # (epoch, acc)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
            epoch_loss += loss.item()
            n_batches += 1
        sched.step()
        epoch_loss /= max(1, n_batches)

        log = {"epoch": epoch, "train_loss": epoch_loss}
        if epoch % EVAL_EVERY == 0 or epoch == EPOCHS:
            acc = eval_holdout(model, word_to_idx, holdout_angle)
            history.append((epoch, acc))
            log["val_acc"] = acc
            print(f"    epoch {epoch:3d}  loss {epoch_loss:.4f}  acc {acc:.1%}")
        else:
            print(f"    epoch {epoch:3d}  loss {epoch_loss:.4f}")
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
    train_ds = SignWordVideoDataset(train=True, val_angles=())  # 아무 각도도 안 뺌 = 전부 학습
    loader = make_loader(train_ds, BATCH_SIZE)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="videomae-cv",
            name="videomae-final",
            config={"batch_size": BATCH_SIZE, "lr": LR, "n_unfrozen": N_UNFROZEN, "epochs": n_epochs},
            reinit=True,
        )

    for epoch in range(1, n_epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
            epoch_loss += loss.item()
            n_batches += 1
        sched.step()
        epoch_loss /= max(1, n_batches)
        if run is not None:
            run.log({"epoch": epoch, "train_loss": epoch_loss})
        print(f"  final epoch {epoch:4d}  loss {epoch_loss:.4f}")

    if run is not None:
        run.finish()

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model_state": model.state_dict(), "word_to_idx": word_to_idx, "n_unfrozen": N_UNFROZEN},
        MODEL_OUT,
    )
    print(f"최종 모델 저장 -> {MODEL_OUT}")


def main():
    probe_ds = SignWordVideoDataset(train=True, val_angles=("U",))
    word_to_idx = probe_ds.word_to_idx
    probe_ds.save_label_map()
    print(f"단어 {len(word_to_idx)}개, device: {DEVICE}\n")

    print("=== 1) leave-one-angle-out 5-fold 교차검증 (VideoMAE) ===")
    results = []
    for angle in ALL_ANGLES:
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
