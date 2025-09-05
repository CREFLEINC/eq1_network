# 제품 요구사항 문서: EQ-1 Network
EQ-1 Network는 다양한 산업 및 IoT 환경에서 사용할 수 있는 플러그인 기반 통신 프레임워크입니다.

## 문서 목적
이 문서는 EQ-1 Network의 목적, 요구사항, 설계 방향, 제약사항을 명확히 정의하여 팀 내 공통된 이해를 돕습니다.

## 개요
- MQTT, TCP, Serial을 시작으로 다양한 통신 프로토콜을 표준화된 인터페이스로 지원합니다.
- 신규 프로토콜을 플러그인 방식으로 쉽게 확장할 수 있습니다.
- 공통 ReqRes / PubSub 인터페이스와 일관된 직렬화 규칙을 제공합니다.
- Core-Network 연동: PacketStructureInterface 인터페이스를 통한 표준화된 패킷 처리 시스템을 제공합니다.

### 아키텍처 다이아그램
```mermaid
flowchart TD
    subgraph Application["응용 시스템"]
        UI["UI / Vision System"] --> NET["EQ-1 Network 모듈"]
    end

    NET --> MANAGER["Protocol Manager"]
    MANAGER --> INTERFACES["ReqRes / PubSub Interfaces"]
    INTERFACES --> PACKET["PacketStructureInterface"]
    INTERFACES --> PROTOCOLS["Protocol Plugins"]

    PROTOCOLS --> MQTT["MQTTProtocol"]
    PROTOCOLS --> TCP["TCPClient/TCPServer"]
    PROTOCOLS --> SERIAL["SerialProtocol"]
    PROTOCOLS --> MODBUS[(Future) ModbusProtocol]
    
    PACKET --> SENDDATA["SendData"]
    PACKET --> RECEIVEDDATA["ReceivedData"]
    PACKET --> NETWORKHANDLER["NetworkHandler"]
```

## 목표
- 신규 프로토콜을 플러그인 형태로 쉽게 확장
- 공통 인터페이스(ReqRes, PubSub) 제공
- 일관된 패킷 직렬화/역직렬화 규칙 확립
- Core-Network 연동: 표준화된 패킷 인터페이스를 통한 데이터 처리 통합

## 배경
- 기존 시스템별 통신 구현 중복
- MQTT, TCP/UDP, Serial, Modbus 등 여러 프로토콜을 하나의 코드베이스로 관리할 필요성 존재
- Core-Network 연동 필요성: 다양한 데이터 타입(List, Dict 등)을 일관된 방식으로 처리할 수 있는 표준 인터페이스 필요

## 성공 지표

### 현재 상태
- **개발 속도**: ✅ 달성 - MQTT v3.1.1, TCP, Serial 기본 기능 구현 완료
- **품질 지표**: ✅ 달성 - 테스트 커버리지 90%+ 달성
- **MQTT 기본 기능**: ✅ 달성 - MQTT v3.1.1 기본 표준 준수
- **TCP 프로토콜**: ✅ 구현됨 - TCPClient/TCPServer 클래스 구현 완료
- **Serial 프로토콜**: ✅ 구현됨 - SerialProtocol 클래스 구현 완료
- **데이터 클래스**: ✅ 구현됨 - SendData, ReceivedData, PacketStructure 클래스 구현 완료
- **인터페이스**: ✅ 구현됨 - BaseProtocol, ReqResProtocol, PubSubProtocol 인터페이스 구현
- **예외 처리**: ✅ 구현됨 - ProtocolError 계층 구조 구현
- **워커 모듈**: ✅ 구현됨 - Listener, Requester 스레드 기반 워커 구현
- **매니저 시스템**: ✅ 구현됨 - ReqResManager, PubSubManager 구현 완료

### 지속적 목표
- **안정성**: 3개월간 치명적 통신 버그 0건 유지
- **성능**: 초당 10,000 메시지 처리 성능 유지
- **확장성**: 6개월 내 Modbus 프로토콜 추가

## 범위

