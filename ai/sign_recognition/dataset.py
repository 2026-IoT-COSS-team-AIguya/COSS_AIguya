"""캐싱된 keypoint(.npy)들을 불러와서, 매 에폭마다 랜덤 증강을 적용해 학습 샘플을
만들어주는 Dataset. 단어당 실제 영상은 5개(5각도)뿐이라 증강이 핵심이다.

증강 종류:
  - 랜덤 구간 자르기 + 길이 보간 (time-warp 효과)
  - 좌표에 약간의 가우시안 노이즈
  - 아주 약간의 스케일/회전 jitter (정규화된 좌표 기준)
  - 프레임 일부 랜덤 드롭 (occlusion 시뮬레이션)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words_keypoints"
FIXED_LEN = 64  # 모든 샘플을 이 프레임 길이로 리샘플


def _resize_time(seq: np.ndarray, target_len: int) -> np.ndarray:
    """[T, D] -> [target_len, D], 시간축 선형보간."""
    t_orig = seq.shape[0]
    if t_orig == target_len:
        return seq
    x_old = np.linspace(0, 1, t_orig)
    x_new = np.linspace(0, 1, target_len)
    out = np.empty((target_len, seq.shape[1]), dtype=np.float32)
    for d in range(seq.shape[1]):
        out[:, d] = np.interp(x_new, x_old, seq[:, d])
    return out


def augment(seq: np.ndarray, train: bool = True) -> np.ndarray:
    seq = seq.copy()
    t = seq.shape[0]

    if train and t > 10:
        # 속도 변화(빠르게/느리게 사인하는 것처럼): 전체 길이를 먼저 리샘플
        speed = np.random.uniform(0.8, 1.25)
        new_t = max(10, int(t / speed))
        seq = _resize_time(seq, new_t)
        t = new_t

        # 랜덤 구간 자르기 (80~100% 길이)
        keep_ratio = np.random.uniform(0.8, 1.0)
        keep_len = max(8, int(t * keep_ratio))
        start = np.random.randint(0, t - keep_len + 1)
        seq = seq[start : start + keep_len]

    seq = _resize_time(seq, FIXED_LEN)

    if train:
        # 좌표 노이즈
        seq = seq + np.random.normal(0, 0.01, seq.shape).astype(np.float32)

        # 아주 약간의 스케일 jitter
        scale = np.random.uniform(0.95, 1.05)
        seq = seq * scale

        # 프레임 일부 드롭(occlusion 시뮬레이션) -> 이전 프레임 값으로 대체
        pts = seq.reshape(FIXED_LEN, -1, 3)
        n_drop = np.random.randint(0, 4)
        for _ in range(n_drop):
            idx = np.random.randint(1, FIXED_LEN)
            pts[idx] = pts[idx - 1]
        seq = pts.reshape(FIXED_LEN, -1)

    return seq.astype(np.float32)


class SignWordDataset(Dataset):
    def __init__(self, train: bool = True, val_angles: tuple[str, ...] = ("U",)):
        """val_angles: 검증(val)으로 빼둘 각도. 나머지 각도는 학습에 씀.
        각도 기준으로 나누면 '한 번도 안 본 시점'에 대한 일반화를 확인할 수 있다."""
        self.train = train
        self.samples: list[tuple[str, Path]] = []  # (word, npy_path)

        words = sorted(p.name for p in CACHE_DIR.iterdir() if p.is_dir())
        self.word_to_idx = {w: i for i, w in enumerate(words)}

        for word_dir in sorted(CACHE_DIR.iterdir()):
            if not word_dir.is_dir():
                continue
            for npy_path in sorted(word_dir.glob("*.npy")):
                angle = npy_path.stem.split("_")[-1]
                is_val = angle in val_angles
                if is_val == (not train):
                    self.samples.append((word_dir.name, npy_path))

        if not self.samples:
            raise RuntimeError(
                f"{CACHE_DIR} 에 학습용 npy가 없습니다. extract_all.py 먼저 실행하세요."
            )

    def label_map_path(self) -> Path:
        return CACHE_DIR.parent / "word_label_map.json"

    def save_label_map(self):
        with open(self.label_map_path(), "w", encoding="utf-8") as f:
            json.dump(self.word_to_idx, f, ensure_ascii=False, indent=1)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        word, path = self.samples[i]
        seq = np.load(path)
        seq = augment(seq, train=self.train)
        label = self.word_to_idx[word]
        return torch.from_numpy(seq), label
