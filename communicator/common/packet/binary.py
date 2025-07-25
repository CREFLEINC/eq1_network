from communicator.common.packet.base import PacketStructure
from communicator.utils.numeric import Numeric
from enum import IntEnum

class FrameType(IntEnum):
    """
    프레임 타입(명령) Enum.
    """
    GET_SLAVE_INFO = 0x01
    GET_INPUT = 0xC0
    GET_OUTPUT = 0xC5
    GET_IO_LEVEL = 0xCA
    SET_OUTPUT = 0xC6
    SET_IO_LEVEL = 0xCB

class BinaryPacketStructure(PacketStructure):
    """
    이진 프로토콜 패킷 구조체.
    동기화 번호, 프레임 타입, 페이로드를 포함하며 패킷 빌드/파싱 기능 제공.
    """
    def __init__(self, sync_no: int, cmd: FrameType, payload: bytes = b''):
        """
        BinaryPacketStructure 인스턴스를 초기화합니다.

        Args:
            sync_no (int): 패킷 동기화 번호.
            cmd (FrameType): 프레임 타입(명령).
            payload (bytes, optional): 페이로드 데이터. 기본값은 b''.
        """
        self.sync_no = sync_no
        self._frame_type = cmd
        self._payload = payload

    def build(self) -> bytes:
        """
        패킷을 프로토콜 규격에 맞게 직렬화하여 bytes로 반환합니다.

        Returns:
            bytes: 직렬화된 패킷 데이터
        """
        header = b'\xAA'
        sync = Numeric.int_to_bytes(self.sync_no, 1)
        reserved = b'\x00'
        cmd = Numeric.int_to_bytes(self._frame_type, 1)
        length = Numeric.int_to_bytes(len(sync + reserved + cmd + self._payload), 1)
        return header + length + sync + reserved + cmd + self._payload

    @classmethod
    def parse(cls, data: bytes) -> 'BinaryPacketStructure':
        """
        bytes 데이터를 BinaryPacketStructure로 파싱합니다.

        Args:
            data (bytes): 원시 패킷 데이터
        Returns:
            BinaryPacketStructure: 파싱된 패킷 인스턴스
        Raises:
            ValueError: 패킷 헤더가 잘못된 경우
        """
        if len(data) < 6 or data[0] != 0xAA:
            raise ValueError("Invalid packet header")
        length = data[1]
        sync = data[2]
        cmd = FrameType(data[4])
        payload = data[5:5 + length - 3]
        return cls(sync_no=sync, cmd=cmd, payload=payload)

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
