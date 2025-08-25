import abc
import threading
import time

from lib.communication.data import PacketStructure, ReceivedData
from lib.communication.protocol.interface import Protocol
from src.logger import AppLogger  # TODO : src 의존성 제거하기


class ListenerEvent(abc.ABC):
    @abc.abstractmethod
    def on_received(self, received_data: ReceivedData):
        pass

    @abc.abstractmethod
    def on_failed_recv(self, data: bytes):
        pass

    @abc.abstractmethod
    def on_disconnected(self, data: bytes):
        pass


class Listener(threading.Thread):

    def __init__(
        self,
        event_callback: ListenerEvent,
        packet_structure_impl: PacketStructureInterface,
        protocol: Protocol,
    ):
        super().__init__()
        self._protocol = protocol
        self._stop_flag = threading.Event()
        self._event_callback = event_callback
        self._packet_structure = packet_structure_impl

    def stop(self):
        AppLogger.write_debug(self, "Set Stop flag for Tcp Listener")
        self._stop_flag.set()

    def run(self) -> None:
        if not isinstance(self._protocol, Protocol):
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
                elif not self._packet_structure.is_valid(bytes_data):
                    packets = PacketStructure.split_packet(bytes_data)
                else:
                    packets = [bytes_data]

                for packet in packets:
                    self._event_callback.on_received(
                        ReceivedData.from_bytes(PacketStructure.from_packet(packet))
                    )
            except Exception as e:
                import traceback

                traceback.print_exc()

        self._protocol.disconnect()
        AppLogger.write_debug(self, "Terminated Tcp Listener Thread")
