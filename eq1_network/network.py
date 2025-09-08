import logging
import queue
import threading
import time
from typing import Any, Dict, Union

from eq1_network.data import DataPackage
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol
from eq1_network.manager.protocol_factory import create_protocol
from eq1_network.worker.listener import Listener, ListenerEvent
from eq1_network.worker.requester import Requester, RequesterEvent

logger = logging.getLogger(__name__)
Protocol = Union[ReqResProtocol, PubSubProtocol]

class NetworkEvent:
    pass


class NetworkHandler(threading.Thread, ListenerEvent, RequesterEvent):
    def __init__(self, network_config: Dict, event_callback: NetworkEvent = None, net_id: Any = None):
        super().__init__()
        self._net_id = net_id
        self._stop_flag = threading.Event()
        self._network_config = network_config
        self._protocol = None
        self._requester = None
        self._listener = None
        self._request_queue = None
        self._retry_flag = True
        self._is_server = network_config.get('mode', 'client').lower() == 'server'

        self._event_callback = event_callback or self

    def on_sent(self, data: DataPackage.SendData):
        logger.write_debug(self, f"on_sent - {self._net_id} - {data}", print_to_terminal=True)
        if hasattr(self._event_callback, 'on_sent'):
            self._event_callback.on_sent(data)

    def on_failed_send(self, data: DataPackage.SendData):
        logger.write_error(self, f"on_failed_send - {self._net_id} - {data}", print_to_terminal=True)
        if hasattr(self._event_callback, 'on_failed_send'):
            self._event_callback.on_failed_send(data)

    def on_received(self, data: DataPackage.ReceivedData):
        logger.write_debug(self, f"on_received - {self._net_id} - {data}", print_to_terminal=True)
        if hasattr(self._event_callback, 'on_received'):
            self._event_callback.on_received(data)

    def on_failed_recv(self, data: DataPackage.ReceivedData):
        logger.write_error(self, f"on_failed_recv - {self._net_id} - {data}", print_to_terminal=True)
        if hasattr(self._event_callback, 'on_failed_recv'):
            self._event_callback.on_failed_recv(data)

    def on_disconnected(self, data: Union[DataPackage.ReceivedData, DataPackage.SendData]):
        logger.write_debug(self, f"on_disconnected - {self._net_id}", print_to_terminal=True)
        self._retry_flag = True
        if hasattr(self._event_callback, 'on_disconnected'):
            self._event_callback.on_disconnected(data)

    def start_communication(self):
        logger.write_debug(self, f"start_communication - {self._net_id} - wait for connection...", print_to_terminal=True)
        self._protocol = create_protocol(
            params=self._network_config
        )
        while not self._stop_flag.is_set():
            time.sleep(0.001)
            if self._protocol.connect():
                logger.write_debug(self, f"  {self._net_id} - connected !!", print_to_terminal=True)
                break

        self._request_queue = queue.Queue()

        self._listener = Listener(
            event_callback=self,
            protocol=self._protocol
        )

        self._requester = Requester(
            event_callback=self,
            protocol=self._protocol,
            request_queue=self._request_queue
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

    def send_data(self, data: DataPackage.SendData) -> bool:
        if not isinstance(data, DataPackage.SendData):
            raise ValueError(f"Invalid data type. {data}")

        # 서버 모드에서는 직접 프로토콜을 통해 전송
        if self._is_server and self._protocol and self._protocol.is_connected():
            return self._protocol.send(data.to_bytes())

        # 클라이언트 모드에서는 큐를 통해 전송
        if not self._request_queue:
            logger.write_debug(self,
                                  f"Request Queue is not initialized. {self._net_id}, May be not connected yet",
                                  print_to_terminal=True)
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

    def start_server(self):
        """서버 모드에서 통신 시작"""
        if self._is_server:
            self.start()
            return True
        return False

    def stop_server(self):
        """서버 모드에서 통신 중지"""
        if self._is_server:
            self.stop()
            return True
        return False
