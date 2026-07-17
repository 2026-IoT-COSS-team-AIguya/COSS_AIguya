"""카메라와 아두이노를 감싼 얇은 층.

실물이 없을 때를 위해 가짜 구현을 함께 둡니다. 덕분에 하드웨어 없이도
업로드·폴링 경로를 그대로 검증할 수 있습니다 (capture_client.py --simulate).
"""

import logging
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# 카메라
# ============================================================================


class PiCamera:
    """Picamera2로 mp4를 녹화합니다.

    picamera2는 라즈베리파이에서만 import되므로 여기서 지연 import합니다.
    (개발 PC에서 이 파일을 불러도 터지지 않게)
    """

    def __init__(self, width, height):
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder

        self._encoder_cls = H264Encoder
        self._camera = Picamera2()

        config = self._camera.create_video_configuration(
            main={'size': (width, height)}
        )
        self._camera.configure(config)

    def record(self, output_path, seconds):
        # 명세 7.1이 video/mp4를 받으므로 FfmpegOutput으로 바로 mp4를 만듭니다.
        # (H264 raw로 저장하면 컨테이너가 없어 업로드가 415로 거절됩니다.)
        from picamera2.outputs import FfmpegOutput

        output = FfmpegOutput(str(output_path))

        self._camera.start_recording(self._encoder_cls(), output)
        try:
            time.sleep(seconds)
        finally:
            self._camera.stop_recording()

        return output_path

    def close(self):
        try:
            self._camera.close()
        except Exception:
            logger.warning('카메라를 닫는 중 오류', exc_info=True)


class FakeCamera:
    """카메라가 없을 때 씁니다. 미리 준비한 mp4를 복사해 촬영한 척합니다."""

    def __init__(self, sample_path):
        self._sample = Path(sample_path)

        if not self._sample.exists():
            raise FileNotFoundError(f'샘플 영상이 없습니다: {self._sample}')

    def record(self, output_path, seconds):
        logger.info('[가짜 카메라] %s초 촬영하는 척', seconds)
        time.sleep(min(seconds, 1))  # 시연 흐름만 흉내내고 오래 기다리진 않습니다.
        shutil.copy(self._sample, output_path)
        return output_path

    def close(self):
        pass


# ============================================================================
# 아두이노
# ============================================================================


class ArduinoSerial:
    """USB 시리얼로 아두이노와 주고받습니다."""

    def __init__(self, port, baud):
        import serial

        # 아두이노는 시리얼이 열리면 리셋됩니다. 부팅을 기다려야 첫 줄을 놓치지 않습니다.
        self._serial = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        self._serial.reset_input_buffer()

    def read_line(self):
        """한 줄을 읽습니다. 타임아웃이면 빈 문자열."""
        raw = self._serial.readline()

        if not raw:
            return ''

        return raw.decode('utf-8', errors='replace').strip()

    def send(self, command):
        self._serial.write((command + '\n').encode('utf-8'))
        self._serial.flush()

    def close(self):
        try:
            self._serial.close()
        except Exception:
            logger.warning('시리얼을 닫는 중 오류', exc_info=True)


class FakeArduino:
    """아두이노가 없을 때. Enter를 치면 버튼을 누른 것으로 칩니다."""

    def read_line(self):
        try:
            input('\n[가짜 아두이노] Enter = 버튼 누름 (Ctrl+C 종료) ')
        except EOFError:
            time.sleep(1)
            return ''

        return 'BUTTON'

    def send(self, command):
        print(f'[가짜 아두이노] <- {command}')

    def close(self):
        pass
