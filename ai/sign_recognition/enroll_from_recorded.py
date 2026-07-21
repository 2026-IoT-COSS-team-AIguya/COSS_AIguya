"""이미 촬영해둔 팀원 영상(ai/data/recorded/)으로 등록(enroll)한다.

enroll.py는 시연자가 새로 녹화한 영상이 있어야 하는데, 이번엔 실제 시연자가
이미 sign_recognition 학습용으로 촬영한 사람들(A/B/D) 중에 있어서, 새로 찍을
필요 없이 캐싱된 keypoint(.npy)를 그대로 재사용해서 등록 프로토타입을 만든다.

DEMO_PERSONS에 있는 사람만 쓰고(예: 시연 안 하는 C는 제외), AIHub 유래 데이터는
특정 시연자 것이 아니라서 등록에는 안 쓴다(학습에만 쓰였음).

기본적으로 등록 단어를 DEMO_SCENARIOS.md에서 농인이 실제로 사인하는(수어
인식 대상) 12개로 제한한다(ONLY_DEMO_WORDS=True). 병원 시나리오는 텍스트->
수어 전용이라 인식 대상이 아니라서 제외. 후보 단어 풀이 78개->12개로 줄면
그만큼 다른 단어와 헷갈릴 여지가 줄어서 top-1 정확도가 재학습 없이 바로
올라간다. 대신 이 12개 밖의 단어는 등록에서 아예 빠지므로 인식 요청이 와도
후보에 안 뜬다 -- 데모 스크립트 밖의 단어를 테스트하려면 ONLY_DEMO_WORDS=
False로 바꿀 것.

사용법:
    1. 아래 DEMO_PERSONS를 실제 시연자로 맞추기 (기본값: ["A", "B", "D"])
    2. conda activate coss && python ai/sign_recognition/enroll_from_recorded.py
    3. ai/models/enrolled_prototypes.npz 생성됨 -> infer.py에서 바로 씀
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from dataset import CACHE_DIR, augment
from model import SignEncoder
from train_front_only import scan_f_only_instances

DEMO_PERSONS = {"A", "B", "D"}

ONLY_DEMO_WORDS = True
DEMO_WORDS = {
    "친구", "놀다", "기대", "괜찮다", "기다리다",
    "은행", "대출", "알다", "잠깐", "죄송", "모르다", "감사", "어디",
}

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "sign_encoder.pt"
OUT_PATH = Path(__file__).resolve().parent.parent / "models" / "enrolled_prototypes.npz"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_model() -> SignEncoder:
    ckpt = torch.load(MODEL_PATH, map_location=DEVICE)
    model = SignEncoder().to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model


def main():
    instances = scan_f_only_instances()
    demo_instances = [(w, p, person) for w, p, person in instances if person in DEMO_PERSONS]
    if ONLY_DEMO_WORDS:
        demo_instances = [(w, p, person) for w, p, person in demo_instances if w in DEMO_WORDS]

    if not demo_instances:
        print(f"DEMO_PERSONS({DEMO_PERSONS})에 해당하는 촬영본이 없습니다. ai/data/recorded/ 확인 필요.")
        return

    print(f"등록 대상 인스턴스: {len(demo_instances)}개 (시연자: {sorted(DEMO_PERSONS)})")

    model = load_model()

    word_embeddings: dict[str, list[np.ndarray]] = {}
    with torch.no_grad():
        for word, path, person in demo_instances:
            seq = augment(np.load(path), train=False)
            x = torch.from_numpy(seq).unsqueeze(0).to(DEVICE)
            emb = model(x).cpu().numpy()[0]
            word_embeddings.setdefault(word, []).append(emb)

    words = sorted(word_embeddings.keys())
    protos = np.stack([np.mean(word_embeddings[w], axis=0) for w in words])
    protos = protos / np.linalg.norm(protos, axis=1, keepdims=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT_PATH, words=np.array(words), embeddings=protos)
    print(f"\n등록 완료: 단어 {len(words)}개 -> {OUT_PATH}")
    universe = DEMO_WORDS if ONLY_DEMO_WORDS else set(w for w, _, _ in instances)
    missing = sorted(universe - set(words))
    if missing:
        print(f"주의: 시연자 {sorted(DEMO_PERSONS)} 촬영본이 없는 단어 {len(missing)}개: {missing}")


if __name__ == "__main__":
    main()
