"""DRF 예외를 명세 8장의 공통 오류 형식으로 변환합니다.

    {"error": {"code": "...", "message": "...", "fields": {...}}}

27장 원칙: 프론트에는 내부 예외 전체가 아니라 정리된 오류 코드와 안내 메시지만 전달합니다.
"""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from project.errors import ApiError, ErrorCode

logger = logging.getLogger(__name__)


def error_response(code, message, status_code, fields=None):
    body = {'code': code, 'message': message}
    if fields:
        body['fields'] = fields
    return Response({'error': body}, status=status_code)


def _flatten_validation_detail(detail):
    """DRF ValidationError의 detail을 명세의 fields 형태로 정리합니다."""
    if isinstance(detail, dict):
        return {
            key: [str(item) for item in (value if isinstance(value, list) else [value])]
            for key, value in detail.items()
        }
    if isinstance(detail, list):
        return {'non_field_errors': [str(item) for item in detail]}
    return None


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return error_response(exc.code, exc.message, exc.status_code, exc.fields)

    if isinstance(exc, ValidationError):
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            '입력값을 확인해주세요.',
            status.HTTP_400_BAD_REQUEST,
            _flatten_validation_detail(exc.detail),
        )

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        # 만료된 토큰과 아예 없는 토큰을 구분해야 프론트가
        # "갱신 후 재시도"와 "로그인 화면으로"를 나눌 수 있습니다 (명세 10장).
        detail_code = getattr(exc, 'detail', None)
        code = ErrorCode.AUTHENTICATION_REQUIRED
        if getattr(detail_code, 'code', '') in ('token_not_valid', 'token_expired'):
            code = ErrorCode.TOKEN_EXPIRED
        return error_response(code, str(exc.detail), status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, PermissionDenied):
        return error_response(
            ErrorCode.CONVERSATION_ACCESS_DENIED,
            '접근 권한이 없습니다.',
            status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, Http404):
        return error_response(
            ErrorCode.CONVERSATION_NOT_FOUND,
            '대상을 찾을 수 없습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    response = exception_handler(exc, context)

    if response is None:
        # DRF가 처리하지 못한 예외 = 서버 내부 오류.
        # 내부 예외는 로그로만 남기고 사용자에게는 정리된 문구만 보냅니다.
        logger.exception('Unhandled exception in %s', context.get('view'))
        return error_response(
            ErrorCode.INTERNAL_SERVER_ERROR,
            '서버에 문제가 발생했습니다.',
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return error_response(
        ErrorCode.VALIDATION_ERROR,
        str(getattr(exc, 'detail', exc)),
        response.status_code,
    )
