import pytest
from communicator.common.packet.data import PacketSender, PacketReceiver
from communicator.common.packet.base import PacketStructure


class MockPacketStructure(PacketStructure):
    """
    테스트용 MockPacketStructure.
    sync_no, cmd, payload를 관리하며 직렬화/파싱 기능을 제공합니다.
    """
    def __init__(self, sync_no: int, cmd: int, payload: bytes = b''):
        self.sync_no = sync_no
        self._cmd = cmd
        self._payload = payload

    def build(self) -> bytes:
        """
        sync_no, cmd, payload를 ':' 구분자로 직렬화하여 bytes로 반환합니다.
        """
        return f"{self.sync_no}:{self._cmd}:{self._payload.decode()}".encode()

    @classmethod
    def parse(cls, data: bytes) -> 'MockPacketStructure':
        """
        bytes 데이터를 MockPacketStructure로 파싱합니다.
        """
        try:
            parts = data.decode().split(":")
            sync = int(parts[0])
            cmd = int(parts[1])
            payload = parts[2].encode()
            return cls(sync_no=sync, cmd=cmd, payload=payload)
        except Exception:
            raise ValueError("Invalid format")

    @property
    def frame_type(self) -> int:
        """
        패킷의 cmd 값을 반환합니다.
        """
        return self._cmd

    @property
    def payload(self) -> bytes:
        """
        패킷의 payload 값을 반환합니다.
        """
        return self._payload


class MockSyncNoGenerator:
    """
    테스트용 SyncNoGenerator. next() 호출 시마다 1씩 증가하는 카운터를 제공합니다.
    """
    def __init__(self):
        self.counter = 0

    def next(self) -> int:
        """
        카운터를 1 증가시켜 반환합니다.
        """
        self.counter += 1
        return self.counter


@pytest.fixture
def sync_gen():
    """
    SyncNoGenerator 인스턴스를 반환합니다.
    """
    return MockSyncNoGenerator()


def test_packet_sender_build(sync_gen):
    """
    PacketSender의 send 메서드가 정상적으로 동작하는지 테스트합니다.
    """
    sender = PacketSender(structure_cls=MockPacketStructure, sync_gen=sync_gen)
    built = sender.send(cmd=10, payload=b'hello')
    
    # 예: b'1:10:hello'
    assert isinstance(built, bytes)
    assert built == b'1:10:hello'


def test_packet_receiver_parse_valid():
    """
    PacketReceiver의 parse 메서드가 정상적인 데이터를 파싱할 때 정상적으로 동작하는지 테스트합니다.
    """
    raw_data = b'5:20:world'
    frame_type, payload = PacketReceiver.parse(raw_data, MockPacketStructure)

    assert frame_type == 20
    assert payload == b'world'


def test_packet_receiver_parse_invalid():
    """
    PacketReceiver의 parse 메서드가 비정상적인 데이터를 파싱할 때 정상적으로 동작하는지 테스트합니다.
    """
    raw_data = b'invalid_data'
    frame_type, payload = PacketReceiver.parse(raw_data, MockPacketStructure)

    assert frame_type is None
    assert payload is None
