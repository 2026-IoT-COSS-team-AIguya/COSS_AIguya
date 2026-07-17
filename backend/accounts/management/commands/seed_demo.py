"""시연용 초기 데이터.

    python manage.py seed_demo

여러 번 돌려도 안전합니다 (get_or_create 기반).

시연은 노트북 두 대로 농인(민지) / 청인(채진)이 각자 로그인해서 진행합니다.
대화방은 **비어 있는 상태로** 만듭니다 — 촬영해서 채우는 게 시연의 목적이라
메시지를 미리 넣지 않습니다.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import FriendRequestStatus, Friendship, User, UserRole
from conversations.models import Conversation, ConversationParticipant
from sign_videos.models import QuickKeyword, SignVideo

# (keyword, title, emoji, video 파일명)
# 영상은 AI 개발 완료 후 AI DB에서 공급될 예정이라, 지금 파일이 있는 3개만 예시로 씁니다.
SIGN_WORDS = [
    # 시나리오 1 · 친구
    ('약속', '약속', '🤝', 'promise_sign.mp4'),
    ('늦다', '늦다', '⏰', None),
    ('괜찮다', '괜찮다', '👌', None),
    ('천천히', '천천히', '🐢', None),
    ('지금', '지금', '⏱️', None),
    ('가다', '가다', '🏃', None),
    ('빨리', '빨리', '⚡', None),
    ('기대', '기대', '✨', None),
    ('놀다', '놀다', '🎮', None),
    ('신나다', '신나다', '🎉', None),
    ('대박', '대박', '🤩', None),
    ('좋다', '좋다', '👍', None),
    ('친구', '친구', '👫', None),
    ('반갑다', '반갑다', '🙌', None),
    # 시나리오 2 · 길찾기
    ('길', '길', '🛣️', None),
    ('모르다', '모르다', '🤷', None),
    ('어디', '어디', '📍', None),
    ('지하철', '지하철', '🚇', None),
    ('저기', '저기', '👉', None),
    ('오른쪽', '오른쪽', '➡️', None),
    ('가깝다', '가깝다', '🤏', None),
    ('알다', '알다', '💡', None),
    ('감사', '감사', '🙏', None),
    # 시나리오 3 · 병원
    ('오늘', '오늘', '📅', None),
    ('3시', '3시', '🕒', None),
    ('병원', '병원', '🏥', None),
    ('오다', '오다', '🚶', None),
    ('확인', '확인', '✅', None),
    ('도착', '도착', '🏁', None),
    ('대기', '대기', '🪑', None),
    ('의사', '의사', '🩺', None),
    # 시나리오 4 · 은행
    ('은행', '은행', '🏦', None),
    ('번호', '번호표', '🎫', None),
    ('받다', '받다', '🤲', None),
    ('신분증', '신분증', '🪪', None),
    ('잠깐', '잠깐', '✋', None),
    ('기다리다', '기다리다', '⏳', None),
    ('카드', '카드', '💳', None),
    ('1회', '한 번', '1️⃣', None),
    ('돈', '돈', '💰', None),
    ('얼마', '얼마', '❔', None),
    ('맞다', '맞다', '⭕', None),
    # 공통
    ('토요일', '토요일', '📆', 'saturday_sign.mp4'),
    ('미안', '미안하다', '🙇', 'sorry_sign.mp4'),
    ('화장실', '화장실', '🚻', None),
    ('도움', '도움', '🆘', None),
]

QUICK_KEYWORDS = [
    '약속', '늦다', '지금', '빨리', '가다',
    '어디', '감사', '확인', '도움', '화장실',
]

# 시연은 두 명이지만, DB에는 여러 계정을 넣어둡니다.
DEMO_USERS = [
    ('민지', UserRole.SIGN_USER),
    ('채진', UserRole.HEARING_USER),
    ('지호', UserRole.SIGN_USER),
    ('은우', UserRole.HEARING_USER),
    ('○○병원', UserRole.HEARING_USER),
]

DEMO_PASSWORD = 'password'

# 채팅 시나리오만 둡니다.
# 길찾기 · 은행 창구는 대면 번역기 시나리오라 대화방을 만들지 않습니다.
# (번역기 모드는 대화방 없이 그 자리에서 번역합니다.)
CONVERSATIONS = [
    ('친구 채팅', '👫', '일상 · 티키타카', 'FRIEND', ['민지', '채진']),
    ('병원 알림', '🏥', '중요 알림 · 건강검진', 'HOSPTL', ['민지', '○○병원']),
]


class Command(BaseCommand):
    help = '시연용 계정 · 대화 · 수어 사전을 만듭니다.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for nickname, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=nickname,
                defaults={'role': role, 'onboarding_completed': True},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[nickname] = user
        self.stdout.write(f'사용자 {len(users)}명')

        # 민지 ↔ 채진은 이미 친구인 상태로 시작합니다 (시연 시간 절약).
        # 나머지는 친구 추가 기능을 시연할 수 있게 남겨둡니다.
        Friendship.objects.get_or_create(
            requester=users['민지'],
            addressee=users['채진'],
            defaults={'status': FriendRequestStatus.ACCEPTED},
        )

        for keyword, title, emoji, filename in SIGN_WORDS:
            SignVideo.objects.get_or_create(
                keyword=keyword,
                defaults={
                    'title': title,
                    'emoji': emoji,
                    # 파일은 frontend/public/videos/ 에 있습니다. 백엔드로 옮기기 전까지
                    # external_url로 프론트 정적 경로를 가리킵니다.
                    'external_url': f'http://localhost:3000/videos/{filename}' if filename else '',
                },
            )
        self.stdout.write(f'수어 단어 {len(SIGN_WORDS)}개')

        for position, keyword in enumerate(QUICK_KEYWORDS, start=1):
            sign_video = SignVideo.objects.filter(keyword=keyword).first()
            if sign_video:
                QuickKeyword.objects.get_or_create(
                    sign_video=sign_video,
                    defaults={'position': position},
                )
        self.stdout.write(f'빠른 키워드 {len(QUICK_KEYWORDS)}개')

        for title, icon, category, code, members in CONVERSATIONS:
            conversation, _ = Conversation.objects.get_or_create(
                code=code,
                defaults={'title': title, 'icon': icon, 'category': category},
            )
            for nickname in members:
                ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=users[nickname],
                )
        self.stdout.write(f'대화 {len(CONVERSATIONS)}개 (메시지는 비어 있음)')

        self.stdout.write(self.style.SUCCESS(f'완료. 비밀번호는 전부 "{DEMO_PASSWORD}"'))
