# EQ-1 Network

EQ-1 Network는 다양한 통신 프로토콜을 플러그인 기반으로 확장 가능하게 구성한 Python 통신 프레임워크입니다.

## 개요

현재 MQTT, TCP, Serial 프로토콜을 지원하며, 다음 기능을 제공합니다:

- **MQTT**: MQTT v3.1.1 기본 기능 지원, 인증, 재연결, QoS
- **TCP**: TCP 클라이언트/서버 통신, 바이너리/텍스트 데이터 지원
- **Serial**: 시리얼 포트 통신, 다양한 보드레이트 지원
- **Authentication**: Username/Password 인증 (MQTT)
- **Reliability**: 재연결 시 구독 자동 복구 (MQTT)
- **Thread Safety**: 스레드 안전한 API 설계
- **Manager System**: ReqResManager, PubSubManager를 통한 통합 관리

## 시작하기 전에

다음 요구사항을 확인하세요:

- Python 3.10+
- paho-mqtt 1.6.0+
- pyserial 3.5+ (Serial 통신 사용 시)

## 설치

```bash
pip install -r requirements.txt
```

## 빠른 시작

### 기본 MQTT 사용법
```python
from eq1_network.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

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

### 기본 TCP 사용법
```python
from app import ReqResManager
from eq1_network.protocols.ethernet.tcp_client import TCPClient
from eq1_network.protocols.ethernet.tcp_server import TCPServer

# TCP 클라이언트 설정
tcp_client = TCPClient("localhost", 8080, timeout=1)
ReqResManager.register("tcp_client", tcp_client)

# TCP 서버 설정
tcp_server = TCPServer("localhost", 8081, timeout=1)
ReqResManager.register("tcp_server", tcp_server)

# 연결 및 통신
if ReqResManager.connect("tcp_client"):
    result = ReqResManager.send("tcp_client", b"Hello Server!")
    if result > 0:
        response = ReqResManager.read("tcp_client")
        print(f"Response: {response.decode()}")
    ReqResManager.disconnect("tcp_client")
```

### 기본 Serial 사용법
```python
from app import ReqResManager
from eq1_network.protocols.serial.serial_protocol import SerialProtocol

# 시리얼 프로토콜 설정
serial_protocol = SerialProtocol("COM1", 9600, timeout=1)
ReqResManager.register("serial", serial_protocol)

# 연결 및 통신
if ReqResManager.connect("serial"):
    result = ReqResManager.send("serial", b"AT\r\n")
    if result > 0:
        response = ReqResManager.read("serial")
        print(f"Response: {response.decode()}")
    ReqResManager.disconnect("serial")
```

### 인증 연결 (MQTT)
```python
from eq1_network.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

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
- **TCP 프로토콜:**
    - TCP 클라이언트/서버 통신 지원
    - 바이너리/텍스트 데이터 송수신
    - 타임아웃 설정 및 연결 관리
    - JSON 데이터 구조화 지원
- **Serial 프로토콜:**
    - 시리얼 포트 통신 지원
    - 다양한 보드레이트 설정
    - 바이너리/텍스트 데이터 송수신
    - AT 명령어 지원
- **인증 기능:**
    - Username/Password 인증 (MQTT)
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
- **데이터 클래스:**
    - `SendData`, `ReceivedData` 추상 클래스 구현
    - `PacketStructure` 패킷 구조화 클래스
    - `PacketStructureInterface` 패킷 인터페이스
- **매니저 시스템:**
    - `ReqResManager`: ReqRes 프로토콜 통합 관리
    - `PubSubManager`: PubSub 프로토콜 통합 관리

### 🔄 미구현 기능
- **플러그인 기반 확장:**
    - Modbus 등 새로운 프로토콜 추가 예정
- **보안 강화:**
    - TLS/SSL 지원, Will Message 등
- **MQTT v5.0 기능들:**
    - Shared Subscriptions, Message Expiry 등
- **PacketInterface 완전 구현:**
    - SendData/ReceivedData 클래스의 PacketInterface 상속
    - NetworkHandler 클래스의 PacketInterface 지원

