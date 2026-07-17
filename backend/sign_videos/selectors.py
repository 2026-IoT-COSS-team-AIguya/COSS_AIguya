"""조회 전용 (명세 20장 체크리스트)."""

from sign_videos.models import QuickKeyword, SignVideo


def get_sign_video_by_id(video_id):
    return SignVideo.objects.filter(pk=video_id, is_active=True).first()


def find_sign_video_by_keyword(keyword):
    return SignVideo.objects.filter(keyword=keyword, is_active=True).first()


def find_sign_videos_by_keywords(keywords):
    """키워드 여러 개를 한 번에 조회해 keyword → SignVideo 로 돌려줍니다.

    호출부가 요청 순서를 유지해야 하므로(명세 7.2) 리스트가 아니라 dict를 줍니다.
    """
    videos = SignVideo.objects.filter(keyword__in=keywords, is_active=True)
    return {video.keyword: video for video in videos}


def search_sign_videos(keyword=None):
    queryset = SignVideo.objects.filter(is_active=True)

    if keyword:
        queryset = queryset.filter(keyword__icontains=keyword)

    return queryset


def get_active_quick_keywords():
    return (
        QuickKeyword.objects.filter(is_active=True, sign_video__is_active=True)
        .select_related('sign_video')
    )
