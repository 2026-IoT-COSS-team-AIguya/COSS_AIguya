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

from keypoints import extract_keypoints_from_video, normalize_sequence
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python infer.py <영상경로.mp4>")
        raise SystemExit(1)

    results = predict(sys.argv[1])
    print("\nAI 인식 결과")
    for i, (word, conf) in enumerate(results, 1):
        print(f"{i}. {word} {conf:.0%}")
