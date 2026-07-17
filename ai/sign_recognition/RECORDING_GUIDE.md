# 직접 촬영 가이드

AIHub 데이터만으로는 정확도가 부족한 단어들이 있어서(특히 L 각도, 그리고
단어DB 유래 단어는 원래 인스턴스가 5개뿐), 실제 시연 조건(정면 카메라,
실제 시연자)에 맞는 영상을 직접 찍어서 학습 데이터에 더한다.

## 촬영 방법

- **카메라는 정면(F)만**. 각도 여러 개 찍을 필요 없음 — 어차피 데모도 정면으로 함.
- **단어당 3~5번** 반복 촬영 (많을수록 좋지만, 시간 없으면 최소 3개).
- 상체(어깨~머리)와 양손이 전부 프레임 안에 들어오게. 배경은 단순할수록 좋음.
- 한 클립에 단어 하나만. 시작 전/끝난 후 손을 잠깐 내렸다가 다시 드는 정도의
  여유를 두면 좋음(자연스러운 시작/끝 구간 확보).
- 여러 사람이 나눠 찍어도 됨 — 오히려 시연자가 여러 명이면 더 일반화 잘 됨.

## 파일 저장 위치 (중요: 파일명에 촬영자를 꼭 넣어주세요)

```
ai/data/recorded/{단어}/{단어}_{촬영자이니셜}{번호}.mp4
```

예) `ai/data/recorded/감사/감사_kim1.mp4`, `감사_kim2.mp4`, `감사_lee1.mp4`, ...

폴더명(단어)은 아래 목록의 단어와 **정확히 똑같이** 적어야 자동 처리 스크립트가 인식함.

**촬영자 이니셜을 꼭 넣어야 하는 이유**: `train_front_only.py`가 "이 사람 영상은 학습에서
빼고 검증에만 써서, 새로운 사람이 해도 인식되는지" 확인하는 방식으로 평가해요.
파일명에 촬영자가 없으면(예: 그냥 `감사_1.mp4`) 이 검증에서 빠지고 항상 학습에만
쓰여요 — 촬영자 수/인원이 매번 달라져도 상관없이 자동으로 인식되니, 번호 앞에
사람 이니셜만 붙여주면 됩니다.

## 처리 방법

다 찍은 뒤:
```bash
conda activate coss
python ai/sign_recognition/extract_recorded.py
python ai/sign_recognition/train.py
```

## 우선순위 + 촬영 전 참고 영상 (정확도 낮은 순 -- 시간 없으면 1티어부터)

시간이 부족하면 1티어만이라도 찍는 걸 추천. (수치는 5-fold 교차검증 평균,
용량 확장 전 기준이라 지금은 다를 수 있지만 상대적 우선순위는 유효함)

**촬영 전에 그 단어가 정확히 어떤 동작인지 아래 "참고 영상"을 먼저 보고
따라 찍으세요.** 출처가 두 종류라 참고 영상 위치가 다름:
- [단어DB] → `ai/data/sign_words/{단어}/{단어}_F.mp4`
- [문장클립] → `ai/data/reference_clips/{단어}/{단어}_ref1.mp4` (`_ref2.mp4`도 있음)

### 1티어 -- 정확도 40% 이하 (제일 급함, 26개)

| 단어 | 참고 영상 |
|---|---|
| 가능 | [단어DB] sign_words/가능/가능_F.mp4 |
| 감사 | [단어DB] sign_words/감사/감사_F.mp4 |
| 무엇 | [문장클립] reference_clips/무엇/무엇_ref1.mp4 |
| 빨리 | [단어DB] sign_words/빨리/빨리_F.mp4 |
| 소개 | [단어DB] sign_words/소개/소개_F.mp4 |
| 신나다 | [단어DB] sign_words/신나다/신나다_F.mp4 |
| 어디 | [문장클립] reference_clips/어디/어디_ref1.mp4 |
| 오다 | [단어DB] sign_words/오다/오다_F.mp4 |
| 전화번호 | [단어DB] sign_words/전화번호/전화번호_F.mp4 |
| 좋다 | [단어DB] sign_words/좋다/좋다_F.mp4 |
| 119 | [문장클립] reference_clips/119/119_ref1.mp4 |
| 가깝다 | [단어DB] sign_words/가깝다/가깝다_F.mp4 |
| 가다 | [단어DB] sign_words/가다/가다_F.mp4 |
| 그립다 | [단어DB] sign_words/그립다/그립다_F.mp4 |
| 대출 | [단어DB] sign_words/대출/대출_F.mp4 |
| 딸 | [단어DB] sign_words/딸/딸_F.mp4 |
| 맞다 | [단어DB] sign_words/맞다/맞다_F.mp4 |
| 받다 | [단어DB] sign_words/받다/받다_F.mp4 |
| 알다 | [단어DB] sign_words/알다/알다_F.mp4 |
| 얼마 | [단어DB] sign_words/얼마/얼마_F.mp4 |
| 일 | [단어DB] sign_words/일/일_F.mp4 |
| 죄송 | [단어DB] sign_words/죄송/죄송_F.mp4 |
| 친구 | [단어DB] sign_words/친구/친구_F.mp4 |
| 할아버지 | [단어DB] sign_words/할아버지/할아버지_F.mp4 |
| 행복 | [단어DB] sign_words/행복/행복_F.mp4 |
| 회사 | [단어DB] sign_words/회사/회사_F.mp4 |

