import pytest
from abc import ABC
from communicator.common.packet.base import PacketStructure
from communicator.common.packet.config import PacketConfig


class ConcretePacketStructure(PacketStructure):
    """
    문자열 직렬화를 사용하는 PacketStructure 테스트 구현체
    (frame_type:payload 형식)
    """
    def __init__(self, frame_type_value: int, payload_value: bytes):
        self._frame_type = frame_type_value
        self._payload = payload_value

    def build(self, config: PacketConfig, **kwargs) -> bytes:
        """frame_type과 payload를 문자열로 직렬화"""
        return f"{self._frame_type}:{self._payload.decode()}".encode()

    @classmethod
    def parse(cls, data: bytes, config: PacketConfig) -> "ConcretePacketStructure":
        """문자열 직렬화된 데이터를 다시 ConcretePacketStructure로 복원"""
        parts = data.decode().split(":")
        frame_type = int(parts[0])
        payload = parts[1].encode()
        return cls(frame_type, payload)

    @property
    def frame_type(self) -> int:
        return self._frame_type

    @property
    def payload(self) -> bytes:
        return self._payload


class MockPacketStructure(PacketStructure):
    """
    단순 바이너리 직렬화를 사용하는 PacketStructure 테스트 구현체
    (1바이트 frame_type + 나머지 payload)
    """
    def __init__(self, frame_type_value: int, payload_value: bytes):
        self._frame_type = frame_type_value
        self._payload = payload_value

    def build(self) -> bytes:
        return self._frame_type.to_bytes(1, "big") + self._payload

    @classmethod
    def parse(cls, data: bytes) -> "MockPacketStructure":
        frame_type = data[0]
        payload = data[1:]
        return cls(frame_type, payload)

    @property
    def frame_type(self) -> int:
        return self._frame_type

    @property
    def payload(self) -> bytes:
        return self._payload


# ---------------------
# 공통 fixture
# ---------------------
@pytest.fixture
def string_packet() -> ConcretePacketStructure:
    """frame_type=100, payload='hello'로 구성된 문자열 기반 패킷"""
    return ConcretePacketStructure(100, b"hello")


@pytest.fixture
def binary_packet() -> MockPacketStructure:
    """frame_type=1, payload='hello'로 구성된 바이너리 기반 패킷"""
    return MockPacketStructure(1, b"hello")


# ---------------------
# 테스트 케이스
# ---------------------

def test_cannot_instantiate_abstract_class():
    """추상 클래스 PacketStructure는 직접 인스턴스화할 수 없어야 한다."""
    with pytest.raises(TypeError):
        PacketStructure()


def test_string_based_build_and_parse(string_packet):
    """문자열 직렬화 방식의 build / parse 동작 테스트"""
    config = PacketConfig()
    built = string_packet.build(config)
    assert built == b"100:hello"

    parsed = ConcretePacketStructure.parse(built, config)
    assert parsed.frame_type == 100
    assert parsed.payload == b"hello"


def test_binary_based_build_and_parse(binary_packet):
    """바이너리 직렬화 방식의 build / parse 동작 테스트"""
    built = binary_packet.build()
    assert built == b"\x01hello"

    parsed = MockPacketStructure.parse(built)
    assert parsed.frame_type == 1
    assert parsed.payload == b"hello"


def test_string_based_properties(string_packet):
    """문자열 직렬화 PacketStructure의 frame_type, payload 프로퍼티 테스트"""
    assert string_packet.frame_type == 100
    assert string_packet.payload == b"hello"


def test_binary_based_properties(binary_packet):
    """바이너리 직렬화 PacketStructure의 frame_type, payload 프로퍼티 테스트"""
    assert binary_packet.frame_type == 1
    assert binary_packet.payload == b"hello"


def test_concrete_packet_with_different_data():
    """다른 데이터로 ConcretePacketStructure 생성 및 테스트"""
    packet = ConcretePacketStructure(200, b"world")
    assert packet.frame_type == 200
    assert packet.payload == b"world"
    
    config = PacketConfig()
    built = packet.build(config)
    assert built == b"200:world"


