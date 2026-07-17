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
from pydantic import BaseModel

_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from recognize import MODEL_VERSION, predict_sign_from_video  # noqa: E402

app = FastAPI()


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
            # enroll.py로 시연자 등록(ai/models/enrolled_prototypes.npz)이 안 돼있으면 여기로 옴.
            return _fail("AI_INFERENCE_FAILED", f"등록된 시연자 데이터 없음: {e}", start)
        except Exception as e:
            return _fail("AI_INFERENCE_FAILED", str(e), start)

        if not result.get("keywords"):
            return _fail("SIGN_NOT_DETECTED", "영상에서 수어 동작을 찾지 못했습니다.", start)

        result["status"] = "COMPLETED"
        result["processing_ms"] = int((time.time() - start) * 1000)
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}
