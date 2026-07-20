"""쓰기와 외부 연동. 명세 20장 체크리스트: 쓰기는 services.py에 작성합니다."""

from django.utils import timezone
from rest_framework import status

from accounts.models import Friendship, FriendRequestStatus, User
from accounts.selectors import find_friendship_between, get_user_by_nickname
from project.errors import ApiError, ErrorCode


def create_user(nickname, password, role):
    return User.objects.create_user(
        username=nickname,
        password=password,
        role=role,
    )


def update_user_nickname(user, nickname):
    user.username = nickname
    user.save(update_fields=['username'])
    return user


def update_user_display_name(user, display_name):
    user.display_name = display_name
    user.save(update_fields=['display_name'])
    return user


def complete_user_onboarding(user):
    user.onboarding_completed = True
    user.save(update_fields=['onboarding_completed'])
    return user


def send_friend_request(user, nickname):
    target = get_user_by_nickname(nickname)

    if target is None:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            '입력값을 확인해주세요.',
            status.HTTP_404_NOT_FOUND,
            fields={'nickname': ['일치하는 아이디를 찾지 못했어요. 아이디와 순서를 다시 확인해 주세요.']},
        )

    if target.id == user.id:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            '입력값을 확인해주세요.',
            fields={'nickname': ['자기 자신에게는 친구 신청할 수 없습니다.']},
        )

    existing = find_friendship_between(user, target)

    if existing is not None:
        if existing.status == FriendRequestStatus.ACCEPTED:
            raise ApiError(
                ErrorCode.ALREADY_JOINED,
                '이미 친구입니다.',
                status.HTTP_409_CONFLICT,
            )

        if existing.status == FriendRequestStatus.PENDING:
            # 상대가 나에게 이미 신청해둔 상태라면, 다시 신청하는 대신 바로 수락합니다.
            if existing.addressee_id == user.id:
                return accept_friend_request(user, existing.id)

            raise ApiError(
                ErrorCode.ALREADY_JOINED,
                '이미 신청한 사용자입니다.',
                status.HTTP_409_CONFLICT,
            )

        # 거절당한 이력이 있으면 같은 행을 다시 PENDING으로 되돌립니다
        # (unique 제약 때문에 새 행을 만들 수 없습니다).
        existing.requester = user
        existing.addressee = target
        existing.status = FriendRequestStatus.PENDING
        existing.responded_at = None
        existing.save()
        return existing

    return Friendship.objects.create(requester=user, addressee=target)


def _respond(user, friendship_id, new_status):
    friendship = Friendship.objects.filter(pk=friendship_id).first()

    if friendship is None:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            '친구 신청을 찾을 수 없습니다.',
            status.HTTP_404_NOT_FOUND,
        )

    # 받은 사람만 답할 수 있습니다.
    if friendship.addressee_id != user.id:
        raise ApiError(
            ErrorCode.CONVERSATION_ACCESS_DENIED,
            '이 신청에 답할 권한이 없습니다.',
            status.HTTP_403_FORBIDDEN,
        )

    if friendship.status != FriendRequestStatus.PENDING:
        raise ApiError(
            ErrorCode.ALREADY_JOINED,
            '이미 처리된 신청입니다.',
            status.HTTP_409_CONFLICT,
        )

    friendship.status = new_status
    friendship.responded_at = timezone.now()
    friendship.save(update_fields=['status', 'responded_at'])
    return friendship


def accept_friend_request(user, friendship_id):
    return _respond(user, friendship_id, FriendRequestStatus.ACCEPTED)


def reject_friend_request(user, friendship_id):
    return _respond(user, friendship_id, FriendRequestStatus.REJECTED)