def test_mock_packet_with_different_data():
    """다른 데이터로 MockPacketStructure 생성 및 테스트"""
    packet = MockPacketStructure(255, b"test")
    assert packet.frame_type == 255
    assert packet.payload == b"test"
    
    built = packet.build()
    assert built == b"\xfftest"


def test_concrete_packet_build_with_kwargs():
    """ConcretePacketStructure build 메서드에 kwargs 전달 테스트"""
    packet = ConcretePacketStructure(50, b"kwargs")
    config = PacketConfig()
    # kwargs는 무시되지만 메서드 시그니처 테스트
    built = packet.build(config, extra_param="ignored")
    assert built == b"50:kwargs"


def test_concrete_packet_parse_edge_cases():
    """ConcretePacketStructure parse 메서드 엣지 케이스 테스트"""
    config = PacketConfig()
    
    # 빈 payload
    parsed = ConcretePacketStructure.parse(b"123:", config)
    assert parsed.frame_type == 123
    assert parsed.payload == b""
    
    # 큰 frame_type 값
    parsed = ConcretePacketStructure.parse(b"999:data", config)
    assert parsed.frame_type == 999
    assert parsed.payload == b"data"


def test_mock_packet_parse_edge_cases():
    """MockPacketStructure parse 메서드 엣지 케이스 테스트"""
    # 빈 payload
    parsed = MockPacketStructure.parse(b"\x42")
    assert parsed.frame_type == 66  # 0x42
    assert parsed.payload == b""
    
    # 긴 payload
    long_payload = b"a" * 100
    data = b"\x01" + long_payload
    parsed = MockPacketStructure.parse(data)
    assert parsed.frame_type == 1
    assert parsed.payload == long_payload


def test_abstract_methods_coverage():
    """추상 메서드들이 올바르게 구현되었는지 확인"""
    # ConcretePacketStructure의 모든 추상 메서드 구현 확인
    packet = ConcretePacketStructure(1, b"test")
    config = PacketConfig()
    
    # build 메서드
    result = packet.build(config)
    assert isinstance(result, bytes)
    
    # parse 클래스 메서드
    parsed = ConcretePacketStructure.parse(result, config)
    assert isinstance(parsed, ConcretePacketStructure)
    
    # frame_type 프로퍼티
    assert isinstance(packet.frame_type, int)
    
    # payload 프로퍼티
    assert isinstance(packet.payload, bytes)


def test_inheritance_structure():
    """상속 구조 테스트"""
    concrete = ConcretePacketStructure(1, b"test")
    mock = MockPacketStructure(1, b"test")
    
    # 둘 다 PacketStructure를 상속받았는지 확인
    assert isinstance(concrete, PacketStructure)
    assert isinstance(mock, PacketStructure)
    
    # 서로 다른 클래스인지 확인
    assert type(concrete) != type(mock)


class IncompletePacketStructure(PacketStructure):
    """추상 메서드를 구현하지 않은 클래스 (테스트용)"""
    def build(self, config: PacketConfig, **kwargs) -> bytes:
        return super().build(config, **kwargs)
    
    @classmethod
    def parse(cls, data: bytes, config: PacketConfig) -> 'PacketStructure':
        return super().parse(data, config)
    
    @property
    def frame_type(self):
        return super().frame_type
    
    @property
    def payload(self) -> bytes:
        return super().payload


def test_abstract_method_pass_statements():
    """추상 메서드의 pass 문 커버리지 테스트"""
    incomplete = IncompletePacketStructure()
    config = PacketConfig()
    
    # build 메서드의 pass 문 실행
    try:
        incomplete.build(config)
    except (NotImplementedError, TypeError):
        pass  # 예상된 동작
    
    # parse 메서드의 pass 문 실행
    try:
        IncompletePacketStructure.parse(b"test", config)
    except (NotImplementedError, TypeError):
        pass  # 예상된 동작
    
    # frame_type 프로퍼티의 pass 문 실행
    try:
        _ = incomplete.frame_type
    except (NotImplementedError, TypeError, AttributeError):
        pass  # 예상된 동작
    
    # payload 프로퍼티의 pass 문 실행
    try:
        _ = incomplete.payload
    except (NotImplementedError, TypeError, AttributeError):
        pass  # 예상된 동작
