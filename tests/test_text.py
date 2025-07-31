import pytest
import json
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.text import TextPacketStructure


# ---------------------------
# 공통 픽스처
# ---------------------------
@pytest.fixture
def text_config():
    """
    텍스트 패킷 테스트를 위한 기본 PacketConfig를 제공하는 픽스처.
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


# ---------------------------
# 통합 테스트 클래스
# ---------------------------
class TestTextPacketStructure:
    """TextPacketStructure 클래스 전체 동작 테스트"""

    # --- 기본 빌드/파싱 사이클 ---
    def test_build_and_parse_cycle(self, text_config, sample_packet_data):
        """
        build -> parse 사이클에서 원래 데이터가 복원되는지 테스트
        """
        packet = TextPacketStructure(text_config, **sample_packet_data)
        built_data = packet.build(text_config)

        parsed_packet = TextPacketStructure.parse(built_data, text_config)
        assert parsed_packet._data == sample_packet_data

    # --- config 누락/필드 누락/형식 오류 ---
    def test_build_without_fields_in_config(self, sample_packet_data):
        empty_config = PacketConfig()
        packet = TextPacketStructure(empty_config, **sample_packet_data)
        with pytest.raises(ValueError, match="Building packet requires 'fields'"):
            packet.build(empty_config)

    def test_build_with_missing_field_in_data(self, text_config):
        incomplete_data = {'command': 'SET', 'id': 123}
        packet = TextPacketStructure(text_config, **incomplete_data)
        with pytest.raises(ValueError, match="Missing required field: data"):
            packet.build(text_config)

    def test_parse_field_count_mismatch(self, text_config):
        raw_data = b'STXCMD|123ETX'  # 2개 필드만 있음
        with pytest.raises(ValueError, match="Packet field count mismatch"):
            TextPacketStructure.parse(raw_data, text_config)

    # --- 프로퍼티 ---
    def test_properties(self, text_config, sample_packet_data):
        packet = TextPacketStructure(text_config, frame_type='GET', **sample_packet_data)
        assert packet.frame_type == 'GET'
        expected_payload = json.dumps(packet._data, ensure_ascii=False).encode('utf-8')
        assert packet.payload == expected_payload

    # --- _serialize_value / _deserialize_value 테스트 ---
    @pytest.mark.parametrize("value, field_type, expected", [
        ('text', 'str', 'text'),
        (12345, 'int', '12345'),
        ({'a': 1, 'b': 'c'}, 'json', '{"a": 1, "b": "c"}'),
    ])
    def test_serialize_value(self, value, field_type, expected):
        assert TextPacketStructure._serialize_value(value, field_type) == expected

    def test_serialize_unsupported_type(self):
        with pytest.raises(ValueError, match="Invalid field type: float. Allowed types:"):
            TextPacketStructure._serialize_value(123.45, 'float')

    @pytest.mark.parametrize("value_str, field_type, expected", [
        ('text', 'str', 'text'),
        ('12345', 'int', 12345),
        ('{"a": 1, "b": "c"}', 'json', {'a': 1, 'b': 'c'}),
    ])
    def test_deserialize_value(self, value_str, field_type, expected):
        assert TextPacketStructure._deserialize_value(value_str, field_type) == expected

    def test_deserialize_unsupported_type(self):
        with pytest.raises(ValueError, match="Invalid field type: float. Allowed types:"):
            TextPacketStructure._deserialize_value('123.45', 'float')

    # ---------------------------
    # Extended Tests
    # ---------------------------
    def test_init_without_config_raises_error(self):
        with pytest.raises(ValueError, match="config: PacketConfig는 필수입니다"):
            TextPacketStructure(None)

    def test_build_with_kwargs_override(self):
        config = PacketConfig(fields={'cmd': 'str', 'value': 'int'})
        packet = TextPacketStructure(config, cmd='OLD', value=1)
        # kwargs로 오버라이드
        result = packet.build(config, cmd='NEW', value=2)
        assert result == b'NEW,2'

    def test_build_with_different_config(self):
        original_config = PacketConfig(fields={'a': 'str'})
        new_config = PacketConfig(head=b'[', tail=b']', fields={'a': 'str'})
        packet = TextPacketStructure(original_config, a='test')
        result = packet.build(new_config)
        assert result == b'[test]'

    def test_parse_with_head_only(self):
        config = PacketConfig(head=b'START', fields={'data': 'str'})
        raw_data = b'STARTvalue'
        packet = TextPacketStructure.parse(raw_data, config)
        assert packet._data == {'data': 'value'}

    def test_parse_with_tail_only(self):
        config = PacketConfig(tail=b'END', fields={'data': 'str'})
        raw_data = b'valueEND'
        packet = TextPacketStructure.parse(raw_data, config)
        assert packet._data == {'data': 'value'}

    def test_parse_without_config_raises_error(self):
        with pytest.raises(ValueError, match="Parsing requires 'fields'"):
            TextPacketStructure.parse(b'data', None)

    def test_parse_without_fields_raises_error(self):
        config = PacketConfig()
        with pytest.raises(ValueError, match="Parsing requires 'fields'"):
            TextPacketStructure.parse(b'data', config)

    def test_frame_type_none_when_not_set(self):
        config = PacketConfig(fields={'data': 'str'})
        packet = TextPacketStructure(config, data='test')
        assert packet.frame_type is None

    def test_payload_json_encoding(self):
        config = PacketConfig(fields={'data': 'str'})
        packet = TextPacketStructure(config, data='test', extra='value')
        expected = json.dumps(packet._data).encode('utf-8')
        assert packet.payload == expected

    def test_custom_delimiter(self):
        config = PacketConfig(delimiter=b'|', fields={'a': 'str', 'b': 'int'})
        packet = TextPacketStructure(config, a='hello', b=123)
        result = packet.build()
        assert result == b'hello|123'

    def test_custom_encoding(self):
        config = PacketConfig(encoding='ascii', fields={'data': 'str'})
        packet = TextPacketStructure(config, data='test')
        result = packet.build()
        assert result == b'test'

    def test_json_field_with_korean(self):
        config = PacketConfig(fields={'data': 'json'})
        test_data = {'message': '안녕하세요'}
        packet = TextPacketStructure(config, data=test_data)
        result = packet.build()
        expected = json.dumps(test_data, ensure_ascii=False).encode('utf-8')
        assert result == expected

    def test_int_field_conversion(self):
        config = PacketConfig(fields={'num': 'int'})
        packet = TextPacketStructure(config, num='123')
        result = packet.build()
        assert result == b'123'
        parsed = TextPacketStructure.parse(result, config)
        assert parsed._data['num'] == 123
        assert isinstance(parsed._data['num'], int)
