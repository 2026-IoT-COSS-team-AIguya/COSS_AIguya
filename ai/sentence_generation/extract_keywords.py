"""일반인이 입력한 자유 문장 -> 재생 가능한 수어 영상이 있는 단어 중 해당하는
키워드 추출 (일반인 -> 수어사용자).

주의: 어휘 목록을 ai/data/word_label_map.json에서 가져오지 않는다 -- 그
파일은 train_front_only.py가 "팀원이 직접 촬영해서(recorded/) 인식 모델을
학습시킨 단어"만 기준으로 재학습할 때마다 덮어쓰는 파일이라, AIHub에서만
가져온 단어(예: 병원 시나리오의 수요일/상담/치료 등, 인식 학습엔 안 쓰지만
텍스트->수어 영상 재생은 되는 단어)가 재학습 한 번에 통째로 사라지는 버그가
있었다. 대신 여기서는 실제 영상이 존재하는 폴더(sign_words/reference_clips/
recorded)를 직접 스캔해서 "영상이 있으면 곧 재생 가능한 단어"로 어휘를
구성한다 -- 재학습 여부와 무관하게 항상 정확하다.

LLM에게 문장을 자유롭게 이해시키되, 답은 반드시 이 목록 안에서만 고르게 해서
목록에 없는 단어를 지어내는(hallucination) 걸 막는다.

실행:
    conda activate coss
    python ai/sentence_generation/extract_keywords.py "병원 어디로 가야 돼요?"
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "text_to_sign"))
from lookup import RECORDED_DIR, REFERENCE_CLIPS_DIR, SIGN_WORDS_DIR  # noqa: E402

from _llm_common import generate_json, get_client

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

MODEL = "gemini-flash-lite-latest"

SYSTEM_PROMPT_TEMPLATE = """너는 한국어 문장을 한국 수어로 통역하는 통역사다.
지금 수어로 표현 가능한 단어는 아래 목록뿐이다(목록에 없는 단어는 통역할 수 없다):

{vocab}

사용자 문장의 의미를 이 목록 안의 단어들로만 최대한 표현해라. 목록에 없는
개념은 버려라. 문장에서 의미상 실제로 필요한 단어만, 등장 순서대로 골라라.

반드시 아래 형식의 JSON으로만 답하라: {{"keywords": ["단어1", "단어2"]}}
목록에 맞는 단어가 하나도 없으면 {{"keywords": []}}로 답하라.
"""


def _load_vocab() -> list[str]:
    words = set()
    for base in (SIGN_WORDS_DIR, REFERENCE_CLIPS_DIR, RECORDED_DIR):
        if not base.exists():
            continue
        words.update(p.name for p in base.iterdir() if p.is_dir())
    return sorted(words)


def extract_keywords(sentence: str) -> list[str]:
    vocab = _load_vocab()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(vocab=", ".join(vocab))

    client = get_client()
    data = generate_json(client, MODEL, system_prompt, sentence, temperature=0.2)
    keywords = data.get("keywords", [])
    return [w for w in keywords if w in vocab]  # 목록 밖 단어가 나오면 방어적으로 제거


if __name__ == "__main__":
    import sys

    sentence = sys.argv[1] if len(sys.argv) > 1 else None
    if not sentence:
        print("사용법: python extract_keywords.py <문장>")
        raise SystemExit(1)
    print(extract_keywords(sentence))
