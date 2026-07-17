"""문장 영상 속 형태소 라벨 구간에서 특정 단어의 keypoint만 잘라내 캐싱한다.

AIHub 단어 영상(WORD####)에는 없는 단어(은행/카드/확인/만나다 등 28개)가,
문장 영상(SEN####) 데이터셋 안에는 "이 구간(몇 초~몇 초)은 이 단어다"라는
형태소 라벨(morpheme.json)로 이미 태깅되어 있다. ffmpeg로 영상을 물리적으로
자를 필요 없이, 그 구간만 cv2로 seek해서 keypoint를 뽑으면 된다.

주의: 형태소 라벨은 문장당 REAL01~REAL16(다른 수어사 16명) 촬영본이 다 있지만,
실제로 다운로드된 원본 영상은 REAL01뿐이다. 그래서 REAL01 라벨만 쓴다.

실행:
    conda activate coss
    python ai/sign_recognition/extract_sentence_clips.py
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from keypoints import FEATURE_DIM, N_HAND, N_POSE, _landmarks_to_array, _make_landmarker, normalize_sequence

SIGN_VIDEO_ROOT = Path(r"D:\수어 영상\1.Training")
MORPHEME_ZIP = SIGN_VIDEO_ROOT / "[라벨]01_real_sen_morpheme.zip"
VIDEO_ZIPS = [
    SIGN_VIDEO_ROOT / "[원천]01_real_sen_video.zip",
    SIGN_VIDEO_ROOT / "[원천]02_real_sen_video.zip",
]
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "sign_words_keypoints"

# 단어 영상(WORD) 데이터셋에 없어서 문장 영상 라벨로만 확보 가능한 단어들.
TARGET_WORDS = [
    "119", "1회", "경찰", "계단", "기다리다", "도움받다", "돈", "만나다", "무엇",
    "반갑다", "번호", "보다", "부르다", "신분증", "안내하다", "어디", "엘리베이터",
    "여기", "위험", "은행", "이름", "잠깐", "저기", "전화걸다", "차내리다", "카드",
    "학교", "확인",
]
# 단어당 최대 인스턴스 수 -- "저기"(1210개) 같은 흔한 단어가 학습을 지배하거나
# 추출 시간이 지나치게 길어지지 않도록 상한을 둔다.
MAX_PER_WORD = 20


def build_word_instances(target_words: set[str]) -> dict[str, list[dict]]:
    """형태소 라벨 zip 전체(REAL01만)를 스캔해서 단어별 (영상파일, 시작, 끝) 목록을 만든다."""
    instances: dict[str, list[dict]] = {w: [] for w in target_words}
    with zipfile.ZipFile(MORPHEME_ZIP) as zf:
        names = [n for n in zf.namelist() if "_REAL01_" in n and n.endswith("_morpheme.json")]
        for n in names:
            with zf.open(n) as f:
                data = json.load(f)
            mp4name = data.get("metaData", {}).get("name", "")
            for seg in data.get("data", []):
                attrs = seg.get("attributes") or []
                if not attrs:
                    continue
                w = attrs[0].get("name")
                if w in target_words and len(instances[w]) < MAX_PER_WORD * 3:
                    # 나중에 각도별로 고르게 뽑을 수 있도록 넉넉히(최대치의 3배) 모아둔다.
                    instances[w].append({"mp4": mp4name, "start": seg["start"], "end": seg["end"]})
    return instances


def build_video_zip_index() -> dict[str, tuple[Path, str]]:
    """mp4 파일명 -> (zip 경로, zip 내부 entry 이름)."""
    index = {}
    for zp in VIDEO_ZIPS:
        if not zp.exists():
            print(f"  [경고] zip 없음: {zp}")
            continue
        with zipfile.ZipFile(zp) as zf:
            for n in zf.namelist():
                if n.endswith(".mp4"):
                    index[Path(n).name] = (zp, n)
    return index


def extract_keypoints_from_segment(video_bytes: bytes, start: float, end: float) -> np.ndarray:
    """영상 바이트를 임시 파일로 써서 [start, end] 구간만 keypoint로 추출.

    landmarker는 클립마다 새로 만든다 -- detect_for_video는 같은 landmarker
    안에서 타임스탬프가 계속 단조증가해야 하는데, 서로 무관한 클립을 하나의
    landmarker로 이어 돌리면 클립이 바뀔 때 타임스탬프가 앞으로 되돌아가서
    "monotonically increasing" 에러가 난다(keypoints.py도 영상 하나당 landmarker
    하나를 새로 만드는 이유가 이것).
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    frames = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
        landmarker = _make_landmarker()
        try:
            frame_idx = 0
            while True:
                cur_sec = start + frame_idx / fps
                if cur_sec > end:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                result = landmarker.detect_for_video(mp_image, int(cur_sec * 1000))

                pose = _landmarks_to_array(result.pose_landmarks, N_POSE)
                left_hand = _landmarks_to_array(result.left_hand_landmarks, N_HAND)
                right_hand = _landmarks_to_array(result.right_hand_landmarks, N_HAND)
                frames.append(np.concatenate([pose, left_hand, right_hand], axis=0).reshape(-1))
                frame_idx += 1
        finally:
            landmarker.close()
            cap.release()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not frames:
        return np.zeros((1, FEATURE_DIM), dtype=np.float32)
    return np.stack(frames, axis=0)


