"""COSS 플랫폼(oneM2M / Mobius) 연동.

계약은 포털이 배포하는 Postman 컬렉션(Mobius_API_Release2)에서 확인했습니다.

    Base    : https://onem2m.iotcoss.ac.kr
    CSE     : Mobius
    AE 생성  : POST {base}/{cse}                 Content-Type: application/json;ty=2
    CNT 생성 : POST {base}/{cse}/{ae}            ...;ty=3
    CIN 생성 : POST {base}/{cse}/{ae}/{cnt}      ...;ty=4
    최신 조회: GET  {base}/{cse}/{ae}/{cnt}/la

    헤더: X-API-KEY, X-AUTH-CUSTOM-LECTURE, X-AUTH-CUSTOM-CREATOR,
          X-M2M-Origin, X-M2M-RI, Accept

30장 최종안대로 **영상 원본은 여기에 넣지 않습니다.** 컨테이너 mbs가 16KB라
애초에 불가능하고, 플랫폼에는 영상 URL과 촬영/처리 메타데이터만 등록합니다.

27장 원칙: **이 모듈의 실패가 영상과 AI 결과를 삭제하게 두지 않습니다.**
호출부는 OneM2MError를 잡아서 로그로만 남깁니다.
"""

import json
import logging
import uuid

import requests
from django.conf import settings

from project.errors import ErrorCode, OneM2MError

logger = logging.getLogger(__name__)

# oneM2M 리소스 타입 번호
TY_AE = 2
TY_CONTAINER = 3
TY_CONTENT_INSTANCE = 4

# 28.6에서 쓰는 컨테이너 두 개
CONTAINER_VIDEO_METADATA = 'video_metadata'
CONTAINER_RECOGNITION_RESULTS = 'recognition_results'

# 컨테이너 최대 크기. Postman 예시 기준 16KB — 메타데이터에는 충분합니다.
CONTAINER_MAX_BYTE_SIZE = 16384

# 과제 식별용 라벨
LABEL = '손말이음'


def is_configured():
    return bool(settings.ONEM2M_BASE_URL and settings.ONEM2M_AE_NAME)


def _headers(origin=None, resource_type=None):
    headers = {
        'Accept': 'application/json',
        # 요청마다 고유해야 합니다.
        'X-M2M-RI': uuid.uuid4().hex[:16],
        'X-M2M-Origin': origin or settings.ONEM2M_ORIGINATOR,
    }

    if settings.ONEM2M_API_KEY:
        headers['X-API-KEY'] = settings.ONEM2M_API_KEY

    if settings.ONEM2M_LECTURE_ID:
        headers['X-AUTH-CUSTOM-LECTURE'] = settings.ONEM2M_LECTURE_ID

    if settings.ONEM2M_CREATOR:
        headers['X-AUTH-CUSTOM-CREATOR'] = settings.ONEM2M_CREATOR

    if resource_type is not None:
        headers['Content-Type'] = f'application/json;ty={resource_type}'

    return headers


def _cse_url(*parts):
    segments = [settings.ONEM2M_BASE_URL.rstrip('/'), settings.ONEM2M_CSE_NAME]
    segments.extend(str(part) for part in parts if part)
    return '/'.join(segments)


