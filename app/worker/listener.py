import abc
import queue
import threading
import time
import traceback
import logging
from typing import Callable, Generic, Optional, Type, TypeVar, Union, runtime_checkable

from app.data import PacketStructure, SendData, ReceivedData
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol
from app.interfaces.packet import PacketStructureInterface
from app.common.exception import ProtocolError, ProtocolConnectionError, ProtocolTimeoutError, ProtocolDecodeError, ProtocolValidationError, ProtocolAuthenticationError

ProtocolLike = Union[ReqResProtocol, PubSubProtocol]
TSend = TypeVar("TSend", bound=SendData)
TRecv = TypeVar("TRecv", bound=ReceivedData)

logger = logging.getLogger(__name__)


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
        """스레드 중지"""
        logger.debug(f"Set Stop flag for {self.__class__.__name__}")
        self._stop_flag.set()

    def run(self) -> None:
        """스레드 실행"""
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
                    packets = self._packet_structure_interface.split_packet(bytes_data)
                else:
                    packets = [bytes_data]

                for packet in packets:
                    try:
                        raw_data = self._packet_structure_interface.from_packet(packet)
                        if self._received_data_class:
                            received_data = self._received_data_class.from_bytes(raw_data)
                        else:
                            received_data = raw_data
                        self._event_callback.on_received(received_data)
                    except (ProtocolDecodeError, ProtocolValidationError) as e:
                        logger.warning(f"Packet decode/validation error: {e}")
                        self._event_callback.on_failed_recv(packet)
                    except Exception as e:
                        logger.error(f"Error processing packet in {self.__class__.__name__}: {e}")
                        self._event_callback.on_failed_recv(packet)
                        
            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__}: {e}")
                traceback.print_exc()

        try:
            self._protocol.disconnect()
            logger.debug(f"Terminated {self.__class__.__name__} Thread")
        except Exception as e:
            logger.error(f"Error disconnecting protocol in {self.__class__.__name__}: {e}")
            traceback.print_exc()
