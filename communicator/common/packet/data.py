from .builder import SyncNoGenerator
from .base import PacketStructure
from typing import Type, Tuple, Optional

class PacketSender:
    """
    PacketStructure와 SyncNoGenerator를 이용해 패킷을 생성하고 송신하는 헬퍼 클래스입니다.
    """
    def __init__(self, structure_cls: Type[PacketStructure], sync_gen: SyncNoGenerator):
        """
        PacketSender 인스턴스를 초기화합니다.

        Args:
            structure_cls (Type[PacketStructure]): 사용할 패킷 구조체 클래스
            sync_gen (SyncNoGenerator): 동기화 번호 생성기
        """
        self.structure_cls = structure_cls
        self.sync_gen = sync_gen

    def send(self, cmd: int, payload: bytes = b'') -> bytes:
        """
        주어진 명령과 페이로드로 패킷을 빌드하여 bytes로 반환합니다.

        Args:
            cmd: 프레임 타입(명령, Enum 또는 int)
            payload (bytes, optional): 페이로드 데이터. 기본값 b''
        Returns:
            bytes: 직렬화된 패킷 데이터
        """
        packet = self.structure_cls(sync_no=self.sync_gen.next(), cmd=cmd, payload=payload)
        return packet.build()

class PacketReceiver:
    """
    수신된 프로토콜 패킷을 파싱하는 헬퍼 클래스입니다.
    """
    @staticmethod
    def parse(raw_data: bytes, structure_cls: Type[PacketStructure]) -> Tuple[Optional[object], Optional[bytes]]:
        """
        원시 bytes 데이터를 패킷으로 파싱하고, 프레임 타입과 페이로드를 추출합니다.

        Args:
            raw_data (bytes): 수신된 원시 데이터
            structure_cls (Type[PacketStructure]): 파싱에 사용할 패킷 구조체 클래스
        Returns:
            Tuple[Optional[object], Optional[bytes]]: (프레임 타입, 페이로드) 또는 실패 시 (None, None)
        """
        try:
            packet = structure_cls.parse(raw_data)
            return packet.frame_type, packet.payload
        except Exception:
            return None, None