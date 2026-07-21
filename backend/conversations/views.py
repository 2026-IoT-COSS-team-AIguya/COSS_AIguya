from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from conversations import selectors, services
from conversations.serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationJoinSerializer,
    ConversationListSerializer,
    MessageSerializer,
    SignVideoSequenceMessageCreateSerializer,
    TextMessageCreateSerializer,
    TranslationMessageCreateSerializer,
)
from project.errors import ApiError, ErrorCode
from recognitions.models import SignTranslation


def _get_conversation_or_404(conversation_id):
    conversation = selectors.get_conversation_by_id(conversation_id)

    if conversation is None:
        raise ApiError(
            ErrorCode.CONVERSATION_NOT_FOUND,
            '대화를 찾을 수 없습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    return conversation


class ConversationListCreateAPIView(APIView):
    def get(self, request):
        conversations = selectors.get_user_conversations(request.user)
        return Response(
            ConversationListSerializer(
                conversations, many=True, context={'request': request}
            ).data
        )

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = services.create_conversation(
            user=request.user,
            title=serializer.validated_data['title'],
            icon=serializer.validated_data.get('icon', '💬'),
            category=serializer.validated_data.get('category', ''),
            participant_nicknames=serializer.validated_data.get(
                'participant_nicknames', []
            ),
        )

        # 명세 9장: 대화 생성 성공은 201 Created
        return Response(
            ConversationDetailSerializer(
                selectors.get_conversation_by_id(conversation.id),
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailAPIView(APIView):
    def get(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)
        services.check_conversation_access(conversation, request.user)

        return Response(
            ConversationDetailSerializer(
                conversation, context={'request': request}
            ).data
        )


class ConversationJoinAPIView(APIView):
    def post(self, request):
        serializer = ConversationJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = services.join_conversation(
            request.user, serializer.validated_data['code'].strip().upper()
        )

        return Response(
            ConversationDetailSerializer(
                selectors.get_conversation_by_id(conversation.id),
                context={'request': request},
            ).data
        )


class ConversationLeaveAPIView(APIView):
    def post(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)
        services.leave_conversation(request.user, conversation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationReadAPIView(APIView):
    def post(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)
        services.check_conversation_access(conversation, request.user)
        services.mark_conversation_as_read(request.user, conversation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationMessageListAPIView(APIView):
    """명세 5.1 / 12장: 2초 간격 폴링, 신규 메시지는 after_id로 받아갑니다."""

    def get(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)
        services.check_conversation_access(conversation, request.user)

        raw_after_id = request.query_params.get('after_id')

        try:
            after_id = int(raw_after_id) if raw_after_id else 0
        except ValueError:
            raise ApiError(
                ErrorCode.VALIDATION_ERROR,
                '입력값을 확인해주세요.',
                fields={'after_id': ['숫자여야 합니다.']},
            )

        messages = list(selectors.fetch_messages_after(conversation_id, after_id))

        # 신규분이 없어도 클라이언트가 커서를 유지할 수 있도록 after_id로 물러섭니다
        # (명세 5.1의 has_new_messages: false 예시).
        last_message_id = messages[-1].id if messages else after_id

        return Response(
            {
                'has_new_messages': bool(messages),
                'last_message_id': last_message_id,
                'messages': MessageSerializer(
                    messages, many=True, context={'request': request}
                ).data,
            }
        )


class TextMessageCreateAPIView(APIView):
    def post(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)

        serializer = TextMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = services.create_text_message(
            conversation, request.user, serializer.validated_data['text']
        )

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class TranslationMessageCreateAPIView(APIView):
    def post(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)
        services.check_conversation_access(conversation, request.user)

        serializer = TranslationMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        translation = SignTranslation.objects.filter(
            pk=serializer.validated_data['translation_id']
        ).first()

        if translation is None:
            raise ApiError(
                ErrorCode.CONVERSATION_NOT_FOUND,
                '번역 결과를 찾을 수 없습니다.',
                status.HTTP_404_NOT_FOUND,
            )

        message = services.create_translation_message(
            conversation, request.user, translation
        )

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class SignVideoSequenceMessageCreateAPIView(APIView):
    def post(self, request, conversation_id):
        conversation = _get_conversation_or_404(conversation_id)

        serializer = SignVideoSequenceMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = services.create_sign_video_sequence_message(
            conversation,
            request.user,
            serializer.validated_data['keywords'],
            text=serializer.validated_data.get('text', '').strip(),
        )

        # 방금 만든 시퀀스를 붙여서 돌려줘야 프론트가 바로 렌더할 수 있습니다.
        message = (
            selectors.fetch_messages_after(conversation.id, message.id - 1)
            .first()
        )

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
