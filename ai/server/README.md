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

**시연자 등록(enroll) 완료됨 -- 정상 동작합니다.**
`predict_sign_from_video()`가 내부적으로 쓰는 `infer.predict()`는
`ai/models/enrolled_prototypes.npz`가 있어야 동작하는데, 이 파일이 이미 생성돼
있다. 실제 시연자(A/B/D)가 학습 데이터 촬영 때 이미 78개 단어를 다 찍어놔서,
새로 등록 영상을 찍는 대신 `enroll_from_recorded.py`로 기존 촬영본(F 각도)의
keypoint를 재사용해 등록했다(468개 인스턴스, 78개 단어 전부 커버).

- 요청/응답 형식, 에러 처리, 영상 다운로드, 등록 후 추론까지 전부 테스트 완료.
- 시연자가 A/B/D 세 명이 아니거나 인원이 바뀌면
  `ai/sign_recognition/enroll_from_recorded.py`의 `DEMO_PERSONS`를 수정하고
  다시 실행해서 `enrolled_prototypes.npz`를 재생성해야 한다.
- 새 시연자가 기존 학습 데이터에 없는 사람이면(전혀 새로운 사람), 그 사람은
  `ai/sign_recognition/enroll.py`로 별도 촬영 후 등록해야 한다.