### 포함 사항
- 통신 프로토콜 공통 인터페이스
- 패킷 구조화 및 직렬화
- MQTT 프로토콜 구현 (PubSub)
- TCP 프로토콜 구현 (ReqRes) - 클라이언트/서버
- Serial 프로토콜 구현 (ReqRes)
- 단위 테스트 및 샘플 예제
- PacketStructureInterface 인터페이스 구현
- SendData/ReceivedData 클래스 구현
- NetworkHandler 클래스 구현
- Listener/Requester 워커 모듈 구현
- ReqResManager/PubSubManager 구현
- NetworkPacketStructure 및 다중 포맷 메시지 지원
- DataPackage 통합 관리 시스템

### 제외 사항
- UI (GUI, Web)
- 데이터 저장소, 서비스 로직
- 배포/운영 자동화

## 기능 요구사항
| ID   | 요구사항 | 상세 |
| :--- | :--- | :--- |
| **F-01** | **플러그인 기반 통신 모듈** | - `BaseProtocol` 인터페이스를 상속한 클래스를 `protocols` 디렉토리에 추가하는 것만으로 신규 프로토콜이 확장되어야 함.<br/>- `ProtocolManager`는 지정된 경로에서 사용 가능한 프로토콜을 동적으로 탐색하고 로드해야 함. |
| **F-02** | **ReqRes 인터페이스** | - `ReqResProtocol` 추상 클래스는 다음 메서드를 반드시 포함해야 함:<br/>  - `connect()` / `disconnect()`: 대상과의 연결 수립 및 종료<br/>  - `send(data: bytes) -> int`: 데이터 동기 전송 (전송된 바이트 수 반환)<br/>  - `read() -> Tuple[bool, Optional[bytes]]`: 응답 데이터 수신 (Non-blocking)<br/>  - `is_connected() -> bool`: 연결 상태 반환 |
| **F-03** | **PubSub 인터페이스** | - `PubSubProtocol` 추상 클래스는 다음 메서드를 반드시 포함해야 함:<br/>  - `connect()` / `disconnect()`: 브로커와의 연결 수립 및 종료<br/>  - `publish(topic: str, message: str, qos: int, retain: bool)`: 메시지 발행<br/>  - `subscribe(topic: str, callback: Callable)`: 토픽 구독 및 콜백 등록<br/>  - `unsubscribe(topic: str, callback: Callable)`: 토픽 구독 취소 |
| **F-04** | **PacketStructure** | - 모든 통신 데이터는 `PacketStructure` 클래스를 통해 처리.<br/>- `to_packet(data: bytes) -> bytes`: 데이터를 패킷으로 직렬화.<br/>- `from_packet(packet: bytes) -> bytes`: 패킷을 데이터로 역직렬화.<br/>- `is_valid(packet: bytes) -> bool`: 패킷 유효성 검사.<br/>- `split_packet(packet: bytes) -> list[bytes]`: 패킷 분할. |
| **F-05** | **RFC 준수 MQTTProtocol 구현** | - `PubSubProtocol` 인터페이스를 `paho-mqtt` 라이브러리로 구현.<br/>- **현재 구현**: Username/Password 인증, Retained Messages<br/>- **현재 구현**: 예기치 못한 연결 실패 시 자동 재연결 (지수 백오프)<br/>- **현재 구현**: 재연결 시 구독 자동 복구 및 메시지 큐 처리<br/>- **현재 구현**: QoS (0, 1, 2) 레벨 완전 지원<br/>- **현재 구현**: 상세한 RFC 준수 에러 처리 |
| **F-06** | **TCP 프로토콜 구현** | - `ReqResProtocol` 인터페이스를 구현한 TCPClient/TCPServer 클래스<br/>- **현재 구현**: TCP 클라이언트/서버 통신 지원<br/>- **현재 구현**: 바이너리/텍스트 데이터 송수신<br/>- **현재 구현**: 타임아웃 설정 및 연결 관리<br/>- **현재 구현**: JSON 데이터 구조화 지원 |
| **F-07** | **Serial 프로토콜 구현** | - `ReqResProtocol` 인터페이스를 구현한 SerialProtocol 클래스<br/>- **현재 구현**: 시리얼 포트 통신 지원<br/>- **현재 구현**: 다양한 보드레이트 설정<br/>- **현재 구현**: 바이너리/텍스트 데이터 송수신<br/>- **현재 구현**: AT 명령어 지원 |
| **F-08** | **Thread-safe 보장** | - publish, subscribe, unsubscribe, 큐 처리 등 모든 API가 thread-safe해야 함 |
| **F-09** | **테스트 코드 제공** | - `pytest`와 `unittest.mock`을 사용하여 각 컴포넌트의 독립적인 동작을 검증.<br/>- `MQTTProtocol` 테스트를 위해 Mock MQTT 브로커를 사용.<br/>- CI 환경에서 실행 가능해야 하며, 코드 커버리지 90% 이상을 목표로 함. |
| **F-10** | **PacketStructureInterface 인터페이스** | - `abc.ABC` 기반의 `PacketStructureInterface` 추상 클래스 구현<br/>- `to_packet(data: bytes) -> bytes`: 데이터를 패킷으로 직렬화<br/>- `from_packet(packet: bytes) -> bytes`: 패킷을 데이터로 역직렬화<br/>- `is_valid(packet: bytes) -> bool`: 패킷 유효성 검사<br/>- `split_packet(packet: bytes) -> list[bytes]`: 패킷 분할 |
| **F-11** | **SendData 클래스 구현** | - `abc.ABC` 기반의 `SendData` 추상 클래스 구현<br/>- `to_bytes() -> bytes`: 객체를 전송 가능한 바이트로 직렬화 |
| **F-12** | **ReceivedData 클래스 구현** | - `abc.ABC` 기반의 `ReceivedData` 추상 클래스 구현<br/>- `from_bytes(data: bytes) -> Self`: 바이트 데이터를 객체로 역직렬화 |
| **F-13** | **NetworkHandler 클래스 구현** | - `send`, `receive` 메서드가 포함된 클래스 구축<br/>- Listener, Requester 워커 모듈과 연동 |
| **F-14** | **워커 모듈 구현** | - Listener: 수신 처리 스레드<br/>- Requester: 송신 처리 스레드<br/>- 이벤트 기반 콜백 처리 |
| **F-15** | **매니저 시스템 구현** | - ReqResManager: ReqRes 프로토콜 통합 관리<br/>  - `register(name, protocol)`: 프로토콜 등록<br/>  - `send(name, data) -> int`: 데이터 전송 (전송된 바이트 수 반환)<br/>  - `read(name) -> bytes`: 데이터 수신 (bytes 반환)<br/>- PubSubManager: PubSub 프로토콜 통합 관리<br/>  - `register(name, protocol)`: 프로토콜 등록<br/>  - `publish(name, topic, message)`: 메시지 발행<br/>  - `subscribe(name, topic, callback)`: 토픽 구독<br/>- 플러그인 등록/관리 기능 |
| **F-16** | **NetworkPacketStructure 구현** | - `PacketStructureInterface`를 구현한 `NetworkPacketStructure` 클래스<br/>- 4바이트 헤더 기반 패킷 구조 (빅엔디안)<br/>- 최대 1MB 페이로드 크기 제한<br/>- 패킷 분할 및 병합 기능<br/>- 메시지 타입별 직렬화/역직렬화 지원 |
| **F-17** | **다중 포맷 메시지 지원** | - TEXT, BINARY, INT 포맷 지원<br/>- 각 포맷별 SendData/ReceivedData 클래스 구현<br/>- 메시지 타입 정의 (COMMAND, DATA, RESPONSE, STATUS, ERROR, HEARTBEAT, FILE_TRANSFER, BULK_DATA)<br/>- 타임스탬프, 소스/목적지 정보 포함 |
| **F-18** | **DataPackage 통합 관리** | - 패킷 구조와 데이터 클래스를 묶은 `DataPackage` 클래스<br/>- 포맷별 사전 정의된 패키지 (TEXT_PACKAGE, BINARY_PACKAGE, INT_PACKAGE)<br/>- 일관된 데이터 처리 인터페이스 제공 |

