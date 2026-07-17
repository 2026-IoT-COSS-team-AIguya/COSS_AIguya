"""프로젝트 공통 오류 코드와 예외.

이름은 팀이 확정한 API 명세 8장 기준입니다. 설계 초안 26장이 같은 뜻에
다른 이름(UNSUPPORTED_VIDEO_FORMAT / NO_SIGN_DETECTED)을 쓰지만 8장이 우선합니다.
26장에만 있던 코드는 아래에 병합했습니다.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class ErrorCode:
    # --- 명세 8장 ---
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    AUTHENTICATION_REQUIRED = 'AUTHENTICATION_REQUIRED'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    CONVERSATION_NOT_FOUND = 'CONVERSATION_NOT_FOUND'
    CONVERSATION_ACCESS_DENIED = 'CONVERSATION_ACCESS_DENIED'
    ALREADY_JOINED = 'ALREADY_JOINED'
    VIDEO_TOO_LARGE = 'VIDEO_TOO_LARGE'
    UNSUPPORTED_VIDEO_TYPE = 'UNSUPPORTED_VIDEO_TYPE'
    SIGN_NOT_DETECTED = 'SIGN_NOT_DETECTED'
    SIGN_VIDEO_NOT_FOUND = 'SIGN_VIDEO_NOT_FOUND'
    AI_SERVER_UNAVAILABLE = 'AI_SERVER_UNAVAILABLE'
    INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR'

    # --- 26.1 영상 업로드 (추가분) ---
    VIDEO_REQUIRED = 'VIDEO_REQUIRED'
    DUPLICATE_CAPTURE_ID = 'DUPLICATE_CAPTURE_ID'
    VIDEO_SAVE_FAILED = 'VIDEO_SAVE_FAILED'

    # --- 26.2 AI 처리 (추가분) ---
    AI_TIMEOUT = 'AI_TIMEOUT'
    AI_INFERENCE_FAILED = 'AI_INFERENCE_FAILED'
    LOW_CONFIDENCE = 'LOW_CONFIDENCE'
    INVALID_AI_RESPONSE = 'INVALID_AI_RESPONSE'

    # --- 26.3 oneM2M (추가분) ---
    ONEM2M_AUTH_FAILED = 'ONEM2M_AUTH_FAILED'
    ONEM2M_CONNECTION_FAILED = 'ONEM2M_CONNECTION_FAILED'
    ONEM2M_RESOURCE_NOT_FOUND = 'ONEM2M_RESOURCE_NOT_FOUND'
    ONEM2M_DUPLICATE_RESOURCE = 'ONEM2M_DUPLICATE_RESOURCE'
    ONEM2M_CREATE_FAILED = 'ONEM2M_CREATE_FAILED'
    ONEM2M_INVALID_RESPONSE = 'ONEM2M_INVALID_RESPONSE'


class ApiError(APIException):
    """명세 8장 형식으로 직렬화되는 예외.

    27장 원칙: 사용자에게 노출할 정리된 코드/메시지만 담고,
    내부 예외 전체는 로그로 남깁니다.
    """

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code, message, status_code=None, fields=None):
        self.code = code
        self.message = message
        self.fields = fields
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=message)


class OneM2MError(Exception):
    """oneM2M 연동 실패.

    27장 원칙에 따라 이 예외는 요청을 실패시키지 않습니다.
    호출부가 잡아서 로그로만 남기고, 영상과 AI 결과는 그대로 둡니다.
    """

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f'{code}: {message}')
