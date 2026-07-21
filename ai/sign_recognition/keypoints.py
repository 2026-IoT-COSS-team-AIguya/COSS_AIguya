"""영상 -> 프레임별 keypoint 시퀀스 추출.

수어 인식에는 얼굴 468개 랜드마크까지는 필요 없고, 상체 자세(포즈) + 양손 모양이면
충분하다는 게 정설이라 MediaPipe HolisticLandmarker에서 pose(33) + 왼손(21) +
오른손(21) = 75개 포인트 * (x, y, z) = 225차원 벡터를 프레임마다 뽑는다.

한 영상 -> shape (num_frames, 225) numpy 배열.

MediaPipe 0.10.30+ 부터 예전 mp.solutions API가 제거되고 Tasks API로 바뀌었으므로,
반드시 아래처럼 .task 모델 번들을 받아서 HolisticLandmarker를 써야 한다.
모델 파일: ai/models/mediapipe/holistic_landmarker.task
  (없으면 prepare_data.py 안내 또는 README 참고해서 다시 받을 것)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions

N_POSE = 33
N_HAND = 21
FEATURE_DIM = (N_POSE + N_HAND + N_HAND) * 3  # 225

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "mediapipe" / "holistic_landmarker.task"


def _make_landmarker(running_mode=mp_vision.RunningMode.VIDEO) -> mp_vision.HolisticLandmarker:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"MediaPipe 모델이 없습니다: {MODEL_PATH}\n"
            "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/"
            "holistic_landmarker/float16/latest/holistic_landmarker.task 를 받아서 저장하세요."
        )
    options = mp_vision.HolisticLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=running_mode,
        min_pose_detection_confidence=0.5,
        min_hand_landmarks_confidence=0.3,
    )
    return mp_vision.HolisticLandmarker.create_from_options(options)


def _landmarks_to_array(landmarks, n_points: int) -> np.ndarray:
    if not landmarks:
        return np.zeros((n_points, 3), dtype=np.float32)
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)
    if pts.shape[0] != n_points:  # 방어적 처리 (드물게 개수 불일치)
        fixed = np.zeros((n_points, 3), dtype=np.float32)
        fixed[: min(n_points, pts.shape[0])] = pts[: min(n_points, pts.shape[0])]
        return fixed
    return pts


def extract_keypoints_from_video(video_path: str, max_frames: int | None = None) -> np.ndarray:
    """비디오 파일 경로를 받아 (T, 225) keypoint 시퀀스를 반환한다."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []

    landmarker = _make_landmarker()
    try:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int((frame_idx / fps) * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            pose = _landmarks_to_array(result.pose_landmarks, N_POSE)
            left_hand = _landmarks_to_array(result.left_hand_landmarks, N_HAND)
            right_hand = _landmarks_to_array(result.right_hand_landmarks, N_HAND)

            frame_vec = np.concatenate([pose, left_hand, right_hand], axis=0).reshape(-1)
            frames.append(frame_vec)

            frame_idx += 1
            if max_frames and len(frames) >= max_frames:
                break
    finally:
        landmarker.close()
        cap.release()

    if not frames:
        return np.zeros((1, FEATURE_DIM), dtype=np.float32)
    return np.stack(frames, axis=0)


def trim_to_motion(seq: np.ndarray, pad: int = 5, motion_frac: float = 0.05) -> np.ndarray:
    """손 움직임이 없는 앞/뒤 대기 구간을 잘라내고 실제 동작 구간만 남긴다.

    라즈베리파이 실촬영본은 촬영 시작~수어 시작 사이 대기 시간이 길어서(예:
    8초짜리 영상 중 앞 5초가 완전히 정지 상태), FIXED_LEN=64로 균등
    리샘플하면 실제 수어 동작이 극히 일부 프레임에만 눌려 담겨 인식률이
    크게 떨어진다. 학습 데이터는 이미 트리밍돼 있어서 이 함수를 거쳐도
    거의 그대로 남는다(무해).
    """
    if seq.shape[0] < 20:
        return seq
    hands = seq.reshape(seq.shape[0], -1, 3)[:, N_POSE:].reshape(seq.shape[0], -1)
    velocity = np.linalg.norm(np.diff(hands, axis=0), axis=1)
    if velocity.max() < 1e-6:
        return seq
    threshold = velocity.max() * motion_frac
    motion_idx = np.where(velocity > threshold)[0]
    if len(motion_idx) == 0:
        return seq
    start = max(0, int(motion_idx[0]) - pad)
    end = min(seq.shape[0], int(motion_idx[-1]) + pad + 2)
    if end - start < 10:
        return seq
    return seq[start:end]


def normalize_sequence(seq: np.ndarray) -> np.ndarray:
    """어깨 중심을 원점으로, 어깨너비로 스케일 정규화 -> 사람의 위치/체격 차이를 지운다.
    pose landmark 11 = 왼쪽 어깨, 12 = 오른쪽 어깨 (MediaPipe pose 인덱스 기준).
    """
    seq = seq.reshape(seq.shape[0], -1, 3).copy()
    left_shoulder = seq[:, 11, :2]
    right_shoulder = seq[:, 12, :2]
    center = (left_shoulder + right_shoulder) / 2
    shoulder_width = np.linalg.norm(right_shoulder - left_shoulder, axis=1, keepdims=True)
    shoulder_width = np.clip(shoulder_width, 1e-4, None)

    seq[:, :, 0] = (seq[:, :, 0] - center[:, 0:1]) / shoulder_width
    seq[:, :, 1] = (seq[:, :, 1] - center[:, 1:2]) / shoulder_width
    return seq.reshape(seq.shape[0], -1)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("사용법: python keypoints.py <영상경로.mp4>")
        raise SystemExit(1)
    kp = extract_keypoints_from_video(path)
    kp = normalize_sequence(kp)
    print(f"{Path(path).name}: keypoints shape = {kp.shape}")
    print(f"프레임당 손 인식 안 된 비율(왼손): {(kp.reshape(kp.shape[0], -1, 3)[:, 33:54].sum(-1) == 0).mean():.1%}")
