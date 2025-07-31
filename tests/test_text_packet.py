import pytest
import json
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.text import TextPacketStructure

@pytest.fixture
def text_config():
    """
    텍스트 패킷 테스트를 위한 기본 PacketConfig를 제공하는 픽스처.
    - head: b'STX'
    - tail: b'ETX'
    - delimiter: b'|'
    - fields: {'command': 'str', 'id': 'int', 'data': 'json'}
    """
    return PacketConfig(
        head=b'STX',
        tail=b'ETX',
        delimiter=b'|',
        fields={'command': 'str', 'id': 'int', 'data': 'json'}
    )

@pytest.fixture
def sample_packet_data():
    """
    테스트에 사용될 샘플 패킷 데이터를 제공하는 픽스처.
    """
    return {'command': 'SET', 'id': 123, 'data': {'key': 'value'}}

class TestTextPacketStructure:
    """
    TextPacketStructure 클래스의 직렬화 및 역직렬화 로직을 테스트합니다.
    """

    def test_build_and_parse_cycle(self, text_config, sample_packet_data):
        """
        패킷을 빌드하고 다시 파싱했을 때 원래 데이터로 복원되는지 테스트합니다.
        (build -> parse -> original data)
        """
        packet = TextPacketStructure(**sample_packet_data)
        built_data = packet.build(text_config)

        parsed_packet = TextPacketStructure.parse(built_data, text_config)
        assert parsed_packet._data == sample_packet_data

    def test_build_without_fields_in_config(self, sample_packet_data):
        """
        config에 'fields'가 정의되지 않았을 때 build 메서드가 ValueError를 발생시키는지 테스트합니다.
        """
        packet = TextPacketStructure(**sample_packet_data)
        empty_config = PacketConfig()
        with pytest.raises(ValueError, match="Building packet requires 'fields'"):
            packet.build(empty_config)

    def test_build_with_missing_field_in_data(self, text_config):
        """
        빌드할 데이터에 config에서 요구하는 필드가 누락되었을 때 ValueError를 발생시키는지 테스트합니다.
        """
        incomplete_data = {'command': 'SET', 'id': 123} # 'data' field is missing
        packet = TextPacketStructure(**incomplete_data)
        with pytest.raises(ValueError, match="Missing required field: data"):
            packet.build(text_config)

    def test_parse_field_count_mismatch(self, text_config):
        """
        파싱할 데이터의 필드 수가 config와 일치하지 않을 때 ValueError를 발생시키는지 테스트합니다.
        """
        raw_data = b'STXCMD|123ETX' # Not enough fields
        with pytest.raises(ValueError, match="Packet field count mismatch"):
            TextPacketStructure.parse(raw_data, text_config)

    def test_properties(self, sample_packet_data):
        """
        frame_type과 payload 프로퍼티가 올바른 값을 반환하는지 테스트합니다.
        """
        packet = TextPacketStructure(frame_type='GET', **sample_packet_data)
        assert packet.frame_type == 'GET'
        
        # payload는 _data 전체를 json으로 직렬화하여 반환
        expected_payload = json.dumps(packet._data, ensure_ascii=False).encode('utf-8')
        assert packet.payload == expected_payload

    @pytest.mark.parametrize("value, field_type, expected", [
        ('text', 'str', 'text'),
        (12345, 'int', '12345'),
        ({'a': 1, 'b': 'c'}, 'json', '{"a": 1, "b": "c"}'),
    ])
    def test_serialize_value(self, value, field_type, expected):
        """
        _serialize_value가 타입에 따라 값을 올바르게 문자열로 직렬화하는지 테스트합니다.
        """
        assert TextPacketStructure._serialize_value(value, field_type) == expected

    def test_serialize_unsupported_type(self):
        """
        지원하지 않는 타입을 직렬화하려 할 때 TypeError가 발생하는지 테스트합니다.
        """
        with pytest.raises(TypeError, match="Unsupported field type for serialization"):
            TextPacketStructure._serialize_value(123.45, 'float')

    @pytest.mark.parametrize("value_str, field_type, expected", [
        ('text', 'str', 'text'),
        ('12345', 'int', 12345),
        ('{"a": 1, "b": "c"}', 'json', {'a': 1, 'b': 'c'}),
    ])
    def test_deserialize_value(self, value_str, field_type, expected):
        """
        _deserialize_value가 타입에 따라 문자열을 올바른 값으로 역직렬화하는지 테스트합니다.
        """
        assert TextPacketStructure._deserialize_value(value_str, field_type) == expected

    def test_deserialize_unsupported_type(self):
        """
        지원하지 않는 타입을 역직렬화하려 할 때 TypeError가 발생하는지 테스트합니다.
        """
        with pytest.raises(TypeError, match="Unsupported field type for deserialization"):
            TextPacketStructure._deserialize_value('123.45', 'float')
