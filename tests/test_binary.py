import pytest
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.binary import BinaryPacketStructure, FrameType
from communicator.utils.numeric import Numeric


@pytest.fixture
def default_config():
    """
    테스트용 기본 PacketConfig를 반환합니다.
    - 헤더, 테일 모두 존재
    - 길이 필드와 sync 필드 사용
    """
    return PacketConfig(
        head=b"HH",
        tail=b"TT",
        use_length_field=True,
        use_sync_field=True,
        include_frame_type_in_length=True,
        include_sync_in_length=True,
        include_tail_in_length=True,
    )


def test_build_and_parse_with_all_fields(default_config):
    """
    [기능 테스트]
    BinaryPacketStructure.build()로 만든 패킷이
    parse()로 다시 정확히 복원되는지 테스트합니다.
    """
    payload = b"DATA123"
    frame_type = FrameType.GET_INPUT
    sync_no = 7

    packet = BinaryPacketStructure(default_config, frame_type=frame_type, sync_no=sync_no, payload=payload)
    built = packet.build()

    # build 결과의 기본 조건 확인
    assert built.startswith(default_config.head)
    assert built.endswith(default_config.tail)

    # parse
    parsed = BinaryPacketStructure.parse(built, default_config)

    assert parsed.frame_type == frame_type
    assert parsed._sync_no == sync_no
    assert parsed.payload == payload


def test_build_without_head_and_tail():
    """
    [헤더/테일 비사용 테스트]
    head, tail 없이 패킷을 빌드하고 parse할 때 예외 없이 동작해야 합니다.
    """
    config = PacketConfig(
        head=None,
        tail=None,
        use_length_field=True,
        use_sync_field=False,
        include_frame_type_in_length=True,
        include_sync_in_length=False,
        include_tail_in_length=False,
    )
    payload = b"PAYLOAD"
    frame_type = FrameType.SET_OUTPUT
    sync_no = 1

    packet = BinaryPacketStructure(config, frame_type=frame_type, sync_no=sync_no, payload=payload)
    built = packet.build()

    # 헤더와 테일이 없어도 동작해야 함
    parsed = BinaryPacketStructure.parse(built, config)
    assert parsed.frame_type == frame_type
    assert parsed.payload == payload


def test_is_valid_packet_with_no_length_field():
    """
    [길이 필드 없음 테스트]
    use_length_field=False 일 경우, 길이 검증 없이 헤더/테일만으로 True를 반환해야 합니다.
    """
    config = PacketConfig(
        head=b"H",
        tail=b"T",
        use_length_field=False,
        use_sync_field=False,
        include_frame_type_in_length=False,
        include_sync_in_length=False,
        include_tail_in_length=False,
    )
    raw_data = b"HABCDEFRT"
    # _is_valid_packet 호출
    assert BinaryPacketStructure._is_valid_packet(raw_data, config)


def test_invalid_header_or_tail(default_config):
    """
    [유효성 검사 실패 테스트]
    헤더나 테일이 잘못된 경우 ValueError 예외를 발생시키는지 검증합니다.
    """
    payload = b"DATA"
    packet = BinaryPacketStructure(default_config, frame_type=FrameType.GET_SLAVE_INFO, sync_no=1, payload=payload)
    built = packet.build()

    # 헤더가 틀린 경우
    broken_head = b"XX" + built[2:]
    with pytest.raises(ValueError):
        BinaryPacketStructure.parse(broken_head, default_config)

    # 테일이 틀린 경우
    broken_tail = built[:-2] + b"XX"
    with pytest.raises(ValueError):
        BinaryPacketStructure.parse(broken_tail, default_config)


def test_invalid_length_field(default_config):
    """
    [길이 불일치 테스트]
    길이 필드 값이 실제 데이터와 불일치할 때 _is_valid_packet이 False를 반환해야 합니다.
    """
    payload = b"123"
    packet = BinaryPacketStructure(default_config, frame_type=FrameType.GET_OUTPUT, sync_no=1, payload=payload)
    built = bytearray(packet.build())

    # 길이 필드를 잘못된 값으로 조작
    header_len = len(default_config.head)
    built[header_len:header_len+2] = Numeric.int_to_bytes(1, 2)

    assert BinaryPacketStructure._is_valid_packet(bytes(built), default_config) is False


def test_properties(default_config):
    """
    [프로퍼티 테스트]
    frame_type과 payload 프로퍼티 접근이 정상 동작하는지 테스트합니다.
    """
    payload = b"HELLO"
    frame_type = FrameType.SET_IO_LEVEL
    sync_no = 42

    packet = BinaryPacketStructure(default_config, frame_type=frame_type, sync_no=sync_no, payload=payload)

    assert packet.frame_type == frame_type
    assert packet.payload == payload
