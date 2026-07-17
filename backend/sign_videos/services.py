"""쓰기와 조합 (명세 20장 체크리스트)."""

from rest_framework import status

from project import gemini
from project.errors import ApiError, ErrorCode
from sign_videos.selectors import find_sign_videos_by_keywords, get_sign_video_keywords

# 수어로 보여줄 수 있는 단어는 사전에 있는 것뿐이라, LLM에게 문장은 자유롭게
# 이해시키되 답은 반드시 이 목록 안에서만 고르게 합니다. 목록에 없는 단어를
# 지어내면(hallucination) 시퀀스에 재생할 수 없는 칸이 생깁니다.
# (ai/sentence_generation/extract_keywords.py 와 같은 전략입니다. 다만 vocab을
#  gitignore된 word_label_map.json이 아니라 우리 DB에서 가져옵니다 — 그래야
#  고른 키워드에 영상·이모지 row가 반드시 존재합니다.)
_KEYWORD_SYSTEM_PROMPT = """너는 한국어 문장을 한국 수어로 통역하는 통역사다.
지금 수어로 표현 가능한 단어는 아래 목록뿐이다(목록에 없는 단어는 통역할 수 없다):

{vocab}

사용자 문장의 의미를 이 목록 안의 단어들로만 최대한 표현해라. 목록에 없는
개념은 버려라. 문장에서 의미상 실제로 필요한 단어만, 등장 순서대로 골라라.

반드시 아래 형식의 JSON으로만 답하라: {{"keywords": ["단어1", "단어2"]}}
목록에 맞는 단어가 하나도 없으면 {{"keywords": []}}로 답하라.
"""


def validate_sign_video_keywords(keywords):
    """요청한 키워드가 전부 사전에 있는지 확인합니다.

    없는 키워드가 섞이면 시퀀스에 구멍이 생기므로, 조용히 빼지 않고 알려줍니다.
    """
    found = find_sign_videos_by_keywords(keywords)
    missing = [keyword for keyword in keywords if keyword not in found]

    if missing:
        raise ApiError(
            ErrorCode.SIGN_VIDEO_NOT_FOUND,
            '수어 영상이 없는 키워드가 있습니다.',
            status.HTTP_404_NOT_FOUND,
            fields={'keywords': missing},
        )

    return found


def build_sign_video_sequence(keywords):
    """명세 7.2: 백엔드는 요청받은 키워드 순서를 유지해야 합니다.

    DB 조회 결과는 순서를 보장하지 않으므로, 요청 리스트를 기준으로 다시 세웁니다.
    """
    found = validate_sign_video_keywords(keywords)

    return [
        {'position': index + 1, 'sign_video': found[keyword]}
        for index, keyword in enumerate(keywords)
    ]


def extract_keywords_from_sentence(sentence):
    """자유 문장 → 수어 사전 안의 키워드 목록 (등장 순서 유지).

    쉼표로 끊어 넣는 대신 그냥 문장을 쓰게 하는 게 목적이라, 조사·어미·어순은
    Gemini가 알아서 걷어냅니다. 다만 사전 밖 단어가 섞여 나오면 뒤따르는
    build_sign_video_sequence가 404를 내므로, 여기서 한 번 더 걸러냅니다.
    """
    vocab = get_sign_video_keywords()

    if not vocab:
        raise ApiError(
            ErrorCode.SIGN_VIDEO_NOT_FOUND,
            '수어 사전이 비어 있습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    data = gemini.generate_json(
        _KEYWORD_SYSTEM_PROMPT.format(vocab=', '.join(sorted(vocab))),
        sentence,
        temperature=0.2,
    )

    if not isinstance(data, dict):
        raise ApiError(
            ErrorCode.INVALID_AI_RESPONSE,
            '문장을 분석하지 못했습니다. 잠시 후 다시 시도해주세요.',
        )

    keywords = data.get('keywords') or []
    allowed = set(vocab)

    # 순서는 유지하되 중복은 뺍니다 — 같은 영상을 두 번 재생할 이유가 없습니다.
    seen = set()
    result = []
    for keyword in keywords:
        if isinstance(keyword, str) and keyword in allowed and keyword not in seen:
            seen.add(keyword)
            result.append(keyword)

    return result


def build_sign_video_sequence_from_sentence(sentence):
    """자유 문장 → 수어 영상 시퀀스 (일반인 → 농인 전체 흐름).

    ai/pipeline/recognize.py 의 sign_sequence_from_sentence 와 같은 역할입니다.
    """
    keywords = extract_keywords_from_sentence(sentence)

    if not keywords:
        # 27장: 인식 실패와 서버 장애는 다릅니다. 문장은 멀쩡히 분석됐는데
        # 사전에 겹치는 단어가 없는 것뿐이라, 장애가 아니라 빈 결과입니다.
        return {'keywords': [], 'sequence': []}

    return {
        'keywords': keywords,
        'sequence': build_sign_video_sequence(keywords),
    }
