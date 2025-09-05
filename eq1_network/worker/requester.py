import abc
import logging
import queue
import threading
import traceback
from typing import Generic, Optional, Type, TypeVar, Union

from eq1_network.common.exception import (
    ProtocolAuthenticationError,
    ProtocolConnectionError,
    ProtocolDecodeError,
    ProtocolError,
    ProtocolTimeoutError,
    ProtocolValidationError,
)
from eq1_network.data import SendData
from eq1_network.interfaces.packet import PacketStructureInterface
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol

ProtocolLike = Union[ReqResProtocol, PubSubProtocol]
TSend = TypeVar("TSend", bound=SendData)

logger = logging.getLogger(__name__)


class RequesterEvent(Generic[TSend], abc.ABC):
    @abc.abstractmethod
    def on_sent(self, data: TSend) -> None:
        """데이터 전송 성공"""
        ...

    @abc.abstractmethod
    def on_failed_send(self, data: TSend) -> None:
        """데이터 전송 실패"""
        ...

    @abc.abstractmethod
    def on_disconnected(self, data: TSend) -> None:
        """연결 해제"""
        ...


class Requester(Generic[TSend], threading.Thread):
    def __init__(
        self,
        *,
        event_callback: RequesterEvent[TSend],
        protocol: ProtocolLike,
        packet_structure_interface: Type[PacketStructureInterface],
        request_queue: Optional[queue.Queue[TSend]] = None,
        queue_wait_time: float = 0.1,
    ):
        super().__init__()
        self._event_callback = event_callback
        self._protocol = protocol
        self._packet_structure = packet_structure_interface
        self._request_queue: queue.Queue[TSend] = request_queue or queue.Queue()
        self._stop_flag = threading.Event()
        self._queue_wait_time = queue_wait_time

    def stop(self):
        """스레드 종료 요청"""
        logger.debug(f"Set Stop flag for {self.__class__.__name__}")
        self._stop_flag.set()

    def put(self, data: TSend) -> None:
        """외부에서 TSend를 직접 주입"""
        logger.debug(f"Put data to {self.__class__.__name__}")
        self._request_queue.put_nowait(data)

    def run(self) -> None:
        """스레드 실행"""
        if not isinstance(self._protocol, (ReqResProtocol, PubSubProtocol)):
            raise ValueError(f"Protocol is not initialized in {self}")

        if not isinstance(self._event_callback, RequesterEvent):
            raise ValueError(f"Event callback is not initialized in {self}")

        while not self._stop_flag.is_set():
            try:
                data = self._request_queue.get(timeout=self._queue_wait_time)
            except queue.Empty:
                # 큐가 비어있을 때 stop_flag를 다시 확인
                if self._stop_flag.is_set():
                    break
                continue

            try:
                payload = data.to_bytes()
                packet = self._packet_structure.to_packet(payload)

                if isinstance(self._protocol, PubSubProtocol):
                    topic = getattr(data, "topic", None)
                    if not topic:
                        self._event_callback.on_failed_send(data)
                        continue
                    ok = self._protocol.publish(topic, packet)
                else:
                    ok = self._protocol.send(packet)

                if ok is True:
                    self._event_callback.on_sent(data)
                elif ok is False:
                    self._event_callback.on_failed_send(data)
                else:
                    self._event_callback.on_failed_send(data)

            except ProtocolConnectionError:
                self._event_callback.on_disconnected(data)

            except (
                ProtocolTimeoutError,
                ProtocolDecodeError,
                ProtocolValidationError,
                ProtocolAuthenticationError,
                ProtocolError,
            ):
                self._event_callback.on_failed_send(data)

            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__}: {e}")
                self._event_callback.on_failed_send(data)

        try:
            self._protocol.disconnect()
            logger.debug(f"Terminated {self.__class__.__name__} Thread")
        except Exception as e:
            logger.error(f"Error disconnecting protocol in {self.__class__.__name__}: {e}")
            traceback.print_exc()
