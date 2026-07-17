"""단어 -> 보여줄 수어 영상 클립 경로를 찾는다.

우선순위: 단어 영상 DB 정면(sign_words) > 문장영상에서 자른 참고 클립
(reference_clips) > 직접 촬영본(recorded). AIHub 영상은 전문 수어사가 찍은
정확한 수어라 농인 사용자에게 보여주는 용도로 우선하고, 팀원이 직접 찍은
recorded 영상은 (수어 전공자가 아닌 이상) 정확도를 보장 못 하므로 그 단어가
AIHub에 아예 없을 때만 최후의 수단으로 쓴다. (recorded 영상은 어차피
sign_recognition 학습용이 원래 목적이고, 여기선 보여주기용 fallback일 뿐.)

실행:
    conda activate coss
    python ai/text_to_sign/lookup.py 은행 카드 잠깐
"""
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECORDED_DIR = DATA_DIR / "recorded"
SIGN_WORDS_DIR = DATA_DIR / "sign_words"
REFERENCE_CLIPS_DIR = DATA_DIR / "reference_clips"


def find_clip(word: str) -> Path | None:
    """word에 해당하는 영상 파일 하나를 찾아 반환. 없으면 None."""
    front = SIGN_WORDS_DIR / word / f"{word}_F.mp4"
    if front.exists():
        return front

    ref_dir = REFERENCE_CLIPS_DIR / word
    if ref_dir.exists():
        ref = sorted(ref_dir.glob("*_ref1.mp4"))
        if ref:
            return ref[0]

    # AIHub(전문 수어사)에 아예 없는 단어일 때만 팀원 촬영본을 최후의 수단으로 사용.
    recorded_dir = RECORDED_DIR / word
    if recorded_dir.exists():
        recorded = sorted(recorded_dir.glob("*.mp4"))
        if recorded:
            return recorded[0]

    return None


def find_all_clips(words: list[str]) -> dict[str, Path | None]:
    return {w: find_clip(w) for w in words}


if __name__ == "__main__":
    import sys

    words = sys.argv[1:]
    if not words:
        print("사용법: python lookup.py 단어1 단어2 ...")
        raise SystemExit(1)
    for w, p in find_all_clips(words).items():
        print(f"{w}: {p if p else '[영상 없음]'}")
