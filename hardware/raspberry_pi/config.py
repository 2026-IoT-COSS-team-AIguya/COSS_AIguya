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


# --- 백엔드 (프-백) ---
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1')

# 라즈베리파이가 누구로 로그인할지.
# 시연에서는 농인 계정으로 올립니다 — 번역기 화면이 이 계정의 최근 촬영을 폴링합니다.
API_NICKNAME = os.getenv('API_NICKNAME', '민지')
API_PASSWORD = os.getenv('API_PASSWORD', 'password')

# 채팅방에 올리려면 대화 ID를 넣습니다. 비우면 번역기 모드(대면)로 올라갑니다.
CONVERSATION_ID = os.getenv('CONVERSATION_ID', '').strip()

# --- 장치 ---
DEVICE_ID = os.getenv('DEVICE_ID', 'rpi-demo-01')

# 아두이노 시리얼 포트. 라즈베리파이에서는 보통 /dev/ttyACM0 또는 /dev/ttyUSB0.
SERIAL_PORT = os.getenv('SERIAL_PORT', '/dev/ttyACM0')
SERIAL_BAUD = _int('SERIAL_BAUD', 115200)

# --- 촬영 ---
# 명세 7.1: 권장 최대 길이 30초. 시연에서는 짧게 갑니다.
RECORD_SECONDS = _int('RECORD_SECONDS', 5)
VIDEO_WIDTH = _int('VIDEO_WIDTH', 1280)
VIDEO_HEIGHT = _int('VIDEO_HEIGHT', 720)

# 촬영한 영상을 잠시 두는 곳
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', str(BASE_DIR / 'captures')))

# --- 폴링 ---
# 명세 5.2: 상태는 1초 간격으로 조회하고, 60초가 지나면 지연으로 봅니다.
POLL_INTERVAL_SECONDS = _int('POLL_INTERVAL_SECONDS', 1)
POLL_TIMEOUT_SECONDS = _int('POLL_TIMEOUT_SECONDS', 60)
