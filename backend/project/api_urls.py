"""/api/v1/ 아래 전체 경로.

프론트(frontend/lib/api/endpoints.ts)가 호출하는 주소와 1:1로 맞춰져 있습니다.
"""

from django.urls import path

from accounts import views as accounts_views
from conversations import views as conversations_views
from recognitions import views as recognitions_views
from sign_videos import views as sign_videos_views

urlpatterns = [
    # --- accounts ---
    path('auth/signup/', accounts_views.SignupAPIView.as_view()),
    path('auth/login/', accounts_views.LoginAPIView.as_view()),
    path('auth/refresh/', accounts_views.TokenRefreshAPIView.as_view()),
    path('auth/logout/', accounts_views.LogoutAPIView.as_view()),
    path('users/me/', accounts_views.MyProfileAPIView.as_view()),
    path('users/me/nickname/', accounts_views.NicknameUpdateAPIView.as_view()),
    path(
        'users/me/onboarding-complete/',
        accounts_views.OnboardingCompleteAPIView.as_view(),
    ),

    # --- friends ---
    path('friends/', accounts_views.FriendListAPIView.as_view()),
    path('friends/requests/', accounts_views.FriendRequestAPIView.as_view()),
    path(
        'friends/requests/<int:friendship_id>/accept/',
        accounts_views.FriendRequestAcceptAPIView.as_view(),
    ),
    path(
        'friends/requests/<int:friendship_id>/reject/',
        accounts_views.FriendRequestRejectAPIView.as_view(),
    ),

    # --- conversations ---
    path('conversations/', conversations_views.ConversationListCreateAPIView.as_view()),
    path('conversations/join/', conversations_views.ConversationJoinAPIView.as_view()),
    path(
        'conversations/<int:conversation_id>/',
        conversations_views.ConversationDetailAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/leave/',
        conversations_views.ConversationLeaveAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/read/',
        conversations_views.ConversationReadAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/messages/',
        conversations_views.ConversationMessageListAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/messages/text/',
        conversations_views.TextMessageCreateAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/messages/translation/',
        conversations_views.TranslationMessageCreateAPIView.as_view(),
    ),
    path(
        'conversations/<int:conversation_id>/messages/sign-video-sequence/',
        conversations_views.SignVideoSequenceMessageCreateAPIView.as_view(),
    ),

    # --- translations ---
    path(
        'sign-translations/',
        recognitions_views.SignTranslationCreateAPIView.as_view(),
    ),
    # <int:translation_id> 보다 먼저 와야 'latest'가 숫자 변환에 걸리지 않습니다.
    path(
        'sign-translations/latest/',
        recognitions_views.SignTranslationLatestAPIView.as_view(),
    ),
    path(
        'sign-translations/<int:translation_id>/',
        recognitions_views.SignTranslationDetailAPIView.as_view(),
    ),
    path(
        'sign-translations/<int:translation_id>/retry/',
        recognitions_views.SignTranslationRetryAPIView.as_view(),
    ),
    path(
        'sign-translations/<int:translation_id>/result-callback/',
        recognitions_views.SignTranslationResultCallbackAPIView.as_view(),
    ),

    # --- sign_videos ---
    path('quick-keywords/', sign_videos_views.QuickKeywordListAPIView.as_view()),
    path('sign-videos/', sign_videos_views.SignVideoSearchAPIView.as_view()),
    path(
        'sign-videos/sequence-preview/',
        sign_videos_views.SignVideoSequencePreviewAPIView.as_view(),
    ),
    path(
        'sign-videos/<int:video_id>/',
        sign_videos_views.SignVideoDetailAPIView.as_view(),
    ),
]
