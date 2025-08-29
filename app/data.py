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
    """PacketStructure, SendData, ReceivedData 클래스를 담는 구성 객체"""
    packet_structure: type[PacketStructureInterface]
    send_data: type[TSend]
    received_data: type[TRecv]

if __name__ == "__main__":
    pass