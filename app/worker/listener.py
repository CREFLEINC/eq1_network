import abc
import queue
import threading
import time
import traceback
from typing import Callable, Generic, Optional, Type, TypeVar, Union, runtime_checkable

from app.data import PacketStructure, SendData, ReceivedData
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol
from app.interfaces.packet import PacketStructureInterface
from app.common.exception import ProtocolError, ProtocolConnectionError, ProtocolTimeoutError, ProtocolDecodeError, ProtocolValidationError, ProtocolAuthenticationError
from src.logger import AppLogger

ProtocolLike = Union[ReqResProtocol, PubSubProtocol]
TSend = TypeVar("TSend", bound=SendData)
TRecv = TypeVar("TRecv", bound=ReceivedData)


class ListenerEvent(Generic[TRecv], abc.ABC):
    @abc.abstractmethod
    def on_received(self, received_data: TRecv):
        """데이터 수신"""
        ...

    @abc.abstractmethod
    def on_failed_recv(self, data: bytes):
        """데이터 수신 실패"""
        ...

    @abc.abstractmethod
    def on_disconnected(self, data: bytes):
        """연결 해제"""
        ...


class Listener(Generic[TRecv], threading.Thread):

    def __init__(
        self,
        *,
        event_callback: ListenerEvent[TRecv],
        packet_structure_interface: Type[PacketStructureInterface],
        protocol: ProtocolLike,
        received_data_class: Type[TRecv] = None,
    ):
        super().__init__()
        self._protocol = protocol
        self._stop_flag = threading.Event()
        self._event_callback = event_callback
        self._packet_structure_interface = packet_structure_interface
        self._received_data_class = received_data_class

    def stop(self):
        AppLogger.write_debug(self, "Set Stop flag for Tcp Listener")
        self._stop_flag.set()

    def run(self) -> None:
        if not isinstance(self._protocol, (ReqResProtocol, PubSubProtocol)):
            raise ValueError(f"Protocol is not initialized in {self}")

        if not isinstance(self._event_callback, ListenerEvent):
            raise ValueError(f"Event callback is not initialized in {self}")

        while not self._stop_flag.is_set():
            try:
                is_ok, bytes_data = self._protocol.read()
                packets = []
                if not is_ok:
                    self._event_callback.on_failed_recv(bytes_data)
                    self._event_callback.on_disconnected(bytes_data)
                elif bytes_data is None:
                    time.sleep(0.01)
                    continue
                elif not self._packet_structure_interface.is_valid(bytes_data):
                    packets = PacketStructure.split_packet(bytes_data)
                else:
                    packets = [bytes_data]

                for packet in packets:
                    raw_data = self._packet_structure_interface.from_packet(packet)
                    if self._received_data_class:
                        received_data = self._received_data_class.from_bytes(raw_data)
                    else:
                        # 기본 구현체가 없는 경우 bytes를 그대로 전달
                        received_data = raw_data
                    self._event_callback.on_received(received_data)
            except Exception as e:
                import traceback

                traceback.print_exc()

        self._protocol.disconnect()
        AppLogger.write_debug(self, "Terminated Tcp Listener Thread")
