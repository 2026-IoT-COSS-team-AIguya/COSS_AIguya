"""시연용 초기 데이터.

    python manage.py seed_demo

여러 번 돌려도 안전합니다 (get_or_create 기반).

시연은 노트북 두 대로 농인 / 청인이 각자 로그인해서 진행합니다.

**대화방은 만들지 않습니다.** 친구 추가 → 대화 시작이 시연에서 보여줄 흐름이라,
미리 만들어두면 그 흐름을 건너뛰게 됩니다. 계정과 수어 사전만 심습니다.
"""

import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User, UserRole
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

# 아이디는 전부 이모지입니다 — 농인이든 청인이든.
#
# 농인만 이모지로 하면 반쪽입니다: 농인이 청인 친구를 추가하려면 결국 청인의
# 글자 아이디를 키보드로 쳐야 하니까요. 아이디는 "남이 입력하는 것"이라
# 한쪽만 쉬워서는 소용이 없습니다.
#
# (frontend/components/EmojiKeypad.tsx 의 ID_EMOJIS 팔레트 안에서 골랐습니다 —
#  거기 없는 이모지는 화면에서 입력할 수가 없습니다.)
DEMO_USERS = [
    ('🐶🍎⭐', UserRole.SIGN_USER),
    ('🦊🎈🌈', UserRole.HEARING_USER),
    ('🐰🍇🌙', UserRole.SIGN_USER),
    ('🐻🍒☀️', UserRole.HEARING_USER),
    ('🐼🎁💎', UserRole.HEARING_USER),
]

# 농인은 숫자 PIN, 청인은 글자 비밀번호를 씁니다.
# (비밀번호는 남이 입력하지 않으므로 형식이 달라도 됩니다.)
DEMO_PIN = '1234'
DEMO_PASSWORD = 'password'


class Command(BaseCommand):
    help = '시연용 계정 · 수어 사전을 만듭니다. (대화방은 화면에서 직접 만듭니다.)'

    @transaction.atomic
    def handle(self, *args, **options):
        # 아이디가 이모지라 Windows 기본 콘솔(cp949)에서는 출력하다 죽습니다.
        # handle이 atomic이라 출력 한 줄 때문에 시드 전체가 롤백됩니다 — 화면에
        # 글자를 예쁘게 찍는 일이 데이터를 심는 일을 망치면 안 됩니다.
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')

        users = {}
        for nickname, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=nickname,
                defaults={'role': role, 'onboarding_completed': True},
            )
            if created:
                user.set_password(
                    DEMO_PIN if role == UserRole.SIGN_USER else DEMO_PASSWORD
                )
                user.save()
            users[nickname] = user
        self.stdout.write(f'사용자 {len(users)}명')

        # 친구 관계도 심지 않습니다. 닉네임으로 신청 → 수락 → 대화 시작이
        # 직접 해봐야 할 흐름이라, 미리 이어두면 확인할 게 없어집니다.

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

        self.stdout.write(self.style.SUCCESS('완료.'))
        for nickname, role in DEMO_USERS:
            secret = DEMO_PIN if role == UserRole.SIGN_USER else DEMO_PASSWORD
            label = '농인' if role == UserRole.SIGN_USER else '청인'
            self.stdout.write(f'  {nickname}  ({label}) — {secret}')
        self.stdout.write('대화방은 친구 화면에서 친구를 추가한 뒤 직접 만드세요.')
