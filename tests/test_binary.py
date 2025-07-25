import pytest
from communicator.common.packet.binary import BinaryPacketStructure, FrameType
from communicator.utils.numeric import Numeric
from communicator.common.packet.base import PacketStructure


class TestBinaryPacketStructure:
    """
    BinaryPacketStructure 클래스의 기능을 검증하는 테스트 케이스 모음입니다.
    """

    def test_build_packet(self):
        """
        build() 메서드가 프로토콜 사양에 맞는 bytes 패킷을 생성하는지 테스트합니다.
        - header (1 byte): 0xAA
        - length (1 byte): sync + reserved + cmd + payload의 총 길이
        - sync (1 byte)
        - reserved (1 byte)
        - cmd (1 byte)
        - payload (N bytes)
        """
        packet = BinaryPacketStructure(sync_no=0x01, cmd=FrameType.GET_INPUT, payload=b'data')
        built = packet.build()

        expected_header = b'\xAA'
        expected_sync = Numeric.int_to_bytes(0x01, 1)
        expected_reserved = b'\x00'
        expected_cmd = Numeric.int_to_bytes(FrameType.GET_INPUT, 1)
        expected_length = Numeric.int_to_bytes(len(expected_sync + expected_reserved + expected_cmd + b'data'), 1)

        assert built.startswith(expected_header)
        assert built[1:2] == expected_length
        assert built[2:3] == expected_sync
        assert built[3:4] == expected_reserved
        assert built[4:5] == expected_cmd
        assert built[5:] == b'data'

    def test_parse_valid_packet(self):
        """
        parse() 메서드가 유효한 bytes 패킷 데이터를 BinaryPacketStructure 인스턴스로 올바르게 복원하는지 테스트합니다.
        - sync_no, cmd, payload 값을 확인합니다.
        """
        sync_no = 0x01
        cmd = FrameType.GET_OUTPUT
        payload = b'xyz'

        sync = Numeric.int_to_bytes(sync_no, 1)
        reserved = b'\x00'
        cmd_bytes = Numeric.int_to_bytes(cmd, 1)
        length = Numeric.int_to_bytes(len(sync + reserved + cmd_bytes + payload), 1)
        packet = b'\xAA' + length + sync + reserved + cmd_bytes + payload

        parsed = BinaryPacketStructure.parse(packet)

        assert isinstance(parsed, PacketStructure)
        assert parsed.sync_no == sync_no
        assert parsed.frame_type == FrameType.GET_OUTPUT
        assert parsed.payload == payload

    def test_parse_invalid_header(self):
        """
        parse() 호출 시, 첫 바이트가 0xAA가 아닌 경우 ValueError 예외를 발생시키는지 테스트합니다.
        """
        invalid_packet = b'\xAB\x06\x01\x00\xC0fail'

        with pytest.raises(ValueError, match="Invalid packet header"):
            BinaryPacketStructure.parse(invalid_packet)

    def test_parse_too_short_packet(self):
        """
        parse() 호출 시, 패킷 데이터 길이가 유효한 최소 길이보다 짧을 경우 ValueError를 발생시키는지 테스트합니다.
        """
        short_packet = b'\xAA\x01'

        with pytest.raises(ValueError, match="Invalid packet header"):
            BinaryPacketStructure.parse(short_packet)

    def test_frame_type_property(self):
        """
        frame_type 프로퍼티가 Enum(FrameType) 값을 정확히 반환하는지 테스트합니다.
        """
        packet = BinaryPacketStructure(sync_no=0x02, cmd=FrameType.SET_OUTPUT)
        assert packet.frame_type == FrameType.SET_OUTPUT

    def test_payload_property(self):
        """
        payload 프로퍼티가 패킷 생성 시 주어진 payload bytes를 정확히 반환하는지 테스트합니다.
        """
        packet = BinaryPacketStructure(sync_no=0x03, cmd=FrameType.SET_IO_LEVEL, payload=b'status')
        assert packet.payload == b'status'
