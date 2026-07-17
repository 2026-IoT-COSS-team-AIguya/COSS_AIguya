from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import Friendship, User, UserRole


class UserSerializer(serializers.ModelSerializer):
    # 명세는 nickname을 쓰고, 모델은 username에 담습니다.
    nickname = serializers.CharField(source='username', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'nickname', 'role', 'onboarding_completed']


class SignupSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source='username', max_length=30)
    password = serializers.CharField(write_only=True, min_length=4)
    role = serializers.ChoiceField(choices=UserRole.choices)

    class Meta:
        model = User
        fields = ['nickname', 'password', 'role']

    def validate_username(self, value):
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
    nickname = serializers.CharField(max_length=30)

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
