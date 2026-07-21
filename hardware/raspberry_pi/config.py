"""라즈베리파이 촬영 클라이언트 설정.

.env 파일이나 환경변수로 덮어씁니다. .env.example을 복사해서 쓰세요.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / '.env')


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


# --- 백엔드 (프-백) ---
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1')

# 라즈베리파이가 누구로 로그인할지.
# 시연에서는 농인 계정으로 올립니다 — 그 계정이 보고 있는 화면(대화방/번역기)으로
# 촬영분이 갑니다.
#
# 아이디는 이모지입니다 (seed_demo의 DEMO_USERS 참고). 농인 비밀번호는 숫자 PIN.
# 이 파일과 .env는 UTF-8로 저장해야 합니다 — 아니면 이모지가 깨져서 로그인이 실패합니다.
API_NICKNAME = os.getenv('API_NICKNAME', '🐶🍎⭐')
API_PASSWORD = os.getenv('API_PASSWORD', '1234')

# 촬영분이 어디로 갈지는 **비워두는 게 정상**입니다.
#
# 비워두면 백엔드가 화면 쪽이 등록해둔 대상(PUT /capture-target/)을 보고 라우팅합니다
# — 사용자가 채팅방을 열어두고 있으면 그 방으로, 번역기 화면을 보고 있으면 번역기로.
# 여기에 값을 박으면 화면에서 뭘 보고 있든 무조건 그 방으로 올라갑니다. 화면 없이
# 기기만 돌려서 특정 방에 넣고 싶을 때만 쓰세요.
CONVERSATION_ID = os.getenv('CONVERSATION_ID', '').strip()

# --- 장치 ---
DEVICE_ID = os.getenv('DEVICE_ID', 'rpi-demo-01')

# 아두이노 시리얼 포트. 라즈베리파이에서는 보통 /dev/ttyACM0 또는 /dev/ttyUSB0.
SERIAL_PORT = os.getenv('SERIAL_PORT', '/dev/ttyACM0')
SERIAL_BAUD = _int('SERIAL_BAUD', 115200)

# --- 촬영 ---
# 명세 7.1: 권장 최대 길이 30초. 시연에서는 짧게 갑니다.
# 첫 버튼을 누른 뒤 자세를 잡을 시간입니다.
CAPTURE_START_DELAY_SECONDS = _float('CAPTURE_START_DELAY_SECONDS', 1.0)

# 촬영은 두 번째 버튼을 누르면 끝납니다. 버튼/시리얼 장애로 무한 촬영되는 것을
# 막기 위한 안전 상한만 유지합니다.
MAX_RECORD_SECONDS = _int('MAX_RECORD_SECONDS', 30)
VIDEO_WIDTH = _int('VIDEO_WIDTH', 1280)
VIDEO_HEIGHT = _int('VIDEO_HEIGHT', 720)

# 촬영한 영상을 잠시 두는 곳
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', str(BASE_DIR / 'captures')))

# --- 폴링 ---
# 명세 5.2: 상태는 1초 간격으로 조회하고, 60초가 지나면 지연으로 봅니다.
POLL_INTERVAL_SECONDS = _int('POLL_INTERVAL_SECONDS', 1)
POLL_TIMEOUT_SECONDS = _int('POLL_TIMEOUT_SECONDS', 60)
