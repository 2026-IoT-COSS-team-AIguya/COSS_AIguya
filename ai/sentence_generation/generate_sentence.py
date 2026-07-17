"""수어 인식 후보 단어들 -> 자연스러운 문장 후보 여러 개 생성 (수어사용자 -> 일반인).

infer.py의 predict()가 반환하는 Top-K 후보 단어+확신도를 그대로 나열하면 어순도
안 맞고 조사도 없어서 부자연스럽다. 게다가 keypoint 인식이 100% 정확하지 않으니
가장 그럴듯한 해석 하나만 보여주면 오인식일 때 대안이 없다. 그래서 LLM에게
후보 단어(확신도 포함)를 통째로 주고, 가능한 해석을 문장 여러 개로 제안받아서
사용자(청인)가 그중 맞는 걸 고르게 한다.

실행:
    conda activate coss
    python ai/sentence_generation/generate_sentence.py
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from _llm_common import generate_json, get_client

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

MODEL = "gemini-flash-lite-latest"
N_CANDIDATES = 3

SYSTEM_PROMPT = """너는 한국 수어를 통역하는 통역사다. 수어 인식 AI가 영상에서
인식한 단어 후보들(확신도 포함, 순서는 수어 동작이 나온 시간 순)을 보고 화자가
실제로 하려던 말이 무엇인지 자연스러운 한국어 문장으로 추측한다.

- 수어는 어순이 한국어 구어와 다르고 조사가 없으므로, 인식된 단어를 그대로
  나열하지 말고 자연스러운 문장으로 재구성해라.
- 확신도가 낮은 단어는 오인식일 수 있으니 다른 단어 후보로 바꿔서도 해석해봐라.
- 정답을 확신할 수 없으므로 서로 뜻이 다른 해석의 문장을 여러 개 제안해라.
- 반드시 아래 형식의 JSON으로만 답하라: {"sentences": ["문장1", "문장2", "문장3"]}
"""


def generate_sentence_candidates(
    word_candidates: list[list[tuple[str, float]]], n: int = N_CANDIDATES
) -> list[str]:
    """word_candidates: 시간 순으로 인식된 각 수어 단어의 Top-K 후보 리스트.

    예) [[("병원", 0.82), ("의사", 0.11)], [("가다", 0.90), ("오다", 0.07)]]
    -> ["병원에 가요", "병원에 가고 싶어요", "의사 선생님 오세요"]
    """
    lines = []
    for i, candidates in enumerate(word_candidates, 1):
        formatted = ", ".join(f"{w}({p:.0%})" for w, p in candidates)
        lines.append(f"{i}번째 단어 후보: {formatted}")
    user_prompt = "\n".join(lines) + f"\n\n서로 다른 해석의 문장 후보를 {n}개 제안해줘."

    client = get_client()
    data = generate_json(client, MODEL, SYSTEM_PROMPT, user_prompt, temperature=0.7)
    return data.get("sentences", [])[:n]


if __name__ == "__main__":
    # infer.py로 영상 여러 개(단어 시퀀스)를 돌린 뒤 나온 Top-K 결과를 여기 순서대로
    # 넣는다고 가정한 예시. 실제로는 pipeline 모듈이 infer.py 결과를 이 형식으로
    # 넘겨줄 예정.
    example = [
        [("병원", 0.82), ("의사", 0.11), ("직원", 0.05)],
        [("가다", 0.90), ("오다", 0.07), ("빨리", 0.02)],
    ]
    for i, sentence in enumerate(generate_sentence_candidates(example), 1):
        print(f"후보{i}: {sentence}")
