from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import Friendship, User, UserRole, nickname_validator


class UserSerializer(serializers.ModelSerializer):
    # 명세는 nickname을 쓰고, 모델은 username에 담습니다.
    nickname = serializers.CharField(source='username', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'nickname', 'role', 'onboarding_completed']


class SignupSerializer(serializers.ModelSerializer):
    # 농인은 이모지 조합, 청인은 글자 — 둘 다 이 한 필드에 들어옵니다.
    nickname = serializers.CharField(
        source='username',
        max_length=30,
        validators=[nickname_validator],
    )
    # 농인은 숫자 PIN을 씁니다. 어느 쪽이든 여기서는 형식을 강제하지 않고
    # 화면이 입력 방식을 정합니다 — 역할과 인증 형식을 묶으면 나중에 바꾸기 어렵습니다.
    #
    # 이 문구는 프론트가 그대로 화면에 띄웁니다(fields로 전달). DRF 기본 문구
    # ("이 필드의 글자 수가 적어도 4 이상인지 확인하세요")는 사람이 읽을 말이 아닙니다.
    password = serializers.CharField(
        write_only=True,
        min_length=4,
        error_messages={
            'min_length': '비밀번호는 4자 이상이어야 합니다.',
            'blank': '비밀번호를 입력해주세요.',
        },
    )
    role = serializers.ChoiceField(choices=UserRole.choices)

    class Meta:
        model = User
        fields = ['nickname', 'password', 'role']

    # DRF는 source가 아니라 **필드 이름**으로 validate_<이름>을 찾습니다.
    # validate_username으로 두면 영영 호출되지 않아, 중복 닉네임이 검사를 통과한 뒤
    # DB UNIQUE 제약에 부딪혀 500이 납니다.
    def validate_nickname(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('닉네임을 입력해주세요.')
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('이미 사용 중인 닉네임입니다.')
        return value


class LoginSerializer(serializers.Serializer):
    nickname = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['nickname'], password=attrs['password'])

        if user is None:
            # 어느 쪽이 틀렸는지 알려주지 않습니다 (계정 존재 여부 노출 방지).
            raise serializers.ValidationError('invalid_credentials')

        attrs['user'] = user
        return attrs


class NicknameUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=30, validators=[nickname_validator])

    def validate_nickname(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('닉네임을 입력해주세요.')

        user = self.context['request'].user
        if User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('이미 사용 중인 닉네임입니다.')
        return value


class FriendshipSerializer(serializers.ModelSerializer):
    """친구 신청 한 건. 목록에서 상대가 누구인지 바로 보이게 합니다."""

    requester = UserSerializer(read_only=True)
    addressee = UserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'requester', 'addressee', 'status', 'created_at']


class FriendRequestCreateSerializer(serializers.Serializer):
    nickname = serializers.CharField()