## 프로젝트 구조
```
app/
├── common/         # 공통 모듈 (예외, 로깅 등)
├── interfaces/     # 추상 인터페이스 (Protocol, Packet 등)
├── manager/        # 프로토콜 매니저
├── protocols/      # 실제 프로토콜 구현체
│   ├── mqtt/       # MQTT 프로토콜 구현
│   ├── ethernet/   # TCP 프로토콜 구현
│   └── serial/     # Serial 프로토콜 구현
├── worker/         # Listener, Requester 워커 모듈
├── data.py         # SendData, ReceivedData, PacketStructure
├── network.py      # NetworkHandler
└── cli.py          # CLI 인터페이스
```

## 시스템 요구사항
- Python 3.10+ (권장)
- OS: Windows, macOS, Linux
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
    - 추상 메소드: `send()`, `read()`
- **PubSubProtocol (BaseProtocol 상속)**
    - 발행/구독 기반 통신 프로토콜 인터페이스
    - 추상 메소드: `publish()`, `subscribe()`, `unsubscribe()`

### 현재 구현체
- **MQTTProtocol**
    - `PubSubProtocol` 인터페이스 구현
    - paho-mqtt 라이브러리 기반
    - 기본 MQTT 기능 지원
- **TCPClient/TCPServer**
    - `ReqResProtocol` 인터페이스 구현
    - TCP 클라이언트/서버 통신 지원
- **SerialProtocol**
    - `ReqResProtocol` 인터페이스 구현
    - 시리얼 포트 통신 지원
- **BrokerConfig & ClientConfig**
    - MQTT 연결 설정을 위한 데이터 클래스
    - 브로커 주소, 포트, 인증 정보 등

### 데이터 클래스
- **SendData (ABC)**
    - 전송 데이터 추상 클래스
    - `to_bytes()` 메서드 구현 필요
- **ReceivedData (ABC)**
    - 수신 데이터 추상 클래스
    - `from_bytes()` 클래스 메서드 구현 필요
- **PacketStructure**
    - 패킷 구조화 및 직렬화/역직렬화
    - HEAD_PACKET, TAIL_PACKET 기반 프레이밍

### 매니저 시스템
- **ReqResManager**
    - ReqRes 프로토콜 통합 관리
    - `register(name, protocol)`: 프로토콜 등록
    - `connect(name)`: 연결
    - `send(name, data)`: 데이터 전송 (int 반환)
    - `read(name)`: 데이터 수신 (bytes 반환)
    - `disconnect(name)`: 연결 해제
- **PubSubManager**
    - PubSub 프로토콜 통합 관리
    - `register(name, protocol)`: 프로토콜 등록
    - `connect(name)`: 연결
    - `publish(name, topic, message)`: 메시지 발행
    - `subscribe(name, topic, callback)`: 토픽 구독
    - `disconnect(name)`: 연결 해제

### 예외 처리
- **ProtocolConnectionError**: 연결 실패, 타임아웃
- **ProtocolValidationError**: 메시지 발행/구독 실패
- **ProtocolError**: 일반적인 프로토콜 오류
- **ProtocolAuthenticationError**: 인증 실패
- **ProtocolTimeoutError**: 타임아웃 오류
- **ProtocolDecodeError**: 디코딩 오류

## 프레임워크 확장
새로운 통신 프로토콜을 추가하려면 적절한 인터페이스를 상속받아 구현합니다.

### Req/Res 프로토콜 추가
```python
from eq1_network.interfaces.protocol import ReqResProtocol

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
    
    def read(self) -> Tuple[bool, Optional[bytes]]:
        # 데이터 수신 구현
        pass
```

### Pub/Sub 프로토콜 추가
```python
from eq1_network.interfaces.protocol import PubSubProtocol

class RedisProtocol(PubSubProtocol):
    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool:
        # Redis pub/sub 구현
        pass
    
    def subscribe(self, topic: str, callback, qos: int = 0) -> bool:
        # Redis 구독 구현
        pass
```

