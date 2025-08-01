# 제품 요구사항 문서: EQ-1 Network

EQ-1 Network는 다양한 산업 및 IoT 환경에서 사용할 수 있는 플러그인 기반 통신 프레임워크입니다.

## 문서 목적

이 문서는 EQ-1 Network의 목적, 요구사항, 설계 방향, 제약사항을 명확히 정의하여 팀 내 공통된 이해를 돕습니다.

## 개요
- MQTT를 시작으로 다양한 통신 프로토콜을 표준화된 인터페이스로 지원합니다.
- 신규 프로토콜을 플러그인 방식으로 쉽게 확장할 수 있습니다.
- 공통 ReqRes / PubSub 인터페이스와 일관된 직렬화 규칙을 제공합니다.

### 아키텍처 다이아그램
```mermaid
flowchart TD
    subgraph Application["응용 시스템"]
        UI["UI / Vision System"] --> NET["EQ-1 Network 모듈"]
    end

    NET --> MANAGER["Protocol Manager"]
    MANAGER --> INTERFACES["ReqRes / PubSub Interfaces"]
    INTERFACES --> PACKET["PacketStructure"]
    INTERFACES --> PROTOCOLS["Protocol Plugins"]

    PROTOCOLS --> MQTT["MQTTProtocol"]
    PROTOCOLS --> MODBUS[(Future) ModbusProtocol]
    PROTOCOLS --> TCPUDP[(Future) TCP/UDPProtocol]
```

## 목표
- 신규 프로토콜을 플러그인 형태로 쉽게 확장
- 공통 인터페이스(ReqRes, PubSub) 제공
- 일관된 패킷 직렬화/역직렬화 규칙 확립

## 배경
- 기존 시스템별 통신 구현 중복
- MQTT, TCP/UDP, Modbus 등 여러 프로토콜을 하나의 코드베이스로 관리할 필요성 존재
- 신규 참여자 온보딩 시간 단축 필요성 존재

## 성공 지표

### 현재 상태
- **개발 속도**: ✅ 달성 - RFC 준수 MQTT 구현 완료
- **품질 지표**: ✅ 달성 - 테스트 커버리지 90%+ 달성
- **RFC 준수**: ✅ 달성 - MQTT v3.1.1/v5.0 표준 95% 준수

### 지속적 목표
- **안정성**: 3개월간 치명적 통신 버그 0건 유지
- **성능**: 초당 10,000 메시지 처리 성능 유지
- **확장성**: 6개월 내 TCP/Serial 프로토콜 추가

## 범위

### 포함 사항
- 통신 프로토콜 공통 인터페이스
- 패킷 구조화 및 직렬화
- MQTT 프로토콜 구현
- 단위 테스트 및 샘플 예제

### 제외 사항
- UI (GUI, Web)
- 데이터 저장소, 서비스 로직
- 배포/운영 자동화

## 기능 요구사항
| ID   | 요구사항 | 상세 |
| :--- | :--- | :--- |
| **F-01** | **플러그인 기반 통신 모듈** | - `IProtocol` 인터페이스를 상속한 클래스를 `protocols` 디렉토리에 추가하는 것만으로 신규 프로토콜이 확장되어야 함.<br/>- `ProtocolManager`는 지정된 경로에서 사용 가능한 프로토콜을 동적으로 탐색하고 로드해야 함. |
| **F-02** | **ReqRes 인터페이스** | - `ReqResProtocol` 추상 클래스는 다음 메서드를 반드시 포함해야 함:<br/>  - `connect()` / `disconnect()`: 대상과의 연결 수립 및 종료<br/>  - `send(data: bytes)`: 데이터 동기 전송<br/>  - `receive() -> bytes`: 응답 데이터 수신 (Blocking)<br/>  - `is_connected() -> bool`: 연결 상태 반환 |
| **F-03** | **PubSub 인터페이스** | - `PubSubProtocol` 추상 클래스는 다음 메서드를 반드시 포함해야 함:<br/>  - `connect()` / `disconnect()`: 브로커와의 연결 수립 및 종료<br/>  - `publish(topic: str, payload: bytes)`: 메시지 발행<br/>  - `subscribe(topic: str, callback: Callable)`: 토픽 구독 및 콜백 등록<br/>  - `unsubscribe(topic: str)`: 토픽 구독 취소 |
| **F-04** | **PacketStructure** | - 모든 통신 데이터는 `PacketStructure` 추상 클래스를 상속하여 구현.<br/>- `build() -> bytes`: 패킷 객체를 전송 가능한 `bytes`로 직렬화.<br/>- `parse(bytes) -> PacketStructure`: 수신된 `bytes`를 패킷 객체로 역직렬화.<br/>- `frame_type`: 패킷의 종류나 명령을 식별하는 속성을 제공.<br/>- `payload`: 실제 데이터가 담기는 `bytes` 형식의 속성을 제공. |
| **F-05** | **RFC 준수 MQTTProtocol 구현** | - `PubSubProtocol` 인터페이스를 `paho-mqtt` 라이브러리로 구현.<br/>- **RFC 준수 기능**: Username/Password 인증, TLS/SSL 보안, Will Message, Retained Messages<br/>- 연결 끊김 시 자동 재연결 및 구독 복구<br/>- QoS (0, 1, 2) 레벨 완전 지원<br/>- 상세한 RFC 준수 에러 처리 (rc 1-5) |
| **F-06** | **Thread-safe 보장** | - publish, subscribe, unsubscribe, 큐 처리 등 모든 API가 thread-safe해야 함 |
| **F-07** | **테스트 코드 제공** | - `pytest`와 `unittest.mock`을 사용하여 각 컴포넌트의 독립적인 동작을 검증.<br/>- `MQTTProtocol` 테스트를 위해 Mock MQTT 브로커를 사용.<br/>- CI 환경에서 실행 가능해야 하며, 코드 커버리지 90% 이상을 목표로 함. |

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
communicator/
├── common/         # 예외, 로깅
├── interfaces/     # Protocol 인터페이스
├── protocols/      # MQTTProtocol 등
├── manager/        # 프로토콜 로딩 및 관리
├── tests/          # 단위 테스트
└── requirements.txt
```

### 주요 컴포넌트
- **인터페이스 레이어**
    - `ReqResProtocol` / `PubSubProtocol`: 통신 유형별 표준 인터페이스
    - `BaseProtocol`: 모든 프로토콜의 공통 기반 인터페이스
- **RFC 준수 MQTT 구현**
    - `MQTTProtocol`: paho-mqtt 기반 RFC 준수 구현
    - `MQTTConfig`: 설정 관리를 위한 데이터 클래스
- **보안 및 신뢰성**
    - Username/Password 인증
    - TLS/SSL 암호화 연결
    - Will Message (Last Will and Testament)
    - Retained Messages
    - 자동 재연결 및 구독 복구
    - Thread-safe 설계
- **에러 처리**
    - RFC 준수 상세 연결 실패 코드 처리
    - 예외 클래스 계층 구조

## 사용자 시나리오

### RFC 준수 MQTT 예시
```python
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

