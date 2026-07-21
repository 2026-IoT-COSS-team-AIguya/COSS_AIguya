"""쓰기와 외부 연동 (명세 20장 체크리스트)."""

import secrets

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import status

from accounts.selectors import get_user_by_nickname
from conversations.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageType,
    SignVideoSequenceItem,
)
from conversations.selectors import (
    get_conversation_participant,
    get_last_message,
)
from project.errors import ApiError, ErrorCode
from sign_videos.services import build_sign_video_sequence

_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_conversation_code():
    """헷갈리는 글자(0/O, 1/I)를 뺀 코드. 대면에서 불러주기 쉬워야 합니다."""
    for _ in range(10):
        code = ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        if not Conversation.objects.filter(code=code).exists():
            return code

    raise ApiError(
        ErrorCode.INTERNAL_SERVER_ERROR,
        '대화 코드를 만들지 못했습니다.',
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def check_conversation_access(conversation, user):
    """참여자가 아니면 막습니다. 조회/쓰기 진입점마다 호출합니다."""
    if get_conversation_participant(conversation, user) is None:
        raise ApiError(
            ErrorCode.CONVERSATION_ACCESS_DENIED,
            '이 대화에 접근할 권한이 없습니다.',
            status.HTTP_403_FORBIDDEN,
        )


@transaction.atomic
def create_conversation(user, title, icon='💬', category='', participant_nicknames=()):
    # 참가자(나 제외)를 먼저 확정합니다.
    targets = []
    for nickname in participant_nicknames:
        target = get_user_by_nickname(nickname)

        if target is None:
            raise ApiError(
                ErrorCode.VALIDATION_ERROR,
                '입력값을 확인해주세요.',
                fields={'participant_nicknames': [f'{nickname} 사용자를 찾을 수 없습니다.']},
            )

        if target.id != user.id and target not in targets:
            targets.append(target)

    # 1:1 대화는 같은 상대와 이미 방이 있으면 재사용합니다 — 안 그러면 양쪽이
    # 각각 "대화"를 누를 때 같은 상대와 방이 두 개씩 생깁니다.
    existing = _find_direct_conversation(user, targets)
    if existing is not None:
        return existing

    conversation = Conversation.objects.create(
        title=title,
        icon=icon,
        category=category,
        code=generate_conversation_code(),
    )

    ConversationParticipant.objects.create(conversation=conversation, user=user)

    for target in targets:
        ConversationParticipant.objects.get_or_create(
            conversation=conversation, user=target
        )

    return conversation


def _find_direct_conversation(user, targets):
    """나와 상대 단둘(참가자 정확히 2명)인 기존 대화를 찾습니다. 없으면 None."""
    if len(targets) != 1:
        return None

    target = targets[0]

    # 나와 상대가 모두 든 대화방 후보를 먼저 추립니다.
    candidate_ids = (
        ConversationParticipant.objects.filter(user__in=[user, target])
        .values('conversation')
        .annotate(matched=Count('user', distinct=True))
        .filter(matched=2)
        .values_list('conversation', flat=True)
    )

    # 그중 참가자가 정확히 2명인 방(= 단둘 대화)만 재사용합니다.
    return (
        Conversation.objects.filter(id__in=candidate_ids)
        .annotate(total=Count('participants'))
        .filter(total=2)
        .first()
    )


def join_conversation(user, code):
    conversation = Conversation.objects.filter(code=code).first()

    if conversation is None:
        raise ApiError(
            ErrorCode.CONVERSATION_NOT_FOUND,
            '대화를 찾을 수 없습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    if get_conversation_participant(conversation, user) is not None:
        # 명세 9장: 이미 대화 참여는 409 Conflict
        raise ApiError(
            ErrorCode.ALREADY_JOINED,
            '이미 참여한 대화입니다.',
            status.HTTP_409_CONFLICT,
        )

    ConversationParticipant.objects.create(conversation=conversation, user=user)
    return conversation


def leave_conversation(user, conversation):
    participant = get_conversation_participant(conversation, user)

    if participant is not None:
        participant.delete()


def mark_conversation_as_read(user, conversation):
    participant = get_conversation_participant(conversation, user)

    if participant is None:
        return

    last = get_last_message(conversation)
    participant.last_read_message_id = last.id if last else 0
    participant.save(update_fields=['last_read_message_id'])


def touch_conversation(conversation):
    """목록 정렬 기준을 갱신합니다. 메시지가 생길 때마다 호출합니다."""
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])


def _create_message(conversation, sender, message_type, **kwargs):
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        type=message_type,
        **kwargs,
    )
    touch_conversation(conversation)
    return message


def create_text_message(conversation, sender, text):
    check_conversation_access(conversation, sender)
    return _create_message(conversation, sender, MessageType.TEXT, text=text)


def create_translation_message(conversation, sender, translation):
    """분석이 끝난 인식 결과를 대화에 올립니다.

    명세 20장: 콜백 중복 수신에도 결과 저장이 중복되지 않아야 하므로,
    이미 메시지가 있으면 새로 만들지 않고 기존 것을 돌려줍니다.
    """
    existing = Message.objects.filter(sign_translation=translation).first()

    if existing is not None:
        return existing

    return _create_message(
        conversation,
        sender,
        MessageType.SIGN_TRANSLATION,
        sign_translation=translation,
    )


@transaction.atomic
def create_sign_video_sequence_message(conversation, sender, keywords):
    check_conversation_access(conversation, sender)

    # 명세 7.2: 요청받은 키워드 순서를 유지합니다.
    sequence = build_sign_video_sequence(keywords)

    message = _create_message(conversation, sender, MessageType.SIGN_VIDEO_SEQUENCE)

    SignVideoSequenceItem.objects.bulk_create(
        [
            SignVideoSequenceItem(
                message=message,
                sign_video=item['sign_video'],
                position=item['position'],
            )
            for item in sequence
        ]
    )

    return message
