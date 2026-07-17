# pipeline

`sign_recognition` + `sentence_generation` + `text_to_sign`을 하나로 묶어서
백엔드가 호출할 단일 진입점을 제공하는 모듈. 백엔드 인수인계 문서
(`잇손_백엔드_AI_oneM2M_인수인계.md`)의 19.3, 21번 섹션이 원하는 JSON 형태를
그대로 반환한다.

## 왜 이런 구조인가

백엔드(Django) 쪽이 아직 스켈레톤 상태라 실제 연결은 나중에 하게 되는데,
그때 백엔드 담당이 이 모듈의 함수만 그대로 호출하면 되도록 미리 인터페이스를
맞춰뒀다. 백엔드가 준비되기 전에도 AI 쪽에서 독립적으로 개발/테스트할 수 있음.

## 파일 구성

| 함수 | 방향 | 역할 |
|---|---|---|
| `predict_sign_from_video(video_path)` | 수어→일반인 | 영상 → 인식 키워드 + 문장 후보 |
| `search_sign_video(keyword)` | 일반인→수어 | 단어 하나 → 영상 경로 |
| `build_sign_sequence(keywords)` | 일반인→수어 | 단어 리스트 → 영상 경로 리스트 |
| `sign_sequence_from_sentence(sentence)` | 일반인→수어 | 문장 → 키워드 추출 → 영상 경로 리스트 |

## 실행 방법

```bash
conda activate coss

python ai/pipeline/recognize.py predict ai/data/sign_words/은행/은행_F.mp4
python ai/pipeline/recognize.py search 은행 카드 잠깐
python ai/pipeline/recognize.py sentence "은행 카드 좀 잠깐 빌려줄 수 있어요?"
```

## 알아둘 점

- `predict_sign_from_video`는 `ai/models/enrolled_prototypes.npz`가 있어야
  동작한다 (`enroll.py`로 시연자 영상 등록 필요, 아직 안 함 -- 등록 전까지는
  `FileNotFoundError`가 정상 동작).
- 반환값은 `video_url`이 아니라 `video_path`(로컬 경로)다. URL로 바꾸는 것
  (Django `MEDIA_URL` 접두사 붙이기 등)은 백엔드가 할 일이라 여기서는 관여하지
  않는다.
- `MODEL_VERSION` 상수는 `sign_encoder.pt`를 재학습해서 갈아끼울 때마다 같이
  올려주면, 나중에 DB에 "어떤 모델이 이 결과를 냈는지" 기록이 남는다.
