from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from project.errors import ApiError, ErrorCode
from sign_videos import selectors, services
from sign_videos.serializers import (
    QuickKeywordSerializer,
    SentenceToSequenceSerializer,
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


class SentenceToSequenceAPIView(APIView):
    """자유 문장 → 수어 영상 시퀀스.

    요청: {"sentence": "괜찮아 천천히 와"}
    응답: {"keywords": ["괜찮다", "천천히"], "sequence": [...]}

    문장을 Gemini가 사전 안의 키워드로 분해합니다. 사전에 겹치는 단어가 하나도
    없으면 오류가 아니라 빈 결과입니다 — 문장 분석 자체는 성공했으므로.
    """

    def post(self, request):
        serializer = SentenceToSequenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = services.build_sign_video_sequence_from_sentence(
            serializer.validated_data['sentence']
        )

        return Response(
            {
                'keywords': result['keywords'],
                'sequence': SignVideoSequenceItemSerializer(
                    result['sequence'], many=True, context={'request': request}
                ).data,
            }
        )
