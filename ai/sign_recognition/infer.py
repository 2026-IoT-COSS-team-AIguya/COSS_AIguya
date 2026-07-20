"""새 수어 영상 -> 등록된 단어 중 가장 가까운 후보 Top-K 반환.

손말이음 앱의 "AI 인식 결과: 1.오늘 92% / 2.지금 74% / 3.내일 61%" 화면이 바로 이거다.

사용법:
  conda activate coss
  python ai/sign_recognition/infer.py <영상경로.mp4>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

from keypoints import extract_keypoints_from_video, normalize_sequence, segment_words, trim_to_motion
from dataset import augment
from model import SignEncoder

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "sign_encoder.pt"
PROTOTYPES_PATH = Path(__file__).resolve().parent.parent / "models" / "enrolled_prototypes.npz"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model: SignEncoder | None = None
_proto_words: np.ndarray | None = None
_proto_embeddings: np.ndarray | None = None


def _load():
    global _model, _proto_words, _proto_embeddings
    if _model is not None:
        return
    ckpt = torch.load(MODEL_PATH, map_location=DEVICE)
    _model = SignEncoder().to(DEVICE)
    _model.load_state_dict(ckpt["model_state"])
    _model.eval()

    data = np.load(PROTOTYPES_PATH, allow_pickle=True)
    _proto_words = data["words"]
    _proto_embeddings = data["embeddings"]


def predict(video_path: str, top_k: int = 3) -> list[tuple[str, float]]:
    """(단어, 확신도 0~1) 리스트를 유사도 높은 순으로 top_k개 반환.
    확신도는 코사인 유사도를 softmax로 정규화한 값 (실제 확률은 아니고 상대적 확신도)."""
    _load()

    kp = extract_keypoints_from_video(video_path)
    kp = normalize_sequence(kp)
    kp = trim_to_motion(kp)  # 실촬영본의 대기시간(정지 구간)이 리샘플을 희석시키는 것 방지
    kp = augment(kp, train=False)

    with torch.no_grad():
        x = torch.from_numpy(kp).unsqueeze(0).to(DEVICE)
        emb = _model(x).cpu().numpy()[0]

    sims = _proto_embeddings @ emb  # 코사인 유사도 (둘 다 정규화되어 있음)
    # softmax로 상대적 확신도 변환 (temperature로 날카로움 조절)
    temperature = 0.1
    logits = sims / temperature
    probs = np.exp(logits - logits.max())
    probs = probs / probs.sum()

    order = np.argsort(-probs)[:top_k]
    return [(str(_proto_words[i]), float(probs[i])) for i in order]


def _predict_segment(kp_segment: np.ndarray) -> tuple[str, float]:
    seq = augment(kp_segment, train=False)
    with torch.no_grad():
        x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
        emb = _model(x).cpu().numpy()[0]
    sims = _proto_embeddings @ emb
    temperature = 0.1
    logits = sims / temperature
    probs = np.exp(logits - logits.max())
    probs = probs / probs.sum()
    best = int(np.argmax(probs))
    return str(_proto_words[best]), float(probs[best])


def predict_sequence(video_path: str) -> list[tuple[str, float]]:
    """한 영상 안에 여러 단어가 순서대로 사인된 경우, 움직임이 멈추는
    지점(단어 사이 pause)마다 나눠서 단어별로 하나씩 예측한다.

    predict()는 "영상 전체 = 단어 하나"라는 가정으로 top-k 후보를 주는
    반면, 이 함수는 영상 하나에 여러 단어가 연달아 들어있는 실제 라즈베리
    파이 촬영(버튼 한 번 = 여러 단어 연속)을 위한 것. 반환값은 영상에 나온
    순서대로 (단어, 확신도) 리스트 -- 단어 개수가 세그먼트 개수만큼 나온다.
    """
    _load()

    kp = extract_keypoints_from_video(video_path)
    kp = normalize_sequence(kp)
    kp = trim_to_motion(kp)

    MIN_SEGMENT_CONF = 0.6  # 단어 경계에서 동작이 섞여 애매하게 나오는 조각 필터링용

    segments = segment_words(kp)
    raw_results = []
    for start, end in segments:
        word, conf = _predict_segment(kp[start:end])
        if conf < MIN_SEGMENT_CONF:
            continue  # 실제 단어 사이 전환 구간이 섞여 들어온 노이즈일 가능성이 큼
        raw_results.append((word, conf))

    # 한 단어 동작 안에서도 준비/스트로크 사이에 미세하게 멈칫하는 순간이
    # 있어서, segment_words가 같은 단어를 여러 조각으로 쪼갤 때가 있다.
    # 연속으로 같은 단어가 나오면 하나로 합친다(신뢰도는 더 높은 쪽 사용).
    results: list[tuple[str, float]] = []
    for word, conf in raw_results:
        if results and results[-1][0] == word:
            results[-1] = (word, max(results[-1][1], conf))
        else:
            results.append((word, conf))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python infer.py <영상경로.mp4>")
        raise SystemExit(1)

    results = predict_sequence(sys.argv[1])
    print("\nAI 인식 결과 (순서대로)")
    for i, (word, conf) in enumerate(results, 1):
        print(f"{i}. {word} {conf:.0%}")
