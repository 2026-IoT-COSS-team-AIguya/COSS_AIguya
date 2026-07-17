# sentence_generation

수어 인식 결과 <-> 자연어 문장을 LLM(Gemini)으로 서로 변환하는 모듈.

## 왜 LLM이 필요한가

- **수어사용자 -> 일반인**: `sign_recognition`이 주는 건 Top-K 후보 단어(확신도
  포함)일 뿐이고, 수어는 어순/조사가 한국어 구어와 다르다. 단어를 그대로
  나열하면 부자연스럽고, 인식이 100% 정확하지도 않으므로 "그럴듯한 해석" 여러
  개를 문장으로 보여줘야 한다.
- **일반인 -> 수어사용자**: 자유롭게 입력한 문장에서, 지금 학습된 단어 목록
  (`ai/data/word_label_map.json`) 중 실제로 표현 가능한 키워드만 뽑아내야
  `text_to_sign`이 재생할 수 있다. 동의어/패러프레이즈(예: "병원 어디예요?" ->
  병원)까지 잡아내려면 단순 키워드 매칭보다 LLM이 안전하다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `generate_sentence.py` | 수어 인식 후보 단어들 -> 자연어 문장 후보 N개 |
| `extract_keywords.py` | 자유 문장 -> 학습된 단어 목록 중 해당 키워드만 추출 |

## 실행 방법

```bash
conda activate coss
pip install -r ai/requirements-ai.txt   # google-genai, python-dotenv 포함

# https://aistudio.google.com/apikey 에서 무료로 키 발급받은 뒤,
# 프로젝트 루트에 .env 파일 만들고 GEMINI_API_KEY 채우기 (.env.example 참고)

python ai/sentence_generation/generate_sentence.py
python ai/sentence_generation/extract_keywords.py "병원 어디로 가야 돼요?"
```

## 참고

- 키워드 -> 학습 단어 매칭 기준은 `ai/data/word_label_map.json`(학습 시 자동
  생성됨, `sign_recognition/train.py` 참고)을 그대로 씀.
- `generate_sentence.py`는 지금은 단어 하나짜리 예시로만 테스트 가능하다.
  영상 여러 개(단어 시퀀스)를 순서대로 인식해서 리스트로 넘겨주는 부분은
  아직 없고, `ai/pipeline`에서 `sign_recognition.infer` 결과를 이어붙여
  넘겨줄 예정.
