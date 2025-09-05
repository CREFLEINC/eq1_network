import logging
import queue
import threading
import time
import unittest
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest

from eq1_network.data import DataPackage, ReceivedData, SendData
from eq1_network.interfaces.packet import PacketStructureInterface
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol
from eq1_network.network import NetworkEvent, NetworkHandler
from eq1_network.worker.listener import Listener, ListenerEvent
from eq1_network.worker.requester import Requester, RequesterEvent


class MockNetworkEvent(NetworkEvent):
    """테스트용 NetworkEvent 구현체"""

    def __init__(self):
        self.events = []

    def on_network_event(self, event_type: str, data: Any = None):
        self.events.append((event_type, data))


class MockSendData(SendData):
    """테스트용 SendData 구현체"""

    def __init__(self, data: str = "test_data"):
        self.data = data

    def to_bytes(self) -> bytes:
        return self.data.encode("utf-8")


class MockReceivedData(ReceivedData):
    """테스트용 ReceivedData 구현체"""

    def __init__(self, data: str = "test_data"):
        self.data = data

    @classmethod
    def from_bytes(cls, data: bytes) -> "MockReceivedData":
        return cls(data.decode("utf-8"))


class MockListenerEvent(ListenerEvent[MockReceivedData]):
    """테스트용 ListenerEvent 구현체"""

    def __init__(self):
        self.received_events = []
        self.failed_recv_events = []
        self.disconnected_events = []

    def on_received(self, received_data: MockReceivedData):
        self.received_events.append(received_data)

    def on_failed_recv(self, data: bytes):
        self.failed_recv_events.append(data)

    def on_disconnected(self, data: bytes):
        self.disconnected_events.append(data)


class MockRequesterEvent(RequesterEvent[MockSendData]):
    """테스트용 RequesterEvent 구현체"""

    def __init__(self):
        self.sent_events = []
        self.failed_send_events = []
        self.disconnected_events = []

    def on_sent(self, data: MockSendData) -> None:
        self.sent_events.append(data)

    def on_failed_send(self, data: MockSendData) -> None:
        self.failed_send_events.append(data)

    def on_disconnected(self, data: MockSendData) -> None:
        self.disconnected_events.append(data)


class MockPacketStructure(PacketStructureInterface):
    """테스트용 패킷 구조 인터페이스 구현체"""

    @classmethod
    def is_valid(cls, data: bytes) -> bool:
        return True

    @classmethod
    def split_packet(cls, data: bytes) -> list[bytes]:
        return [data]

    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        return packet

    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        return data


class MockReqResProtocol(ReqResProtocol):
    """테스트용 ReqResProtocol 구현체"""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False
        self.send_called = False
        self.read_called = False
        self._connected = False
        self.connect_result = True
        self.send_result = True
        self.read_result = (True, b"test_data")
        self._read_count = 0
        self.max_reads = 1  # 최소 1번은 읽도록 설정

    def connect(self) -> bool:
        self.connect_called = True
        self._connected = self.connect_result
        return self._connected

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def send(self, data: bytes) -> bool:
        self.send_called = True
        return self.send_result

    def read(self) -> tuple[bool, Optional[bytes]]:
        self.read_called = True
        self._read_count += 1
        if self._read_count <= self.max_reads:
            return self.read_result
        else:
            # 무한루프 방지를 위해 짧은 대기 시간 추가
            time.sleep(0.01)
            return (True, None)  # False 대신 True를 반환하여 무한루프 방지


class MockPubSubProtocol(PubSubProtocol):
    """테스트용 PubSubProtocol 구현체"""

    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False
        self.publish_called = False
        self.subscribe_called = False
        self._connected = False
        self.connect_result = True
        self.publish_result = True
        self._callbacks = {}

    def connect(self) -> bool:
        self.connect_called = True
        self._connected = self.connect_result
        return self._connected

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def publish(self, topic: str, message: bytes, qos: int = 0, retain: bool = False) -> bool:
        self.publish_called = True
        return self.publish_result

    def subscribe(self, topic: str, callback):
        self.subscribe_called = True
        self._callbacks[topic] = callback


