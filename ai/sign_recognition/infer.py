"""새 수어 영상(버튼 한 번 = 여러 단어 연속 촬영) -> 순서대로 인식된 단어 리스트.

슬라이딩 윈도우로 영상을 훑으면서 매 구간마다 등록된 단어 중 가장 가까운
것을 찾고, 같은 단어가 연속되면 하나로 합쳐서 최종 시퀀스를 만든다.

사용법:
  conda activate coss
  python ai/sign_recognition/infer.py <영상경로.mp4>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

from keypoints import extract_keypoints_from_video, normalize_sequence, trim_to_motion
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

    # 마지막 단어는 영상이 거기서 끝나버려서 뒤에서 확인해줄 윈도우가 없다
    # -- min_run(연속 등장 횟수) 조건을 그대로 적용하면 마지막 단어가 구조적으로
    # 불리해서 자주 통째로 버려진다(실제 테스트로 확인: 신뢰도 64%로 정확히
    # 잡혔는데 윈도우 1개뿐이라 버려짐). 그래서 마지막 run만 신뢰도만 통과하면
    # 인정한다.
    last_idx = len(runs) - 1
    return [
        (w, c)
        for i, (w, c, cnt) in enumerate(runs)
        if c >= min_conf and (cnt >= min_run or i == last_idx)
    ]


def predict_sequence(video_path: str) -> list[tuple[str, float]]:
    """한 영상 안에 여러 단어가 순서대로 사인된 경우, 순서대로 단어 리스트를
    예측한다 (버튼 한 번 = 여러 단어 연속 촬영을 위한 함수, 유일한 인식 경로).

    길이로 "단어 하나냐 여러 개냐"를 미리 가르지 않고 항상 슬라이딩 윈도우로
    처리한다 -- 단어 길이가 실제로는 60~177프레임까지 다양해서 고정 길이
    기준으로는 안정적으로 구분할 수 없었고(테스트로 확인), 정지 구간을 찾는
    방식은 한 단어 안에서도 미세하게 멈칫하는 순간을 새 단어 경계로 오인하는
    문제가 있었다. 슬라이딩 윈도우는 단어 하나짜리 긴 영상(177프레임)도
    하나로 합쳐지고, 정지 구간 없이 이어진 여러 단어도 정확히 분리됐다
    (실제 3단어 연속 촬영 테스트로 검증: 감사 92%, 은행 82%, 친구 90%).
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
