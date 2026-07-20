"""데이터 준비: AIHub 수어 영상 zip에서 데모에 쓰는 단어들의 5개 각도 영상을 전부
ai/data/sign_words/{단어}/{단어}_{각도}.mp4 로 뽑아온다.

실행:
    conda activate coss
    python ai/sign_recognition/prepare_data.py
"""
import zipfile
import re
import json
from pathlib import Path

# ── 경로 설정 (팀원 PC마다 다르면 여기만 고치면 됨) ─────────────────────────
SIGN_VIDEO_ROOT = Path(r"D:\수어 영상\1.Training")
WORD_ZIPS = [
    SIGN_VIDEO_ROOT / "[원천]01_real_word_video.zip",  # id 1501~3000
    SIGN_VIDEO_ROOT / "[원천]02_real_word_video.zip",  # id 0001~1500
]
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words"
ANGLES = ["D", "F", "L", "R", "U"]

# 손말이음 데모 시나리오에서 실제로 쓰는 단어 전부 (최초 21개 + 이후 확장분).
# id는 실행 중 word list에서 자동으로 찾으므로 텍스트만 있으면 됨.
TARGET_WORDS = [
    "괜찮다", "가다", "빨리", "기대", "놀다", "신나다", "대박", "좋다", "친구",
    "모르다", "오른쪽", "왼쪽", "가깝다", "알다", "감사",
    "대기", "직원", "대출",
    "병원", "오다", "의사",
    # 신규 데모 시나리오 4종(가족 채팅/재난경보/은행 번역/첫만남 번역) 확장분.
    # 단어DB(word_id_map.json)에 있는 것만 여기 추가 -- 문장영상 라벨에만 있는
    # 단어(만나다/반갑다/은행/카드 등 28개)는 extract_sentence_clips.py가 처리.
    "가족", "걱정", "건강", "그립다", "누나", "딸", "생일", "엄마", "오빠",
    "일어나다", "자다", "축하", "할머니", "할아버지", "행복", "형",
    "가능", "구조", "쓰러지다", "홍수",
    "맞다", "받다", "얼마",
    "나이", "소개", "일", "전화번호", "죄송", "회사",
    # 병원 예약 시나리오 확장분 (2026-07-21).
    "검사", "아프다", "통증", "입원", "퇴원", "간호사", "치료", "상담",
    "월요일", "화요일", "수요일", "금요일", "일요일",
]


def load_word_ids(zips):
    """WORD id -> 단어 텍스트는 morpheme 라벨에 있지만, 여기서는 영상 zip 안의
    파일명(WORD####)만 필요하므로 별도 morpheme.zip 없이도 동작하게, 이미 알고
    있는 단어->id 매핑을 하드코딩 대신 sign_data.json에서 불러온다."""
    sign_data_path = Path(__file__).resolve().parent / "word_id_map.json"
    with open(sign_data_path, encoding="utf-8") as f:
        return json.load(f)


def build_video_index(zip_paths):
    """{(word_id, angle): (zip_path, entry_name)}"""
    idx = {}
    pat = re.compile(r"WORD(\d+)_REAL\d+_(\w)\.mp4$")
    for zp in zip_paths:
        if not zp.exists():
            print(f"  [경고] zip 없음: {zp}")
            continue
        with zipfile.ZipFile(zp) as zf:
            for n in zf.namelist():
                m = pat.search(n)
                if m:
                    idx[(m.group(1), m.group(2))] = (zp, n)
    return idx


def main():
    word_to_id = load_word_ids(WORD_ZIPS)
    print(f"단어 사전 로드: {len(word_to_id)}개")

    print("영상 zip 인덱싱 중...")
    index = build_video_index(WORD_ZIPS)
    print(f"  (id, 각도) {len(index)}개 인덱싱 완료")

    open_zips = {}

    def get_zip(path):
        if path not in open_zips:
            open_zips[path] = zipfile.ZipFile(path)
        return open_zips[path]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_ok, n_missing = 0, 0
    for word in TARGET_WORDS:
        wid = word_to_id.get(word)
        if wid is None:
            print(f"  [MISSING] 단어 사전에 없음: {word}")
            continue
        word_dir = OUT_DIR / word
        word_dir.mkdir(exist_ok=True)
        for angle in ANGLES:
            match = index.get((wid, angle))
            if match is None:
                print(f"  [MISSING] {word}({wid}) 각도 {angle}")
                n_missing += 1
                continue
            zp, entry = match
            out_path = word_dir / f"{word}_{angle}.mp4"
            if out_path.exists():
                n_ok += 1
                continue
            data = get_zip(zp).read(entry)
            out_path.write_bytes(data)
            n_ok += 1
        print(f"  [OK] {word} (id {wid}) -> {word_dir}")

    for zf in open_zips.values():
        zf.close()

    print(f"\n완료: 성공 {n_ok}, 누락 {n_missing}")
    print(f"출력 위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