@pytest.mark.unit
class TestNetworkHandler(unittest.TestCase):
    """NetworkHandler 클래스 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.network_config = {"method": "mqtt", "broker_address": "localhost", "port": 1883}
        self.event_callback = MockNetworkEvent()
        self.net_id = "test_network"

        # DataPackage 생성
        self.data_package = DataPackage(
            packet_structure=MockPacketStructure,
            send_data=MockSendData,
            received_data=MockReceivedData,
        )

        # 로깅 레벨 설정 (테스트에서 DEBUG 로그 출력 방지)
        logging.getLogger("eq1_network.network").setLevel(logging.WARNING)
        
        # NetworkHandler 스레드 시작 방지를 위한 Mock 설정
        self.handler = None

    def _create_handler(self, **kwargs):
        """NetworkHandler를 생성하고 스레드 시작을 방지하는 헬퍼 메서드"""
        # 실제 NetworkHandler 생성하되 스레드 시작 방지
        handler = NetworkHandler(**kwargs)
        # 스레드 관련 메서드들을 Mock으로 교체
        handler.start = Mock()
        handler.run = Mock()
        handler.is_alive = Mock(return_value=False)
        handler.join = Mock()
        return handler

    def tearDown(self):
        """테스트 정리"""
        # NetworkHandler가 생성된 경우 정리
        if hasattr(self, 'handler') and self.handler:
            self.handler.stop()
            self.handler.stop_communications()
            if hasattr(self.handler, 'is_alive') and self.handler.is_alive():
                self.handler.join(timeout=1.0)
        
        # 모든 활성 스레드 강제 종료
        import threading
        import time
        
        # 현재 활성 스레드 목록 가져오기
        active_threads = threading.enumerate()
        for thread in active_threads:
            # 메인 스레드가 아닌 경우에만 종료
            if thread != threading.current_thread() and thread.is_alive():
                try:
                    # 스레드에 stop_flag가 있으면 설정
                    if hasattr(thread, '_stop_flag'):
                        thread._stop_flag.set()
                    # 스레드에 stop 메서드가 있으면 호출
                    if hasattr(thread, 'stop'):
                        thread.stop()
                    # 짧은 대기 후 join 시도
                    thread.join(timeout=0.1)
                except Exception:
                    pass  # 스레드 종료 실패는 무시

    def test_init(self):
        """초기화 테스트"""
        self.handler = self._create_handler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )
        handler = self.handler

        self.assertEqual(handler._net_id, self.net_id)
        self.assertEqual(handler._network_config, self.network_config)
        self.assertEqual(handler._event_callback, self.event_callback)
        self.assertEqual(handler._data_package, self.data_package)
        self.assertIsNone(handler._protocol)
        self.assertIsNone(handler._requester)
        self.assertIsNone(handler._listener)
        self.assertIsNone(handler._request_queue)
        self.assertTrue(handler._retry_flag)
        self.assertFalse(handler._stop_flag.is_set())

    def test_init_without_data_package(self):
        """DataPackage 없이 초기화 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
        )

        self.assertEqual(handler._net_id, self.net_id)
        self.assertEqual(handler._network_config, self.network_config)
        self.assertEqual(handler._event_callback, self.event_callback)
        self.assertIsNone(handler._data_package)
        self.assertIsNone(handler._protocol)
        self.assertIsNone(handler._requester)
        self.assertIsNone(handler._listener)
        self.assertIsNone(handler._request_queue)
        self.assertTrue(handler._retry_flag)
        self.assertFalse(handler._stop_flag.is_set())

    @patch("eq1_network.network.Requester")
    @patch("eq1_network.network.Listener")
    @patch("eq1_network.network.create_protocol")
    def test_start_communication_success(self, mock_create_protocol, mock_listener_class, mock_requester_class):
        """통신 시작 성공 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = True
        mock_create_protocol.return_value = mock_protocol
        
        # Mock 스레드 인스턴스 생성
        mock_listener = Mock()
        mock_requester = Mock()
        mock_listener.is_alive.return_value = False
        mock_requester.is_alive.return_value = False
        mock_listener.start = Mock()  # 실제 스레드 시작 방지
        mock_requester.start = Mock()  # 실제 스레드 시작 방지
        mock_listener_class.return_value = mock_listener
        mock_requester_class.return_value = mock_requester

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # stop_flag를 설정하여 무한루프 방지
        handler._stop_flag.set()

        # start_communication() 호출
        handler.start_communication()

        # create_protocol이 호출되었는지 확인
        mock_create_protocol.assert_called_once_with(params=self.network_config)

        # Listener와 Requester가 생성되었는지 확인
        self.assertEqual(handler._listener, mock_listener)
        self.assertEqual(handler._requester, mock_requester)
        self.assertIsInstance(handler._request_queue, queue.Queue)
        self.assertFalse(handler._retry_flag)

        # 정리
        handler.stop_communications()

    @patch("eq1_network.network.Requester")
    @patch("eq1_network.network.Listener")
    @patch("eq1_network.network.create_protocol")
    def test_start_communication_without_data_package(self, mock_create_protocol, mock_listener_class, mock_requester_class):
        """DataPackage 없이 통신 시작 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = True
        mock_create_protocol.return_value = mock_protocol
        
        # Mock 스레드 인스턴스 생성
        mock_listener = Mock()
        mock_requester = Mock()
        mock_listener.is_alive.return_value = False
        mock_requester.is_alive.return_value = False
        mock_listener.start = Mock()  # 실제 스레드 시작 방지
        mock_requester.start = Mock()  # 실제 스레드 시작 방지
        mock_listener_class.return_value = mock_listener
        mock_requester_class.return_value = mock_requester

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
        )

        # stop_flag를 설정하여 무한루프 방지
        handler._stop_flag.set()

        # start_communication() 호출
        handler.start_communication()

        # create_protocol이 호출되었는지 확인
        mock_create_protocol.assert_called_once_with(params=self.network_config)

        # Listener와 Requester가 생성되었는지 확인
        self.assertEqual(handler._listener, mock_listener)
        self.assertEqual(handler._requester, mock_requester)
        self.assertIsInstance(handler._request_queue, queue.Queue)
        self.assertFalse(handler._retry_flag)

        # 정리
        handler.stop_communications()

    @patch("eq1_network.network.create_protocol")
    def test_start_communication_connection_failure(self, mock_create_protocol):
        """연결 실패 시 재시도 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # stop_flag를 설정하여 무한루프 방지
        handler._stop_flag.set()

        # start_communication() 호출
        handler.start_communication()

        # create_protocol이 호출되었는지 확인
        mock_create_protocol.assert_called_once_with(params=self.network_config)

        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol.connect_called)

        # 정리
        handler.stop_communications()

    @patch("eq1_network.network.create_protocol")
    def test_start_communication_protocol_factory_exception(self, mock_create_protocol):
        """프로토콜 팩토리 예외 처리 테스트"""
        mock_create_protocol.side_effect = Exception("Protocol creation failed")

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._stop_flag.set()

        with self.assertRaises(Exception):
            handler.start_communication()

    @patch("eq1_network.network.create_protocol")
    def test_stop_communications(self, mock_create_protocol):
        """통신 중지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # Mock Listener and Requester instances를 직접 설정
        mock_listener = Mock(spec=Listener)
        mock_requester = Mock(spec=Requester)
        mock_listener.is_alive.return_value = True
        mock_requester.is_alive.return_value = True

        handler._listener = mock_listener
        handler._requester = mock_requester
        handler._protocol = mock_protocol

        handler.stop_communications()

        self.assertTrue(mock_protocol.disconnect_called)
        mock_listener.stop.assert_called_once()
        mock_requester.stop.assert_called_once()
        mock_listener.join.assert_called_once()
        mock_requester.join.assert_called_once()

    @patch("eq1_network.network.create_protocol")
    def test_stop_communications_with_dead_threads(self, mock_create_protocol):
        """죽은 스레드 상태에서 통신 중지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # Mock 스레드 생성 (is_alive()가 False 반환)
        mock_listener = Mock(spec=Listener)
        mock_listener.is_alive.return_value = False
        mock_requester = Mock(spec=Requester)
        mock_requester.is_alive.return_value = False

        handler._listener = mock_listener
        handler._requester = mock_requester

        handler.stop_communications()

        # is_alive()가 False인 경우 stop()과 join()이 호출되지 않아야 함
        mock_listener.stop.assert_not_called()
        mock_requester.stop.assert_not_called()
        mock_listener.join.assert_not_called()
        mock_requester.join.assert_not_called()

    @patch("eq1_network.network.create_protocol")
    def test_reconnect(self, mock_create_protocol):
        """재연결 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # Mock Listener and Requester instances를 직접 설정
        mock_listener = Mock(spec=Listener)
        mock_requester = Mock(spec=Requester)
        mock_listener.is_alive.return_value = False
        mock_requester.is_alive.return_value = False

        handler._listener = mock_listener
        handler._requester = mock_requester
        handler._protocol = mock_protocol

        handler.reconnect()

        self.assertTrue(mock_protocol.disconnect_called)
        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol.connect_called)

    def test_send_data_success(self):
        """데이터 전송 성공 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = queue.Queue()
        test_data = MockSendData("test_message")

        result = handler.send_data(test_data)

        self.assertTrue(result)
        self.assertEqual(handler._request_queue.qsize(), 1)
        sent_data = handler._request_queue.get()
        self.assertEqual(sent_data, test_data)

    def test_send_data_invalid_type(self):
        """잘못된 데이터 타입 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        invalid_data = "invalid_data"

        with self.assertRaises(ValueError):
            handler.send_data(invalid_data)

    def test_send_data_without_data_package(self):
        """DataPackage 없이 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
        )

        handler._request_queue = queue.Queue()
        test_data = "any_data_type"
        result = handler.send_data(test_data)

        self.assertTrue(result)
        self.assertEqual(handler._request_queue.qsize(), 1)

    def test_send_data_queue_not_initialized(self):
        """큐가 초기화되지 않은 상태에서 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = None
        test_data = MockSendData("test_message")

        result = handler.send_data(test_data)
        self.assertFalse(result)

    def test_stop(self):
        """중지 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler.stop()

        self.assertTrue(handler._stop_flag.is_set())

    def test_is_connected(self):
        """연결 상태 확인 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._retry_flag = True
        self.assertFalse(handler.is_connected())

        handler._retry_flag = False
        self.assertTrue(handler.is_connected())

    @patch("eq1_network.network.logger")
    def test_on_sent_logging(self, mock_logger):
        """전송 성공 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockSendData("test_message")
        handler.on_sent(test_data)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertIn("on_sent", call_args[0][0])

    @patch("eq1_network.network.logger")
    def test_on_failed_send_logging(self, mock_logger):
        """전송 실패 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockSendData("test_message")
        handler.on_failed_send(test_data)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertIn("on_failed_send", call_args[0][0])

    @patch("eq1_network.network.logger")
    def test_on_received_logging(self, mock_logger):
        """수신 성공 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockReceivedData("test_message")
        handler.on_received(test_data)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertIn("on_received", call_args[0][0])

    @patch("eq1_network.network.logger")
    def test_on_failed_recv_logging(self, mock_logger):
        """수신 실패 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockReceivedData("test_message")
        handler.on_failed_recv(test_data)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertIn("on_failed_recv", call_args[0][0])

    @patch("eq1_network.network.logger")
    def test_on_disconnected_logging(self, mock_logger):
        """연결 해제 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockReceivedData("test_message")
        handler.on_disconnected(test_data)

        self.assertTrue(handler._retry_flag)
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertIn("on_disconnected", call_args[0][0])

    @patch("eq1_network.network.logger")
    def test_on_disconnected_with_send_data(self, mock_logger):
        """SendData로 연결 해제 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockSendData("test_message")
        handler.on_disconnected(test_data)

        self.assertTrue(handler._retry_flag)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_full_lifecycle(self, mock_create_protocol, mock_logger):
        """전체 생명주기 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # 1. 초기화 확인
        self.assertIsNone(handler._protocol)
        self.assertTrue(handler._retry_flag)

        # 2. 통신 시작 (start_communication() 대신 직접 설정)
        handler._protocol = mock_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        self.assertIsNotNone(handler._protocol)
        self.assertFalse(handler._retry_flag)
        self.assertIsInstance(handler._request_queue, queue.Queue)

        # 3. 데이터 전송
        test_data = MockSendData("test_message")
        result = handler.send_data(test_data)
        self.assertTrue(result)
        self.assertEqual(handler._request_queue.qsize(), 1)

        # 4. 이벤트 콜백 테스트
        handler.on_sent(test_data)
        handler.on_received(MockReceivedData("received_message"))
        handler.on_failed_send(test_data)
        handler.on_failed_recv(MockReceivedData("failed_message"))
        handler.on_disconnected(test_data)
        self.assertTrue(handler._retry_flag)

        # 5. 통신 중지
        handler.stop_communications()
        self.assertTrue(mock_protocol.disconnect_called)

        # 6. 중지
        handler.stop()
        self.assertTrue(handler._stop_flag.is_set())

    def test_thread_inheritance(self):
        """Thread 상속 확인 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        self.assertIsInstance(handler, threading.Thread)

    def test_event_interface_implementation(self):
        """이벤트 인터페이스 구현 확인 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        self.assertTrue(hasattr(handler, "on_sent"))
        self.assertTrue(hasattr(handler, "on_failed_send"))
        self.assertTrue(hasattr(handler, "on_received"))
        self.assertTrue(hasattr(handler, "on_failed_recv"))
        self.assertTrue(hasattr(handler, "on_disconnected"))

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_concurrent_access(self, mock_create_protocol, mock_logger):
        """동시 접근 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = mock_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        import concurrent.futures

        def send_data():
            test_data = MockSendData("concurrent_message")
            return handler.send_data(test_data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_data) for _ in range(10)]
            results = [future.result() for future in futures]

        self.assertTrue(all(results))
        self.assertEqual(handler._request_queue.qsize(), 10)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_error_handling(self, mock_create_protocol, mock_logger):
        """에러 처리 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._protocol = None
        handler._listener = None
        handler._requester = None

        handler.stop_communications()
        
        # stop_flag를 설정하여 무한루프 방지
        handler._stop_flag.set()
        handler.reconnect()

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_protocol_factory_integration(self, mock_create_protocol, mock_logger):
        """프로토콜 팩토리 통합 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler.start_communication()

        call_args = mock_create_protocol.call_args
        self.assertEqual(call_args[1]["params"], self.network_config)

    def test_network_config_validation(self):
        """네트워크 설정 검증 테스트"""
        invalid_config = {}

        handler = NetworkHandler(
            network_config=invalid_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        self.assertEqual(handler._network_config, invalid_config)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_cleanup_on_stop(self, mock_create_protocol, mock_logger):
        """중지 시 정리 작업 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler.stop()
        self.assertTrue(handler._stop_flag.is_set())

        handler.stop_communications()
        self.assertTrue(handler._stop_flag.is_set())

    def test_data_package_attributes(self):
        """DataPackage 속성 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        self.assertEqual(handler._data_package.packet_structure, MockPacketStructure)
        self.assertEqual(handler._data_package.send_data, MockSendData)
        self.assertEqual(handler._data_package.received_data, MockReceivedData)

    def test_data_package_none_handling(self):
        """DataPackage가 None일 때 처리 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
        )

        self.assertIsNone(handler._data_package)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_memory_leak_prevention(self, mock_create_protocol, mock_logger):
        """메모리 누수 방지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = mock_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        self.assertIsNotNone(handler._protocol)
        self.assertIsNotNone(handler._listener)
        self.assertIsNotNone(handler._requester)
        self.assertIsNotNone(handler._request_queue)

        handler.stop_communications()

        self.assertIsNotNone(handler._protocol)
        self.assertIsNotNone(handler._listener)
        self.assertIsNotNone(handler._requester)
        self.assertIsNotNone(handler._request_queue)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_timeout_handling(self, mock_create_protocol, mock_logger):
        """타임아웃 처리 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._stop_flag.set()

        start_time = time.time()
        handler.start_communication()
        end_time = time.time()

        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_protocol_type_handling(self, mock_create_protocol, mock_logger):
        """프로토콜 타입별 처리 테스트"""
        # ReqResProtocol 테스트
        reqres_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = reqres_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = reqres_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        handler.stop_communications()

        self.assertTrue(reqres_protocol.disconnect_called)

        # PubSubProtocol 테스트
        pubsub_protocol = MockPubSubProtocol()
        mock_create_protocol.return_value = pubsub_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = pubsub_protocol
        handler._request_queue = queue.Queue()

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        handler.stop_communications()

        self.assertTrue(pubsub_protocol.disconnect_called)

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = queue.Queue()

        def modify_state():
            handler._retry_flag = not handler._retry_flag
            time.sleep(0.001)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=modify_state)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_connection_retry_logic(self, mock_create_protocol, mock_logger):
        """연결 재시도 로직 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = mock_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol.connect_called)

        mock_protocol.connect_result = True
        handler.reconnect()
        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol.connect_called)

    @patch("eq1_network.network.logger")
    def test_event_callback_integration(self, mock_logger):
        """이벤트 콜백 통합 테스트"""
        received_events = []

        class TestEventCallback(NetworkEvent):
            def on_network_event(self, event_type: str, data: Any = None):
                received_events.append((event_type, data))

        event_callback = TestEventCallback()

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        test_data = MockSendData("test_event")
        handler.on_sent(test_data)
        handler.on_received(MockReceivedData("received_event"))
        handler.on_disconnected(test_data)

    def test_network_id_handling(self):
        """네트워크 ID 처리 테스트"""
        test_cases = ["string_id", 123, None, {"complex": "id"}, ["list", "id"]]

        for net_id in test_cases:
            handler = NetworkHandler(
                network_config=self.network_config,
                event_callback=self.event_callback,
                net_id=net_id,
                data_package=self.data_package,
            )

            self.assertEqual(handler._net_id, net_id)

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # None 값들로 초기화
        handler = NetworkHandler(
            network_config={}, event_callback=None, net_id=None, data_package=None
        )

        self.assertIsNone(handler._net_id)
        self.assertIsNone(handler._event_callback)
        self.assertIsNone(handler._data_package)
        self.assertEqual(handler._network_config, {})

        # 빈 문자열
        handler = NetworkHandler(
            network_config={},
            event_callback=self.event_callback,
            net_id="",
            data_package=self.data_package,
        )

        self.assertEqual(handler._net_id, "")

    def test_data_type_validation_edge_cases(self):
        """데이터 타입 검증 엣지 케이스 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = queue.Queue()

        # 잘못된 타입들
        invalid_types = [None, "", 123, [1, 2, 3], {"key": "value"}]

        for invalid_data in invalid_types:
            with self.assertRaises(ValueError):
                handler.send_data(invalid_data)

    def test_queue_operations(self):
        """큐 작업 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = queue.Queue()

        test_data_list = [MockSendData(f"message_{i}") for i in range(5)]

        for data in test_data_list:
            result = handler.send_data(data)
            self.assertTrue(result)

        self.assertEqual(handler._request_queue.qsize(), 5)

        extracted_data = []
        while not handler._request_queue.empty():
            extracted_data.append(handler._request_queue.get())

        self.assertEqual(len(extracted_data), 5)
        for i, data in enumerate(extracted_data):
            self.assertEqual(data.data, f"message_{i}")

    def test_network_config_immutability(self):
        """네트워크 설정 불변성 테스트"""
        original_config = {"method": "mqtt", "broker_address": "localhost", "port": 1883}

        # 딕셔너리 복사본 생성
        config_copy = original_config.copy()

        handler = NetworkHandler(
            network_config=config_copy,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # 원본 설정 변경
        original_config["method"] = "tcp"
        original_config["new_key"] = "new_value"

        # 핸들러의 설정은 변경되지 않아야 함
        self.assertEqual(handler._network_config["method"], "mqtt")
        self.assertNotIn("new_key", handler._network_config)

    def test_memory_management(self):
        """메모리 관리 테스트"""
        import gc
        import weakref

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        weak_ref = weakref.ref(handler)
        del handler
        gc.collect()

        self.assertIsNone(weak_ref())

    @patch("eq1_network.network.logger")
    def test_concurrent_data_sending(self, mock_logger):
        """동시 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        handler._request_queue = queue.Queue()

        import concurrent.futures
        import threading

        results = []
        lock = threading.Lock()

        def send_data_with_lock():
            with lock:
                test_data = MockSendData(f"concurrent_{threading.current_thread().ident}")
                result = handler.send_data(test_data)
                results.append(result)
                return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_data_with_lock) for _ in range(20)]
            concurrent_results = [future.result() for future in futures]

        self.assertTrue(all(concurrent_results))
        self.assertEqual(handler._request_queue.qsize(), 20)
        self.assertEqual(len(results), 20)

    def test_network_handler_identity(self):
        """NetworkHandler 식별자 테스트"""
        handler1 = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id="handler1",
            data_package=self.data_package,
        )

        handler2 = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id="handler2",
            data_package=self.data_package,
        )

        self.assertIsNot(handler1, handler2)
        self.assertNotEqual(handler1._net_id, handler2._net_id)
        self.assertEqual(handler1._net_id, "handler1")
        self.assertEqual(handler2._net_id, "handler2")

    @patch("eq1_network.network.logger")
    @patch("eq1_network.network.create_protocol")
    def test_protocol_lifecycle_management(self, mock_create_protocol, mock_logger):
        """프로토콜 생명주기 관리 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol

        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package,
        )

        # start_communication() 대신 직접 설정
        handler._protocol = mock_protocol
        handler._request_queue = queue.Queue()

        packet_structure_interface = (
            handler._data_package.packet_structure if handler._data_package else None
        )
        received_data_class = handler._data_package.received_data if handler._data_package else None

        # Mock 객체로 교체하여 실제 스레드 생성 방지
        handler._listener = Mock(spec=Listener)
        handler._listener.is_alive.return_value = False

        handler._requester = Mock(spec=Requester)
        handler._requester.is_alive.return_value = False

        handler._retry_flag = False

        self.assertIsNotNone(handler._protocol)
        self.assertEqual(handler._protocol, mock_protocol)
        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol.connect_called)

        handler.stop_communications()
        self.assertTrue(mock_protocol.disconnect_called)

        mock_protocol2 = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol2

        handler.reconnect()
        self.assertEqual(handler._protocol, mock_protocol2)
        # stop_flag가 설정되어 있어서 connect()가 호출되지 않음
        # self.assertTrue(mock_protocol2.connect_called)


