# EQ-1 Network

EQ-1 Network는 다양한 통신 프로토콜을 플러그인 기반으로 확장 가능하게 구성한 Python 통신 프레임워크입니다.

## 개요

현재 MQTT 프로토콜을 지원하며, 다음 기능을 제공합니다:

- **Basic MQTT**: 기본 MQTT v3.1.1 기능 지원
- **Authentication**: Username/Password 인증
- **Reliability**: 재연결 시 구독 자동 복구
- **Thread Safety**: 스레드 안전한 API 설계

## 시작하기 전에

다음 요구사항을 확인하세요:

- Python 3.10+
- paho-mqtt 1.6.0+

## 설치

```bash
pip install -r requirements.txt
```

## 빠른 시작

### 기본 MQTT 사용법
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

# 1. 설정 객체 생성
broker_config = BrokerConfig(
    broker_address="broker.example.com",
    port=1883,
    keepalive=60
)
client_config = ClientConfig()

# 2. MQTT 프로토콜 인스턴스 생성
mqtt = MQTTProtocol(broker_config, client_config)

# 3. 연결 (명시적 호출 필요)
mqtt.connect()

# 4. 메시지 콜백 정의
def message_callback(topic: str, payload: bytes):
    print(f"Received: [{topic}] {payload.decode()}")

# 5. 토픽 구독
mqtt.subscribe("test/topic", message_callback, qos=1)

# 6. 메시지 발행
mqtt.publish("test/topic", "Hello MQTT!", qos=1)

# 7. 연결 해제
mqtt.disconnect()
```

### 인증 연결
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

# 인증 설정
broker_config = BrokerConfig(
    broker_address="broker.example.com",
    port=1883,
    username="mqtt_username",
    password="mqtt_password",
    keepalive=60
)
client_config = ClientConfig()

mqtt = MQTTProtocol(broker_config, client_config)
mqtt.connect()

# Retained Message 발행
mqtt.publish("device/status", "online", qos=1, retain=True)

mqtt.disconnect()
```

## 주요 기능

### 현재 구현 상태
- **MQTT 프로토콜:**
    - MQTT v3.1.1 기본 기능 지원
    - QoS 0, 1, 2 레벨 지원 (기본값: QoS 0)
    - Keep-alive 메커니즘
- **인증 기능:**
    - Username/Password 인증
- **MQTT 고급 기능:**
    - Retained Messages
    - 재연결 시 구독 자동 복구
- **신뢰성:**
    - **예기치 못한 연결 실패 시 자동 재연결** (지수 백오프)
    - 재연결 시 구독 자동 복구 및 메시지 큐 처리
    - 예외 처리 및 로깅
    - 스레드 안전한 API
    - **명시적 연결 필요**: connect() 메서드를 반드시 호출해야 함
- **추상화된 인터페이스:**
    - `ReqRes(요청/응답), PubSub(발행/구독)` 인터페이스

### 🔄 미구현 기능
- **플러그인 기반 확장:**
    - TCP, Serial, Modbus 등 새로운 프로토콜 추가 예정
- **보안 강화:**
    - TLS/SSL 지원, Will Message 등
- **MQTT v5.0 기능들:**
    - Shared Subscriptions, Message Expiry 등

## 프로젝트 구조
```
communicator/
├── common/         # 공통 모듈 (예외, 로깅 등)
├── interfaces/     # 추상 인터페이스 (Protocol 등)
├── manager/        # 프로토콜 매니저
├── protocols/      # 실제 프로토콜 구현체 (MQTT 등)
│   └── mqtt/       # MQTT 프로토콜 구현
├── docs/           # 문서
└── tests/          # 테스트
    ├── units/      # 단위 테스트 (Mock 기반)
    ├── integrations/ # 통합 테스트 (실제 브로커)
    └── e2e/        # E2E 테스트
```

## 시스템 요구사항
- Python 3.10.18 (권장)
- OS: Windows
- 설치 전 가상환경(venv) 사용을 권장합니다.

## 의존성
```bash
pip install -r requirements.txt
```

## 아키텍처

### 인터페이스
- **BaseProtocol (ABC)**
    - 모든 통신 프로토콜의 공통 동작 정의
    - 추상 메소드: `connect()`, `disconnect()`
- **ReqResProtocol (BaseProtocol 상속)**
    - 요청/응답 기반 통신 프로토콜 인터페이스
    - 추상 메소드: `send()`, `receive()`
- **PubSubProtocol (BaseProtocol 상속)**
    - 발행/구독 기반 통신 프로토콜 인터페이스
    - 추상 메소드: `publish()`, `subscribe()`

### 현재 구현체
- **MQTTProtocol**
    - `PubSubProtocol` 인터페이스 구현
    - paho-mqtt 라이브러리 기반
    - 기본 MQTT 기능 지원
- **BrokerConfig & ClientConfig**
    - MQTT 연결 설정을 위한 데이터 클래스
    - 브로커 주소, 포트, 인증 정보 등

### 예외 처리
- **ProtocolConnectionError**: 연결 실패, 타임아웃
- **ProtocolValidationError**: 메시지 발행/구독 실패
- **ProtocolError**: 일반적인 프로토콜 오류

## 프레임워크 확장
새로운 통신 프로토콜을 추가하려면 적절한 인터페이스를 상속받아 구현합니다.

### Req/Res 프로토콜 추가
```python
from communicator.interfaces.protocol import ReqResProtocol

class TCPProtocol(ReqResProtocol):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self) -> bool:
        # TCP 연결 구현
        pass
    
    def disconnect(self):
        # TCP 연결 해제 구현
        pass
    
    def send(self, data: bytes) -> bool:
        # 데이터 전송 구현
        pass
    
    def receive(self, buffer_size: int = 1024) -> bytes:
        # 데이터 수신 구현
        pass
```

### Pub/Sub 프로토콜 추가
```python
from communicator.interfaces.protocol import PubSubProtocol

class RedisProtocol(PubSubProtocol):
    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool:
        # Redis pub/sub 구현
        pass
    
    def subscribe(self, topic: str, callback, qos: int = 0) -> bool:
        # Redis 구독 구현
        pass
```

## 테스트
- **단위 테스트**: Mock 기반 개별 기능 테스트
- **통합 테스트**: 실제 MQTT 브로커와의 연동 테스트
- **E2E 테스트**: 실제 사용 end-to-end 시나리오 테스트

### 테스트 실행
```bash
# 전체 테스트
pytest tests/

# 단위 테스트만
pytest tests/units/ -v

# 통합 테스트만
pytest tests/integrations/ -v

# MQTT 프로토콜만 테스트
pytest tests/units/test_mqtt_protocol.py -v
```

### 테스트 커버리지
현재 테스트 커버리지: **92%+** 달성

## 다음 단계

### 단기 로드맵
- TLS/SSL 보안 연결 지원
- Will Message 기능 추가
- 자동 재연결 기능 추가 개선 (재시도 횟수 제한, 상태 콜백 등)

### 장기 로드맵
- TCP, Serial, Modbus 프로토콜 추가
- 플러그인 매니저 개발
- 성능 최적화 및 비동기 처리 강화

## 참고 자료
- [MQTT Protocol](mqtt_protocol.md) - MQTT 프로토콜 상세 가이드
- [PRD.md](prd.md) - 프로젝트 요구사항 및 설계 문서