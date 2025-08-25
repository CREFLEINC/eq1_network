import time
import queue
import threading
from typing import Union, Any, Dict
from lib.communication.data import SendData, ReceivedData
from lib.communication.worker import ListenerEvent, RequesterEvent, Listener, Requester
from lib.communication.protocol.interface import Protocol
from lib.communication.protocol.factory import create_protocol

from src.configure import Params  # TODO : src 의존성 제거하기
from src.logger import AppLogger


class NetworkEvent:
    pass


class NetworkHandler(threading.Thread, ListenerEvent, RequesterEvent):
    def __init__(
        self, network_config: Dict, event_callback: NetworkEvent, net_id: Any = None
    ):
        super().__init__()
        self._net_id = net_id
        self._stop_flag = threading.Event()
        self._network_config = network_config
        self._protocol = None
        self._requester = None
        self._listener = None
        self._request_queue = None
        self._retry_flag = True

        self._event_callback = event_callback

    def on_sent(self, data: SendData):
        AppLogger.write_debug(
            self, f"on_sent - {self._net_id} - {data}", print_to_terminal=True
        )

    def on_failed_send(self, data: SendData):
        AppLogger.write_error(
            self, f"on_failed_send - {self._net_id} - {data}", print_to_terminal=True
        )

    def on_received(self, data: ReceivedData):
        AppLogger.write_debug(
            self, f"on_received - {self._net_id} - {data}", print_to_terminal=True
        )

    def on_failed_recv(self, data: ReceivedData):
        AppLogger.write_error(
            self, f"on_failed_recv - {self._net_id} - {data}", print_to_terminal=True
        )

    def on_disconnected(self, data: Union[ReceivedData, SendData]):
        AppLogger.write_debug(
            self, f"on_disconnected - {self._net_id}", print_to_terminal=True
        )
        self._retry_flag = True

    def start_communication(self):
        AppLogger.write_debug(
            self,
            f"start_communication - {self._net_id} - wait for connection...",
            print_to_terminal=True,
        )
        self._protocol = create_protocol(params=self._network_config)
        while not self._stop_flag.is_set():
            time.sleep(0.001)
            if self._protocol.connect():
                AppLogger.write_debug(
                    self, f"  {self._net_id} - connected !!", print_to_terminal=True
                )
                break

        self._request_queue = queue.Queue()

        self._listener = Listener(event_callback=self, protocol=self._protocol)

        self._requester = Requester(
            event_callback=self,
            protocol=self._protocol,
            request_queue=self._request_queue,
        )

        self._listener.start()
        self._requester.start()

        self._retry_flag = False

    def stop_communications(self):
        if isinstance(self._listener, Listener) and self._listener.is_alive():
            self._listener.stop()
            self._listener.join()

        if isinstance(self._requester, Requester) and self._requester.is_alive():
            self._requester.stop()
            self._requester.join()

        if isinstance(self._protocol, Protocol):
            self._protocol.disconnect()

    def reconnect(self):
        self.stop_communications()
        self.start_communication()

    def send_data(self, data: SendData) -> bool:
        if not isinstance(data, SendData):
            raise ValueError(f"Invalid data type. {data}")

        if not self._request_queue:
            AppLogger.write_debug(
                self,
                f"Request Queue is not initialized. {self._net_id}, May be not connected yet",
                print_to_terminal=True,
            )
            return False

        self._request_queue.put(data)

        return True

    def stop(self):
        self._stop_flag.set()

    def run(self):
        self._stop_flag.clear()
        while not self._stop_flag.is_set():
            time.sleep(0.0001)
            if self._retry_flag:
                self.reconnect()
        self.stop_communications()

    def is_connected(self) -> bool:
        return not self._retry_flag
