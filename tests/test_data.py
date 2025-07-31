import pytest
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.text import TextPacketStructure
from communicator.common.packet.data import SendData, ReceivedData
from communicator.common.packet.base import PacketStructure


# ------------------------------------------------------
# 1. MockPacketStructure – 단위 테스트용
# ------------------------------------------------------
class MockPacketStructure(PacketStructure):
    """
    단순화된 PacketStructure (cmd:payload 형식)
    """
    def __init__(self, config: PacketConfig, **fields):
        self.config = config
        self._data = fields

    def build(self, config: PacketConfig = None, **kwargs) -> bytes:
        """
        cmd:payload 형태 직렬화
        """
        config = config or self.config
        data_to_build = kwargs if kwargs else self._data

        cmd = data_to_build.get('cmd', 0)
        payload = data_to_build.get('payload', b'')
        if isinstance(payload, bytes):
            payload_str = payload.decode()
        else:
            payload_str = str(payload)

        return f"{cmd}:{payload_str}".encode()

    @classmethod
    def parse(cls, data: bytes, config: PacketConfig) -> 'MockPacketStructure':
        """
        bytes 데이터를 cmd:payload 로 파싱
        """
        try:
            parts = data.decode().split(":")
            cmd = int(parts[0])
            payload = parts[1].encode() if len(parts) > 1 else b''
            return cls(config, cmd=cmd, payload=payload)
        except Exception:
            raise ValueError("Invalid format")

    @property
    def frame_type(self) -> int:
        return self._data.get('cmd', 0)

    @property
    def payload(self) -> bytes:
        payload = self._data.get('payload', b'')
        return payload if isinstance(payload, bytes) else str(payload).encode()


# ------------------------------------------------------
# 2. 공통 Fixture
# ------------------------------------------------------
@pytest.fixture
def base_config():
    """TextPacketStructure 테스트용 기본 PacketConfig"""
    return PacketConfig(
        head=b'STX',
        tail=b'ETX',
        delimiter=b'|',
        fields={
            'cmd': 'str',
            'data': 'json',
            'seq': 'int'
        }
    )


@pytest.fixture
def text_packet_structure(base_config):
    """TextPacketStructure 인스턴스"""
    return TextPacketStructure(base_config)


@pytest.fixture
def mock_config():
    """MockPacketStructure 테스트용 PacketConfig"""
    return PacketConfig(encoding="utf-8")


@pytest.fixture
def mock_packet_instance(mock_config):
    """cmd=10, payload=b'hello' 로 구성된 MockPacketStructure 인스턴스"""
    return MockPacketStructure(mock_config, cmd=10, payload=b'hello')


# ------------------------------------------------------
# 3. TextPacketStructure 기반 통합 테스트
# ------------------------------------------------------
class TestTextPacketStructureIntegration:
    def test_build_success(self, text_packet_structure, base_config):
        sender = SendData(text_packet_structure, base_config)
        packet = sender.build(cmd='CMD1', data={'key': 'value'}, seq=1)
        assert packet == b'STXCMD1|{"key": "value"}|1ETX'

    def test_parse_success(self, base_config):
        receiver = ReceivedData(TextPacketStructure, base_config)
        raw_data = b'STXCMD2|{"a": 1}|100ETX'
        packet = receiver.parse(raw_data)
        assert isinstance(packet, TextPacketStructure)
        assert packet._data == {'cmd': 'CMD2', 'data': {'a': 1}, 'seq': 100}

    def test_build_missing_field_error(self, text_packet_structure, base_config):
        sender = SendData(text_packet_structure, base_config)
        with pytest.raises(ValueError, match="Missing required field: seq"):
            sender.build(cmd='CMD3', data={})  # seq 누락

    def test_parse_field_count_mismatch_error(self, base_config):
        receiver = ReceivedData(TextPacketStructure, base_config)
        malformed = b'STXCMD4|{"d": 4}ETX'
        packet = receiver.parse(malformed)
        assert packet is None

    def test_no_head_tail_delimiter_config(self):
        config = PacketConfig(
            fields={'f1': 'str', 'f2': 'int'},
            encoding='euc-kr'
        )
        packet_structure = TextPacketStructure(config)
        sender = SendData(packet_structure, config)
        receiver = ReceivedData(TextPacketStructure, config)
        test_data = {'f1': '데이터', 'f2': 123}
        built = sender.build(**test_data)
        parsed = receiver.parse(built)
        assert built == '데이터'.encode('euc-kr') + b',' + b'123'
        assert parsed._data == test_data

    def test_unsupported_field_type_error(self):
        # config 생성 시점에서 검증 오류가 발생해야 함
        with pytest.raises(ValueError, match="Invalid field type 'float' for field 'bad_field'"):
            config = PacketConfig(fields={'bad_field': 'float'})
            TextPacketStructure(config)


# ------------------------------------------------------
# 4. MockPacketStructure 기반 단위 테스트
# ------------------------------------------------------
class TestMockPacketStructureUnit:
    def test_send_data_build(self, mock_packet_instance, mock_config):
        sender = SendData(mock_packet_instance, mock_config)
        built = sender.build(cmd=10, payload=b'hello')
        assert isinstance(built, bytes)
        assert built == b'10:hello'

    def test_received_data_parse_valid(self, mock_config):
        raw_data = b'20:world'
        receiver = ReceivedData(MockPacketStructure, mock_config)
        parsed_packet = receiver.parse(raw_data)
        assert parsed_packet.frame_type == 20
        assert parsed_packet.payload == b'world'

    def test_received_data_parse_invalid(self, mock_config):
        raw_data = b'invalid_data'
        receiver = ReceivedData(MockPacketStructure, mock_config)
        parsed_packet = receiver.parse(raw_data)
        assert parsed_packet is None

    def test_received_data_parse_without_config(self):
        receiver = ReceivedData(MockPacketStructure, None)
        with pytest.raises(ValueError, match="PacketConfig가 지정되지 않았습니다"):
            receiver.parse(b'test')
