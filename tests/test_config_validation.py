import pytest
from communicator.common.packet.config import PacketConfig


class TestPacketConfigValidation:
    """PacketConfig 검증 로직 테스트"""

    def test_valid_config(self):
        """유효한 설정 테스트"""
        config = PacketConfig(
            fields={'cmd': 'str', 'data': 'json', 'seq': 'int'},
            encoding='utf-8'
        )
        assert config.validate() is True

    def test_invalid_field_type(self):
        """잘못된 필드 타입 테스트"""
        config = PacketConfig(
            fields={'invalid_field': 'float'}
        )
        with pytest.raises(ValueError, match="Invalid field type 'float'"):
            config.validate()

    def test_multiple_invalid_field_types(self):
        """여러 잘못된 필드 타입 테스트"""
        config = PacketConfig(
            fields={'field1': 'float', 'field2': 'str', 'field3': 'bool'}
        )
        with pytest.raises(ValueError, match="Invalid field type 'float'"):
            config.validate()

    def test_empty_fields(self):
        """빈 필드 설정 테스트"""
        config = PacketConfig(fields={})
        assert config.validate() is True

    def test_none_fields(self):
        """None 필드 설정 테스트"""
        config = PacketConfig(fields=None)
        assert config.validate() is True

    def test_valid_field_types(self):
        """모든 유효한 필드 타입 테스트"""
        config = PacketConfig(
            fields={
                'string_field': 'str',
                'integer_field': 'int', 
                'json_field': 'json'
            }
        )
        assert config.validate() is True

    def test_invalid_encoding_type(self):
        """잘못된 인코딩 타입 테스트"""
        config = PacketConfig(encoding=123)
        with pytest.raises(ValueError, match="Encoding must be a string"):
            config.validate()

    def test_valid_encoding(self):
        """유효한 인코딩 테스트"""
        config = PacketConfig(encoding='utf-8')
        assert config.validate() is True
        
        config = PacketConfig(encoding='ascii')
        assert config.validate() is True