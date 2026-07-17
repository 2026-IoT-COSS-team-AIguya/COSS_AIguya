"""인-백(AI 서버) 호출.

28.5 / 28.7의 경계입니다. AI_SERVER_URL이 비어 있으면 가짜 결과를 돌려주고,
채워지면 실제 인-백을 호출합니다. **이 파일이 프-백에서 유일하게 가짜인 곳입니다.**

모델(키포인트 기반)이 학습 중이라, 그때까지 업로드 · 상태 전이 · 폴링 · 저장 ·
Message 연결은 전부 진짜로 돌리고 인식 결과만 고정값을 씁니다.
시연에서 이 부분은 반드시 밝혀야 합니다.

응답 형식은 28.5의 예시를 그대로 따릅니다:
    {"keywords": [{"keyword": "화장실", "confidence": 0.92}, ...],
     "sentence_candidates": [{"sentence": "화장실 어디예요?", "score": 0.91}],
     "model_version": "mock-v1", "processing_ms": 100}
"""

import itertools
import logging

import requests
from django.conf import settings

from project.errors import ApiError, ErrorCode

logger = logging.getLogger(__name__)

# 시연 시나리오 대본 순서. 업로드할 때마다 하나씩 돌아가며 나옵니다.
_SCRIPTED_RESULTS = [
    {
        'keywords': [
            {'keyword': '화장실', 'confidence': 0.92},
            {'keyword': '어디', 'confidence': 0.84},
        ],
        'sentence_candidates': [{'sentence': '화장실 어디예요?', 'score': 0.91}],
    },
    {
        'keywords': [
            {'keyword': '약속', 'confidence': 0.91},
            {'keyword': '늦다', 'confidence': 0.87},
        ],
        'sentence_candidates': [{'sentence': '약속에 늦어요', 'score': 0.89}],
    },
    {
        'keywords': [
            {'keyword': '지금', 'confidence': 0.89},
            {'keyword': '가다', 'confidence': 0.90},
            {'keyword': '빨리', 'confidence': 0.83},
        ],
        'sentence_candidates': [{'sentence': '지금 빨리 갈게요', 'score': 0.86}],
    },
    {
        'keywords': [
            {'keyword': '은행', 'confidence': 0.90},
            {'keyword': '번호', 'confidence': 0.86},
            {'keyword': '받다', 'confidence': 0.81},
        ],
        'sentence_candidates': [{'sentence': '은행 번호표 받았어요', 'score': 0.84}],
    },
    {
        'keywords': [{'keyword': '감사', 'confidence': 0.95}],
        'sentence_candidates': [{'sentence': '감사합니다', 'score': 0.93}],
    },
]

_cursor = itertools.cycle(_SCRIPTED_RESULTS)


def is_mock():
    return not settings.AI_SERVER_URL


def _fake_predict_sign_keywords():
    """28.5: 실제 AI 모델이 준비되지 않아도 데이터 흐름을 먼저 검증합니다."""
    scripted = next(_cursor)

    return {
        'status': 'COMPLETED',
        'keywords': scripted['keywords'],
        'sentence_candidates': scripted['sentence_candidates'],
        'model_version': 'mock-v1',
        'processing_ms': 100,
    }


def _build_ai_request_payload(translation, video_url):
    return {
        'translation_id': translation.id,
        'capture_id': translation.capture_id,
        'device_id': translation.device_id,
        'video_url': video_url,
    }


def predict_sign_keywords(translation, video_url):
    """인-백을 호출해 키워드와 문장 후보를 받아옵니다.

    27장 원칙: 인식 실패와 서버 장애를 구분해야 하므로, 여기서는 장애만
    예외로 올리고 인식 실패(빈 결과)는 호출부가 status로 처리합니다.
    """
    if is_mock():
        return _fake_predict_sign_keywords()

    try:
        response = requests.post(
            settings.AI_SERVER_URL,
            json=_build_ai_request_payload(translation, video_url),
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        # 장시간 처리는 타임아웃을 설정합니다 (27장).
        raise ApiError(ErrorCode.AI_TIMEOUT, '분석이 시간 내에 끝나지 않았습니다.') from exc
    except requests.RequestException as exc:
        raise ApiError(
            ErrorCode.AI_SERVER_UNAVAILABLE, 'AI 서버에 연결하지 못했습니다.'
        ) from exc

    if response.status_code >= 300:
        raise ApiError(ErrorCode.AI_INFERENCE_FAILED, f'AI 서버 오류 {response.status_code}')

    try:
        return response.json()
    except ValueError as exc:
        raise ApiError(ErrorCode.INVALID_AI_RESPONSE, 'AI 응답을 읽지 못했습니다.') from exc
