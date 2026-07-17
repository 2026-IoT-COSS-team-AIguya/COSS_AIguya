"""쓰기와 조합 (명세 20장 체크리스트)."""

from rest_framework import status

from project.errors import ApiError, ErrorCode
from sign_videos.selectors import find_sign_videos_by_keywords


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
