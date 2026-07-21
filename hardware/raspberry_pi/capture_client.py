#!/usr/bin/env python3
"""손말이음 - 라즈베리파이 촬영 클라이언트.

아두이노 버튼 -> LED 점등 -> 카메라 촬영 -> 업로드 -> AI 분석 -> 결과.
번역기 화면은 이 업로드 결과를 폴링해서 보여줍니다.

    python capture_client.py                    # 실제 하드웨어
    python capture_client.py --simulate         # 하드웨어 없이 (Enter로 버튼, 샘플 영상)
    python capture_client.py --once             # 한 번만 촬영하고 종료
    python capture_client.py --simulate --once  # 업로드 경로만 빠르게 검증

--simulate는 아두이노와 카메라만 가짜고 업로드·폴링은 진짜입니다.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import config
from api_client import ApiError, BackendClient, new_capture_id
from devices import ArduinoSerial, FakeArduino, FakeCamera, PiCamera

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('capture')


def build_devices(simulate, sample_video):
    if simulate:
        return FakeArduino(), FakeCamera(sample_video)

    arduino = ArduinoSerial(config.SERIAL_PORT, config.SERIAL_BAUD)
    camera = PiCamera(config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
    return arduino, camera


def handle_capture(arduino, camera, backend):
    """버튼 한 번에 대한 전체 처리."""
    capture_id = new_capture_id()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_path = config.OUTPUT_DIR / f'{capture_id}.mp4'

    # 1) 첫 버튼 뒤 자세를 잡을 시간을 주고 촬영을 시작합니다. LED는
    # STATUS:RECORDING을 받을 때 켜지므로 카메라 시작과 거의 동시에 점등됩니다.
    logger.info('촬영 준비 (%s초)', config.CAPTURE_START_DELAY_SECONDS)
    time.sleep(config.CAPTURE_START_DELAY_SECONDS)

    started = False
    try:
        camera.start_recording(video_path)
        started = True
        arduino.send('STATUS:RECORDING')
        logger.info(
            '촬영 시작. 버튼을 다시 누르면 종료합니다. (최대 %s초)',
            config.MAX_RECORD_SECONDS,
        )

        deadline = time.monotonic() + config.MAX_RECORD_SECONDS
        while time.monotonic() < deadline:
            if arduino.read_line() == 'BUTTON_STOP':
                logger.info('촬영 종료 버튼 입력')
                break
        else:
            logger.warning('최대 촬영 시간에 도달하여 자동으로 종료합니다.')
    except Exception:
        logger.exception('촬영 실패')
        arduino.send('STATUS:FAIL')
        return
    finally:
        if started:
            camera.stop_recording()

    size_kb = video_path.stat().st_size / 1024
    logger.info('촬영 완료: %s (%.0f KB)', video_path.name, size_kb)

    # 2) 업로드
    arduino.send('STATUS:BUSY')

    try:
        created = backend.upload_video(video_path, capture_id)
    except ApiError as exc:
        logger.error('업로드 실패: %s', exc)
        arduino.send('STATUS:FAIL')
        return
    except OSError:
        logger.exception('업로드 중 파일 오류')
        arduino.send('STATUS:FAIL')
        return

    translation_id = created['id']
    logger.info('업로드 완료: translation_id=%s status=%s', translation_id, created['status'])

    # 3) 결과 대기
    last_status = {'value': None}

    def on_tick(status):
        if status != last_status['value']:
            logger.info('  상태: %s', status)
            last_status['value'] = status

    try:
        result = backend.wait_for_result(translation_id, on_tick=on_tick)
    except ApiError as exc:
        logger.error('분석 실패: %s', exc)
        arduino.send('STATUS:FAIL')
        return

    # 4) 결과 표시
    if result['status'] == 'COMPLETED':
        keywords = ' '.join(k['keyword'] for k in result['recognized_keywords'])
        sentence = (result['sentence_candidates'] or ['-'])[0]
        logger.info('인식: [%s] -> "%s"', keywords, sentence)
        arduino.send('STATUS:DONE')
    else:
        error = result.get('error') or {}
        logger.warning('인식 실패: %s', error.get('message', '알 수 없음'))
        arduino.send('STATUS:FAIL')

    # 업로드한 영상은 백엔드에 있으므로 로컬 파일은 지웁니다.
    # (SD 카드가 금방 찹니다.)
    try:
        video_path.unlink()
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description='손말이음 촬영 클라이언트')
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='아두이노/카메라 없이 실행 (Enter로 버튼, 샘플 영상 업로드)',
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='한 번 촬영하고 종료',
    )
    parser.add_argument(
        '--sample-video',
        default=str(
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'public'
            / 'videos'
            / 'promise_sign.mp4'
        ),
        help='--simulate에서 업로드할 영상',
    )
    args = parser.parse_args()

    logger.info('백엔드: %s', config.API_BASE_URL)
    logger.info('장치: %s', config.DEVICE_ID)
    logger.info(
        '모드: %s',
        '번역기(대면)' if not config.CONVERSATION_ID else f'채팅방 {config.CONVERSATION_ID}',
    )

    backend = BackendClient()

    try:
        backend.login()
    except (ApiError, OSError) as exc:
        logger.error('로그인 실패: %s', exc)
        logger.error('백엔드가 켜져 있는지, .env의 계정이 맞는지 확인하세요.')
        return 1

    try:
        arduino, camera = build_devices(args.simulate, args.sample_video)
    except Exception as exc:
        logger.error('장치를 열지 못했습니다: %s', exc)
        if not args.simulate:
            logger.error('--simulate 로 하드웨어 없이 시험해볼 수 있습니다.')
        return 1

    logger.info('준비 완료. 버튼을 누르면 촬영합니다.')

    try:
        while True:
            line = arduino.read_line()

            if not line:
                continue

            if line == 'READY':
                logger.info('아두이노 연결됨')
                continue

            if line != 'BUTTON':
                logger.debug('아두이노: %s', line)
                continue

            logger.info('--- 버튼 눌림 ---')
            handle_capture(arduino, camera, backend)

            if args.once:
                break

            # 버튼을 연타해도 촬영이 겹치지 않게 잠깐 둡니다.
            time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info('종료합니다.')
    finally:
        arduino.send('LED:OFF')
        arduino.close()
        camera.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
