/*
 * 손말이음 - 수어 촬영 버튼
 *
 * 물리 버튼을 누르면 LED를 켜고, 시리얼로 라즈베리파이에 촬영 시작을 알립니다.
 * 라즈베리파이가 촬영/분석 상태를 되돌려주면 LED로 표시합니다.
 *
 * 배선
 *   버튼  : D2 - GND        (INPUT_PULLUP을 쓰므로 저항 불필요, 누르면 LOW)
 *   LED   : D9 - 220Ω - GND (촬영 중 표시)
 *   보드   : USB로 라즈베리파이에 연결 (시리얼 통신 겸 전원)
 *
 * 프로토콜 (115200 baud, 줄바꿈 구분)
 *   보냄 : READY            부팅 완료
 *          BUTTON           버튼이 눌림 -> 촬영 시작해라
 *          BUTTON_STOP      버튼이 다시 눌림 -> 촬영을 종료해라
 *   받음 : LED:ON           LED 켜기
 *          LED:OFF          LED 끄기
 *          STATUS:RECORDING 촬영 중   (LED 켜짐)
 *          STATUS:BUSY      분석 중   (LED 느리게 깜빡임)
 *          STATUS:DONE      분석 완료 (LED 3번 빠르게 깜빡이고 꺼짐)
 *          STATUS:FAIL      실패      (LED 길게 2번 깜빡이고 꺼짐)
 */

const uint8_t BUTTON_PIN = 2;
const uint8_t LED_PIN = 9;

// 채터링 방지. 이 시간 안의 변화는 무시합니다.
const unsigned long DEBOUNCE_MS = 50;

// 촬영 중에 버튼을 또 눌러도 무시하는 시간. 라즈베리파이가 STATUS:DONE/FAIL을
// 보내주면 그때 풀리지만, 응답이 없어도 이 시간이 지나면 다시 받습니다.
const unsigned long LOCKOUT_MS = 60000;

enum LedMode {
  LED_OFF,
  LED_ON,
  LED_BLINK_SLOW  // 분석 중
};

LedMode ledMode = LED_OFF;
bool ledState = false;
unsigned long ledLastToggle = 0;

int lastReading = HIGH;
int buttonState = HIGH;
unsigned long lastDebounceTime = 0;

bool capturing = false;
bool recordingActive = false;
unsigned long captureStartedAt = 0;

String inputBuffer = "";

void setLed(bool on) {
  ledState = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// 깜빡임은 delay()를 쓰지 않습니다. delay 중에는 버튼도 시리얼도 못 읽습니다.
void blink(uint8_t times, unsigned long onMs, unsigned long offMs) {
  for (uint8_t i = 0; i < times; i++) {
    setLed(true);
    delay(onMs);
    setLed(false);
    if (i < times - 1) {
      delay(offMs);
    }
  }
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  setLed(false);

  Serial.begin(115200);

  // 부팅했다고 알립니다. 라즈베리파이가 이걸 보고 연결을 확인합니다.
  Serial.println("READY");
}

void handleCommand(const String &command) {
  if (command == "LED:ON") {
    ledMode = LED_ON;
    setLed(true);
  } else if (command == "LED:OFF") {
    ledMode = LED_OFF;
    setLed(false);
  } else if (command == "STATUS:RECORDING") {
    recordingActive = true;
    ledMode = LED_ON;
    setLed(true);
  } else if (command == "STATUS:BUSY") {
    recordingActive = false;
    ledMode = LED_OFF;
    setLed(false);
  } else if (command == "STATUS:DONE") {
    ledMode = LED_OFF;
    setLed(false);
    capturing = false;
    recordingActive = false;
  } else if (command == "STATUS:FAIL") {
    ledMode = LED_OFF;
    setLed(false);
    capturing = false;
    recordingActive = false;
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        handleCommand(inputBuffer);
      }
      inputBuffer = "";
    } else if (c != '\r') {
      inputBuffer += c;
    }
  }
}

void readButton() {
  int reading = digitalRead(BUTTON_PIN);

  if (reading != lastReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_MS && reading != buttonState) {
    buttonState = reading;

    // INPUT_PULLUP이라 누르면 LOW입니다.
    if (buttonState == LOW) {
      if (!capturing) {
        capturing = true;
        recordingActive = false;
        captureStartedAt = millis();

        // Pi가 1초 준비를 마친 뒤 STATUS:RECORDING을 보낼 때 LED를 켭니다.
        Serial.println("BUTTON");
      } else if (recordingActive) {
        // 두 번째 버튼은 현재 촬영을 종료합니다. 완료/실패 상태를 받을 때까지
        // 추가 버튼은 무시합니다.
        recordingActive = false;
        ledMode = LED_OFF;
        setLed(false);
        Serial.println("BUTTON_STOP");
      }
    }
  }

  lastReading = reading;
}

void updateLed() {
  if (ledMode != LED_BLINK_SLOW) {
    return;
  }

  if (millis() - ledLastToggle > 400) {
    ledLastToggle = millis();
    setLed(!ledState);
  }
}

void checkLockout() {
  // 라즈베리파이가 응답하지 않아도 영영 잠겨 있으면 안 됩니다.
  if (capturing && (millis() - captureStartedAt) > LOCKOUT_MS) {
    capturing = false;
    recordingActive = false;
    ledMode = LED_OFF;
    setLed(false);
  }
}

void loop() {
  readSerial();
  readButton();
  updateLed();
  checkLockout();
}