## 비기능 요구사항
| ID | 요구사항 | 상세 |
| :--- | :--- | :--- |
| **NF-01** | **확장성** | - **OCP (개방-폐쇄 원칙):** 새로운 프로토콜 추가 시, 기존 핵심 코드(`manager`, `interfaces` 등)의 수정 없이 확장 가능해야 함.<br/>- 개발자는 정의된 프로토콜 인터페이스를 구현하는 것만으로 모듈을 추가할 수 있어야 함. |
| **NF-02** | **가독성** | - 모든 코드는 `black`, `isort` 포매터를 사용하여 일관된 스타일을 유지.<br/>- 모든 공개(public) 클래스 및 함수에는 **Google Style Docstring**을 작성하여 파라미터, 반환값, 예외 등을 명확히 설명. |
| **NF-03** | **표준화** | - 모든 프로토콜은 `ProtocolManager`를 통해 `get_protocol("이름")` 형식의 단일 API로 접근.<br/>- 예외 처리는 `common.exceptions`에 정의된 커스텀 예외 클래스를 사용하여 일관되게 처리.<br/>- 로깅은 Python 표준 `logging` 모듈을 사용하며, 설정이 통일되어야 함. |
| **NF-04** | **유지보수성** | - 프로토콜 구현(`protocols`), 인터페이스(`interfaces`), 공통 기능(`common`) 등 역할에 따라 코드를 명확히 분리 (낮은 결합도).<br/>- 각 모듈은 하나의 핵심 책임만 가지도록 설계 (높은 응집도). |

