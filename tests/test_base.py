import pytest
from communicator.common.packet.base import PacketStructure

class MockPacketStructure(PacketStructure):
    """
    테스트용 MockPacketStructure.
    frame_type과 payload를 단순하게 관리하는 테스트용 패킷 구조체입니다.
    """
    def __init__(self, _frame_type: int, _payload: bytes):
        self._frame_type = _frame_type
        self._payload = _payload

    def build(self) -> bytes:
        """
        frame_type과 payload를 직렬화하여 bytes로 반환합니다.
        """
        return self._frame_type.to_bytes(1, 'big') + self._payload

    @classmethod
    def parse(cls, data: bytes) -> 'MockPacketStructure':
        """
        bytes 데이터를 MockPacketStructure로 파싱합니다.
        """
        frame_type = data[0]
        payload = data[1:]
        return cls(frame_type, payload)

    @property
    def frame_type(self) -> int:
        """
        패킷의 frame_type 값을 반환합니다.
        """
        return self._frame_type

    @property
    def payload(self) -> bytes:
        """
        패킷의 payload 값을 반환합니다.
        """
        return self._payload

@pytest.fixture
def mock_packet() -> PacketStructure:
    """
    frame_type=0x01, payload=b"hello"로 구성된 MockPacketStructure 인스턴스를 반환합니다.
    """
    return MockPacketStructure(0x01, b"hello")

def test_build(mock_packet):
    """
    build() 메서드가 올바른 bytes를 반환하는지 테스트합니다.
    """
    result = mock_packet.build()
    assert isinstance(result, bytes)
    assert result == b'\x01hello'

def test_parse():
    """
    parse() 메서드가 bytes로부터 올바른 MockPacketStructure 인스턴스를 생성하는지 테스트합니다.
    """
    raw_data = b'\x02world'
    packet = MockPacketStructure.parse(raw_data)
    assert isinstance(packet, PacketStructure)
    assert packet.frame_type == 0x02
    assert packet.payload == b'world'

def test_frame_type_property(mock_packet):
    """
    frame_type 프로퍼티가 올바른 값을 반환하는지 테스트합니다.
    """
    assert mock_packet.frame_type == 0x01

def test_payload_property(mock_packet):
    """
    payload 프로퍼티가 올바른 값을 반환하는지 테스트합니다.
    """
    assert mock_packet.payload == b'hello'
