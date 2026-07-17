"""실제 시연자가 녹화한 영상으로 '기준(레퍼런스) 임베딩'을 등록한다.

AIHub 데이터로 학습한 인코더는 "손동작을 비교하는 눈"만 만든 것이고, 실제 매칭
기준은 여기서 시연자 본인이 등록한 영상이 된다 (얼굴인식 앱의 '내 얼굴 등록'과
같은 개념).

사용법:
  1. ai/data/enrolled/ 폴더에 단어별로 영상을 넣는다.
     예) ai/data/enrolled/오늘.mp4, ai/data/enrolled/오늘_2.mp4 (여러 개면 평균)
  2. conda activate coss && python ai/sign_recognition/enroll.py
  3. ai/models/enrolled_prototypes.npz 가 생성되면 infer.py에서 바로 씀
"""
from pathlib import Path

import numpy as np
import torch

from keypoints import extract_keypoints_from_video, normalize_sequence
from dataset import augment
from model import SignEncoder

ENROLL_DIR = Path(__file__).resolve().parent.parent / "data" / "enrolled"
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
    if not ENROLL_DIR.exists() or not any(ENROLL_DIR.glob("*.mp4")):
        print(f"{ENROLL_DIR} 에 등록할 영상(mp4)이 없습니다.")
        print("파일명은 '단어.mp4' 또는 '단어_1.mp4', '단어_2.mp4' 형식으로 넣어주세요.")
        return

    model = load_model()

    # 단어별로 여러 테이크가 있으면 임베딩을 평균내서 대표 프로토타입으로 사용
    word_embeddings: dict[str, list[np.ndarray]] = {}

    for video_path in sorted(ENROLL_DIR.glob("*.mp4")):
        word = video_path.stem.split("_")[0]  # "오늘_2.mp4" -> "오늘"
        print(f"  처리 중: {video_path.name} (단어: {word})")
        kp = extract_keypoints_from_video(str(video_path))
        kp = normalize_sequence(kp)
        kp = augment(kp, train=False)  # train=False -> 길이만 맞추고 노이즈 없음
        with torch.no_grad():
            x = torch.from_numpy(kp).unsqueeze(0).to(DEVICE)
            emb = model(x).cpu().numpy()[0]
        word_embeddings.setdefault(word, []).append(emb)

    words = sorted(word_embeddings.keys())
    protos = np.stack([np.mean(word_embeddings[w], axis=0) for w in words])
    protos = protos / np.linalg.norm(protos, axis=1, keepdims=True)  # 재정규화

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT_PATH, words=np.array(words), embeddings=protos)
    print(f"\n등록 완료: 단어 {len(words)}개 -> {OUT_PATH}")
    print("등록된 단어:", ", ".join(words))


if __name__ == "__main__":
    main()
