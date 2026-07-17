"""조회 전용. 명세 20장 체크리스트: 조회는 selectors.py에 작성합니다."""

from django.db.models import Q

from accounts.models import Friendship, FriendRequestStatus, User


def get_user_by_nickname(nickname):
    return User.objects.filter(username=nickname).first()


def get_friends(user):
    """수락된 친구 목록.

    Friendship은 한 쌍당 한 행이라, 내가 신청한 쪽과 받은 쪽 양쪽을 봐야 합니다.
    """
    accepted = Friendship.objects.filter(
        Q(requester=user) | Q(addressee=user),
        status=FriendRequestStatus.ACCEPTED,
    ).select_related('requester', 'addressee')

    return [
        friendship.addressee if friendship.requester_id == user.id else friendship.requester
        for friendship in accepted
    ]


def get_incoming_friend_requests(user):
    """내가 수락/거절해야 할 신청."""
    return (
        Friendship.objects.filter(addressee=user, status=FriendRequestStatus.PENDING)
        .select_related('requester', 'addressee')
    )


def get_outgoing_friend_requests(user):
    """내가 보내고 답을 기다리는 신청."""
    return (
        Friendship.objects.filter(requester=user, status=FriendRequestStatus.PENDING)
        .select_related('requester', 'addressee')
    )


def find_friendship_between(user_a, user_b):
    """방향에 상관없이 두 사람 사이의 관계를 찾습니다."""
    return Friendship.objects.filter(
        Q(requester=user_a, addressee=user_b) | Q(requester=user_b, addressee=user_a)
    ).first()


def are_friends(user_a, user_b):
    friendship = find_friendship_between(user_a, user_b)
    return friendship is not None and friendship.status == FriendRequestStatus.ACCEPTED
