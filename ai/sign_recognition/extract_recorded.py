"""팀원이 직접 촬영한 영상(ai/data/recorded/{단어}/*.mp4)을 keypoint로 변환해서
학습 캐시(ai/data/sign_words_keypoints/)에 추가한다.

전부 정면(F) 카메라로 찍는다고 가정하고 각도를 "F"로 저장한다 -- dataset.py의
leave-one-angle-out 교차검증이 파일명 끝의 각도 코드로 학습/검증을 나누는데,
F로 저장해두면 이 촬영본들이 (1) F가 홀드아웃일 때는 검증셋에 들어가서 "실제
시연 조건에서 얼마나 맞는지"를 바로 보여주고, (2) 나머지 4개 fold에서는 학습에
쓰여서 정면 케이스에 대한 학습 신호를 강화해준다.

실행:
    conda activate coss
    python ai/sign_recognition/extract_recorded.py
"""
from pathlib import Path

import numpy as np

from keypoints import extract_keypoints_from_video, normalize_sequence

RECORDED_DIR = Path(__file__).resolve().parent.parent / "data" / "recorded"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words_keypoints"
ANGLE_TAG = "F"  # 촬영은 전부 정면으로 한다는 가정


def main():
    if not RECORDED_DIR.exists():
        print(f"{RECORDED_DIR} 가 없습니다. ai/data/recorded/{{단어}}/{{단어}}_own1.mp4 형식으로 넣어주세요.")
        return

    videos = sorted(RECORDED_DIR.glob("*/*.mp4"))
    if not videos:
        print(f"{RECORDED_DIR} 안에 mp4가 없습니다.")
        return
    print(f"촬영 영상 {len(videos)}개 발견")

    n_ok, n_skip = 0, 0
    for i, video_path in enumerate(videos, 1):
        word = video_path.parent.name
        out_dir = CACHE_DIR / word
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{video_path.stem}_{ANGLE_TAG}.npy"

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
    print("이제 python ai/sign_recognition/train.py 로 재학습하면 됩니다.")


if __name__ == "__main__":
    main()
