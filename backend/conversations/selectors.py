"""조회 전용 (명세 20장 체크리스트)."""

from conversations.models import Conversation, ConversationParticipant, Message

# 메시지를 직렬화할 때마다 N+1 쿼리가 나지 않도록 미리 당겨옵니다.
_MESSAGE_RELATED = (
    'sender',
    'sign_translation',
)
_MESSAGE_PREFETCH = (
    'sign_translation__recognized_keywords',
    'sign_translation__sentence_candidates',
    'sign_video_sequence__sign_video',
)


def get_conversation_by_id(conversation_id):
    return (
        Conversation.objects.filter(pk=conversation_id)
        .prefetch_related('participants__user')
        .first()
    )


def get_conversation_by_code(code):
    return Conversation.objects.filter(code=code).first()


def get_user_conversations(user):
    return (
        Conversation.objects.filter(participants__user=user)
        .prefetch_related('participants__user', 'messages')
        .distinct()
    )


def get_conversation_participant(conversation, user):
    return ConversationParticipant.objects.filter(
        conversation=conversation, user=user
    ).first()


def get_conversation_participants(conversation):
    return conversation.participants.select_related('user')


def _message_queryset(conversation_id):
    return (
        Message.objects.filter(conversation_id=conversation_id)
        .select_related(*_MESSAGE_RELATED)
        .prefetch_related(*_MESSAGE_PREFETCH)
        .order_by('id')
    )


def fetch_initial_messages(conversation_id, limit=50):
    """방에 처음 들어갔을 때 보여줄 최근 메시지."""
    recent = list(_message_queryset(conversation_id).reverse()[:limit])
    return list(reversed(recent))


def fetch_messages_after(conversation_id, after_id):
    """명세 5.1 / 12장: 신규 메시지는 after_id 방식으로 받아갑니다.

    (conversation, id) 인덱스를 그대로 타는 조회입니다 (명세 20장 체크리스트).
    """
    queryset = _message_queryset(conversation_id)

    if after_id:
        queryset = queryset.filter(id__gt=after_id)

    return queryset


def get_last_message(conversation):
    return conversation.messages.order_by('-id').first()


def get_unread_message_count(conversation, user):
    participant = get_conversation_participant(conversation, user)

    if participant is None:
        return 0

    return (
        conversation.messages.filter(id__gt=participant.last_read_message_id)
        .exclude(sender=user)
        .count()
    )
