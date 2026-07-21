from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from project.errors import ApiError, ErrorCode
from recognitions import services
from recognitions.models import SignTranslation
from recognitions.serializers import (
    CaptureTargetSerializer,
    SignTranslationCreatedSerializer,
    SignTranslationCreateSerializer,
    SignTranslationDetailSerializer,
)


def _get_translation_for_user(translation_id, user):
    translation = (
        SignTranslation.objects.filter(pk=translation_id)
        .select_related('conversation', 'requester')
        .prefetch_related('recognized_keywords', 'sentence_candidates')
        .first()
    )

    if translation is None:
        raise ApiError(
            ErrorCode.CONVERSATION_NOT_FOUND,
            '번역 작업을 찾을 수 없습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    # 채팅 모드 건은 같은 대화 참여자만 볼 수 있습니다.
    if translation.conversation_id:
        if translation.conversation.participants.filter(user=user).exists():
            return translation
    # 번역기 모드(대면) 건은 대화방이 없으므로 올린 본인만 볼 수 있습니다.
    elif translation.requester_id == user.id:
        return translation

    raise ApiError(
        ErrorCode.CONVERSATION_ACCESS_DENIED,
        '이 결과에 접근할 권한이 없습니다.',
        status.HTTP_403_FORBIDDEN,
    )


class CaptureTargetAPIView(APIView):
    """지금 촬영하면 결과가 어디로 갈지 등록합니다.

    촬영은 아두이노 물리 버튼이 시작하므로, 라즈베리파이는 사용자가 채팅방을
    보고 있는지 번역기를 보고 있는지 알 수 없습니다. 화면을 옮길 때마다 프론트가
    여기에 등록해두면, 업로드가 들어올 때 백엔드가 읽어서 라우팅합니다.

    요청: {"conversation_id": 3} → 3번 대화방으로
          {"conversation_id": null} → 번역기 모드(대면)
    """

    def put(self, request):
        serializer = CaptureTargetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = services.set_capture_target(
            request.user,
            serializer.validated_data.get('conversation_id'),
        )

        return Response(
            {
                'conversation_id': target.conversation_id,
                'mode': 'CHAT' if target.conversation_id else 'TRANSLATOR',
            }
        )


class SignTranslationCreateAPIView(APIView):
    """명세 7.1: multipart/form-data, 필드명 input_video."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SignTranslationCreateSerializer(data=request.data)

        if not serializer.is_valid():
            errors = serializer.errors.get('input_video', [])
            codes = [str(item) for item in errors]

            # 명세 9장: 형식 오류는 415, 용량 초과는 413
            if 'unsupported_video_type' in codes:
                raise ApiError(
                    ErrorCode.UNSUPPORTED_VIDEO_TYPE,
                    '지원하지 않는 영상 형식입니다.',
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )

            if 'video_too_large' in codes:
                raise ApiError(
                    ErrorCode.VIDEO_TOO_LARGE,
                    '영상 크기가 너무 큽니다.',
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            if 'input_video' in serializer.errors:
                raise ApiError(
                    ErrorCode.VIDEO_REQUIRED,
                    '영상 파일을 첨부해주세요.',
                    fields=serializer.errors,
                )

            serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        translation = services.create_sign_translation(
            user=request.user,
            conversation_id=data.get('conversation_id'),
            input_video=data['input_video'],
            capture_id=data.get('capture_id', ''),
            device_id=data.get('device_id', ''),
        )

        video_url = services.build_video_url(translation, request)

        # 28.6: 영상 업로드 후 메타데이터 등록. 실패해도 업로드는 성공입니다 (27장).
        services.try_register_video_metadata(translation, video_url)

        # 분석은 백그라운드로 넘기고 바로 응답합니다.
        services.submit_translation_to_ai(translation, video_url)

        # 명세 9장: AI 분석 요청 접수는 202 Accepted
        return Response(
            SignTranslationCreatedSerializer(translation).data,
            status=status.HTTP_202_ACCEPTED,
        )


class SignTranslationLatestAPIView(APIView):
    """번역기 화면이 지켜보는 "가장 최근 촬영".

    촬영은 웹 버튼이 아니라 **아두이노 물리 버튼**이 시작합니다. 프론트는 업로드
    응답으로 id를 받을 수 없으므로, 대신 최근 건을 폴링해서 화면에 띄웁니다.

    번역기 모드(대면)라 대화방이 없는 건만 봅니다.
    """

    def get(self, request):
        translation = (
            SignTranslation.objects.filter(
                requester=request.user,
                conversation__isnull=True,
            )
            .prefetch_related('recognized_keywords', 'sentence_candidates')
            .order_by('-id')
            .first()
        )

        # 아직 아무것도 안 찍었으면 빈 상태입니다. 404가 아니라 null을 줍니다 —
        # 폴링하는 쪽이 매번 오류를 처리하게 만들 이유가 없습니다.
        if translation is None:
            return Response({'translation': None})

        return Response(
            {'translation': SignTranslationDetailSerializer(translation).data}
        )


class SignTranslationDetailAPIView(APIView):
    """명세 5.2: 프론트가 1초마다 조회하고, COMPLETED/FAILED면 중지합니다."""

    def get(self, request, translation_id):
        translation = _get_translation_for_user(translation_id, request.user)

        # 명세 9장: 인식 실패는 요청이 정상 처리된 것이므로 200 OK + status FAILED.
        return Response(SignTranslationDetailSerializer(translation).data)


class SignTranslationRetryAPIView(APIView):
    def post(self, request, translation_id):
        translation = _get_translation_for_user(translation_id, request.user)

        services.retry_sign_translation(
            translation,
            services.build_video_url(translation, request),
        )

        return Response(
            SignTranslationCreatedSerializer(translation).data,
            status=status.HTTP_202_ACCEPTED,
        )


class SignTranslationResultCallbackAPIView(APIView):
    """인-백이 send_translation_result로 호출하는 엔드포인트.

    명세 20장: 사용자 JWT가 아니라 내부 API Key로 인증합니다.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, translation_id):
        if request.headers.get('X-Internal-Api-Key') != settings.AI_CALLBACK_API_KEY:
            raise ApiError(
                ErrorCode.AUTHENTICATION_REQUIRED,
                '내부 인증에 실패했습니다.',
                status.HTTP_401_UNAUTHORIZED,
            )

        translation = (
            SignTranslation.objects.filter(pk=translation_id)
            .select_related('conversation', 'requester')
            .first()
        )

        if translation is None:
            raise ApiError(
                ErrorCode.CONVERSATION_NOT_FOUND,
                '번역 작업을 찾을 수 없습니다.',
                status.HTTP_404_NOT_FOUND,
            )

        # 명세 20장: 콜백 중복 수신에도 결과가 중복 저장되지 않아야 합니다.
        if translation.is_settled:
            return Response(SignTranslationDetailSerializer(translation).data)

        translation = services.save_translation_result(translation, request.data)

        return Response(SignTranslationDetailSerializer(translation).data)
