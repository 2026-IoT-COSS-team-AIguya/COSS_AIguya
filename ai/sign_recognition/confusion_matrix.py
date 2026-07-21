"""train_front_only.py와 같은 leave-one-person-out 4-fold로 다시 학습하면서,
이번엔 정확도 숫자만 보지 말고 "어떤 단어를 뭐로 착각했는지"까지 기록한다.

이미 배포된 sign_encoder.pt(전체 데이터로 학습)로 confusion을 뽑으면 학습에 쓴
데이터를 그대로 다시 맞히는 셈이라 의미가 없어서(데이터 누수), 홀드아웃
예측을 얻으려면 CV를 한 번 더 돌려야 한다.

실행:
    conda activate coss
    python ai/sign_recognition/confusion_matrix.py
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from dataset import augment
from model import supervised_contrastive_loss
from train_front_only import (
    DEVICE,
    EPOCHS,
    EVAL_EVERY,
    FrontOnlyDataset,
    make_model_and_optim,
    scan_f_only_instances,
)

OUT_PATH = Path(__file__).resolve().parent.parent / "models" / "confusion_report.txt"


@torch.no_grad()
def eval_with_predictions(model, word_to_idx, idx_to_word, train_instances, query_instances):
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
    pairs = []  # (true_word, pred_word)
    for word, path, _ in query_instances:
        seq = augment(np.load(path), train=False)
        x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
        emb = model(x).cpu().numpy()[0]
        pred_idx = gallery_label[(gallery_emb @ emb).argmax()]
        pred_word = idx_to_word[pred_idx]
        pairs.append((word, pred_word))
        if pred_word == word:
            correct += 1
    model.train()
    acc = correct / max(1, len(query_instances))
    return acc, pairs


def run_fold_with_confusion(holdout_person, all_instances, word_to_idx, idx_to_word):
    train_instances = [inst for inst in all_instances if inst[2] != holdout_person]
    query_instances = [inst for inst in all_instances if inst[2] == holdout_person]

    train_ds = FrontOnlyDataset(train_instances, word_to_idx, train=True)
    loader = DataLoader(train_ds, batch_size=len(train_ds), shuffle=True)
    model, optim, sched = make_model_and_optim()

    best_acc = -1.0
    best_pairs = []
    for epoch in range(1, EPOCHS + 1):
        model.train()
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            loss = supervised_contrastive_loss(model(x), y)
            optim.zero_grad()
            loss.backward()
            optim.step()
        sched.step()

        if epoch % EVAL_EVERY == 0 or epoch == EPOCHS:
            acc, pairs = eval_with_predictions(model, word_to_idx, idx_to_word, train_instances, query_instances)
            print(f"    [holdout={holdout_person}] epoch {epoch:3d}/{EPOCHS}  acc {acc:.1%}")
            if acc > best_acc:
                best_acc, best_pairs = acc, pairs

    print(f"  [holdout={holdout_person}] best acc {best_acc:.1%}")
    return best_acc, best_pairs


def main():
    instances = scan_f_only_instances()
    words = sorted({w for w, _, _ in instances})
    word_to_idx = {w: i for i, w in enumerate(words)}
    idx_to_word = {i: w for w, i in word_to_idx.items()}
    all_persons = sorted({p for _, _, p in instances if p is not None})

    print(f"단어 {len(words)}개, 촬영자 {len(all_persons)}명: {all_persons}, device: {DEVICE}\n")

    all_pairs = []
    for i, person in enumerate(all_persons, 1):
        print(f"\n-- fold {i}/{len(all_persons)} (holdout={person}) --")
        _, pairs = run_fold_with_confusion(person, instances, word_to_idx, idx_to_word)
        all_pairs.extend(pairs)

    # 단어별로 "틀렸을 때 뭐로 착각했는지" 집계
    confusions: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    corrects: Counter = Counter()
    for true_word, pred_word in all_pairs:
        totals[true_word] += 1
        if pred_word == true_word:
            corrects[true_word] += 1
        else:
            confusions[true_word][pred_word] += 1

    lines = []
    lines.append("=== 단어별 정확도 + 오답일 때 가장 많이 헷갈린 단어 (틀린 케이스만) ===\n")
    for word in sorted(words, key=lambda w: corrects[w] / max(1, totals[w])):
        total = totals[word]
        if total == 0:
            continue
        acc = corrects[word] / total
        top_confuse = confusions[word].most_common(3)
        confuse_str = ", ".join(f"{w}({c}회)" for w, c in top_confuse) if top_confuse else "-"
        lines.append(f"{word:8s} acc={acc:5.1%} ({corrects[word]}/{total})  헷갈린 단어: {confuse_str}")

    report = "\n".join(lines)
    print("\n" + report)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"\n리포트 저장 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
