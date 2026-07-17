from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    SIGN_USER = 'SIGN_USER', '농인 (수어 사용자)'
    HEARING_USER = 'HEARING_USER', '비장애인 / 직원'


class User(AbstractUser):
    """서비스 사용자.

    로그인 식별자는 이메일이 아니라 닉네임입니다 (명세 10장의 로그인 응답 기준).
    AbstractUser의 username을 닉네임으로 그대로 쓰고, 명세가 쓰는 nickname이라는
    이름은 프로퍼티로 맞춥니다. 컬럼을 새로 만들면 username과 이중 관리가 됩니다.
    """

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.HEARING_USER,
    )
    onboarding_completed = models.BooleanField(default=False)

    # 시연은 노트북 두 대(농인/청인)로 로그인해서 진행하므로 이메일은 필수가 아닙니다.
    email = models.EmailField(blank=True)

    @property
    def nickname(self):
        return self.username

    @nickname.setter
    def nickname(self, value):
        self.username = value

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class FriendRequestStatus(models.TextChoices):
    PENDING = 'PENDING', '대기'
    ACCEPTED = 'ACCEPTED', '수락'
    REJECTED = 'REJECTED', '거절'


class Friendship(models.Model):
    """친구 관계.

    한 쌍당 한 행만 둡니다. 수락되면 양방향 친구로 취급하며,
    조회할 때 requester/addressee 어느 쪽이든 매칭합니다.
    """

    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
    )
    addressee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
    )
    status = models.CharField(
        max_length=20,
        choices=FriendRequestStatus.choices,
        default=FriendRequestStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # 같은 사람에게 두 번 신청하지 못하게 합니다.
            models.UniqueConstraint(
                fields=['requester', 'addressee'],
                name='unique_friendship_pair',
            ),
            # 자기 자신에게 친구 신청하는 행을 DB 차원에서 막습니다.
            models.CheckConstraint(
                condition=~models.Q(requester=models.F('addressee')),
                name='friendship_no_self',
            ),
        ]

    def __str__(self):
        return f'{self.requester} → {self.addressee} ({self.status})'