def pick_diverse(instances: list[dict], n: int) -> list[dict]:
    """가능하면 여러 문장(sen_id)/각도가 섞이도록 균등 간격으로 n개를 고른다."""
    if len(instances) <= n:
        return instances
    step = len(instances) / n
    return [instances[int(i * step)] for i in range(n)]


def main():
    target_words = set(TARGET_WORDS)
    print("형태소 라벨(REAL01) 스캔 중...")
    instances_by_word = build_word_instances(target_words)
    for w, insts in instances_by_word.items():
        print(f"  {w}: {len(insts)}개 발견 (원본, 상한 적용 전)")

    print("\n문장 영상 zip 인덱싱 중...")
    video_index = build_video_zip_index()
    print(f"  {len(video_index)}개 영상 파일 인덱싱 완료")

    open_zips: dict[Path, zipfile.ZipFile] = {}

    def get_zip(path: Path) -> zipfile.ZipFile:
        if path not in open_zips:
            open_zips[path] = zipfile.ZipFile(path)
        return open_zips[path]

    n_ok, n_skip, n_missing_video = 0, 0, 0
    try:
        for word, instances in instances_by_word.items():
            selected = pick_diverse(instances, MAX_PER_WORD)
            out_dir = CACHE_DIR / word
            out_dir.mkdir(parents=True, exist_ok=True)

            for inst in selected:
                mp4name = inst["mp4"]
                match = video_index.get(mp4name)
                if match is None:
                    n_missing_video += 1
                    continue

                sen_tag = Path(mp4name).stem  # 예: NIA_SL_SEN0042_REAL01_D
                angle = sen_tag.split("_")[-1]
                out_path = out_dir / f"{word}_{sen_tag.split('_')[2]}_{angle}.npy"
                if out_path.exists():
                    n_skip += 1
                    continue

                zp, entry = match
                video_bytes = get_zip(zp).read(entry)
                kp = extract_keypoints_from_segment(video_bytes, inst["start"], inst["end"])
                kp = normalize_sequence(kp)
                np.save(out_path, kp)
                n_ok += 1

            print(f"  [OK] {word}: {len(selected)}개 처리")
    finally:
        for zf in open_zips.values():
            zf.close()

    print(f"\n완료: 새로 추출 {n_ok}, 이미 있어서 건너뜀 {n_skip}, 영상 못 찾음 {n_missing_video}")
    print(f"캐시 위치: {CACHE_DIR}")


if __name__ == "__main__":
    main()
