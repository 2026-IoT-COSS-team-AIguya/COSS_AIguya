"""이미 촬영해둔 팀원 영상(ai/data/recorded/)으로 등록(enroll)한다.

enroll.py는 시연자가 새로 녹화한 영상이 있어야 하는데, 이번엔 실제 시연자가
이미 sign_recognition 학습용으로 촬영한 사람들(A/B/D) 중에 있어서, 새로 찍을
필요 없이 캐싱된 keypoint(.npy)를 그대로 재사용해서 등록 프로토타입을 만든다.

DEMO_PERSONS에 있는 사람만 쓰고(예: 시연 안 하는 C는 제외), AIHub 유래 데이터는
특정 시연자 것이 아니라서 등록에는 안 쓴다(학습에만 쓰였음).

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
    missing = sorted(set(w for w, _, _ in instances) - set(words))
    if missing:
        print(f"주의: 시연자 {sorted(DEMO_PERSONS)} 촬영본이 없는 단어 {len(missing)}개: {missing}")


if __name__ == "__main__":
    main()
