from abc import ABC, abstractmethod


class PacketStructureInterface(ABC):
    @classmethod
    @abstractmethod
    def to_packet(cls, data: bytes) -> bytes:
        """데이터를 패킷(bytes)으로 직렬화"""
        ...

    @classmethod
    @abstractmethod
    def from_packet(cls, packet: bytes) -> bytes:
        """패킷(bytes)을 데이터로 역직렬화"""
        ...

    @classmethod
    @abstractmethod
    def is_valid(cls, packet: bytes) -> bool:
        """패킷(bytes)이 유효한지 확인"""
        ...

    @classmethod
    @abstractmethod
    def split_packet(cls, packet: bytes) -> list[bytes]:
        """패킷(bytes)을 분할"""
        ...
