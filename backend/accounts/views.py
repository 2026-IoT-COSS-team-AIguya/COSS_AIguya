from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts import selectors, services
from accounts.serializers import (
    FriendRequestCreateSerializer,
    FriendshipSerializer,
    LoginSerializer,
    NicknameUpdateSerializer,
    SignupSerializer,
    UserSerializer,
)
from project.errors import ApiError, ErrorCode


def _set_refresh_cookie(response, refresh_token):
    """명세 10장: Refresh Token은 JSON 응답에 노출하지 않고 HttpOnly 쿠키로 전달합니다."""
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh_token),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        path='/',
    )
    return response


def _auth_response(user, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)

    response = Response(
        {
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
        },
        status=status_code,
    )
    return _set_refresh_cookie(response, refresh)


class SignupAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.create_user(
            nickname=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
            role=serializer.validated_data['role'],
        )

        # 명세 9장: 회원 생성 성공은 201 Created
        return _auth_response(user, status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            # 자격 증명 실패는 VALIDATION_ERROR가 아니라 INVALID_CREDENTIALS여야 합니다.
            raise ApiError(
                ErrorCode.INVALID_CREDENTIALS,
                '아이디 또는 비밀번호가 올바르지 않습니다.',
                status.HTTP_401_UNAUTHORIZED,
            )

        return _auth_response(serializer.validated_data['user'])


class TokenRefreshAPIView(APIView):
    """명세 10장: 401이 나면 프론트가 이걸 한 번 호출한 뒤 기존 요청을 재시도합니다."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)

        if not raw_token:
            raise ApiError(
                ErrorCode.AUTHENTICATION_REQUIRED,
                '로그인이 필요합니다.',
                status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_token)
        except TokenError:
            raise ApiError(
                ErrorCode.TOKEN_EXPIRED,
                '세션이 만료되었습니다.',
                status.HTTP_401_UNAUTHORIZED,
            )

        return Response({'access': str(refresh.access_token)})


class LogoutAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # 명세 9장: 로그아웃 성공은 204 No Content
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path='/')
        return response


class MyProfileAPIView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class NicknameUpdateAPIView(APIView):
    def patch(self, request):
        serializer = NicknameUpdateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        user = services.update_user_nickname(
            request.user,
            serializer.validated_data['nickname'],
        )
        return Response(UserSerializer(user).data)


class OnboardingCompleteAPIView(APIView):
    def post(self, request):
        user = services.complete_user_onboarding(request.user)
        return Response(UserSerializer(user).data)


class FriendListAPIView(APIView):
    """친구 목록 + 대기 중인 신청.

    시연에서 농인/청인이 서로를 찾아 대화를 시작하는 출발점입니다.
    """

    def get(self, request):
        return Response(
            {
                'friends': UserSerializer(
                    selectors.get_friends(request.user), many=True
                ).data,
                'incoming_requests': FriendshipSerializer(
                    selectors.get_incoming_friend_requests(request.user), many=True
                ).data,
                'outgoing_requests': FriendshipSerializer(
                    selectors.get_outgoing_friend_requests(request.user), many=True
                ).data,
            }
        )


class FriendRequestAPIView(APIView):
    def post(self, request):
        serializer = FriendRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        friendship = services.send_friend_request(
            request.user,
            serializer.validated_data['nickname'].strip(),
        )
        return Response(
            FriendshipSerializer(friendship).data,
            status=status.HTTP_201_CREATED,
        )


class FriendRequestAcceptAPIView(APIView):
    def post(self, request, friendship_id):
        friendship = services.accept_friend_request(request.user, friendship_id)
        return Response(FriendshipSerializer(friendship).data)


class FriendRequestRejectAPIView(APIView):
    def post(self, request, friendship_id):
        friendship = services.reject_friend_request(request.user, friendship_id)
        return Response(FriendshipSerializer(friendship).data)