### 2티어 -- 45~60% (26개)

| 단어 | 참고 영상 |
|---|---|
| 번호 | [문장클립] reference_clips/번호/번호_ref1.mp4 |
| 카드 | [문장클립] reference_clips/카드/카드_ref1.mp4 |
| 돈 | [문장클립] reference_clips/돈/돈_ref1.mp4 |
| 은행 | [문장클립] reference_clips/은행/은행_ref1.mp4 |
| 1회 | [문장클립] reference_clips/1회/1회_ref1.mp4 |
| 가족 | [단어DB] sign_words/가족/가족_F.mp4 |
| 걱정 | [단어DB] sign_words/걱정/걱정_F.mp4 |
| 괜찮다 | [단어DB] sign_words/괜찮다/괜찮다_F.mp4 |
| 구조 | [단어DB] sign_words/구조/구조_F.mp4 |
| 나이 | [단어DB] sign_words/나이/나이_F.mp4 |
| 놀다 | [단어DB] sign_words/놀다/놀다_F.mp4 |
| 대기 | [단어DB] sign_words/대기/대기_F.mp4 |
| 대박 | [단어DB] sign_words/대박/대박_F.mp4 |
| 모르다 | [단어DB] sign_words/모르다/모르다_F.mp4 |
| 병원 | [단어DB] sign_words/병원/병원_F.mp4 |
| 쓰러지다 | [단어DB] sign_words/쓰러지다/쓰러지다_F.mp4 |
| 안내하다 | [문장클립] reference_clips/안내하다/안내하다_ref1.mp4 |
| 엄마 | [단어DB] sign_words/엄마/엄마_F.mp4 |
| 오른쪽 | [단어DB] sign_words/오른쪽/오른쪽_F.mp4 |
| 오빠 | [단어DB] sign_words/오빠/오빠_F.mp4 |
| 의사 | [단어DB] sign_words/의사/의사_F.mp4 |
| 일어나다 | [단어DB] sign_words/일어나다/일어나다_F.mp4 |
| 자다 | [단어DB] sign_words/자다/자다_F.mp4 |
| 전화걸다 | [문장클립] reference_clips/전화걸다/전화걸다_ref1.mp4 |
| 축하 | [단어DB] sign_words/축하/축하_F.mp4 |
| 확인 | [문장클립] reference_clips/확인/확인_ref1.mp4 |

### 3티어 -- 65~80% (여유 있으면, 22개)

| 단어 | 참고 영상 |
|---|---|
| 경찰 | [문장클립] reference_clips/경찰/경찰_ref1.mp4 |
| 도움받다 | [문장클립] reference_clips/도움받다/도움받다_ref1.mp4 |
| 잠깐 | [문장클립] reference_clips/잠깐/잠깐_ref1.mp4 |
| 보다 | [문장클립] reference_clips/보다/보다_ref1.mp4 |
| 부르다 | [문장클립] reference_clips/부르다/부르다_ref1.mp4 |
| 여기 | [문장클립] reference_clips/여기/여기_ref1.mp4 |
| 위험 | [문장클립] reference_clips/위험/위험_ref1.mp4 |
| 저기 | [문장클립] reference_clips/저기/저기_ref1.mp4 |
| 계단 | [문장클립] reference_clips/계단/계단_ref1.mp4 |
| 차내리다 | [문장클립] reference_clips/차내리다/차내리다_ref1.mp4 |
| 기다리다 | [문장클립] reference_clips/기다리다/기다리다_ref1.mp4 |
| 누나 | [단어DB] sign_words/누나/누나_F.mp4 |
| 만나다 | [문장클립] reference_clips/만나다/만나다_ref1.mp4 |
| 반갑다 | [문장클립] reference_clips/반갑다/반갑다_ref1.mp4 |
| 생일 | [단어DB] sign_words/생일/생일_F.mp4 |
| 신분증 | [문장클립] reference_clips/신분증/신분증_ref1.mp4 |
| 왼쪽 | [단어DB] sign_words/왼쪽/왼쪽_F.mp4 |
| 이름 | [문장클립] reference_clips/이름/이름_ref1.mp4 |
| 직원 | [단어DB] sign_words/직원/직원_F.mp4 |
| 할머니 | [단어DB] sign_words/할머니/할머니_F.mp4 |
| 형 | [단어DB] sign_words/형/형_F.mp4 |
| 홍수 | [단어DB] sign_words/홍수/홍수_F.mp4 |

### 4티어 -- 이미 95%+ (안 찍어도 됨)
엘리베이터, 학교, 건강, 기대

(모든 경로는 `ai/data/` 기준 상대경로. 전부 파일 존재 확인 완료.)
