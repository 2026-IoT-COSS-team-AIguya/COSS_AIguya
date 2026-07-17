from django.conf import settings
from django.db import models


class MessageType(models.TextChoices):
    """명세 12장: 프론트는 메시지를 이 세 유형으로 구분해 표시합니다.

    양쪽 백엔드가 동일한 Enum을 사용해야 합니다 (명세 20장 체크리스트).
    필담은 대응 유형이 없어 TEXT로 저장합니다.
    """

    TEXT = 'TEXT', '텍스트'
    SIGN_TRANSLATION = 'SIGN_TRANSLATION', '수어 인식 결과'
    SIGN_VIDEO_SEQUENCE = 'SIGN_VIDEO_SEQUENCE', '수어 영상 시퀀스'


class Conversation(models.Model):
    """대화방.

    명세 20장 체크리스트: Room 대신 Conversation 용어를 사용합니다.
    """

    title = models.CharField(max_length=100)
    icon = models.CharField(max_length=8, default='💬')
    category = models.CharField(max_length=100, blank=True)
    # 친구가 아니어도 코드로 참여할 수 있게 합니다 (대면 시나리오).
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # 목록 정렬용. 메시지가 생길 때마다 갱신합니다 (touch_conversation).
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_participations',
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    # 안 읽은 개수 계산 기준. mark_conversation_as_read가 갱신합니다.
    last_read_message_id = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'user'],
                name='unique_conversation_participant',
            ),
        ]

    def __str__(self):
        return f'{self.user} in {self.conversation}'


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    type = models.CharField(max_length=30, choices=MessageType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    # TEXT
    text = models.TextField(blank=True)

    # SIGN_TRANSLATION — recognitions를 직접 import하면 순환 참조가 되므로 문자열 참조를 씁니다.
    sign_translation = models.OneToOneField(
        'recognitions.SignTranslation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='message',
    )

    class Meta:
        ordering = ['id']
        indexes = [
            # 명세 20장 체크리스트: 메시지 폴링 조회를 위해 (conversation, id) 인덱스.
            # after_id 방식 조회가 이 인덱스를 그대로 탑니다.
            models.Index(fields=['conversation', 'id'], name='msg_conv_id_idx'),
        ]

    def __str__(self):
        return f'[{self.type}] {self.sender} @ {self.conversation_id}'


class SignVideoSequenceItem(models.Model):
    """SIGN_VIDEO_SEQUENCE 메시지에 붙는 영상 순서.

    명세 7.2: 백엔드는 요청받은 키워드 순서를 유지해야 하고,
    재생 순서는 position으로 전달합니다.
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='sign_video_sequence',
    )
    sign_video = models.ForeignKey(
        'sign_videos.SignVideo',
        on_delete=models.CASCADE,
        related_name='sequence_items',
    )
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'position'],
                name='unique_sequence_position',
            ),
        ]

    def __str__(self):
        return f'{self.position}. {self.sign_video}'