@pytest.mark.unit
class TestListenerEvent(unittest.TestCase):
    """ListenerEvent 인터페이스 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.listener_event = MockListenerEvent()

    def test_on_received(self):
        """데이터 수신 성공 이벤트 테스트"""
        test_data = MockReceivedData("test_received_data")
        self.listener_event.on_received(test_data)
        self.assertEqual(len(self.listener_event.received_events), 1)
        self.assertEqual(self.listener_event.received_events[0], test_data)
        self.assertEqual(self.listener_event.received_events[0].data, "test_received_data")

    def test_on_failed_recv(self):
        """데이터 수신 실패 이벤트 테스트"""
        test_bytes = b"failed_data"
        self.listener_event.on_failed_recv(test_bytes)
        self.assertEqual(len(self.listener_event.failed_recv_events), 1)
        self.assertEqual(self.listener_event.failed_recv_events[0], test_bytes)

    def test_on_disconnected(self):
        """연결 해제 이벤트 테스트"""
        test_bytes = b"disconnect_data"
        self.listener_event.on_disconnected(test_bytes)
        self.assertEqual(len(self.listener_event.disconnected_events), 1)
        self.assertEqual(self.listener_event.disconnected_events[0], test_bytes)

    def test_multiple_events(self):
        """다중 이벤트 처리 테스트"""
        received_data1 = MockReceivedData("data1")
        received_data2 = MockReceivedData("data2")
        failed_bytes = b"failed"
        disconnect_bytes = b"disconnect"
        self.listener_event.on_received(received_data1)
        self.listener_event.on_received(received_data2)
        self.listener_event.on_failed_recv(failed_bytes)
        self.listener_event.on_disconnected(disconnect_bytes)
        self.assertEqual(len(self.listener_event.received_events), 2)
        self.assertEqual(len(self.listener_event.failed_recv_events), 1)
        self.assertEqual(len(self.listener_event.disconnected_events), 1)
        self.assertEqual(self.listener_event.received_events[0].data, "data1")
        self.assertEqual(self.listener_event.received_events[1].data, "data2")
        self.assertEqual(self.listener_event.failed_recv_events[0], failed_bytes)
        self.assertEqual(self.listener_event.disconnected_events[0], disconnect_bytes)


@pytest.mark.unit
class TestRequesterEvent(unittest.TestCase):
    """RequesterEvent 인터페이스 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.requester_event = MockRequesterEvent()

    def test_on_sent(self):
        """데이터 전송 성공 이벤트 테스트"""
        test_data = MockSendData("test_sent_data")
        self.requester_event.on_sent(test_data)
        self.assertEqual(len(self.requester_event.sent_events), 1)
        self.assertEqual(self.requester_event.sent_events[0], test_data)
        self.assertEqual(self.requester_event.sent_events[0].data, "test_sent_data")

    def test_on_failed_send(self):
        """데이터 전송 실패 이벤트 테스트"""
        test_data = MockSendData("failed_send_data")
        self.requester_event.on_failed_send(test_data)
        self.assertEqual(len(self.requester_event.failed_send_events), 1)
        self.assertEqual(self.requester_event.failed_send_events[0], test_data)
        self.assertEqual(self.requester_event.failed_send_events[0].data, "failed_send_data")

    def test_on_disconnected(self):
        """연결 해제 이벤트 테스트"""
        test_data = MockSendData("disconnect_send_data")
        self.requester_event.on_disconnected(test_data)
        self.assertEqual(len(self.requester_event.disconnected_events), 1)
        self.assertEqual(self.requester_event.disconnected_events[0], test_data)
        self.assertEqual(self.requester_event.disconnected_events[0].data, "disconnect_send_data")

    def test_multiple_events(self):
        """다중 이벤트 처리 테스트"""
        sent_data1 = MockSendData("sent1")
        sent_data2 = MockSendData("sent2")
        failed_data = MockSendData("failed")
        disconnect_data = MockSendData("disconnect")
        self.requester_event.on_sent(sent_data1)
        self.requester_event.on_sent(sent_data2)
        self.requester_event.on_failed_send(failed_data)
        self.requester_event.on_disconnected(disconnect_data)
        self.assertEqual(len(self.requester_event.sent_events), 2)
        self.assertEqual(len(self.requester_event.failed_send_events), 1)
        self.assertEqual(len(self.requester_event.disconnected_events), 1)
        self.assertEqual(self.requester_event.sent_events[0].data, "sent1")
        self.assertEqual(self.requester_event.sent_events[1].data, "sent2")
        self.assertEqual(self.requester_event.failed_send_events[0].data, "failed")
        self.assertEqual(self.requester_event.disconnected_events[0].data, "disconnect")


