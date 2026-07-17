"""문장 영상 형태소 라벨 구간에서 실제 mp4 참고 클립을 잘라낸다.

extract_sentence_clips.py는 keypoint만 뽑고 mp4는 저장 안 하기 때문에, 그 28개
단어(은행/카드/확인 등)가 실제로 어떤 동작인지 눈으로 볼 방법이 없다. 직접
촬영하기 전에 참고할 수 있도록, 단어당 몇 개씩 실제 영상을 잘라서 저장한다.

ffmpeg 없이 cv2로 프레임을 그대로 읽어서 VideoWriter로 다시 쓴다(재인코딩이라
화질이 살짝 떨어질 순 있지만 참고용이라 문제없음).

실행:
    conda activate coss
    python ai/sign_recognition/make_reference_clips.py
"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import cv2

from extract_sentence_clips import (
    TARGET_WORDS,
    build_video_zip_index,
    build_word_instances,
    pick_diverse,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "reference_clips"
CLIPS_PER_WORD = 2
PADDING_SEC = 0.2  # 구간 앞뒤로 살짝 여유를 둬서 잘린 느낌 줄이기


def crop_clip(video_bytes: bytes, start: float, end: float, out_path: Path) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    ok_written = False
    try:
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        seek = max(0.0, start - PADDING_SEC)
        end_padded = end + PADDING_SEC
        cap.set(cv2.CAP_PROP_POS_MSEC, seek * 1000)

        writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        try:
            frame_idx = 0
            while True:
                cur_sec = seek + frame_idx / fps
                if cur_sec > end_padded:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                writer.write(frame)
                ok_written = True
                frame_idx += 1
        finally:
            writer.release()
            cap.release()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not ok_written:
        out_path.unlink(missing_ok=True)
    return ok_written


def main():
    target_words = set(TARGET_WORDS)
    print("형태소 라벨(REAL01) 스캔 중...")
    instances_by_word = build_word_instances(target_words)

    print("문장 영상 zip 인덱싱 중...")
    video_index = build_video_zip_index()

    open_zips: dict[Path, zipfile.ZipFile] = {}

    def get_zip(path: Path) -> zipfile.ZipFile:
        if path not in open_zips:
            open_zips[path] = zipfile.ZipFile(path)
        return open_zips[path]

    n_ok, n_missing = 0, 0
    try:
        for word, instances in instances_by_word.items():
            selected = pick_diverse(instances, CLIPS_PER_WORD)
            out_dir = OUT_DIR / word
            out_dir.mkdir(parents=True, exist_ok=True)

            for i, inst in enumerate(selected, 1):
                match = video_index.get(inst["mp4"])
                if match is None:
                    n_missing += 1
                    continue
                out_path = out_dir / f"{word}_ref{i}.mp4"
                if out_path.exists():
                    n_ok += 1
                    continue
                zp, entry = match
                video_bytes = get_zip(zp).read(entry)
                if crop_clip(video_bytes, inst["start"], inst["end"], out_path):
                    n_ok += 1
                    print(f"  [OK] {out_path}")
                else:
                    n_missing += 1
    finally:
        for zf in open_zips.values():
            zf.close()

    print(f"\n완료: {n_ok}개 저장, {n_missing}개 실패/누락")
    print(f"저장 위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
