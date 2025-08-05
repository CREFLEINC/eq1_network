# MQTTProtocol 사용 가이드
MQTTProtocol은 EQ-1 Network의 MQTT Pub/Sub 프로토콜 구현체입니다.
MQTT 브로커와 연결하여 메시지 발행(publish), 토픽 구독(subscribe), 자동 재연결 등의 기본 기능을 제공합니다.

## 1. 빠른 시작
### 기본 사용법
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

# 1. 설정 객체 생성
config = MQTTConfig(
    broker_address="broker.example.com",
    port=1883,
    keepalive=60    # 별도의 설정 가능
)

# 2. 프로토콜 객체 생성
mqtt = MQTTProtocol(config)

# 3. 브로커 연결
mqtt.connect()

# 4. 메시지 콜백 함수 정의
def message_callback(topic: str, payload: bytes):
    print(f"Received: [{topic}] {payload.decode()}")

# 5. 토픽 구독
mqtt.subscribe("topic/test", message_callback)

# 6. 메시지 발행
mqtt.publish("topic/test", "hello")

# 7. 연결 해제
mqtt.disconnect()
```

### 인증 기능 사용법
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

# 인증 설정
config = MQTTConfig(
    broker_address="test.mosquitto.org",
    port=1883,
    username="mqtt_username",
    password="mqtt_password",
    keepalive=60
)

mqtt = MQTTProtocol(config)
mqtt.connect()

# Retained Message 발행
mqtt.publish("device/status", "online", qos=1, retain=True)

mqtt.disconnect()
```

## 2. 주요 개념
### 동작 모드
- **non-blocking (기본)**
    - `loop_start()` 기반
    - 연결 후 별도 스레드에서 통신
    - 메인 스레드에서 자유롭게 작업 가능
- **blocking**
    - `loop_forever()` 기반
    - 별도 스레드에서 통신 루프 실행
    - 메인 스레드는 블록되지 않음

### 주요 기능
#### 기본 MQTT 기능
- 브로커 연결/해제
- 토픽 구독 및 메시지 콜백 처리
- QoS 0, 1, 2 지원 메시지 발행 (기본값: QoS 0)
- 재연결 시 구독 자동 복구
- 연결 상태 확인 기능

#### 추가 기능
- **보안 인증**: username/password 인증 지원
- **Retained Messages**: retain 플래그 지원
- **예외 처리**: 연결, 발행, 구독 실패 예외 처리
- **로깅**: 주요 이벤트 로깅 지원

## 3. 클래스 구조
```python
@dataclass
class MQTTConfig:
    broker_address: str
    port: int = 1883
    keepalive: int = 60
    mode: str = "non-blocking"
    username: Optional[str] = None
    password: Optional[str] = None

class MQTTProtocol(PubSubProtocol):
    def __init__(self, config: MQTTConfig)
    def connect(self) -> bool
    def disconnect(self)
    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool
    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 0) -> bool
    def unsubscribe(self, topic: str) -> bool
    def is_connected(self) -> bool
```

### MQTTConfig 파라미터 설명
#### 기본 연결 설정
- `broker_address` (str): 브로커 주소 (IP 또는 호스트명) - **필수**
- `port` (int): MQTT 포트 (기본 1883)
- `keepalive` (int): Keep-alive 간격(초 단위, 기본 60)
- `mode` (str): 'blocking' 또는 'non-blocking' (기본 'non-blocking')

#### 보안 설정
- `username` (Optional[str]): MQTT 인증 사용자명
- `password` (Optional[str]): MQTT 인증 비밀번호

## 4. 고급 동작 방식
### 자동 재연결 및 구독 복구
- 연결 끊김 감지 → 수동 재연결 가능
- 재연결 성공 → 기존 구독 정보 자동 복구
- 발행 실패 시 → False 반환

### 스레드 처리
- non-blocking 모드: `loop_start()` 사용
- blocking 모드: 별도 스레드에서 `loop_forever()` 실행

### 콜백 흐름
```mermaid
sequenceDiagram
    participant Broker
    participant PahoClient
    participant MQTTProtocol
    participant UserCallback

    Broker->>PahoClient: 메시지 수신
    PahoClient->>MQTTProtocol: on_message 이벤트
    MQTTProtocol->>UserCallback: callback(topic, payload)
```

## 5. 사용 방법
### 연결 및 구독
```python
def on_message(topic: str, payload: bytes):
    print(f"[{topic}] {payload.decode()}")

mqtt.connect()
mqtt.subscribe("vision/events", callback=on_message)
```

### 메시지 발행
```python
# 기본 메시지 발행 (QoS 0 기본값)
mqtt.publish("vision/events", "Camera started")

# QoS 레벨 명시적 지정
mqtt.publish("vision/events", "Camera started", qos=1)  # QoS 1
mqtt.publish("vision/events", "Camera started", qos=2)  # QoS 2

# Retained Message 발행
mqtt.publish("device/status", "online", qos=1, retain=True)
```

### 구독 해제
```python
mqtt.unsubscribe("vision/events")
```

### 연결 해제
```python
mqtt.disconnect()
```

### 예외 처리
#### 주요 예외 클래스:
- `ProtocolConnectionError`: 브로커 연결 실패
- `ProtocolValidationError`: 메시지 발행/구독 실패
- `ProtocolError`: 일반적인 프로토콜 오류

#### 예외 처리 예시:
```python
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError
)

try:
    mqtt.connect()
except ProtocolConnectionError as e:
    print(f"Connection failed: {e}")

try:
    mqtt.subscribe("test/topic", callback)
except ProtocolValidationError as e:
    print(f"Subscribe failed: {e}")
```

## 6. 테스트 방법
### 단위 테스트
```bash
# Mock 기반 단위 테스트
pytest -m "unit" -v
```

### 통합 테스트
```bash
# 실제 브로커와 연동 테스트
pytest -m "integration" -v
```

### E2E 테스트
```bash
# 실제 시나리오 테스트
pytest -m "e2e" -v
```

## 7. 현재 구현 수준
현재 구현은 MQTT v3.1.1 기본 기능을 지원합니다:

### ✅ 완전 지원
- 기본 MQTT 기능 (CONNECT, DISCONNECT, PUBLISH, SUBSCRIBE)
- QoS 0, 1, 2 레벨
- Keep-alive 메커니즘
- Username/Password 인증
- Retained Messages
- 재연결 시 구독 복구
- 예외 처리 및 로깅

### 🔄 미지원
- TLS/SSL 보안 연결
- Will Message (Last Will and Testament)
- MQTT v5.0 기능들
- 자동 재연결 (수동 재연결만 지원)

## 8. 참고 자료
- [README.md](README.md) - 프로젝트 전체 개요
- [PRD.md](prd.md) - 프로젝트 요구사항 문서