## 설계 개요

### 디렉토리 구조
```
app/
├── common/         # 예외, 로깅
├── interfaces/     # Protocol 인터페이스, PacketStructureInterface 인터페이스
├── protocols/      # MQTTProtocol, TCPClient/TCPServer, SerialProtocol 등
│   ├── mqtt/       # MQTT 프로토콜 구현
│   ├── ethernet/   # TCP 프로토콜 구현
│   └── serial/     # Serial 프로토콜 구현
├── manager/        # 프로토콜 로딩 및 관리
├── worker/         # Listener, Requester
├── data.py         # SendData, ReceivedData
├── network.py      # NetworkHandler
└── cli.py          # CLI 인터페이스
```

### 주요 컴포넌트
- **인터페이스 레이어**
    - `ReqResProtocol` / `PubSubProtocol`: 통신 유형별 표준 인터페이스
    - `BaseProtocol`: 모든 프로토콜의 공통 기반 인터페이스
    - **`PacketStructureInterface`**: 패킷 직렬화/역직렬화 표준 인터페이스
- **데이터 클래스**
    - **`SendData`**: 전송 데이터 추상 클래스
    - **`ReceivedData`**: 수신 데이터 추상 클래스
- **네트워크 핸들러**
    - **`NetworkHandler`**: 네트워크 통신 핸들러
- **워커 모듈**
    - **`Listener`**: 수신 처리 스레드
    - **`Requester`**: 송신 처리 스레드
- **매니저 시스템**
    - **`ReqResManager`**: ReqRes 프로토콜 통합 관리
        - `register(name, protocol)`: 프로토콜 등록
        - `connect(name)`: 연결
        - `send(name, data)`: 데이터 전송 (int 반환)
        - `read(name)`: 데이터 수신 (bytes 반환)
        - `disconnect(name)`: 연결 해제
    - **`PubSubManager`**: PubSub 프로토콜 통합 관리
        - `register(name, protocol)`: 프로토콜 등록
        - `connect(name)`: 연결
        - `publish(name, topic, message)`: 메시지 발행
        - `subscribe(name, topic, callback)`: 토픽 구독
        - `disconnect(name)`: 연결 해제
- **RFC 준수 MQTT 구현**
    - `MQTTProtocol`: paho-mqtt 기반 RFC 준수 구현
    - `BrokerConfig`, `ClientConfig`: 설정 관리를 위한 데이터 클래스
- **TCP 프로토콜 구현**
    - `TCPClient`: TCP 클라이언트 구현
    - `TCPServer`: TCP 서버 구현
