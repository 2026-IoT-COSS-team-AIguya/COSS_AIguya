"""ai/data/sign_words/ 안의 모든 mp4를 keypoint로 변환해서 .npy로 캐싱한다.
학습 때마다 MediaPipe를 다시 돌리면 느리므로 한 번만 뽑아두고 재사용.

실행:
    conda activate coss
    python ai/sign_recognition/extract_all.py
"""
from pathlib import Path

import numpy as np

from keypoints import extract_keypoints_from_video, normalize_sequence

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words_keypoints"


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    videos = sorted(DATA_DIR.glob("*/*.mp4"))
    print(f"영상 {len(videos)}개 발견")

    n_ok, n_skip = 0, 0
    for i, video_path in enumerate(videos, 1):
        word = video_path.parent.name
        out_dir = CACHE_DIR / word
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / (video_path.stem + ".npy")

        if out_path.exists():
            n_skip += 1
            continue

        kp = extract_keypoints_from_video(str(video_path))
        kp = normalize_sequence(kp)
        np.save(out_path, kp)
        n_ok += 1
        print(f"  [{i}/{len(videos)}] {word}/{video_path.name} -> {kp.shape}")

    print(f"\n완료: 새로 추출 {n_ok}, 이미 있어서 건너뜀 {n_skip}")
    print(f"캐시 위치: {CACHE_DIR}")


if __name__ == "__main__":
    main()
