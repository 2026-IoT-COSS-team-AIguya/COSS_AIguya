# 하드웨어 (아두이노 + 라즈베리파이)

수어 촬영은 웹 버튼이 아니라 **아두이노 물리 버튼**이 시작합니다.

```
아두이노 버튼 → LED 점등 → (시리얼 "BUTTON") → 라즈베리파이 카메라 촬영
   → DRF 업로드 (202) → AI 분석 → 1초 폴링 → 결과
   → 번역기 화면에 표시 / oneM2M에 메타데이터 등록
   → 아두이노 LED로 결과 표시 (DONE 3번 깜빡 / FAIL 길게 2번)
```

## 배선

| 부품 | 연결 |
|---|---|
| 버튼 | D2 ↔ GND (`INPUT_PULLUP` 사용, 저항 불필요) |
| LED | D9 → 220Ω → GND |
| 아두이노 | USB로 라즈베리파이에 연결 (시리얼 + 전원) |

## 아두이노

`arduino/sign_button/sign_button.ino`를 Arduino IDE로 열어 업로드합니다.
시리얼 모니터를 **115200 baud**로 열면 버튼을 누를 때 `BUTTON`이 찍힙니다.

프로토콜 (줄바꿈 구분):

| 방향 | 메시지 | 뜻 |
|---|---|---|
| Arduino → Pi | `READY` | 부팅 완료 |
| Arduino → Pi | `BUTTON` | 버튼 눌림, 촬영 시작해라 |
| Pi → Arduino | `STATUS:RECORDING` | 촬영 중 (LED 켜짐) |
| Pi → Arduino | `STATUS:BUSY` | 분석 중 (LED 느리게 깜빡임) |
| Pi → Arduino | `STATUS:DONE` | 완료 (3번 깜빡이고 꺼짐) |
| Pi → Arduino | `STATUS:FAIL` | 실패 (길게 2번 깜빡이고 꺼짐) |

라즈베리파이가 응답하지 않아도 15초 뒤엔 버튼이 다시 눌립니다 (`LOCKOUT_MS`).

## 라즈베리파이

```bash
sudo apt install -y python3-picamera2 ffmpeg
cd hardware/raspberry_pi
python3 -m venv --system-site-packages .venv   # picamera2를 보려면 필수
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env 에서 API_BASE_URL을 백엔드 노트북 IP로 바꾸세요 (localhost 아님!)
# 시리얼 포트 확인: ls /dev/tty*

python capture_client.py
```

### 하드웨어 없이 시험하기

```bash
python capture_client.py --simulate --once
```

아두이노와 카메라만 가짜고 **업로드·폴링은 진짜**입니다. Enter가 버튼 역할을 하고,
`frontend/public/videos/promise_sign.mp4`를 촬영한 셈 치고 올립니다.
백엔드가 켜져 있으면 실제로 translation이 만들어지고 oneM2M에도 등록됩니다.

## 주의할 점

**`API_BASE_URL`에 `localhost`를 쓰면 안 됩니다.** 라즈베리파이 입장에서 localhost는
자기 자신입니다. 백엔드를 띄운 노트북의 IP(예: `http://192.168.0.10:8000/api/v1`)를 적고,
Django를 `python manage.py runserver 0.0.0.0:8000`으로 띄워야 외부에서 붙습니다.

**계정은 농인 계정이어야 합니다.** 번역기 화면이 로그인한 사용자의 최근 촬영을
폴링하므로, 라즈베리파이가 다른 계정으로 올리면 화면에 안 뜹니다.

**`CONVERSATION_ID`를 비워두면 번역기 모드(대면)**로 올라갑니다. 값을 넣으면 그
채팅방에 메시지로 붙습니다.

## 확인된 것 / 확인 못 한 것

`--simulate`로 **로그인 → 업로드(202) → 상태 폴링 → 결과 → oneM2M 등록**까지는
실제로 돌려서 확인했습니다.

**실물로 확인하지 못한 것** (하드웨어가 없어서):
- 아두이노 스케치의 동작 (버튼 디바운스, LED, 시리얼)
- `picamera2` 녹화가 실제로 mp4를 만드는지
- 시리얼 포트 이름과 연결

이 부분들은 실물에서 한 번 돌려보고 알려주세요.
