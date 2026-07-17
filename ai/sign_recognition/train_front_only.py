"""정면(F) 전용 학습 + 사람 기준 교차검증.

D/L/R/U는 버리고 F만 쓴다. 이제 데이터 대부분이 정면(팀원 직접 촬영 + AIHub
정면 1개씩)이라, 기존 leave-one-angle-out(train.py)은 더 이상 의미가 없다 --
F를 통째로 홀드아웃하면 학습 데이터가 D/L/R/U(단어당 1개뿐)만 남아서 애초에
잘될 수가 없는 구조였다 (실제로 F 정확도가 97%->37%로 폭락한 원인).

대신 팀원이 직접 찍은 28개 단어(가깝다~알다, 4명 x 2번)는 **촬영한 사람 기준**
으로 나눠서(leave-one-person-out) "새로운 사람이 해도 인식되는지"를 검증한다.
AIHub 정면 데이터(단어DB 1개, 문장클립 유래 ~4개)는 사람 구분이 없는 데이터라
holdout으로 뺄 수 없어서 모든 fold에서 항상 학습에 포함한다.

실행:
    conda activate coss
    python ai/sign_recognition/train_front_only.py
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from dataset import CACHE_DIR, augment
from model import SignEncoder, supervised_contrastive_loss

WANDB_ENABLED = (
    bool(os.environ.get("WANDB_API_KEY"))
    or Path.home().joinpath(".netrc").exists()
    or Path.home().joinpath("_netrc").exists()
)
if WANDB_ENABLED:
    import wandb
else:
    print("[wandb] 로그인 안 되어 있어서 wandb 로깅 없이 진행합니다")

MODEL_OUT = Path(__file__).resolve().parent.parent / "models" / "sign_encoder.pt"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS = 300
LR = 1e-3
WEIGHT_DECAY = 2e-4
EVAL_EVERY = 10

# 기존 1차 촬영분(가깝다~알다, 224개) 호환용: 단어당 1~2번=A, 3~4번=B, 5~6번=C, 7~8번=D.
# 앞으로 추가 촬영할 때는 이 숫자만으로 사람을 구분하는 방식이 아니라, 파일명에
# 사람을 직접 적어주는 게 안전하다 (사람 수/촬영 순서가 매번 달라질 수 있어서):
#   ai/data/recorded/{단어}/{단어}_{사람이니셜}{번호}.mp4  예) 은행_kim1.mp4, 은행_lee2.mp4
# extract_recorded.py를 거치면 "은행_kim1_F.npy"가 되고, 아래 파싱이 앞의 문자
# 부분("kim")을 사람으로 인식한다. 순수 숫자만 있으면(기존 촬영분) 아래 매핑을 쓴다.
LEGACY_TAKE_TO_PERSON = {1: "A", 2: "A", 3: "B", 4: "B", 5: "C", 6: "C", 7: "D", 8: "D"}


def _parse_person(middle_token: str) -> str | None:
    """파일명 중간 토큰에서 촬영자를 뽑아낸다.

    - 순수 숫자(예: "3")면 1차 촬영분 규칙(LEGACY_TAKE_TO_PERSON)을 적용.
    - "SEN0042"처럼 extract_sentence_clips.py가 붙이는 AIHub 문장 태그면
      사람 구분 없는 데이터로 취급(None).
    - 문자+숫자(예: "kim2", "A1")면 앞의 문자 부분("kim", "A")을 사람으로 사용.
    - 그 외(패턴이 안 맞음)는 None -- 사람 구분 없는 데이터로 취급.
    """
    if middle_token.isdigit():
        return LEGACY_TAKE_TO_PERSON.get(int(middle_token))
    if middle_token.upper().startswith("SEN"):
        return None
    letters = middle_token.rstrip("0123456789")
    return letters if letters else None


def scan_f_only_instances() -> list[tuple[str, Path, str | None]]:
    """모든 단어의 F(정면) 인스턴스만 스캔.

    반환: (단어, 경로, 촬영자) 리스트. 촬영자는 팀원 직접 촬영본만 채워지고,
    AIHub 유래(단어DB/문장클립)는 None -- 사람 구분이 없어서 항상 학습에 포함된다.
    """
    instances = []
    for word_dir in sorted(CACHE_DIR.iterdir()):
        if not word_dir.is_dir():
            continue
        word = word_dir.name
        for npy_path in sorted(word_dir.glob("*_F.npy")):
            parts = npy_path.stem.split("_")  # [단어, ..., F]
            middle = parts[1:-1]
            person = _parse_person(middle[0]) if len(middle) == 1 else None
            instances.append((word, npy_path, person))
    return instances


class FrontOnlyDataset(Dataset):
    def __init__(self, instances: list[tuple[str, Path, str | None]], word_to_idx: dict, train: bool):
        self.instances = instances
        self.word_to_idx = word_to_idx
        self.train = train

    def __len__(self):
        return len(self.instances)

    def __getitem__(self, i):
        word, path, _ = self.instances[i]
        seq = augment(np.load(path), train=self.train)
        return torch.from_numpy(seq), self.word_to_idx[word]


def make_model_and_optim():
    model = SignEncoder().to(DEVICE)
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=EPOCHS)
    return model, optim, sched


@torch.no_grad()
def eval_holdout(model, word_to_idx, train_instances, query_instances):
    model.eval()
    gallery_emb, gallery_label = [], []
    for word, path, _ in train_instances:
        seq = augment(np.load(path), train=False)
        x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
        emb = model(x).cpu().numpy()[0]
        gallery_emb.append(emb)
        gallery_label.append(word_to_idx[word])
    gallery_emb = np.stack(gallery_emb)
    gallery_label = np.array(gallery_label)

    correct = 0
    per_word_correct, per_word_total = defaultdict(int), defaultdict(int)
    for word, path, _ in query_instances:
        seq = augment(np.load(path), train=False)
        x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
        emb = model(x).cpu().numpy()[0]
        pred = gallery_label[(gallery_emb @ emb).argmax()]
        label = word_to_idx[word]
        per_word_total[word] += 1
        if pred == label:
            correct += 1
            per_word_correct[word] += 1
    model.train()
    acc = correct / max(1, len(query_instances))
    return acc, per_word_correct, per_word_total


def run_fold(holdout_person: str, all_instances, word_to_idx):
    train_instances = [inst for inst in all_instances if inst[2] != holdout_person]
    query_instances = [inst for inst in all_instances if inst[2] == holdout_person]

    train_ds = FrontOnlyDataset(train_instances, word_to_idx, train=True)
    loader = DataLoader(train_ds, batch_size=len(train_ds), shuffle=True)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="front-only-person-cv",
            name=f"person-fold-{holdout_person}",
            config={"epochs": EPOCHS, "lr": LR, "n_words": len(word_to_idx), "holdout_person": holdout_person},
            reinit=True,
        )

    history = []
    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
            epoch_loss = loss.item()
        sched.step()

        log = {"epoch": epoch, "train_loss": epoch_loss}
        if epoch % EVAL_EVERY == 0 or epoch == EPOCHS:
            acc, _, _ = eval_holdout(model, word_to_idx, train_instances, query_instances)
            history.append((epoch, acc))
            log["val_acc"] = acc
            print(f"    [holdout={holdout_person}] epoch {epoch:3d}/{EPOCHS}  loss {epoch_loss:.4f}  acc {acc:.1%}")
        if run is not None:
            run.log(log)

    best_epoch, best_acc = max(history, key=lambda h: h[1])
    print(f"  [holdout={holdout_person}] best acc {best_acc:.1%} @ epoch {best_epoch}")
    if run is not None:
        run.summary["best_acc"] = best_acc
        run.summary["best_epoch"] = best_epoch
        run.finish()
    return best_epoch, best_acc


def train_final(all_instances, word_to_idx, n_epochs: int):
    train_ds = FrontOnlyDataset(all_instances, word_to_idx, train=True)
    loader = DataLoader(train_ds, batch_size=len(train_ds), shuffle=True)
    model, optim, sched = make_model_and_optim()

    run = None
    if WANDB_ENABLED:
        run = wandb.init(
            project="coss-sign-recognition",
            group="front-only-person-cv",
            name="front-only-final",
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
    instances = scan_f_only_instances()
    words = sorted({w for w, _, _ in instances})
    word_to_idx = {w: i for i, w in enumerate(words)}

    with open(CACHE_DIR.parent / "word_label_map.json", "w", encoding="utf-8") as f:
        import json

        json.dump(word_to_idx, f, ensure_ascii=False, indent=1)

    all_persons = sorted({p for _, _, p in instances if p is not None})
    n_person_labeled = sum(1 for _, _, p in instances if p is not None)
    print(f"단어 {len(words)}개, 전체 F 인스턴스 {len(instances)}개 (촬영자 라벨 있음: {n_person_labeled}개, 촬영자 {len(all_persons)}명: {all_persons}), device: {DEVICE}\n")

    print(f"=== 1) leave-one-person-out {len(all_persons)}-fold 교차검증 ===")
    results = []
    for i, person in enumerate(all_persons, 1):
        print(f"\n-- fold {i}/{len(all_persons)} (holdout={person}) 시작 --")
        results.append(run_fold(person, instances, word_to_idx))

    accs = [r[1] for r in results]
    epochs_at_best = [r[0] for r in results]
    print(f"\n교차검증 평균 정확도: {np.mean(accs):.1%}  (fold별: {dict(zip(all_persons, [f'{a:.0%}' for a in accs]))})")
    chosen_epochs = int(np.median(epochs_at_best))
    print(f"최종 학습 에폭 수 결정: {chosen_epochs}")

    print("\n=== 2) 전체 데이터로 최종 배포 모델 학습 ===")
    train_final(instances, word_to_idx, chosen_epochs)


if __name__ == "__main__":
    main()