- **Serial 프로토콜 구현**
    - `SerialProtocol`: 시리얼 통신 구현
- **보안 및 신뢰성**
    - Username/Password 인증
    - **예기치 못한 연결 실패 시 자동 재연결** (지수 백오프)
    - 재연결 시 구독 복구 및 메시지 큐 처리
    - Thread-safe 설계
- **에러 처리**
    - RFC 준수 상세 연결 실패 코드 처리
    - 예외 클래스 계층 구조

## 사용자 시나리오

### 현재 구현된 MQTT 예시
```python
from eq1_network.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

# 기본 인증 설정
broker_config = BrokerConfig(
    broker_address="broker.example.com",
    port=1883,
    username="mqtt_username",
    password="mqtt_password"
)
client_config = ClientConfig()

mqtt = MQTTProtocol(broker_config, client_config)

# 명시적 연결 필요
mqtt.connect()

def message_callback(topic: str, payload: bytes):
    print(f"Received: [{topic}] {payload.decode()}")

mqtt.subscribe("topic/test", message_callback)
mqtt.publish("topic/test", "hello", qos=1, retain=True)
mqtt.disconnect()
```

### 현재 구현된 TCP 예시
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

### 현재 구현된 Serial 예시
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

### 미구현 기능 예시 (계획만)
```python
# 다음 기능들은 아직 구현되지 않았습니다:

# TLS/SSL 보안 연결 (미구현)
broker_config = BrokerConfig(
    broker_address="secure-broker.example.com",
    port=8883,
    ca_certs="/path/to/ca.crt"  # 미구현
)

# Will Message 설정 (미구현)
mqtt.set_will("device/status", "offline", qos=1, retain=True)  # 미구현
```

### 향후 Req/Res 예시 (계획)
```python
# Modbus 프로토콜 추가 예정
modbus = ModbusProtocol("192.168.0.10", 502)
modbus.connect()
modbus.send(b"PING")
resp = modbus.read()
```

### PacketStructure 사용 예시
```python
# PacketInterface를 통한 표준화된 데이터 처리
from eq1_network.interfaces.packet import PacketStructureInterface

class PacketStructure(PacketStructureInterface):
    HEAD_PACKET = b'$'
    TAIL_PACKET = b'$'

    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        return cls.HEAD_PACKET + data + cls.TAIL_PACKET

    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        if not cls.is_valid(packet):
            raise ValueError(f"Packet Structure Error : {packet}")

        return packet[1:-1]

    @classmethod
    def is_valid(cls, packet: bytes) -> bool:
        if (cls.TAIL_PACKET + cls.HEAD_PACKET) in packet:
            return False

        if packet[:1] != cls.HEAD_PACKET:
            return False

        if packet[-1:] != cls.TAIL_PACKET:
            return False

        return True

    @classmethod
    def split_packet(cls, packet: bytes) -> list[bytes]:
        results = []
        for _d in packet.split(cls.HEAD_PACKET):
            if len(_d) == 0:
                continue
            results.append(cls.HEAD_PACKET+_d+cls.TAIL_PACKET)
        return results

# SendData 클래스 사용
class TestSendData(SendData):
    def __init__(self, cmd: str, data: list):
        self.cmd = cmd
        self.data = data
    
    def to_bytes(self) -> bytes:
        result = self.cmd
        for datum in self.data:
            result += f"#{datum}"
        return result.encode('utf-8')

# ReceivedData 클래스 사용
class TestReceivedData(ReceivedData):
    @classmethod
    def from_bytes(cls, data: bytes):
        data_str = data.decode('utf-8')
        split_data = data_str.split('#')
        if len(split_data) == 1:
            return cls(cmd=split_data[0], data=[])
        return cls(cmd=split_data[0], data=split_data[1:])

send_data = TestSendData("TEST", ["1", "2", "3", "4", "5"])
packet_bytes = PacketStructure.to_packet(send_data.to_bytes())  # List를 바이트로 직렬화

# NetworkHandler 사용
network_handler = NetworkHandler(network_config, event_callback)
network_handler.send_data(send_data)  # PacketStructure 기반 전송
```

