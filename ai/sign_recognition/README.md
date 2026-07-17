# sign_recognition

수어 영상 -> 핵심 키워드 인식 모듈.

## 왜 이런 구조인가

AIHub 수어 데이터를 다 못 받아서(용량 문제) 데모에 필요한 단어만, 그것도
**한 명의 수어사가 찍은 것**만 확보한 상태다. 이 정도 데이터로 일반
분류기(softmax)를 학습시키면 사실상 그 한 명만 인식하는 모델이 나온다.

그래서 **분류가 아니라 "비교"를 학습**시킨다 (Supervised Contrastive Learning).
- AIHub 데이터로는 "손동작이 같은지 다른지 구별하는 눈"만 학습한다.
- 실제 인식 기준(정답지)은 **시연자 본인이 등록한 영상**으로 만든다 (얼굴인식 앱의
  "내 얼굴 등록"과 같은 원리). 그래서 학습에 없던 사람이 시연해도 동작한다.

단어 소스는 두 종류다 (`ai/data/word_label_map.json`이 최종 학습 단어 목록,
재학습할 때마다 자동 갱신됨):
- **단어 영상(WORD) 데이터셋**: 단어당 5개 각도 영상이 원래부터 잘라져 있음.
- **문장 영상(SEN) 데이터셋의 형태소 라벨**: AIHub가 문장 영상 안에 "이 구간은
  이 단어다"로 태깅해둔 걸 그대로 활용 -- 단어 영상 데이터셋에 없는 단어를
  여기서 추가로 확보한다 (`extract_sentence_clips.py`).

## 파이프라인 순서

```
1a. prepare_data.py          AIHub 단어 영상 zip에서 TARGET_WORDS 영상을 ai/data/sign_words/ 로 추출
1b. extract_sentence_clips.py 문장 영상 형태소 라벨 구간에서 TARGET_WORDS keypoint를 직접 추출
2.  extract_all.py            1a로 받은 mp4 -> keypoint(.npy)로 변환해서 ai/data/sign_words_keypoints/ 에 캐싱
                               (1b는 이미 keypoint로 바로 저장하므로 이 단계 불필요)
3.  train.py                  임베딩 인코더 학습 -> ai/models/sign_encoder.pt
4.  enroll.py                 시연자가 녹화한 영상(ai/data/enrolled/*.mp4)으로 기준 임베딩 등록
                               -> ai/models/enrolled_prototypes.npz
5.  infer.py                  새 영상 -> Top-3 후보 단어 + 확신도
```

## 실행 방법

```bash
conda activate coss

python ai/sign_recognition/prepare_data.py
python ai/sign_recognition/extract_all.py
python ai/sign_recognition/extract_sentence_clips.py   # 문장 라벨로만 확보 가능한 단어
python ai/sign_recognition/train.py

# ai/data/enrolled/ 에 시연자 본인 녹화 영상을 단어별로 넣은 뒤
python ai/sign_recognition/enroll.py

python ai/sign_recognition/infer.py "경로/새영상.mp4"
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `keypoints.py` | MediaPipe HolisticLandmarker로 영상 -> (T, 225) keypoint 시퀀스 |
| `dataset.py` | 캐싱된 keypoint 로드 + 증강(시간축 크롭/보간, 노이즈, occlusion) |
| `model.py` | 1D-CNN 인코더 + Supervised Contrastive Loss |
| `train.py` | 학습 루프. leave-one-angle-out 5-fold 교차검증으로 일반화 확인 |
| `prepare_data.py` | AIHub 단어 영상 zip에서 데모용 단어 영상만 추출 |
| `extract_all.py` | 단어 영상 keypoint 일괄 추출/캐싱 |
| `extract_sentence_clips.py` | 문장 영상 형태소 라벨 구간에서 단어별 keypoint 직접 추출 |
| `enroll.py` | 시연자 영상으로 기준 임베딩 등록 |
| `infer.py` | 추론 (Top-K 후보 + 확신도) |

## 필요한 모델 파일

MediaPipe Tasks API용 모델 번들이 필요하다 (`ai/models/mediapipe/holistic_landmarker.task`,
용량 문제로 git에는 안 올라가 있음 — 팀원 PC마다 아래로 받아야 함):

```bash
curl -L -o ai/models/mediapipe/holistic_landmarker.task ^
  https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task
```

## 현재 지원 단어

`ai/data/word_label_map.json`이 최종 학습 단어 목록이다(개수는 재학습 때마다
바뀌므로 이 파일이 항상 최신 기준). 단어 추가하고 싶으면:
- AIHub 단어 영상 데이터셋에 있는 단어면 `prepare_data.py`의 `TARGET_WORDS`에 추가
- 없으면 `extract_sentence_clips.py`의 `TARGET_WORDS`에 추가(문장 영상 형태소
  라벨에 있는지 먼저 확인 필요)

추가한 뒤 파이프라인을 다시 돌리면 된다 (재학습 필요 — 인코더 자체가 이
단어셋으로 contrastive 학습되기 때문).
