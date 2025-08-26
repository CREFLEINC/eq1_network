import abc
from abc import abstractmethod
from typing import Self


class ReceivedData(abc.ABC):
    @classmethod
    @abstractmethod
    def from_bytes(cls, data: bytes) -> Self:
        """패킷(bytes)을 데이터로 역직렬화"""
        ...


class SendData(abc.ABC):
    @abstractmethod
    def to_bytes(self) -> bytes:
        """데이터를 패킷(bytes)으로 직렬화"""
        ...


class PacketStructure:
    HEAD_PACKET = b"$"
    TAIL_PACKET = b"$"

    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        return cls.HEAD_PACKET + data + cls.TAIL_PACKET

    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        if not cls.is_valid(packet):
            raise ValueError(f"Packet Structure Error : {packet}")

        return packet[1:-1]

    @classmethod
    def is_valid(cls, packet: bytes) -> bool:
        if (cls.TAIL_PACKET + cls.HEAD_PACKET) in packet:
            return False

        if packet[:1] != cls.HEAD_PACKET:
            return False

        if packet[-1:] != cls.TAIL_PACKET:
            return False

        return True

    @classmethod
    def split_packet(cls, packet: bytes) -> list[bytes]:
        results = []
        for _d in packet.split(cls.HEAD_PACKET):
            if len(_d) == 0:
                continue
            results.append(cls.HEAD_PACKET + _d + cls.TAIL_PACKET)
        return results


if __name__ == "__main__":
    message = b"$abc$$def$"
    print(PacketStructure.split_packet(message))