## 테스트 전략
- 단위 테스트 (Unit Test)
    - pytest 기반으로 각 프로토콜과 PacketStructure 단위 테스트 진행
    - Mock 객체를 이용한 독립적인 동작 검증
    - PacketStructureInterface 인터페이스 단위 테스트 추가
    - NetworkHandler 클래스 단위 테스트 추가
- 통합 테스트 (Integration Test)
    - 실제 MQTT 브로커 환경에서 publish/subscribe 기능 검증
    - TCP 클라이언트/서버 통신 테스트
    - 시리얼 통신 테스트
    - SendData/ReceivedData 클래스 통합 테스트 추가
    - PacketStructure 기반 통신 통합 테스트 추가
- 자동화
    - CI 파이프라인에서 자동 실행되도록 설정
    - 코드 커버리지 측정을 통해 목표 커버리지 90% 이상 유지

## 위험 완화
| 위험 (Risk) | 발생 가능성 | 영향도 | 대응 |
| :--- | :---: | :---: | :--- |
| **외부 라이브러리 의존성** | 중간 | 높음 | - 라이브러리 핵심 기능을 직접 호출하지 않고, 어댑터(Adapter) 클래스로 한 번 더 감싸서 구현합니다.<br/>- 이를 통해 문제 발생 시 다른 라이브러리(예: gmqtt)로 최소한의 코드 수정으로 교체할 수 있습니다. |
| **플러그인 아키텍처의 한계** | 중간 | 높음 | - 초기 인터페이스 설계 시 TCP/IP 기반의 요청/응답 시나리오를 미리 고려하여 `ReqResProtocol` 인터페이스를 정의합니다.<br/>- Modbus 프로토콜 추가 단계에서 PoC(Proof of Concept)를 먼저 진행하여 아키텍처의 확장성을 검증합니다. |
| **낮은 내부 채택률** | 높음 | 중간 | - 상세한 `README.md`와 예제 코드를 제공하여 사용 장벽을 낮춥니다.<br/>- 주요 사용 예상 팀을 대상으로 초기 버전 데모 및 피드백 세션을 진행하여 요구사항을 반영하고 참여를 유도합니다. |
| **PacketStructure 설계 복잡성** | 중간 | 중간 | - 간단하고 직관적인 인터페이스 설계로 복잡성 최소화<br/>- 기존 SendData/ReceivedData 클래스와의 호환성 보장<br/>- 충분한 테스트 케이스 작성으로 안정성 확보 |
| **기존 코드 호환성** | 높음 | 높음 | - 단계적 마이그레이션으로 기존 코드와의 호환성 보장<br/>- PacketStructure와 PacketStructureInterface 병행 지원 기간 설정<br/>- 충분한 테스트를 통한 안정성 검증 |

## 배포 및 재사용
- 패키지화
    - 내부 PyPI 서버에 업로드하거나, git submodule 형태로 관리
- 재사용 방법
    - 동일한 구조를 유지하여 다른 비전 시스템, 공장 자동화 시스템에서 그대로 임포트 가능
- 버전 관리
    - SemVer(유의적 버전) 정책 적용
    - 주요 변경사항 발생 시 CHANGELOG에 기록

## 제약사항

### 기술적 제약
- **Python 버전**: 3.10.18 (권장)
- **외부 의존성**: paho-mqtt 1.6.0+, pyserial 3.5+
- **운영체제**: Windows, macOS, Linux

### 기능적 제약
- **현재 지원**: MQTT v3.1.1, TCP, Serial 기본 기능만 지원
- **미구현**: TLS/SSL, Will Message, MQTT v5.0 기능들
- **동시 연결**: 단일 브로커당 하나의 연결만 지원
- **명시적 연결**: connect() 메서드 호출 필수 (자동 연결 없음)

### 성능 제약
- **처리량**: 초당 10,000 메시지 처리 가능
- **동시 연결**: 100개 이하 권장
- **메모리**: 연결당 약 10MB 사용

## 참고 자료
- [MQTT Protocol](mqtt_protocol.md)
- [README.md](README.md)
