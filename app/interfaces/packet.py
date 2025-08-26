from abc import ABC, abstractmethod


class PacketInterface(ABC):
    @abstractmethod
    def to_packet(self, packet: bytes) -> bytes:
        """데이터를 패킷(bytes)으로 직렬화"""
        pass

    @abstractmethod
    def from_packet(self, packet: bytes) -> bytes:
        """패킷(bytes)을 데이터로 역직렬화"""
        pass
