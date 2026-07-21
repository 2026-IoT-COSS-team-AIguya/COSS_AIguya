from rest_framework import serializers

from accounts.serializers import UserSerializer
from conversations.models import Conversation, Message
from recognitions.serializers import SignTranslationDetailSerializer
from sign_videos.serializers import SignVideoSerializer


class ConversationParticipantSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='user.id')
    nickname = serializers.CharField(source='user.username')
    display_name = serializers.CharField(source='user.display_name')
    role = serializers.CharField(source='user.role')


class MessageSenderSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ['id', 'nickname', 'display_name', 'role']


class MessageSequenceItemSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    sign_video = SignVideoSerializer()


class MessageSerializer(serializers.ModelSerializer):
    sender = MessageSenderSerializer(read_only=True)
    sign_translation = SignTranslationDetailSerializer(read_only=True)
    sign_video_sequence = MessageSequenceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'type',
            'sender',
            'created_at',
            'text',
            'sign_translation',
            'sign_video_sequence',
        ]


class ConversationListSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'icon',
            'category',
            'code',
            'participants',
            'last_message_preview',
            'unread_count',
        ]

    def get_last_message_preview(self, obj):
        message = obj.messages.order_by('-id').first()

        if message is None:
            return None

        if message.type == 'TEXT':
            return message.text

        if message.type == 'SIGN_TRANSLATION':
            candidate = (
                message.sign_translation.sentence_candidates.first()
                if message.sign_translation
                else None
            )
            return candidate.sentence if candidate else '수어 분석 중…'

        emojis = ' '.join(
            item.sign_video.emoji for item in message.sign_video_sequence.all()
        )

        # 원문이 있으면 같이 붙입니다. 이모지만 있으면 목록에서 어떤 대화였는지
        # 떠올리기가 어렵습니다.
        if message.text:
            return f'{emojis} {message.text}' if emojis else message.text

        return emojis

    def get_unread_count(self, obj):
        user = self.context['request'].user
        participant = next(
            (p for p in obj.participants.all() if p.user_id == user.id), None
        )

        if participant is None:
            return 0

        return obj.messages.filter(id__gt=participant.last_read_message_id).exclude(
            sender_id=user.id
        ).count()


class ConversationDetailSerializer(ConversationListSerializer):
    pass


class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    icon = serializers.CharField(max_length=8, required=False, default='💬')
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    # 친구를 초대해서 방을 엽니다. 비우면 나 혼자인 방이 만들어집니다.
    participant_nicknames = serializers.ListField(
        child=serializers.CharField(max_length=30),
        required=False,
        default=list,
    )


class ConversationJoinSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)


class TextMessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('내용을 입력해주세요.')
        return value


class TranslationMessageCreateSerializer(serializers.Serializer):
    translation_id = serializers.IntegerField()


class SignVideoSequenceMessageCreateSerializer(serializers.Serializer):
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False,
    )
    # 청인이 실제로 친 문장. 키워드를 직접 골라 보낸 경우에는 원문이 없습니다.
    text = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=''
    )
