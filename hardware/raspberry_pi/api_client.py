"""프-백(DRF) 호출.

계약은 프론트와 같습니다:
  POST /auth/login/               -> access 토큰
  POST /sign-translations/        -> 202 {id, status, created_at}
  GET  /sign-translations/{id}/   -> 1초 폴링, COMPLETED/FAILED면 중지
"""

import logging
import time
import uuid

import requests

import config

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f'{code}: {message}')


def _parse_error(response):
    try:
        body = response.json()
        error = body.get('error', {})
        return ApiError(
            error.get('code', 'UNKNOWN'),
            error.get('message', f'HTTP {response.status_code}'),
        )
    except ValueError:
        return ApiError('UNKNOWN', f'HTTP {response.status_code}')


class BackendClient:
    def __init__(self):
        self._session = requests.Session()
        self._access = None

    def _url(self, path):
        return f"{config.API_BASE_URL.rstrip('/')}{path}"

    def _headers(self):
        if not self._access:
            return {}
        return {'Authorization': f'Bearer {self._access}'}

    def login(self):
        """시작할 때 한 번 로그인해서 토큰을 들고 있습니다.

        Access 토큰은 30분이라, 401이 나면 재로그인합니다 (아래 _request).
        """
        response = self._session.post(
            self._url('/auth/login/'),
            json={
                'nickname': config.API_NICKNAME,
                'password': config.API_PASSWORD,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise _parse_error(response)

        self._access = response.json()['access']
        logger.info('로그인 성공: %s', config.API_NICKNAME)

    def _request(self, method, path, retry_auth=True, **kwargs):
        response = self._session.request(
            method,
            self._url(path),
            headers=self._headers(),
            timeout=30,
            **kwargs,
        )

        # 토큰이 만료되면 재로그인 후 한 번 재시도합니다.
        # (프론트는 refresh 쿠키를 쓰지만, 기기는 그냥 다시 로그인하는 게 단순합니다.)
        if response.status_code == 401 and retry_auth:
            logger.info('토큰 만료 — 재로그인')
            self.login()
            return self._request(method, path, retry_auth=False, **kwargs)

        return response

    def upload_video(self, video_path, capture_id):
        """명세 7.1: multipart/form-data, 필드명 input_video."""
        data = {
            'capture_id': capture_id,
            'device_id': config.DEVICE_ID,
        }

        # 대화 ID가 있으면 채팅 모드, 없으면 번역기 모드(대면)로 올라갑니다.
        if config.CONVERSATION_ID:
            data['conversation_id'] = config.CONVERSATION_ID

        with open(video_path, 'rb') as f:
            response = self._request(
                'POST',
                '/sign-translations/',
                files={'input_video': (video_path.name, f, 'video/mp4')},
                data=data,
            )

        # 명세 9장: 접수는 202 Accepted
        if response.status_code != 202:
            raise _parse_error(response)

        return response.json()

    def wait_for_result(self, translation_id, on_tick=None):
        """명세 5.2: 1초 간격 폴링, COMPLETED/FAILED면 중지, 60초 넘으면 포기."""
        started = time.time()

        while True:
            response = self._request('GET', f'/sign-translations/{translation_id}/')

            if response.status_code != 200:
                raise _parse_error(response)

            result = response.json()
            status = result['status']

            if on_tick:
                on_tick(status)

            if status in ('COMPLETED', 'FAILED'):
                return result

            if time.time() - started > config.POLL_TIMEOUT_SECONDS:
                raise ApiError('AI_TIMEOUT', '분석이 시간 내에 끝나지 않았습니다.')

            time.sleep(config.POLL_INTERVAL_SECONDS)


def new_capture_id():
    """촬영마다 고유해야 합니다. 백엔드가 중복을 409로 막습니다 (27장)."""
    return f'{config.DEVICE_ID}-{uuid.uuid4().hex[:12]}'
