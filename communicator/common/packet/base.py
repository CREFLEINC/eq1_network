from abc import ABC, abstractmethod
from typing import Any

class PacketStructure(ABC):
    """
    모든 패킷 구조체의 추상 베이스 클래스입니다.
    패킷 빌드와 파싱 인터페이스를 정의합니다.
    """
    @abstractmethod
    def build(self) -> bytes:
        """
        패킷을 프로토콜 규격에 맞게 직렬화하여 bytes로 반환합니다.

        Returns:
            bytes: 직렬화된 패킷 데이터
        """
        pass

    @classmethod
    @abstractmethod
    def parse(cls, data: bytes) -> 'PacketStructure':
        """
        bytes 데이터를 패킷 구조체 인스턴스로 파싱합니다.

        Args:
            data (bytes): 원시 패킷 데이터
        Returns:
            PacketStructure: 파싱된 패킷 인스턴스
        """
        pass

    @property
    @abstractmethod
    def frame_type(self) -> Any:
        """
        패킷의 프레임 타입(명령)을 반환합니다. (Enum 또는 int)

        Returns:
            Any: 프레임 타입(명령)
        """
        pass

    @property
    @abstractmethod
    def payload(self) -> bytes:
        """
        패킷의 페이로드(bytes)를 반환합니다.

        Returns:
            bytes: 페이로드 데이터
        """
        pass