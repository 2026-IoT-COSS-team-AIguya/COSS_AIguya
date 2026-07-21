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


def _merge_runs(raw_results: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """연속으로 같은 단어가 나오면 하나로 합친다(신뢰도는 더 높은 쪽 사용)."""
    results: list[tuple[str, float]] = []
    for word, conf in raw_results:
        if results and results[-1][0] == word:
            results[-1] = (word, max(results[-1][1], conf))
        else:
            results.append((word, conf))
    return results


def _predict_by_pause(kp: np.ndarray, min_conf: float = 0.6) -> list[tuple[str, float]]:
    """손 움직임이 멈추는 지점(단어 사이 pause)마다 나눠서 단어별로 예측."""
    segments = segment_words(kp)
    raw = []
    for start, end in segments:
        word, conf = _predict_segment(kp[start:end])
        if conf < min_conf:
            continue  # 단어 경계에서 동작이 섞인 노이즈 구간일 가능성이 큼
        raw.append((word, conf))
    return _merge_runs(raw)


def _predict_sliding(
    kp: np.ndarray, window: int = 55, stride: int = 12, min_conf: float = 0.55, min_run: int = 2
) -> list[tuple[str, float]]:
    """정지 구간이 없어서(자연스럽게 이어지는 수어) pause 기반 분리가 안 될 때
    쓰는 백업 방식. 멈춤을 찾는 대신 일정 길이(window)만큼 겹쳐가며(stride)
    영상을 훑어서 매 구간마다 "지금 이건 무슨 단어야?"를 계속 물어본다.

    같은 단어가 여러 윈도우에 걸쳐 연속으로 나오면 그 구간을 한 단어로 보고,
    winodw 몇 개 이상 연속되지 않으면(=min_run) 스쳐 지나가는 전환 노이즈로
    보고 버린다. pause 기반보다 전환 구간 오탐이 더 잦을 수 있다.
    """
    n = kp.shape[0]
    if n <= window:
        word, conf = _predict_segment(kp)
        return [(word, conf)] if conf >= min_conf else []

    window_preds = []
    for start in range(0, n - window + 1, stride):
        word, conf = _predict_segment(kp[start : start + window])
        window_preds.append((word, conf))
    # 마지막 프레임까지 확실히 덮도록 끝 윈도우 하나 추가
    word, conf = _predict_segment(kp[n - window :])
    window_preds.append((word, conf))

    # run-length: 같은 단어가 연속되는 구간을 하나의 후보로 묶음
    runs: list[tuple[str, float, int]] = []  # (word, best_conf, run_length)
    for word, conf in window_preds:
        if runs and runs[-1][0] == word:
            w, c, cnt = runs[-1]
            runs[-1] = (w, max(c, conf), cnt + 1)
        else:
            runs.append((word, conf, 1))

    return [(w, c) for w, c, cnt in runs if cnt >= min_run and c >= min_conf]


def predict_sequence(video_path: str) -> list[tuple[str, float]]:
    """한 영상 안에 여러 단어가 순서대로 사인된 경우, 순서대로 단어 리스트를
    예측한다 (버튼 한 번 = 여러 단어 연속 촬영을 위한 함수).

    predict()는 "영상 전체 = 단어 하나"라는 가정으로 top-k 후보를 주는
    반면, 이 함수는 여러 단어가 들어있다고 가정한다. 길이로 "단어 하나냐
    여러 개냐"를 미리 가르지 않고 항상 슬라이딩 윈도우로 처리한다 --
    단어 길이가 실제로는 60~177프레임까지 다양해서 고정 길이 기준으로는
    단어 하나/여러 개를 안정적으로 구분할 수 없었다(테스트로 확인).
    슬라이딩 윈도우는 진짜 단어 하나짜리 긴 영상(177프레임)도 알아서 하나로
    합쳐지고, 여러 단어가 이어진 영상도 정지 구간 없이 잘 나뉘었다.

    pause(정지 구간) 기반 분리(_predict_by_pause)는 실제 단어 안에서도
    준비/스트로크 사이에 미세하게 멈칫하는 순간이 있어서 같은 단어를 여러
    조각으로 쪼개는 경우가 잦아 기본값으로는 안 쓴다(디버깅용으로 남겨둠).
    """
    _load()

    kp = extract_keypoints_from_video(video_path)
    kp = normalize_sequence(kp)
    kp = trim_to_motion(kp)

    return _predict_sliding(kp)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python infer.py <영상경로.mp4>")
        raise SystemExit(1)

    results = predict_sequence(sys.argv[1])
    print("\nAI 인식 결과 (순서대로)")
    for i, (word, conf) in enumerate(results, 1):
        print(f"{i}. {word} {conf:.0%}")