# 보안 설정 포함
config = MQTTConfig(
    broker_address="secure-broker.example.com",
    port=8883,
    username="mqtt_user",
    password="secure_password",
    ca_certs="/path/to/ca.crt"
)

mqtt = MQTTProtocol(config)

# Will Message 설정
mqtt.set_will("device/status", "offline", qos=1, retain=True)

mqtt.connect()
mqtt.subscribe("topic/test", callback=print)
mqtt.publish("topic/test", "hello", qos=1, retain=True)
mqtt.disconnect()
```

### 향후 Req/Res 예시 (계획)
```python
# TCP 프로토콜 추가 예정
tcp = TCPProtocol("192.168.0.10", 502)
tcp.connect()
tcp.send(b"PING")
resp = tcp.receive()
```

## 테스트 전략
- 단위 테스트 (Unit Test)
    - pytest 기반으로 각 프로토콜과 PacketStructure 단위 테스트 진행
    - Mock 객체를 이용한 독립적인 동작 검증
- 통합 테스트 (Integration Test)
    - 실제 MQTT 브로커 환경에서 publish/subscribe 기능 검증
    - 향후 Modbus, TCP/UDP 등 다른 프로토콜 추가 시 동일한 시나리오 확장
- 자동화
    - CI 파이프라인에서 자동 실행되도록 설정
    - 코드 커버리지 측정을 통해 목표 커버리지 90% 이상 유지

## 위험 완화
| 위험 (Risk) | 발생 가능성 | 영향도 | 대응 |
| :--- | :---: | :---: | :--- |
| **외부 라이브러리 의존성** | 중간 | 높음 | - 라이브러리 핵심 기능을 직접 호출하지 않고, 어댑터(Adapter) 클래스로 한 번 더 감싸서 구현합니다.<br/>- 이를 통해 문제 발생 시 다른 라이브러리(예: gmqtt)로 최소한의 코드 수정으로 교체할 수 있습니다. |
| **플러그인 아키텍처의 한계** | 중간 | 높음 | - 초기 인터페이스 설계 시 TCP/IP 기반의 요청/응답 시나리오를 미리 고려하여 `ReqResProtocol` 인터페이스를 정의합니다.<br/>- Modbus 프로토콜 추가 단계에서 PoC(Proof of Concept)를 먼저 진행하여 아키텍처의 확장성을 검증합니다. |
| **낮은 내부 채택률** | 높음 | 중간 | - 상세한 `README.md`와 예제 코드를 제공하여 사용 장벽을 낮춥니다.<br/>- 주요 사용 예상 팀을 대상으로 초기 버전 데모 및 피드백 세션을 진행하여 요구사항을 반영하고 참여를 유도합니다. |

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
- **Python 버전**: 3.10+ (현재 3.10.18 권장)
- **외부 의존성**: paho-mqtt 1.6.0+
- **운영체제**: macOS, Linux (테스트 완료), Windows (부분 지원)

### 기능적 제약
- **현재 지원**: RFC 준수 MQTT 프로토콜만 공식 지원
- **MQTT v5.0**: 부분 지원 (session_expiry_interval만)
- **동시 연결**: 단일 브로커당 하나의 연결만 지원

### 성능 제약
- **처리량**: 초당 10,000 메시지 처리 가능
- **동시 연결**: 100개 이하 권장
- **메모리**: 연결당 약 10MB 사용

## 로드맵

### 단기 (3개월)
- **MQTT v5.0 완전 지원**
    - User Properties, Topic Aliases, Reason Codes 추가
    - 현재 95% 준수에서 100% 준수로 향상
- **성능 최적화**
    - 비동기 처리 강화
    - 연결 풀링 지원

### 중기 (6개월)
- **새로운 프로토콜 추가**
    - TCP/UDP 프로토콜 (ReqRes 인터페이스)
    - Serial 통신 프로토콜
    - Modbus 프로토콜
- **플러그인 매니저**
    - 동적 프로토콜 로딩
    - Hot-reload 기능

### 장기 (12개월)
- **엔터프라이즈 기능**
    - 모니터링 및 메트릭 수집
    - 로드 밸런싱 및 클러스터링
    - 설정 관리 시스템

## 참고 자료
- [MQTT Protocol](mqtt_protocol.md)
- [README.md](README.md)
