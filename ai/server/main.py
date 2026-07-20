"""백엔드(Django)가 호출하는 수어 인식 HTTP 서버.

계약은 백엔드 팀이 준 인수인계 문서(ai_server_handoff.md) 기준:

    POST /recognize
    body: {"translation_id": int, "capture_id": str, "device_id": str, "video_url": str}

    성공: {"status": "COMPLETED", "keywords": [...], "sentence_candidates": [...],
           "model_version": str, "processing_ms": int}
    실패: {"status": "FAILED", "error": {"code": str, "message": str},
           "model_version": str, "processing_ms": int}

Django는 mp4 파일 자체를 안 보내고 이미 저장된 영상의 URL만 JSON으로 보낸다 --
그래서 여기서 그 URL을 다운로드한 뒤 기존 ai/pipeline/recognize.py의
predict_sign_from_video()를 그대로 재사용한다.

실행:
    conda activate coss
    uvicorn ai.server.main:app --host 0.0.0.0 --port 9000

    (COSS_AIguya 루트에서 실행해야 `ai.server.main`으로 모듈 경로가 잡힌다.
     다른 위치에서 돌리려면 PYTHONPATH에 루트를 추가할 것.)
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from recognize import (  # noqa: E402
    MODEL_VERSION,
    build_sign_sequence,
    predict_sign_from_video,
    search_sign_video,
    sign_sequence_from_sentence,
)

app = FastAPI()

# 텍스트->수어 방향(21번 섹션)에서 돌려주는 video_url이 실제로 재생 가능한
# HTTP 경로가 되도록, ai/data 밑을 통째로 정적 파일로 서빙한다. lookup.py가
# 찾아주는 절대경로(sign_words/.../*.mp4 등)를 이 루트 기준 상대경로로 바꿔서
# "/media/..." URL을 만든다.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
app.mount("/media", StaticFiles(directory=str(_DATA_DIR)), name="media")


def _to_media_url(path_str: str | None) -> str | None:
    if not path_str:
        return None
    try:
        rel = Path(path_str).resolve().relative_to(_DATA_DIR)
    except ValueError:
        return None
    return "/media/" + rel.as_posix()


class RecognizeRequest(BaseModel):
    translation_id: int
    capture_id: str = ""
    device_id: str = ""
    video_url: str


def _fail(code: str, message: str, start: float) -> dict:
    return {
        "status": "FAILED",
        "error": {"code": code, "message": message},
        "model_version": MODEL_VERSION,
        "processing_ms": int((time.time() - start) * 1000),
    }


def _download_video(url: str) -> Path:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    suffix = Path(url.split("?")[0]).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(resp.content)
    tmp.close()
    return Path(tmp.name)


@app.post("/recognize")
def recognize(req: RecognizeRequest):
    start = time.time()

    try:
        tmp_path = _download_video(req.video_url)
    except Exception as e:
        return _fail("VIDEO_DOWNLOAD_FAILED", str(e), start)

    try:
        try:
            result = predict_sign_from_video(str(tmp_path))
        except FileNotFoundError as e:
            # enroll.py로 시연자 등록(ai/models/enrolled_prototypes.npz)이 안 돼있으면
            # 여기로 옴 -- 다만 FileNotFoundError는 다른 원인(예: SSL 인증서 경로
            # 문제)으로도 날 수 있어서, 실제 원인을 그대로 노출해 오해를 줄인다.
            return _fail("AI_INFERENCE_FAILED", f"파일 없음(시연자 등록 미완료일 수 있음): {e}", start)
        except Exception as e:
            return _fail("AI_INFERENCE_FAILED", str(e), start)

        if not result.get("keywords"):
            return _fail("SIGN_NOT_DETECTED", "영상에서 수어 동작을 찾지 못했습니다.", start)

        result["status"] = "COMPLETED"
        result["processing_ms"] = int((time.time() - start) * 1000)
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


class SignSequenceRequest(BaseModel):
    keywords: list[str]


class SentenceRequest(BaseModel):
    sentence: str


@app.get("/sign-videos/search")
def sign_video_search(keyword: str):
    """인수인계 문서 21번 섹션: GET /api/sign-videos/search/?keyword=약속 대응."""
    result = search_sign_video(keyword)
    return {"keyword": keyword, "video_url": _to_media_url(result.get("video_path"))}


@app.post("/sign-sequences")
def sign_sequences(req: SignSequenceRequest):
    """인수인계 문서 21번 섹션: POST /api/sign-sequences/ 대응."""
    result = build_sign_sequence(req.keywords)
    items = [
        {"order": it["order"], "keyword": it["keyword"], "video_url": _to_media_url(it["video_path"])}
        for it in result["items"]
    ]
    return {"items": items, "missing_keywords": result["missing_keywords"]}


@app.post("/sign-sequence-from-sentence")
def sign_sequence_from_sentence_endpoint(req: SentenceRequest):
    """자유 문장 입력 -> 키워드 추출 -> 영상 시퀀스까지 한 번에 (편의용)."""
    result = sign_sequence_from_sentence(req.sentence)
    items = [
        {"order": it["order"], "keyword": it["keyword"], "video_url": _to_media_url(it["video_path"])}
        for it in result["items"]
    ]
    return {
        "items": items,
        "missing_keywords": result["missing_keywords"],
        "source_sentence": result["source_sentence"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
