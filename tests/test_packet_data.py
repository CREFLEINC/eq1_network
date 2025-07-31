import pytest
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.text import TextPacketStructure
from communicator.common.packet.data import SendData, ReceivedData

@pytest.fixture
def base_config():
    """테스트에 사용할 기본 PacketConfig 픽스처를 생성합니다."""
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
def text_packet_structure():
    """TextPacketStructure 인스턴스 픽스처를 생성합니다."""
    return TextPacketStructure()

class TestPacketDataHelpers:
    """SendData와 ReceivedData 헬퍼 클래스를 테스트합니다."""

    def test_build_success(self, text_packet_structure, base_config):
        """SendData.build: 성공적인 패킷 직렬화 테스트"""
        # given
        sender = SendData(text_packet_structure, base_config)
        test_data = {'cmd': 'CMD1', 'data': {'key': 'value'}, 'seq': 1}

        # when
        packet = sender.build(**test_data)

        # then
        assert packet == b'STXCMD1|{"key": "value"}|1ETX'

    def test_parse_success(self, base_config):
        """ReceivedData.parse: 성공적인 패킷 역직렬화 테스트"""
        # given
        receiver = ReceivedData(TextPacketStructure, base_config)
        raw_data = b'STXCMD2|{"a": 1}|100ETX'

        # when
        packet = receiver.parse(raw_data)

        # then
        assert isinstance(packet, TextPacketStructure)
        assert packet.frame_type is None
        assert packet._data == {'cmd': 'CMD2', 'data': {'a': 1}, 'seq': 100}

    def test_build_missing_field_error(self, text_packet_structure, base_config):
        """SendData.build: 필수 필드 누락 시 예외 발생 테스트"""
        # given
        sender = SendData(text_packet_structure, base_config)
        invalid_data = {'cmd': 'CMD3', 'data': {}}  # 'seq' 필드 누락

        # when / then
        with pytest.raises(ValueError, match="Missing required field: seq"):
            sender.build(**invalid_data)

    def test_parse_field_count_mismatch_error(self, base_config):
        """ReceivedData.parse: 필드 개수 불일치 시 예외 발생 및 None 반환 테스트"""
        # given
        receiver = ReceivedData(TextPacketStructure, base_config)
        malformed_packet = b'STXCMD4|{"d": 4}ETX'  # 필드가 2개만 들어옴 (기대: 3개)

        # when
        packet = receiver.parse(malformed_packet)

        # then
        assert packet is None

    def test_no_head_tail_delimiter_config(self, text_packet_structure):
        """Head, Tail, Delimiter가 없는 설정으로 빌드 및 파싱 테스트"""
        # given
        config = PacketConfig(
            fields={'f1': 'str', 'f2': 'int'},
            encoding='euc-kr'  # 인코딩 변경 테스트
        )
        sender = SendData(text_packet_structure, config)
        receiver = ReceivedData(TextPacketStructure, config)
        test_data = {'f1': '데이터', 'f2': 123}

        # when
        built_packet = sender.build(**test_data)
        parsed_packet = receiver.parse(built_packet)

        # then
        assert built_packet == '데이터'.encode('euc-kr') + b',' + b'123'
        assert parsed_packet._data == test_data

    def test_unsupported_field_type_error(self, text_packet_structure):
        """지원하지 않는 필드 타입 사용 시 TypeError 발생 테스트"""
        # given
        config = PacketConfig(fields={'bad_field': 'float'})
        sender = SendData(text_packet_structure, config)

        # when / then
        with pytest.raises(TypeError, match="Unsupported field type for serialization: float"):
            sender.build(bad_field=1.23)

    def test_send_data_with_text_packet_structure(self, text_packet_structure, base_config):
        """SendData: TextPacketStructure와 함께 사용 테스트"""
        # given
        sender = SendData(text_packet_structure, base_config)
        test_data = {'cmd': 'CMD1', 'data': {'key': 'value'}, 'seq': 1}

        # when
        packet = sender.build(**test_data)

        # then
        assert packet == b'STXCMD1|{"key": "value"}|1ETX'

    def test_received_data_with_text_packet_structure(self, text_packet_structure, base_config):
        """ReceivedData: TextPacketStructure와 함께 사용 테스트"""
        # given
        receiver = ReceivedData(TextPacketStructure, base_config)
        raw_data = b'STXCMD2|{"a": 1}|100ETX'

        # when
        packet = receiver.parse(raw_data)

        # then
        assert isinstance(packet, TextPacketStructure)
        assert packet.frame_type is None
        assert packet._data == {'cmd': 'CMD2', 'data': {'a': 1}, 'seq': 100}

    def test_send_data_with_packet_config(self, text_packet_structure, base_config):
        """SendData: PacketConfig와 함께 사용 테스트"""
        # given
        sender = SendData(text_packet_structure, base_config)
        test_data = {'cmd': 'CMD1', 'data': {'key': 'value'}, 'seq': 1}

        # when
        packet = sender.build(**test_data)

        # then
        assert packet == b'STXCMD1|{"key": "value"}|1ETX'

    def test_received_data_with_packet_config(self, text_packet_structure, base_config):
        """ReceivedData: PacketConfig와 함께 사용 테스트"""
        # given
        receiver = ReceivedData(TextPacketStructure, base_config)
        raw_data = b'STXCMD2|{"a": 1}|100ETX'

        # when
        packet = receiver.parse(raw_data)

        # then
        assert isinstance(packet, TextPacketStructure)
        assert packet.frame_type is None
        assert packet._data == {'cmd': 'CMD2', 'data': {'a': 1}, 'seq': 100}