def _request(method, url, resource_type=None, body=None, origin=None):
    try:
        response = requests.request(
            method,
            url,
            headers=_headers(origin=origin, resource_type=resource_type),
            json=body,
            timeout=settings.ONEM2M_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise OneM2MError(ErrorCode.ONEM2M_CONNECTION_FAILED, '연결 시간 초과') from exc
    except requests.RequestException as exc:
        raise OneM2MError(ErrorCode.ONEM2M_CONNECTION_FAILED, str(exc)) from exc

    if response.status_code in (401, 403):
        raise OneM2MError(ErrorCode.ONEM2M_AUTH_FAILED, '인증 실패 (API Key / 수업 ID 확인)')

    if response.status_code == 404:
        raise OneM2MError(ErrorCode.ONEM2M_RESOURCE_NOT_FOUND, f'리소스 없음: {url}')

    if response.status_code == 409:
        raise OneM2MError(ErrorCode.ONEM2M_DUPLICATE_RESOURCE, '이미 등록된 리소스')

    if response.status_code >= 300:
        raise OneM2MError(
            ErrorCode.ONEM2M_CREATE_FAILED,
            f'HTTP {response.status_code}: {response.text[:200]}',
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise OneM2MError(ErrorCode.ONEM2M_INVALID_RESPONSE, '응답이 JSON이 아님') from exc


def create_ae():
    """AE를 만듭니다. 최초 1회만 필요합니다 (`manage.py setup_onem2m`).

    AE 생성 시에는 아직 AE-ID가 없으므로 Origin에 'S' + AE 이름을 씁니다.
    Postman 샘플의 'SOrigin'을 그대로 쓰면 다른 팀과 aei가 충돌합니다.
    """
    body = {
        'm2m:ae': {
            'rn': settings.ONEM2M_AE_NAME,
            'api': f'N{settings.ONEM2M_AE_NAME}',
            'rr': True,
            'lbl': [LABEL],
        }
    }
    return _request(
        'POST',
        _cse_url(),
        resource_type=TY_AE,
        body=body,
        origin=f'S{settings.ONEM2M_AE_NAME}',
    )


def create_container(name):
    """Container를 만듭니다. 최초 1회만 필요합니다."""
    body = {
        'm2m:cnt': {
            'rn': name,
            'mbs': CONTAINER_MAX_BYTE_SIZE,
            'lbl': [LABEL],
        }
    }
    return _request(
        'POST',
        _cse_url(settings.ONEM2M_AE_NAME),
        resource_type=TY_CONTAINER,
        body=body,
    )


def _create_content_instance(container, payload):
    if not is_configured():
        # 설정이 비어 있으면 오류가 아니라 "아직 안 붙음"입니다.
        logger.info('oneM2M 미설정 — %s 등록 건너뜀', container)
        return None

    # con에는 JSON 문자열을 넣습니다. Mobius가 파싱해서 객체로 돌려줍니다.
    body = {
        'm2m:cin': {
            'con': json.dumps(payload, ensure_ascii=False),
            'lbl': [LABEL],
        }
    }

    return _request(
        'POST',
        _cse_url(settings.ONEM2M_AE_NAME, container),
        resource_type=TY_CONTENT_INSTANCE,
        body=body,
    )


def get_latest(container):
    """컨테이너의 최신 ContentInstance를 조회합니다 (동작 확인용)."""
    return _request('GET', _cse_url(settings.ONEM2M_AE_NAME, container, 'la'))


def register_video_metadata(translation, video_url):
    """28.6: 영상 업로드 후 video_metadata ContentInstance를 만듭니다."""
    return _create_content_instance(
        CONTAINER_VIDEO_METADATA,
        {
            'translation_id': translation.id,
            'capture_id': translation.capture_id,
            'device_id': translation.device_id,
            'video_url': video_url,
            'captured_at': translation.created_at.isoformat(),
            'status': translation.status,
        },
    )


def register_recognition_result(translation):
    """28.6: AI 완료 후 recognition_results ContentInstance를 만듭니다."""
    keywords = [
        {'keyword': item.keyword, 'confidence': item.confidence}
        for item in translation.recognized_keywords.all()
    ]
    sentences = [item.sentence for item in translation.sentence_candidates.all()]

    return _create_content_instance(
        CONTAINER_RECOGNITION_RESULTS,
        {
            'translation_id': translation.id,
            'capture_id': translation.capture_id,
            'status': translation.status,
            'keywords': keywords,
            'sentence_candidates': sentences,
            'model_version': translation.model_version,
            'processing_ms': translation.processing_ms,
        },
    )
