import abc
import time
import queue
import threading
import traceback
from typing import Optional
from lib.communication.protocol.interface import Protocol
from lib.communication.data import SendData, PacketStructure


class RequesterEvent(abc.ABC):
    @abc.abstractmethod
    def on_sent(self, data: SendData):
        pass

    @abc.abstractmethod
    def on_failed_send(self, data: SendData):
        pass

    @abc.abstractmethod
    def on_disconnected(self, data: SendData):
        pass


class Requester(threading.Thread):
    def __init__(
        self,
        event_callback: RequesterEvent,
        protocol: Protocol,
        request_queue: queue.Queue,
        conf_file_path: str = "./public/network.ini",
    ):
        super().__init__()
        self._network_config_file_path = conf_file_path
        self._protocol = protocol
        self._stop_flag = threading.Event()
        self._event_callback = event_callback
        self._request_queue = request_queue

    def stop(self):
        self._stop_flag.set()

    def next(self) -> Optional[SendData]:
        try:
            data = self._request_queue.get_nowait()
            if isinstance(data, SendData):
                return data
        except queue.Empty:
            pass
        except Exception as e:
            traceback.format_exc()

    def run(self) -> None:
        if not isinstance(self._protocol, Protocol):
            raise ValueError(f"Protocol is not initialized in {self}")

        if not isinstance(self._event_callback, RequesterEvent):
            raise ValueError(f"Event callback is not initialized in {self}")

        while not self._stop_flag.is_set():
            time.sleep(0.0001)
            try:
                send_data = self.next()

                if send_data is None:
                    continue

                result = self._protocol.send(
                    PacketStructure.to_packet(send_data.to_bytes())
                )

                if result:
                    self._event_callback.on_sent(send_data)
                else:
                    self._event_callback.on_failed_send(send_data)
                    self._event_callback.on_disconnected(send_data)

            except Exception as e:
                traceback.print_exc()
