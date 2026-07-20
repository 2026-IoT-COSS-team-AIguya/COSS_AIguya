"""브라우저(Chrome)가 재생 못 하는 코덱으로 저장된 영상을 H.264로 재인코딩한다.

배경: reference_clips는 mpeg4(구형 코덱), recorded는 대부분 hevc(H.265)로
저장돼 있어서 <video> 태그에서 검은 화면 + 0:00으로 나오는 문제가 있었다
(sign_words는 이미 h264라 문제 없음). ffprobe로 코덱을 확인해서 h264가
아닌 파일만 골라 libx264로 재인코딩(-pix_fmt yuv420p -movflags +faststart)한다.

기본은 검사 대상을 lookup.find_clip()이 실제로 반환하는 파일로만 좁힌다
(전체 recorded 624개를 다 인코딩할 필요는 없음 -- 어차피 sign_words/
reference_clips가 있으면 recorded는 안 쓰임). --all 옵션을 주면
sign_words/reference_clips 전체를 검사한다(recorded는 학습용 캐시가 커서
기본적으로 전수조사 대상에서 뺀다).

사용법:
    conda activate coss
    python ai/text_to_sign/fix_video_codecs.py            # 데모 단어 기준
    python ai/text_to_sign/fix_video_codecs.py --all       # sign_words+reference_clips 전체
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lookup import DATA_DIR, REFERENCE_CLIPS_DIR, SIGN_WORDS_DIR, find_clip  # noqa: E402

FFPROBE = shutil.which("ffprobe") or r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
FFMPEG = shutil.which("ffmpeg") or r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"

DEMO_WORDS = [
    "친구", "놀다", "기대", "회사", "일", "잠깐", "괜찮다", "기다리다", "죄송", "빨리",
    "가능", "좋다", "어디", "여기", "만나다", "반갑다", "대박", "신나다",
    "홍수", "위험", "계단", "쓰러지다", "도움받다", "119", "구조", "확인",
    "은행", "대출", "알다", "신분증", "번호", "받다", "카드", "맞다", "감사",
    "얼마", "저기", "돈", "1회",
    "모르다", "가깝다", "오른쪽", "가다", "학교", "왼쪽",
]


def get_codec(path: Path) -> str | None:
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip() or None
    except Exception as e:
        print(f"  [ffprobe 실패] {path}: {e}")
        return None


def reencode(path: Path) -> bool:
    tmp = path.with_suffix(".reencode_tmp.mp4")
    result = subprocess.run(
        [FFMPEG, "-y", "-i", str(path), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", "-an", str(tmp)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0 or not tmp.exists():
        print(f"  [실패] {path}: {result.stderr[-300:]}")
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(path)
    return True


def collect_targets(all_files: bool) -> list[Path]:
    if all_files:
        return sorted(SIGN_WORDS_DIR.rglob("*.mp4")) + sorted(REFERENCE_CLIPS_DIR.rglob("*.mp4"))
    targets = []
    for word in DEMO_WORDS:
        p = find_clip(word)
        if p is not None:
            targets.append(p)
    return targets


def main():
    all_files = "--all" in sys.argv
    targets = collect_targets(all_files)
    print(f"검사 대상: {len(targets)}개 파일 ({'전체 sign_words+reference_clips' if all_files else '데모 단어 기준'})\n")

    fixed, skipped, failed = 0, 0, 0
    for path in targets:
        codec = get_codec(path)
        if codec == "h264":
            skipped += 1
            continue
        rel = path.relative_to(DATA_DIR)
        print(f"[재인코딩] {rel} (codec={codec})")
        if reencode(path):
            fixed += 1
        else:
            failed += 1

    print(f"\n완료: 재인코딩 {fixed}개, 이미 h264라 건너뜀 {skipped}개, 실패 {failed}개")


if __name__ == "__main__":
    main()
