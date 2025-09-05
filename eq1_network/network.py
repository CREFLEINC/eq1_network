import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

from eq1_network.data import DataPackage
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol
from eq1_network.manager.protocol_factory import create_protocol
from eq1_network.worker.listener import Listener, ListenerEvent
from eq1_network.worker.requester import Requester, RequesterEvent

logger = logging.getLogger(__name__)


class NetworkEvent:
    pass


class NetworkHandler(threading.Thread, ListenerEvent, RequesterEvent):
    def __init__(
        self,
        network_config: Dict,
        event_callback: NetworkEvent,
        net_id: Any = None,
        data_package: Optional[DataPackage] = None,
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
        self._data_package = data_package
        self._event_callback = event_callback

    def on_sent(self, data):
        logger.debug(f"on_sent - {self._net_id} - {data}")

    def on_failed_send(self, data):
        logger.error(f"on_failed_send - {self._net_id} - {data}")

    def on_received(self, data):
        logger.debug(f"on_received - {self._net_id} - {data}")

    def on_failed_recv(self, data):
        logger.error(f"on_failed_recv - {self._net_id} - {data}")

    def on_disconnected(self, data):
        logger.debug(f"on_disconnected - {self._net_id}")
        self._retry_flag = True

    def start_communication(self):
        logger.debug(f"start_communication - {self._net_id} - wait for connection...")
        self._protocol = create_protocol(params=self._network_config)
        while not self._stop_flag.is_set():
            time.sleep(0.001)
            if self._protocol.connect():
                logger.debug(f"  {self._net_id} - connected !!")
                break

        self._request_queue = queue.Queue()

        # DataPackage를 사용하여 Listener와 Requester에 필요한 정보 전달
        packet_structure_interface = (
            self._data_package.packet_structure if self._data_package else None
        )
        received_data_class = self._data_package.received_data if self._data_package else None

        self._listener = Listener(
            event_callback=self,
            protocol=self._protocol,
            packet_structure_interface=packet_structure_interface,
            received_data_class=received_data_class,
        )

        self._requester = Requester(
            event_callback=self,
            protocol=self._protocol,
            packet_structure_interface=packet_structure_interface,
            request_queue=self._request_queue,
        )

        self._listener.start()
        self._requester.start()

        self._retry_flag = False

    def stop_communications(self):
        if self._listener and hasattr(self._listener, 'is_alive') and self._listener.is_alive():
            self._listener.stop()
            self._listener.join()

        if self._requester and hasattr(self._requester, 'is_alive') and self._requester.is_alive():
            self._requester.stop()
            self._requester.join()

        if isinstance(self._protocol, (ReqResProtocol, PubSubProtocol)):
            self._protocol.disconnect()

    def reconnect(self):
        self.stop_communications()
        self.start_communication()

    def send_data(self, data) -> bool:
        if self._data_package and not isinstance(data, self._data_package.send_data):
            raise ValueError(
                f"Invalid data type. Expected {self._data_package.send_data}, got {type(data)}"
            )

        if not self._request_queue:
            logger.debug(
                f"Request Queue is not initialized. {self._net_id}, May be not connected yet"
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
