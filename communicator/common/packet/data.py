from typing import Type, Optional, Dict, Any, Tuple

from communicator.common.packet.base import PacketStructure
from communicator.common.packet.config import PacketConfig


class SendData:
    """
    설정 기반으로 패킷을 직렬화하는 클래스입니다.
    """
    def __init__(self, packet_structure: PacketStructure, config: PacketConfig):
        """
        SendData 인스턴스를 초기화합니다.
        Args:
            packet_structure (PacketStructure): 사용할 패킷 구조체 인스턴스
            config (PacketConfig): 패킷 구성 정보
        """
        self._packet_structure = packet_structure
        self._config = config

    def build(self, **kwargs) -> bytes:
        """
        주어진 데이터로 패킷을 빌드하여 bytes로 반환합니다.
        Args:
            **kwargs: 패킷 필드에 해당하는 데이터
        Returns:
            bytes: 직렬화된 패킷 데이터
        Raises:
            ValueError: config 또는 필수 필드 누락시
        """
        return self._packet_structure.build(self._config, **kwargs)


class ReceivedData:
    """
    수신된 프로토콜 패킷을 파싱하는 헬퍼 클래스입니다.
    """
    def __init__(self, structure_cls: Type[PacketStructure], config: PacketConfig):
        """
        ReceivedData 인스턴스를 초기화합니다.
        Args:
            structure_cls (Type[PacketStructure]): 파싱에 사용할 패킷 구조체 클래스
            config (PacketConfig): 패킷 구성 정보
        """
        self.structure_cls = structure_cls
        self.config = config

    def parse(self, raw_data: bytes) -> Optional[PacketStructure]:
        """
        원시 bytes 데이터를 패킷으로 파싱하여 PacketStructure 인스턴스를 반환합니다.
        Args:
            raw_data (bytes): 수신된 원시 데이터
        Returns:
            Optional[PacketStructure]: 파싱된 패킷 인스턴스 또는 실패 시 None
        Raises:
            ValueError: config 누락 등
        """
        if not self.config:
            raise ValueError("PacketConfig가 지정되지 않았습니다.")
        try:
            return self.structure_cls.parse(raw_data, self.config)
        except Exception as e:
            # 실제 환경에서는 print 대신 logging 사용 권장
            print(f"Failed to parse packet: {e}")
            return None