"""ai/data/sign_words/ 안의 mp4를 직접 읽어서 VideoMAE 입력 텐서로 변환하는 Dataset.

keypoint 버전(dataset.py)과 달리 캐싱이 필요 없다 (MediaPipe 포즈 추정처럼 무거운
연산이 없고, 그냥 프레임 리사이즈+정규화라 매번 읽어도 충분히 빠름).
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import torch
from torch.utils.data import Dataset, Sampler

from video_frames import load_video_as_tensor

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words"


class SignWordVideoDataset(Dataset):
    def __init__(self, train: bool = True, val_angles: tuple[str, ...] = ("U",)):
        self.train = train
        self.samples: list[tuple[str, Path]] = []

        words = sorted(p.name for p in DATA_DIR.iterdir() if p.is_dir())
        self.word_to_idx = {w: i for i, w in enumerate(words)}

        for word_dir in sorted(DATA_DIR.iterdir()):
            if not word_dir.is_dir():
                continue
            for mp4_path in sorted(word_dir.glob("*.mp4")):
                angle = mp4_path.stem.split("_")[-1]
                is_val = angle in val_angles
                if is_val == (not train):
                    self.samples.append((word_dir.name, mp4_path))

        if not self.samples:
            raise RuntimeError(f"{DATA_DIR} 에 학습용 mp4가 없습니다.")

    def label_map_path(self) -> Path:
        return DATA_DIR.parent / "word_label_map.json"

    def save_label_map(self):
        with open(self.label_map_path(), "w", encoding="utf-8") as f:
            json.dump(self.word_to_idx, f, ensure_ascii=False, indent=1)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        word, path = self.samples[i]
        tensor = load_video_as_tensor(str(path), jitter=self.train)
        label = self.word_to_idx[word]
        return tensor, label

    def labels(self) -> list[int]:
        return [self.word_to_idx[word] for word, _ in self.samples]


class PKBatchSampler(Sampler[list[int]]):
    """클래스당 k개씩 뽑아 배치를 구성해 SupCon의 positive pair를 보장한다.

    fold당 84개(21단어 x 4각도)처럼 클래스당 샘플이 몇 개 안 되는 데이터셋에서는
    무작위 셔플만 쓰면 배치 안에 같은 단어가 하나도 안 들어가는 경우가 흔해서,
    positive가 없는 anchor는 supervised_contrastive_loss에서 통째로 빠져버려
    (model.py의 has_positive 마스킹) 학습 신호가 약해진다.
    """

    def __init__(self, labels: list[int], batch_size: int, k: int | None = None):
        self.by_class: dict[int, list[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            self.by_class[label].append(idx)
        self.classes = list(self.by_class.keys())

        counts = Counter(labels)
        self.k = k if k is not None else min(counts.values())
        self.p = max(1, min(len(self.classes), batch_size // self.k))
        # 이전 shuffle+batch_size 방식과 비슷한 스텝 수(마지막 자투리 배치까지 포함)를
        # 유지하려고 올림 나눗셈을 쓴다 -- PK 샘플링은 배치마다 클래스를 다시 뽑으므로
        # "에폭"이 데이터를 정확히 한 번씩 도는 개념은 아니지만, 스텝 수는 맞춰준다.
        self.n_batches = max(1, -(-len(labels) // batch_size))

    def __iter__(self):
        for _ in range(self.n_batches):
            chosen = random.sample(self.classes, self.p)
            batch = []
            for c in chosen:
                pool = self.by_class[c]
                if len(pool) >= self.k:
                    batch.extend(random.sample(pool, self.k))
                else:
                    batch.extend(random.choices(pool, k=self.k))
            random.shuffle(batch)
            yield batch

    def __len__(self):
        return self.n_batches
