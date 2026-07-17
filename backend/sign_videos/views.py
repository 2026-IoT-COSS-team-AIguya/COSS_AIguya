from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from project.errors import ApiError, ErrorCode
from sign_videos import selectors, services
from sign_videos.serializers import (
    QuickKeywordSerializer,
    SignVideoSequenceItemSerializer,
    SignVideoSequencePreviewSerializer,
    SignVideoSerializer,
)


class QuickKeywordListAPIView(APIView):
    def get(self, request):
        return Response(
            QuickKeywordSerializer(
                selectors.get_active_quick_keywords(), many=True
            ).data
        )


class SignVideoSearchAPIView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        videos = selectors.search_sign_videos(keyword or None)

        # 프론트가 keyword → emoji 사전을 만들 때 이 목록을 씁니다.
        return Response(
            [
                {
                    'position': index + 1,
                    'sign_video': SignVideoSerializer(
                        video, context={'request': request}
                    ).data,
                }
                for index, video in enumerate(videos)
            ]
        )


class SignVideoDetailAPIView(APIView):
    def get(self, request, video_id):
        video = selectors.get_sign_video_by_id(video_id)

        if video is None:
            raise ApiError(
                ErrorCode.SIGN_VIDEO_NOT_FOUND,
                '수어 영상을 찾을 수 없습니다.',
                status.HTTP_404_NOT_FOUND,
            )

        return Response(
            SignVideoSerializer(video, context={'request': request}).data
        )


class SignVideoSequencePreviewAPIView(APIView):
    """명세 7.2의 요청 형식: {"keywords": ["토요일", "약속", "미안하다"]}"""

    def post(self, request):
        serializer = SignVideoSequencePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sequence = services.build_sign_video_sequence(
            serializer.validated_data['keywords']
        )

        return Response(
            SignVideoSequenceItemSerializer(
                sequence, many=True, context={'request': request}
            ).data
        )