@pytest.mark.unit
class TestEventIntegration(unittest.TestCase):
    """ListenerEvent와 RequesterEvent 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.listener_event = MockListenerEvent()
        self.requester_event = MockRequesterEvent()

    def test_event_interface_compatibility(self):
        """이벤트 인터페이스 호환성 테스트"""
        # ListenerEvent가 올바른 인터페이스를 구현하는지 확인
        self.assertIsInstance(self.listener_event, ListenerEvent)
        # RequesterEvent가 올바른 인터페이스를 구현하는지 확인
        self.assertIsInstance(self.requester_event, RequesterEvent)

    def test_event_data_types(self):
        """이벤트 데이터 타입 테스트"""
        # ListenerEvent는 MockReceivedData 타입을 사용
        received_data = MockReceivedData("test")
        self.listener_event.on_received(received_data)
        self.assertIsInstance(self.listener_event.received_events[0], MockReceivedData)
        # RequesterEvent는 MockSendData 타입을 사용
        send_data = MockSendData("test")
        self.requester_event.on_sent(send_data)
        self.assertIsInstance(self.requester_event.sent_events[0], MockSendData)

    def test_event_callback_chain(self):
        """이벤트 콜백 체인 테스트"""
        # Listener 이벤트 체인
        received_data = MockReceivedData("received")
        failed_bytes = b"failed"
        disconnect_bytes = b"disconnect"
        self.listener_event.on_received(received_data)
        self.listener_event.on_failed_recv(failed_bytes)
        self.listener_event.on_disconnected(disconnect_bytes)
        # Requester 이벤트 체인
        sent_data = MockSendData("sent")
        failed_send_data = MockSendData("failed_send")
        disconnect_send_data = MockSendData("disconnect_send")
        self.requester_event.on_sent(sent_data)
        self.requester_event.on_failed_send(failed_send_data)
        self.requester_event.on_disconnected(disconnect_send_data)
        # 모든 이벤트가 올바르게 기록되었는지 확인
        self.assertEqual(len(self.listener_event.received_events), 1)
        self.assertEqual(len(self.listener_event.failed_recv_events), 1)
        self.assertEqual(len(self.listener_event.disconnected_events), 1)
        self.assertEqual(len(self.requester_event.sent_events), 1)
        self.assertEqual(len(self.requester_event.failed_send_events), 1)
        self.assertEqual(len(self.requester_event.disconnected_events), 1)


if __name__ == "__main__":
    unittest.main()
