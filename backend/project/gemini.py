"""Gemini 호출 공통 로직.

ai/sentence_generation/_llm_common.py 와 같은 계약(같은 SDK · 같은 모델 ·
JSON 모드 · 429/500/503 재시도)을 쓰되, 실패를 명세 8장의 ApiError로 옮깁니다.
ai/ 쪽은 CLI라 예외를 그대로 띄우면 되지만, 여기서는 HTTP 응답이 나가야 합니다.

ai/pipeline/recognize.py 를 직접 import하지 않는 이유:
그 모듈은 sign_recognition(torch · mediapipe)을 같이 끌고 오는데, 문장 분해에는
필요 없는 무게입니다. 인-백이 HTTP 서버로 뜨면 AI_SERVER_URL 경로로 옮겨갑니다.
"""

import json
import logging
import time

from django.conf import settings

from project.errors import ApiError, ErrorCode

logger = logging.getLogger(__name__)

# 쿼터 초과 · 서버 과부하 — 잠깐 쉬었다 재시도하면 되는 것들 (_llm_common.py와 동일).
_RETRYABLE_CODES = {429, 500, 503}
_MAX_RETRIES = 2


def is_configured():
    return bool(settings.GEMINI_API_KEY)


def _get_client():
    if not is_configured():
        raise ApiError(
            ErrorCode.AI_SERVER_UNAVAILABLE,
            '문장 분석 기능이 설정되지 않았습니다. 관리자에게 문의해주세요.',
        )

    # import를 함수 안에 두면, 키를 안 쓰는 배포에서 SDK가 없어도 서버가 뜹니다.
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_json(system_prompt, user_content, temperature):
    """JSON 모드로 호출해 dict로 파싱합니다."""
    from google.genai import errors as genai_errors
    from google.genai import types

    client = _get_client()

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type='application/json',
                    temperature=temperature,
                ),
            )
        except genai_errors.APIError as exc:
            if exc.code in _RETRYABLE_CODES and attempt < _MAX_RETRIES:
                time.sleep(1.5 * (attempt + 1))
                continue

            # 27장: 사용자에게는 정리된 메시지만, 내부 예외는 로그로.
            logger.exception('Gemini 호출 실패')
            raise ApiError(
                ErrorCode.AI_INFERENCE_FAILED,
                '문장을 분석하지 못했습니다. 잠시 후 다시 시도해주세요.',
            ) from exc

        try:
            # response_mime_type을 줘도 JSON 뒤에 여분 텍스트가 붙어 나올 때가 있어
            # (json.loads가 "Extra data"로 실패), 맨 앞 JSON 값 하나만 읽습니다.
            data, _ = json.JSONDecoder().raw_decode(response.text.strip())
            return data
        except (ValueError, AttributeError) as exc:
            logger.exception('Gemini 응답 파싱 실패: %r', response.text)
            raise ApiError(
                ErrorCode.INVALID_AI_RESPONSE,
                '문장을 분석하지 못했습니다. 잠시 후 다시 시도해주세요.',
            ) from exc
