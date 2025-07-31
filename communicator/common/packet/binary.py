from communicator.common.packet.base import PacketStructure
from communicator.utils.numeric import Numeric
from enum import IntEnum
from communicator.common.packet.config import PacketConfig
from typing import Dict, Any

class FrameType(IntEnum):
    """
    요청-응답 형식의 프로토콜을 위한 프레임 타입(명령) Enum.
    """
    GET_SLAVE_INFO = 0x01
    GET_INPUT = 0xC0
    GET_OUTPUT = 0xC5
    GET_IO_LEVEL = 0xCA
    SET_OUTPUT = 0xC6
    SET_IO_LEVEL = 0xCB
    RETRANSMISSION_REQUEST = 0xF0   # 클라이언트가 서버에 특정 패킷의 재전송을 요청할 때 사용
    RETRANSMISSION_RESPONSE = 0xF1  # 서버가 클라이언트에 특정 패킷의 재전송을 응답할 때 사용

class BinaryPacketStructure(PacketStructure):
    """
    이진 프로토콜 패킷 구조체.
    동기화 번호, 프레임 타입, 페이로드를 포함하며 패킷 빌드/파싱 기능 제공.
    """
    def __init__(self, config: PacketConfig, *, frame_type: FrameType, sync_no: int, payload: bytes = b''):
        """
        BinaryPacketStructure 인스턴스를 초기화합니다.
        Args:
            config (PacketConfig): 패킷 구성 정보 (항상 명시적으로 제공)
            frame_type (FrameType): 프레임 타입
            sync_no (int): 동기화 번호
            payload (bytes, optional): 페이로드
        """
        if not config:
            raise ValueError("config: PacketConfig는 필수입니다.")
        self.config = config
        self._frame_type = frame_type
        self._sync_no = sync_no
        self._payload = payload

    def build(self) -> bytes:
        """
        config 기반으로 직렬화
        """
        parts = []

        # 헤더
        if self.config.head:
            parts.append(self.config.head)

        # 길이 계산: length 필드가 있는 경우만
        if self.config.use_length_field:
            # length는 (전체 길이 - header 길이)로 계산하는 것을 기본으로 두되, 옵션으로 조정 가능
            total_len = len(self._payload)
            if self.config.include_frame_type_in_length:
                total_len += 1
            if self.config.include_sync_in_length:
                total_len += 1
            if self.config.include_tail_in_length and self.config.tail:
                total_len += len(self.config.tail)
            total_len += 2  # length field 자체를 포함
            parts.append(Numeric.int_to_bytes(total_len, 2))

        # frame_type
        parts.append(Numeric.int_to_bytes(self._frame_type, 1))

        # sync
        if self.config.use_sync_field:
            parts.append(Numeric.int_to_bytes(self._sync_no, 1))

        # payload
        parts.append(self._payload)

        # tail
        if self.config.tail:
            parts.append(self.config.tail)

        return b"".join(parts)

    @classmethod
    def parse(cls, raw_data: bytes, config: PacketConfig) -> 'BinaryPacketStructure':
        """
        raw_data를 config에 맞춰 파싱하여 BinaryPacketStructure 인스턴스를 반환합니다.
        Args:
            raw_data (bytes): 원시 패킷 데이터
            config (PacketConfig): 패킷 구성 정보
        Returns:
            BinaryPacketStructure: 파싱된 패킷 인스턴스
        Raises:
            ValueError: 패킷 형식이 유효하지 않거나 필수 필드가 누락된 경우
        """
        if not cls._is_valid_packet(raw_data, config):
            raise ValueError("Invalid binary packet format")
        offset = 0
        if config.head:
            offset += len(config.head)
        if config.use_length_field:
            offset += 2
        frame_type = Numeric.bytes_to_int(raw_data[offset:offset+1])
        offset += 1
        sync_no = None
        if config.use_sync_field:
            sync_no = Numeric.bytes_to_int(raw_data[offset:offset+1])
            offset += 1
        end_index = -len(config.tail) if config.tail else None
        payload = raw_data[offset:end_index] if end_index else raw_data[offset:]
        return cls(config, frame_type=frame_type, sync_no=sync_no, payload=payload)

    @classmethod
    def _is_valid_packet(cls, raw_data: bytes, config: PacketConfig) -> bool:
        """
        config에 따라 패킷이 유효한지 검사
        """
        # 헤더/테일 검사
        if config.head and not raw_data.startswith(config.head):
            return False
        if config.tail and not raw_data.endswith(config.tail):
            return False

        # 길이 필드가 없으면 헤더/테일만 맞으면 통과
        if not config.use_length_field:
            return True

        # 길이 검증
        header_len = len(config.head) if config.head else 0
        declared_length = Numeric.bytes_to_int(raw_data[header_len:header_len+2])
        actual_length = len(raw_data) - header_len

        return declared_length == actual_length

    @property
    def frame_type(self) -> FrameType:
        """
        패킷의 프레임 타입(명령)을 반환합니다.

        Returns:
            FrameType: 프레임 타입(Enum)
        """
        return self._frame_type

    @property
    def payload(self) -> bytes:
        """
        패킷의 페이로드(bytes)를 반환합니다.

        Returns:
            bytes: 페이로드 데이터
        """
        return self._payload
