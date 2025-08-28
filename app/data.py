import abc
from abc import abstractmethod
from typing import Optional, Protocol, Type, TypeVar, Generic, Self
import dataclasses
from dataclasses import dataclass, field
import time

from app.interfaces.packet import PacketStructureInterface

TRecv = TypeVar("TRecv", bound="ReceivedData")
TSend = TypeVar("TSend", bound="SendData")


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


@dataclass(slots=True)
class DataPackage(Generic[TSend, TRecv]):
    """
    외부 주입 데이터(SendData/ReceivedData)와 패킷 구조를 하나로 다루는 컨테이너.
    - 송신: send_data + packet_structure -> build_packet()
    - 수신: parse_packet(...) -> received_data 세팅된 DataPackage 반환
    """
    send_data: Optional[TSend] = None
    received_data: Optional[TRecv] = None
    packet_structure: Optional[type[PacketStructureInterface]] = None

    timestamp: float = field(default_factory=lambda: time.time())
    source: Optional[str] = None
    destination: Optional[str] = None

    def is_outgoing(self) -> bool:
        return self.send_data is not None

    def is_incoming(self) -> bool:
        return self.received_data is not None

    def set_send_data(self, data: TSend) -> "DataPackage[TSend, TRecv]":
        self.send_data = data
        return self

    def set_received_data(self, data: TRecv) -> "DataPackage[TSend, TRecv]":
        self.received_data = data
        return self

    def set_packet_structure(self, packet_structure: type[PacketStructureInterface]) -> "DataPackage[TSend, TRecv]":
        self.packet_structure = packet_structure
        return self

    def build_packet(self) -> bytes:
        """송신용: send_data -> payload -> packet"""
        if self.send_data is None:
            raise ValueError("send_data가 없습니다.")
        if self.packet_structure is None:
            raise ValueError("packet_structure가 없습니다.")
        payload = self.send_data.to_bytes()
        return self.packet_structure.to_packet(payload)

    @classmethod
    def parse_packet(
        cls,
        packet: bytes,
        *,
        receiver_type: Type[TRecv],
        packet_structure: type[PacketStructureInterface],
        source: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> "DataPackage[TSend, TRecv]":
        """단일 프레임 수신용"""
        payload = packet_structure.from_packet(packet)
        received_data = receiver_type.from_bytes(payload)
        return cls(
            received_data=received_data,
            packet_structure=packet_structure,
            source=source,
            destination=destination,
        )
    
    @classmethod
    def parse_packets(
        cls,
        stream: bytes,
        *,
        receiver_type: Type[TRecv],
        packet_structure: type[PacketStructureInterface],
        drop_empty: bool = True,
    ) -> list["DataPackage[TSend, TRecv]"]:
        """멀티 프레임 수신용"""
        packets = packet_structure.split_packet(stream)
        out: list["DataPackage[TSend, TRecv]"] = []
        for p in packets:
            payload = packet_structure.from_packet(p)
            if drop_empty and len(payload) == 0:
                continue
            received = receiver_type.from_bytes(payload)
            out.append(cls(received_data=received, packet_structure=packet_structure))
        return out


if __name__ == "__main__":
    pass