"""쓰기와 조합 (명세 20장 체크리스트)."""

from rest_framework import status

from project import gemini
from project.errors import ApiError, ErrorCode
from sign_videos import ai_client
from sign_videos.models import SignVideo
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


def _build_local_sign_video_sequence(keywords):
    """명세 7.2: 백엔드는 요청받은 키워드 순서를 유지해야 합니다.

    DB 조회 결과는 순서를 보장하지 않으므로, 요청 리스트를 기준으로 다시 세웁니다.
    """
    found = validate_sign_video_keywords(keywords)

    return [
        {'position': index + 1, 'sign_video': found[keyword]}
        for index, keyword in enumerate(keywords)
    ]


def _sync_remote_sequence(items):
    """AI 영상 URL을 기존 SignVideo 형식으로 동기화합니다.

    대화 메시지는 SignVideo FK를 저장하므로 원격 응답을 그대로 반환하는 대신
    로컬 row에 URL을 반영합니다. 이 덕분에 번역기와 채팅이 같은 재생 구조를 씁니다.
    """
    sequence = []

    for index, item in enumerate(items, start=1):
        keyword = item['keyword']
        video, created = SignVideo.objects.get_or_create(
            keyword=keyword,
            defaults={
                'title': item.get('title') or keyword,
                'emoji': item.get('emoji') or '🖐️',
                'external_url': item.get('video_url') or '',
            },
        )

        update_fields = []
        video_url = item.get('video_url') or ''
        if video_url and video.external_url != video_url:
            video.external_url = video_url
            update_fields.append('external_url')

        # 기존 시연 데이터의 이모지/표시명은 보존하고, AI가 명시적으로 준 값만 반영합니다.
        if item.get('title') and video.title != item['title']:
            video.title = item['title']
            update_fields.append('title')
        if item.get('emoji') and video.emoji != item['emoji']:
            video.emoji = item['emoji']
            update_fields.append('emoji')
        if not video.is_active:
            video.is_active = True
            update_fields.append('is_active')

        if not created and update_fields:
            video.save(update_fields=update_fields)

        sequence.append(
            {
                'position': item.get('position') or index,
                'sign_video': video,
            }
        )

    sequence.sort(key=lambda item: item['position'])
    return sequence


def build_sign_video_sequence(keywords):
    """키워드 순서대로 수어 영상을 만듭니다.

    AI 영상 서버가 설정되면 원격 영상 사전을 사용하고, 설정되지 않은 개발
    환경에서는 기존 로컬 DB 방식으로 동작합니다.
    """
    if not ai_client.is_enabled():
        return _build_local_sign_video_sequence(keywords)

    result = ai_client.fetch_sequence(keywords)
    returned = {item['keyword'] for item in result['items']}
    missing = list(result['missing_keywords'])
    missing.extend(
        keyword
        for keyword in keywords
        if keyword not in returned and keyword not in missing
    )

    if missing:
        raise ApiError(
            ErrorCode.SIGN_VIDEO_NOT_FOUND,
            '수어 영상이 없는 키워드가 있습니다.',
            status.HTTP_404_NOT_FOUND,
            fields={'keywords': missing},
        )

    return _sync_remote_sequence(result['items'])


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
    if ai_client.is_enabled():
        result = ai_client.fetch_sequence_from_sentence(sentence)
        sequence = _sync_remote_sequence(result['items'])
        return {
            'keywords': [item['sign_video'].keyword for item in sequence],
            'sequence': sequence,
            'missing_keywords': result['missing_keywords'],
        }

    keywords = extract_keywords_from_sentence(sentence)

    if not keywords:
        # 27장: 인식 실패와 서버 장애는 다릅니다. 문장은 멀쩡히 분석됐는데
        # 사전에 겹치는 단어가 없는 것뿐이라, 장애가 아니라 빈 결과입니다.
        return {'keywords': [], 'sequence': [], 'missing_keywords': []}

    return {
        'keywords': keywords,
        'sequence': _build_local_sign_video_sequence(keywords),
        'missing_keywords': [],
    }
