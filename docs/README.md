# EQ-1 Network
EQ-1 Network는 다양한 통신 프로토콜을 플러그인 기반으로 확장 가능하게 구성한 파이썬 통신 프레임워크입니다.
현재 MQTT 프로토콜를 우선 지원하며, 향후 TCP 및 Serial 프로토콜로 확장될 예정입니다.

## 1. 빠른 시작
### 요청/응답(Req/Res) 예시
```python
from communicator.manager import ProtocolManager
from communicator.protocols.mqtt import MQTTProtocol

# MQTT 프로토콜 인스턴스 생성 (기본값: localhost:1883)
mqtt = MQTTProtocol()

# 매니저에 등록
manager = ProtocolManager()
manager.add_protocol("mqtt", mqtt)

# 연결
manager.connect("mqtt")

# 데이터 송신
manager.send("mqtt", b"hello")

# 데이터 수신
success, data = manager.read("mqtt")
print(success, data)

# 연결 해제
manager.disconnect("mqtt")
```

### 발행/구독(Pub/Sub) 예시
```python
from communicator.manager import ProtocolManager
from communicator.protocols.mqtt import MQTTProtocol

# MQTT 프로토콜 인스턴스 생성 (기본값: localhost:1883)
mqtt = MQTTProtocol()

# 매니저에 등록
manager = ProtocolManager()
manager.add_protocol("mqtt", mqtt)

# 연결
manager.connect("mqtt")

# 데이터 발행
manager.publish("mqtt", b"hello")

# 데이터 구독
manager.subscribe("mqtt", "topic/test", callback=print)

# 연결 해제
manager.disconnect("mqtt")
```

## 2. 주요 특징
- **플러그인 기반 확장:**
    - `MQTT, TCP(확장 예정), Serial(확장 예정)` 등 새로운 프로토콜을 손쉽게 추가할 수 있습니다.
- **추상화된 인터페이스:**
    - `ReqRes(요청/응답), PubSub(발행/구독)` 등 통신 방식에 따라 추상화된 인터페이스를 제공하여 일관된 코드를 작성할 수 있습니다.
- **중앙 관리:**
    - `ProtocolManager`를 통해 여러 통신 프로토콜을 동시에 관리하고 사용할 수 있습니다.
- **예외/로깅 통합:**
    - 모든 프로토콜 동작에서 공통 예외 클래스와 로깅 체계를 제공합니다.

## 3. 디렉토리 구조
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

## 4. 환경 설정
### 요구 사항
- Python 3.10.18 (권장)
- OS: macOS Sonoma
- 설치 전 가상환경(venv) 사용을 권장합니다.

### 의존성 설치
```bash
pip install -r requirements.txt
```

## 5. 구성 요소
### 인터페이스(`communicator/interfaces/protocol.py`)
- BaseProtocol (ABC)
    - 모든 통신 프로토콜의 공통 동작(connect/disconnect) 정의
    - 추상 메소드: 
        - `connect() -> bool`
        - `disconnect()`
- ReqResProtocol (BaseProtocol 상속)
    - 요청/응답(Req/Res) 기반 통신 프로토콜 인터페이스
    - 추상 메소드: 
        - `send(data: bytes) -> bool`
        - `read() -> Tuple[bool, Optional[bytes]]`
- PubSubProtocol (BaseProtocol 상속)
    - 발행/구독(Pub/Sub) 기반 통신 프로토콜 인터페이스
    - 추상 메소드: 
        - `publish(topic: str, message: bytes, qos: int = 0) -> bool`
        - `subscribe(topic: str, callback: Callable[[str, bytes], None])`

### 예외 클래스(`communicator.common.exception`)
- `ProtocolConnectionError`
- `ProtocolValidationError`
- `ProtocolDecodeError`
- `ProtocolAuthenticationError`
- `ProtocolError`

## 6. 확장 방법
- 새로운 통신 프로토콜을 추가하려면 `BaseProtocol` 또는 하위 추상 클래스를 상속받아 구현합니다.
- 예시:
```python
from communicator.interfaces.protocol import ReqResProtocol

class CustomProtocol(ReqResProtocol):
    def connect(self): ...
    def disconnect(self): ...
    def send(self, data: bytes): ...
    def read(self): ...
```

## 7. 테스트
- Mock 기반 단위 테스트
    - 정상 연결/해제, 데이터 송수신 동작
    - 연결되지 않은 상태에서의 예외 처리
    - 잘못된 타입 입력 시 TypeError 발생 확인
    - Pub/Sub 콜백 함수 예외 처리

## 7. 테스트 실행
```bash
pytest tests/
```

## 다음 단계
- TCP, Serial 프로토콜 추가 지원
- 보안 기능 강화
- CI 환경에 통합된 테스트 커버리지 확대

## 참고 문서
- [PRD.md](PRD.md)
- [MQTT Protocol](mqtt_protocol.md)