"""AI 서버의 텍스트 -> 수어 영상 API 클라이언트."""

from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from rest_framework import status

from project.errors import ApiError, ErrorCode


def is_enabled():
    return bool(settings.AI_SIGN_SERVER_BASE_URL)


def _endpoint(path):
    base = settings.AI_SIGN_SERVER_BASE_URL.rstrip('/') + '/'
    return urljoin(base, path.lstrip('/'))


def _absolute_video_url(value):
    if not isinstance(value, str) or not value.strip():
        return ''

    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https'):
        return value

    return _endpoint(value)


def _post(path, payload):
    try:
        response = requests.post(
            _endpoint(path),
            json=payload,
            timeout=settings.AI_SIGN_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise ApiError(
            ErrorCode.AI_TIMEOUT,
            '수어 영상을 가져오는 데 시간이 오래 걸리고 있습니다.',
            status.HTTP_504_GATEWAY_TIMEOUT,
        ) from exc
    except requests.RequestException as exc:
        raise ApiError(
            ErrorCode.AI_SERVER_UNAVAILABLE,
            '수어 영상 서버에 연결하지 못했습니다.',
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if response.status_code >= 300:
        raise ApiError(
            ErrorCode.AI_INFERENCE_FAILED,
            f'수어 영상 서버 오류 {response.status_code}',
            status.HTTP_502_BAD_GATEWAY,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ApiError(
            ErrorCode.INVALID_AI_RESPONSE,
            '수어 영상 서버의 응답을 읽지 못했습니다.',
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    if not isinstance(data, dict):
        raise ApiError(
            ErrorCode.INVALID_AI_RESPONSE,
            '수어 영상 서버의 응답 형식이 올바르지 않습니다.',
            status.HTTP_502_BAD_GATEWAY,
        )

    return data


def _normalize_item(item, fallback_position):
    """AI 응답의 평면형/기존 프론트 중첩형을 모두 받아들입니다."""
    if not isinstance(item, dict):
        return None

    nested = item.get('sign_video')
    video = nested if isinstance(nested, dict) else item

    keyword = video.get('keyword') or item.get('keyword')
    if not isinstance(keyword, str) or not keyword.strip():
        return None

    position = item.get('position', fallback_position)
    if not isinstance(position, int) or position < 1:
        position = fallback_position

    return {
        'position': position,
        'keyword': keyword.strip(),
        'title': video.get('title') or item.get('title') or keyword.strip(),
        'emoji': video.get('emoji') or item.get('emoji') or '',
        'video_url': _absolute_video_url(
            video.get('video_url') or item.get('video_url')
        ),
    }


def _normalize_response(data):
    raw_items = data.get('items')
    if raw_items is None:
        raw_items = data.get('sequence')
    if raw_items is None:
        raw_items = []

    if not isinstance(raw_items, list):
        raise ApiError(
            ErrorCode.INVALID_AI_RESPONSE,
            '수어 영상 목록의 형식이 올바르지 않습니다.',
            status.HTTP_502_BAD_GATEWAY,
        )

    items = []
    for index, item in enumerate(raw_items, start=1):
        normalized = _normalize_item(item, index)
        if normalized is not None:
            items.append(normalized)

    raw_keywords = data.get('keywords') or []
    keywords = [
        keyword.strip()
        for keyword in raw_keywords
        if isinstance(keyword, str) and keyword.strip()
    ]
    if not keywords:
        keywords = [item['keyword'] for item in items]

    raw_missing = data.get('missing_keywords') or []
    missing = [
        keyword.strip()
        for keyword in raw_missing
        if isinstance(keyword, str) and keyword.strip()
    ]

    return {'keywords': keywords, 'items': items, 'missing_keywords': missing}


def fetch_sequence(keywords):
    data = _post('/sign-sequences', {'keywords': keywords})
    return _normalize_response(data)


def fetch_sequence_from_sentence(sentence):
    data = _post('/sign-sequence-from-sentence', {'sentence': sentence})
    result = _normalize_response(data)

    # 문장 분석 API가 키워드만 돌려주는 구현도 지원합니다.
    if result['keywords'] and not result['items']:
        return fetch_sequence(result['keywords'])

    return result
