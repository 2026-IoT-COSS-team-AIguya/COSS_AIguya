"""백엔드가 부를 AI 진입점 -- sign_recognition/sentence_generation/text_to_sign을
하나로 묶어서, 백엔드 인수인계 문서(잇손_백엔드_AI_oneM2M_인수인계.md 19.3, 21번
섹션)가 원하는 JSON 형태 그대로 반환한다.

백엔드(Django)가 아직 없어도 이 함수 시그니처만 보고 나중에 바로 연결할 수 있게
만든 것 -- Django 쪽에서는 이 함수들을 그대로 호출하고, 반환된 dict를 각자의
모델(SignRecognition/RecognitionKeyword/SentenceCandidate/SignVideo)에 맞게
저장하면 된다.

주의: video_url이 아니라 video_path를 준다. URL로 바꾸는 것(MEDIA_URL 접두사
붙이기 등)은 Django가 할 일이라 여기서는 로컬 파일 경로만 준다.

실행:
    conda activate coss
    python ai/pipeline/recognize.py predict <영상경로.mp4>
    python ai/pipeline/recognize.py search 은행 카드 잠깐
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_SIGN_RECOGNITION = Path(__file__).resolve().parent.parent / "sign_recognition"
_SENTENCE_GENERATION = Path(__file__).resolve().parent.parent / "sentence_generation"
_TEXT_TO_SIGN = Path(__file__).resolve().parent.parent / "text_to_sign"
for _p in (_SIGN_RECOGNITION, _SENTENCE_GENERATION, _TEXT_TO_SIGN):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# sign_encoder.pt를 재학습해서 갈아끼울 때마다 이 값도 같이 올려주면, 백엔드
# DB(SignRecognition.model_version)에 어떤 모델이 처리했는지 기록이 남는다.
MODEL_VERSION = "keypoint-sign-encoder-v1"


def predict_sign_from_video(video_path: str, top_k: int = 3, n_sentences: int = 3) -> dict:
    """영상 하나(버튼 한 번으로 여러 단어를 연속 촬영) -> 순서대로 인식된
    키워드들 + 문장 후보 (수어사용자 -> 일반인 방향).

    영상 안에서 손 움직임이 멈추는 지점(단어 사이 pause)마다 나눠서 단어별로
    하나씩 예측한다(infer.predict_sequence) -- top_k는 더 이상 "후보 개수"가
    아니라 감지된 단어 수가 곧 키워드 개수가 된다(인수인계 문서 11.6/16.2
    예시: "화장실"+"어디"처럼 서로 다른 단어 여러 개가 keywords에 담김).

    주의: infer 모듈은 ai/models/enrolled_prototypes.npz(enroll.py로 생성)가
    있어야 동작한다. 아직 시연자 등록 전이면 여기서 FileNotFoundError가 난다.
    """
    t0 = time.time()

    import infer

    top_words = infer.predict_sequence(video_path)  # [(word, confidence), ...] 시간 순

    # 문장 생성(LLM)은 키워드 인식과 별개 단계다 -- LLM 호출이 실패해도(쿼터
    # 초과, 네트워크 문제, SSL 등) 이미 성공한 키워드 인식 결과까지 버리지
    # 않고, 문장 후보만 빈 채로 돌려준다.
    try:
        import generate_sentence

        sentences = generate_sentence.generate_sentence_candidates([list(top_words)], n=n_sentences)
    except Exception as e:
        print(f"[recognize] 문장 생성 실패(키워드는 정상 반환): {e}")
        sentences = []

    processing_ms = int((time.time() - t0) * 1000)

    return {
        "keywords": [
            {"keyword": w, "confidence": round(c, 4), "order": i}
            for i, (w, c) in enumerate(top_words, 1)
        ],
        "sentence_candidates": [{"sentence": s, "score": None} for s in sentences],
        "model_version": MODEL_VERSION,
        "processing_ms": processing_ms,
    }


def search_sign_video(keyword: str) -> dict:
    """단일 키워드 -> 수어 영상 정보 (일반인 -> 수어사용자, 단일 검색)."""
    import lookup

    path = lookup.find_clip(keyword)
    return {"keyword": keyword, "video_path": str(path) if path else None}


def build_sign_sequence(keywords: list[str]) -> dict:
    """키워드 리스트 -> 수어 영상 시퀀스 (일반인 -> 수어사용자, 카드 여러 개)."""
    import lookup

    items = []
    missing = []
    for i, kw in enumerate(keywords, 1):
        path = lookup.find_clip(kw)
        if path is None:
            missing.append(kw)
        else:
            items.append({"order": i, "keyword": kw, "video_path": str(path)})
    return {"items": items, "missing_keywords": missing}


def sign_sequence_from_sentence(sentence: str) -> dict:
    """자유 문장 -> 키워드 추출 -> 수어 영상 시퀀스 (일반인 -> 수어사용자 전체 흐름)."""
    import extract_keywords

    keywords = extract_keywords.extract_keywords(sentence)
    result = build_sign_sequence(keywords)
    result["source_sentence"] = sentence
    return result


if __name__ == "__main__":
    import json

    args = sys.argv[1:]
    if not args:
        print("사용법:")
        print("  python recognize.py predict <영상경로.mp4>")
        print("  python recognize.py search <단어1> <단어2> ...")
        print("  python recognize.py sentence <문장>")
        raise SystemExit(1)

    cmd, *rest = args
    if cmd == "predict":
        out = predict_sign_from_video(rest[0])
    elif cmd == "search":
        out = build_sign_sequence(rest)
    elif cmd == "sentence":
        out = sign_sequence_from_sentence(" ".join(rest))
    else:
        print(f"알 수 없는 명령: {cmd}")
        raise SystemExit(1)

    print(json.dumps(out, ensure_ascii=False, indent=2))
