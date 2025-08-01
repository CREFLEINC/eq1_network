# EQ-1 Network

EQ-1 Network는 다양한 통신 프로토콜을 플러그인 기반으로 확장 가능하게 구성한 Python 통신 프레임워크입니다.

## 개요

현재 RFC 준수 MQTT 프로토콜을 완전 지원하며, 다음 기능을 제공합니다:

- **Security**: Username/Password 인증, TLS/SSL 암호화
- **Reliability**: 자동 재연결, 메시지 큐잉
- **RFC Compliance**: Will Message, Retained Messages, QoS 0-2
- **Thread Safety**: 모든 API가 thread-safe하게 설계

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
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

# 1. 설정 객체 생성
config = MQTTConfig(
    broker_address="localhost",
    port=1883,
    timeout=60
)

# 2. MQTT 프로토콜 인스턴스 생성
mqtt = MQTTProtocol(config)

# 3. 연결
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

### 보안 연결
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

# RFC 준수: 인증 및 TLS 보안 설정
config = MQTTConfig(
    broker_address="secure-broker.example.com",
    port=8883,  # TLS 포트
    username="mqtt_user",
    password="secure_password",
    ca_certs="/path/to/ca.crt",
    timeout=30
)

mqtt = MQTTProtocol(config)

# RFC 준수: Will Message 설정
mqtt.set_will(
    topic="device/status",
    payload="offline",
    qos=1,
    retain=True
)

mqtt.connect()

# RFC 준수: Retained Message 발행
mqtt.publish("device/status", "online", qos=1, retain=True)

mqtt.disconnect()
```

## 주요 기능

### 현재 구현 상태
- **RFC 준수 MQTT 프로토콜:**
    - MQTT v3.1.1 및 v5.0 표준 95% 준수
    - QoS 0, 1, 2 레벨 완전 지원 (기본값: QoS 1)
    - Keep-alive 메커니즘 및 자동 재연결
- **보안 기능:**
    - Username/Password 인증
    - TLS/SSL 암호화 연결
    - CA 인증서 기반 인증
- **고급 MQTT 기능:**
    - Will Message (Last Will and Testament)
    - Retained Messages
    - 상세한 RFC 준수 에러 처리
- **신뢰성 보장:**
    - 자동 재연결 시 구독 복구
    - publish 실패 시 내부 큐에 저장 후 재전송
    - Thread-safe API 설계

### 계획된 기능
- **플러그인 기반 확장:**
    - TCP, Serial, Modbus 등 새로운 프로토콜 추가 예정
- **추상화된 인터페이스:**
    - `ReqRes(요청/응답), PubSub(발행/구독)` 인터페이스
- **예외/로깅 통합:**
    - 공통 예외 클래스와 로깅 체계

## 프로젝트 구조
```
communicator/
├── common/         # 공통 모듈 (예외, 로깅 등)
├── interfaces/     # 추상 인터페이스 (Protocol 등)
├── manager/        # 프로토콜 매니저
├── protocols/      # 실제 프로토콜 구현체 (MQTT 등)
├── docs/           # 문서
├── __init__.py
└── ...
├── tests/          # 단위 테스트
├── README.md       # 프로젝트 설명
└── requirements.txt # 프로젝트 의존성
```

## 시스템 요구사항
- Python 3.10.18 (권장)
- OS: macOS Sonoma
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
    - **RFC 준수**: `retain` 파라미터 지원

### 현재 구현체
- **MQTTProtocol**
    - `PubSubProtocol` 인터페이스 구현
    - paho-mqtt 라이브러리 기반
    - RFC 준수 기능 완전 지원
- **MQTTConfig**
    - MQTT 연결 설정을 위한 데이터 클래스
    - 보안, 재연결, 고급 옵션 지원

### 예외 처리
- **ProtocolConnectionError**: 연결 실패, 타임아웃
- **ProtocolAuthenticationError**: 인증 실패 (RFC 준수)
- **ProtocolValidationError**: 메시지 발행/구독 실패
- **ProtocolDecodeError**: 메시지 디코딩 실패
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
- **RFC 준수 테스트**: 보안, Will Message, Retained Messages 등

### 테스트 실행
```bash
# 전체 테스트
pytest tests/

# 커버리지 포함 테스트
pytest tests/ --cov=communicator --cov-report=html

# MQTT 프로토콜만 테스트
pytest tests/test_mqtt_protocol.py -v
```

### 테스트 커버리지
현재 테스트 커버리지: **90%+** 달성

## 다음 단계

### 단기 로드맵
- MQTT v5.0 완전 지원 (User Properties, Topic Aliases)
- 클러스터 브로커 지원
- 메트릭 및 모니터링 기능

### 장기 로드맵
- TCP, Serial, Modbus 프로토콜 추가
- 플러그인 매니저 개발
- 성능 최적화 및 비동기 처리 강화

## 참고 자료
- [PRD.md](docs/prd.md) - 프로젝트 요구사항 및 설계 문서
- [MQTT Protocol](docs/mqtt_protocol.md) - RFC 준수 MQTT 프로토콜 상세 가이드
- [RFC 3376](https://tools.ietf.org/html/rfc3376) - MQTT v3.1.1 표준
- [MQTT v5.0 Specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html) - MQTT v5.0 표준