## 예제 코드

### 메시지 팩토리 및 통신 예시
`data_utils.py`에서 제공하는 메시지 생성 및 통신 예시:

```python
from eq1_network.examples.data.data_utils import MessageFactory, example_text_communication

# 메시지 생성
text_msg = MessageFactory.create_text_message("msg001", MessageType.COMMAND, "client", "server", "Hello")
binary_msg = MessageFactory.create_binary_message("msg002", MessageType.DATA, "sensor", "controller", b"\x01\x02")
int_msg = MessageFactory.create_int_message("msg003", MessageType.STATUS, "device", "monitor", 42)

# 통신 예시 실행
packet, received = example_text_communication()
print(f"Packet: {packet}, Received: {received}")
```

### 종합 예제
프로젝트에는 각 프로토콜별 종합 예제가 포함되어 있습니다:

- `examples/comprehensive_mqtt_example.py` - MQTT 종합 예제
- `examples/comprehensive_tcp_example.py` - TCP 종합 예제
- `examples/comprehensive_serial_example.py` - Serial 종합 예제
- `examples/data/data_utils.py` - 메시지 생성 및 통신 유틸리티

### TCP 클라이언트-서버 예제
```python
import threading
import time
from app import ReqResManager
from eq1_network.protocols.ethernet.tcp_client import TCPClient
from eq1_network.protocols.ethernet.tcp_server import TCPServer

# 서버 스레드
def server_thread():
    server = TCPServer("localhost", 8080, timeout=1)
    ReqResManager.register("server", server)
    
    if ReqResManager.connect("server"):
        print("Server started")
        while True:
            data = ReqResManager.read("server")
            if data:
                print(f"Server received: {data.decode()}")
                ReqResManager.send("server", b"Server response")
            time.sleep(0.1)

# 클라이언트
def client_example():
    client = TCPClient("localhost", 8080, timeout=1)
    ReqResManager.register("client", client)
    
    if ReqResManager.connect("client"):
        result = ReqResManager.send("client", b"Hello from client")
        if result > 0:
            response = ReqResManager.read("client")
            print(f"Client received: {response.decode()}")
        ReqResManager.disconnect("client")

# 실행
server = threading.Thread(target=server_thread, daemon=True)
server.start()
time.sleep(1)
client_example()
```

### Serial 통신 예제
```python
from app import ReqResManager
from eq1_network.protocols.serial.serial_protocol import SerialProtocol

# 시리얼 프로토콜 설정
serial = SerialProtocol("COM1", 9600, timeout=1)
ReqResManager.register("serial", serial)

if ReqResManager.connect("serial"):
    # AT 명령어 전송
    result = ReqResManager.send("serial", b"AT\r\n")
    if result > 0:
        response = ReqResManager.read("serial")
        print(f"AT Response: {response.decode()}")
    
    # 데이터 전송
    result = ReqResManager.send("serial", b"Hello Device\r\n")
    if result > 0:
        response = ReqResManager.read("serial")
        print(f"Device Response: {response.decode()}")
    
    ReqResManager.disconnect("serial")
```

## 테스트
- **단위 테스트**: Mock 기반 개별 기능 테스트
- **통합 테스트**: 실제 MQTT 브로커, TCP, Serial과의 연동 테스트
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

# TCP 프로토콜만 테스트
pytest tests/units/test_tcp_protocol.py -v
```

### 테스트 커버리지
현재 테스트 커버리지: **90%+** 달성

## 다음 단계

### 단기 로드맵
- TLS/SSL 보안 연결 지원
- Will Message 기능 추가
- 자동 재연결 기능 추가 개선 (재시도 횟수 제한, 상태 콜백 등)

### 장기 로드맵
- Modbus 프로토콜 추가
- 플러그인 매니저 개발
- 성능 최적화 및 비동기 처리 강화

## 참고 자료
- [MQTT Protocol](mqtt_protocol.md) - MQTT 프로토콜 상세 가이드
- [PRD.md](prd.md) - 프로젝트 요구사항 및 설계 문서