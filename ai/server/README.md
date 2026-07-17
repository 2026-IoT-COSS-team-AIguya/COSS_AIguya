# server

Django 백엔드가 호출하는 수어 인식 HTTP 서버. 백엔드 팀이 준
`ai_server_handoff.md` 계약을 그대로 구현한다.

## 계약 요약

```
POST /recognize
body: {"translation_id": int, "capture_id": str, "device_id": str, "video_url": str}

성공: {"status": "COMPLETED", "keywords": [...], "sentence_candidates": [...],
       "model_version": str, "processing_ms": int}
실패: {"status": "FAILED", "error": {"code": str, "message": str},
       "model_version": str, "processing_ms": int}
```

Django는 mp4 파일을 직접 안 보내고, 이미 자기 media에 저장해둔 영상의 URL만
JSON으로 보낸다. 이 서버가 그 URL을 다운로드해서
`ai/pipeline/recognize.py`의 `predict_sign_from_video()`를 그대로 호출한다.

## 실행 방법

```bash
conda activate coss
cd COSS_AIguya  # 반드시 프로젝트 루트에서 실행 (모듈 경로 때문)
uvicorn ai.server.main:app --host 0.0.0.0 --port 9000
```

Django `.env`에는:
```env
AI_SERVER_URL=http://127.0.0.1:9000/recognize
```
(AI 서버를 다른 PC에서 돌린다면 `127.0.0.1` 대신 그 PC의 LAN IP)

## 테스트 방법

```bash
curl http://127.0.0.1:9000/health
# {"status":"ok"}

curl -X POST http://127.0.0.1:9000/recognize -H "Content-Type: application/json" \
  -d '{"translation_id":1,"capture_id":"test-1","device_id":"test","video_url":"http://예시주소/영상.mp4"}'
```

## 알아둘 점 (중요)

**아직 `enroll.py`(시연자 등록)를 안 해서 실제로는 항상 실패 응답이 나와요.**
`predict_sign_from_video()`가 내부적으로 `infer.predict()`를 쓰는데, 이건
`ai/models/enrolled_prototypes.npz`가 있어야 동작한다 -- 시연자가 78개 단어를
직접 녹화해서 `enroll.py`로 등록해야 이 파일이 생긴다. 등록 전까지는 서버가
정상적으로 뜨고 요청도 잘 받지만, 매번 `AI_INFERENCE_FAILED`로 응답한다(서버
버그 아님, 의도된 동작).

- 요청/응답 형식, 에러 처리, 영상 다운로드까지는 전부 테스트 완료.
- 등록 끝나면 별도 코드 수정 없이 그대로 정상 동작한다.
