"""영상 -> VideoMAE 입력 형식(16프레임, 224x224, ImageNet 정규화)으로 변환.

MediaPipe keypoint 대신 원본 RGB 프레임을 그대로 사전학습된 VideoMAE에 태우는
방식. VideoMAE가 이미 Kinetics-400 대규모 영상으로 "동작을 이해하는 법"을 배워
놨기 때문에, 우리 21개 단어 데이터는 그 지식을 우리 문제에 맞게 미세조정하는
용도로만 쓰면 된다 (그래서 84개 샘플로도 말이 되는 학습이 가능하다).
"""
from __future__ import annotations

import numpy as np
import cv2
import torch
from transformers import VideoMAEImageProcessor

NUM_FRAMES = 16

_processor = VideoMAEImageProcessor.from_pretrained("MCG-NJU/videomae-base")


def sample_frames(video_path: str, num_frames: int = NUM_FRAMES, jitter: bool = False) -> list[np.ndarray]:
    """영상에서 num_frames장을 균등 간격으로 샘플링.
    jitter=True면 매번 살짝 다른 시작점/간격으로 뽑아서 데이터 증강 효과를 준다.

    이전엔 영상 전체를 프레임 리스트로 다 읽어놓고 그중 16장만 골라 썼는데,
    1080p 영상은 프레임당 ~6MB라 영상 하나(수백 프레임)를 통째로 메모리에
    올리면 DataLoader 워커 여러 개가 동시에 돌 때 시스템 메모리가 바닥나서
    ArrayMemoryError로 죽었다. 필요한 프레임 위치로 직접 seek해서 그 프레임만
    디코딩하면 메모리 사용량이 16장 분량으로 끝난다.
    """
    cap = cv2.VideoCapture(str(video_path))
    t = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if t <= 0:
        cap.release()
        raise RuntimeError(f"프레임 수를 읽을 수 없습니다: {video_path}")

    if t <= num_frames:
        idx = np.linspace(0, t - 1, num_frames).round().astype(int)
    elif jitter:
        # 전체 구간의 80~100%만 랜덤하게 써서 균등 샘플링 (time-warp 증강)
        keep_ratio = np.random.uniform(0.8, 1.0)
        end = max(num_frames, int(t * keep_ratio))
        start = np.random.randint(0, t - end + 1)
        idx = np.linspace(start, start + end - 1, num_frames).round().astype(int)
    else:
        idx = np.linspace(0, t - 1, num_frames).round().astype(int)

    frames = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if not ok:
            # 코덱에 따라 정확한 seek이 안 될 때가 있어 한 프레임 전에서 재시도
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(i) - 1))
            ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError(f"{i}번 프레임을 읽을 수 없습니다: {video_path}")
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


def frames_to_tensor(frames: list[np.ndarray]) -> torch.Tensor:
    """VideoMAEImageProcessor로 리사이즈+정규화 -> [num_frames, 3, 224, 224] 텐서."""
    processed = _processor(list(frames), return_tensors="pt")
    return processed["pixel_values"][0]  # [T, 3, 224, 224]


def load_video_as_tensor(video_path: str, jitter: bool = False) -> torch.Tensor:
    frames = sample_frames(video_path, jitter=jitter)
    return frames_to_tensor(frames)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("사용법: python video_frames.py <영상경로.mp4>")
        raise SystemExit(1)
    t = load_video_as_tensor(path)
    print("tensor shape:", t.shape, "min/max:", t.min().item(), t.max().item())
