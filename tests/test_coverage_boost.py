import pytest
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.text import TextPacketStructure
from communicator.common.packet.binary import BinaryPacketStructure, FrameType
from communicator.common.packet.data import SendData, ReceivedData
from communicator.common.packet.builder import SyncNoGenerator


class TestCoverageBoost:
    """커버리지 향상을 위한 추가 테스트들"""

    def test_sync_generator_max_value_validation(self):
        """SyncNoGenerator max_value 검증 테스트"""
        with pytest.raises(ValueError, match="max_value는 1 이상이어야 합니다"):
            SyncNoGenerator(max_value=0)
        
        with pytest.raises(ValueError, match="max_value는 1 이상이어야 합니다"):
            SyncNoGenerator(max_value=-1)

    def test_sync_generator_custom_max_value(self):
        """SyncNoGenerator 사용자 정의 max_value 테스트"""
        gen = SyncNoGenerator(max_value=10)
        
        # 10번 호출하여 1~10 범위 확인
        for i in range(1, 11):
            assert gen.next() == i
        
        # 11번째 호출 시 0으로 순환
        assert gen.next() == 0

    def test_binary_packet_init_without_config(self):
        """BinaryPacketStructure config 없이 초기화 시 오류 테스트"""
        with pytest.raises(ValueError, match="config: PacketConfig는 필수입니다"):
            BinaryPacketStructure(None, frame_type=FrameType.GET_INPUT, sync_no=1)

    def test_binary_packet_is_valid_short_data(self):
        """BinaryPacketStructure 짧은 데이터 검증 테스트"""
        config = PacketConfig(head=b"HH", use_length_field=True)
        short_data = b"HH"  # 길이 필드를 읽을 수 없을 정도로 짧음
        
        assert not BinaryPacketStructure._is_valid_packet(short_data, config)

    def test_text_packet_default_delimiter(self):
        """TextPacketStructure 기본 delimiter 테스트"""
        config = PacketConfig(fields={'a': 'str', 'b': 'int'})
        packet = TextPacketStructure(config, a='test', b=123)
        
        result = packet.build()
        assert result == b'test,123'  # 기본 delimiter는 ','

    def test_text_packet_parse_with_default_delimiter(self):
        """TextPacketStructure 기본 delimiter로 파싱 테스트"""
        config = PacketConfig(fields={'a': 'str', 'b': 'int'})
        raw_data = b'hello,456'
        
        packet = TextPacketStructure.parse(raw_data, config)
        assert packet._data == {'a': 'hello', 'b': 456}

    def test_send_data_build_with_empty_kwargs(self):
        """SendData build 시 빈 kwargs 테스트"""
        config = PacketConfig(fields={'data': 'str'})
        packet_structure = TextPacketStructure(config, data='original')
        sender = SendData(packet_structure, config)
        
        # kwargs가 비어있으면 인스턴스의 _data 사용
        result = sender.build()
        assert result == b'original'

    def test_received_data_parse_exception_handling(self):
        """ReceivedData parse 시 예외 처리 테스트"""
        config = PacketConfig(fields={'a': 'int', 'b': 'int'})  # 2개 필드 기대
        receiver = ReceivedData(TextPacketStructure, config)
        
        # 필드 개수 불일치로 예외 발생 시 None 반환
        result = receiver.parse(b'single_field_only')  # 1개 필드만 있음
        assert result is None

    def test_packet_config_all_fields(self):
        """PacketConfig 모든 필드 설정 테스트"""
        config = PacketConfig(
            head=b'HEAD',
            tail=b'TAIL',
            delimiter=b'|',
            encoding='ascii',
            fields={'test': 'str'},
            extra_args={'custom': 'value'},
            use_length_field=True,
            use_sync_field=True,
            include_frame_type_in_length=True,
            include_sync_in_length=True,
            include_tail_in_length=True
        )
        
        assert config.head == b'HEAD'
        assert config.tail == b'TAIL'
        assert config.delimiter == b'|'
        assert config.encoding == 'ascii'
        assert config.fields == {'test': 'str'}
        assert config.extra_args == {'custom': 'value'}
        assert config.use_length_field is True
        assert config.use_sync_field is True
        assert config.include_frame_type_in_length is True
        assert config.include_sync_in_length is True
        assert config.include_tail_in_length is True

    def test_binary_packet_without_sync_field(self):
        """BinaryPacketStructure sync 필드 없이 빌드/파싱 테스트"""
        config = PacketConfig(
            head=b'AA',
            tail=b'BB',
            use_length_field=False,
            use_sync_field=False
        )
        
        packet = BinaryPacketStructure(config, frame_type=FrameType.GET_INPUT, sync_no=1, payload=b'test')
        built = packet.build()
        
        parsed = BinaryPacketStructure.parse(built, config)
        assert parsed.frame_type == FrameType.GET_INPUT
        assert parsed.payload == b'test'

    def test_text_packet_build_config_override(self):
        """TextPacketStructure build 시 config 오버라이드 테스트"""
        original_config = PacketConfig(fields={'data': 'str'})
        override_config = PacketConfig(head=b'[', tail=b']', fields={'data': 'str'})
        
        packet = TextPacketStructure(original_config, data='test')
        
        # 원본 config로 빌드
        result1 = packet.build()
        assert result1 == b'test'
        
        # 오버라이드 config로 빌드
        result2 = packet.build(override_config)
        assert result2 == b'[test]'