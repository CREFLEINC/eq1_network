import pytest
from communicator.common.packet.config import PacketConfig

class TestPacketConfig:
    """
    PacketConfig 데이터 클래스를 테스트합니다.
    """

    def test_default_initialization(self):
        """
        PacketConfig가 기본값으로 올바르게 초기화되는지 테스트합니다.
        - head, tail, delimiter는 None이어야 합니다.
        - encoding은 'utf-8'이어야 합니다.
        - fields와 extra_args는 빈 딕셔너리여야 합니다.
        """
        config = PacketConfig()

        assert config.head is None
        assert config.tail is None
        assert config.delimiter is None
        assert config.encoding == 'utf-8'
        assert config.fields == {}
        assert config.extra_args == {}

    def test_custom_initialization(self):
        """
        사용자 정의 값으로 PacketConfig가 올바르게 초기화되는지 테스트합니다.
        - 모든 속성에 임의의 값을 할당하고, 해당 값이 정확히 설정되었는지 확인합니다.
        """
        custom_head = b'\xAA'
        custom_tail = b'\xBB'
        custom_delimiter = b'|'
        custom_encoding = 'ascii'
        custom_fields = {'name': 'str', 'age': 'int'}
        custom_extra_args = {'timeout': 10}

        config = PacketConfig(
            head=custom_head,
            tail=custom_tail,
            delimiter=custom_delimiter,
            encoding=custom_encoding,
            fields=custom_fields,
            extra_args=custom_extra_args
        )

        assert config.head == custom_head
        assert config.tail == custom_tail
        assert config.delimiter == custom_delimiter
        assert config.encoding == custom_encoding
        assert config.fields == custom_fields
        assert config.extra_args == custom_extra_args
