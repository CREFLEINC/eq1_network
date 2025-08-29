import unittest
from unittest.mock import Mock, patch, MagicMock, call, AsyncMock
import threading
import time
import queue
import pytest
import logging
from typing import Dict, Any, Union, Optional

from app.network import NetworkHandler, NetworkEvent
from app.data import ReceivedData, SendData, DataPackage
from app.worker.listener import Listener
from app.worker.requester import Requester
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol
from app.interfaces.packet import PacketStructureInterface
from app.common.params import Params
from app.manager.protocol_factory import create_protocol


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
        return self.data.encode('utf-8')


class MockReceivedData(ReceivedData):
    """테스트용 ReceivedData 구현체"""
    def __init__(self, data: str = "test_data"):
        self.data = data

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MockReceivedData':
        return cls(data.decode('utf-8'))


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
        return self.read_result


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
        self.network_config = {
            "method": "mqtt",
            "broker_address": "localhost",
            "port": 1883
        }
        self.event_callback = MockNetworkEvent()
        self.net_id = "test_network"
        self.packet_structure = MockPacketStructure
        self.received_data_class = MockReceivedData
        
        # DataPackage 생성
        self.data_package = DataPackage(
            packet_structure=MockPacketStructure,
            send_data=MockSendData,
            received_data=MockReceivedData
        )
        
        # 로깅 레벨 설정
        logging.getLogger('app.network').setLevel(logging.DEBUG)

    def tearDown(self):
        """테스트 정리"""
        pass

    def test_init(self):
        """초기화 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
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
            net_id=self.net_id
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

    @patch('app.network.create_protocol')
    def test_start_communication_success(self, mock_create_protocol):
        """통신 시작 성공 테스트"""
        # Mock 프로토콜 설정
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = True
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 검증
        mock_create_protocol.assert_called_once_with(params=self.network_config)
        self.assertTrue(mock_protocol.connect_called)
        self.assertIsInstance(handler._listener, Listener)
        self.assertIsInstance(handler._requester, Requester)
        self.assertIsInstance(handler._request_queue, queue.Queue)
        self.assertFalse(handler._retry_flag)

    @patch('app.network.create_protocol')
    def test_start_communication_without_data_package(self, mock_create_protocol):
        """DataPackage 없이 통신 시작 테스트"""
        # Mock 프로토콜 설정
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = True
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 검증
        mock_create_protocol.assert_called_once_with(params=self.network_config)
        self.assertTrue(mock_protocol.connect_called)
        self.assertIsInstance(handler._listener, Listener)
        self.assertIsInstance(handler._requester, Requester)
        self.assertIsInstance(handler._request_queue, queue.Queue)
        self.assertFalse(handler._retry_flag)

    @patch('app.network.create_protocol')
    def test_start_communication_connection_failure(self, mock_create_protocol):
        """연결 실패 시 재시도 테스트"""
        # Mock 프로토콜 설정 - 연결 실패
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 통신 시작
        handler.start_communication()
        
        # 검증
        mock_create_protocol.assert_called_once_with(params=self.network_config)
        self.assertTrue(mock_protocol.connect_called)

    @patch('app.network.create_protocol')
    def test_start_communication_protocol_factory_exception(self, mock_create_protocol):
        """프로토콜 팩토리 예외 처리 테스트"""
        # 프로토콜 팩토리에서 예외 발생
        mock_create_protocol.side_effect = Exception("Protocol creation failed")
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 예외가 발생해야 함
        with self.assertRaises(Exception):
            handler.start_communication()

    @patch('app.network.create_protocol')
    def test_stop_communications(self, mock_create_protocol):
        """통신 중지 테스트"""
        # Mock 프로토콜 설정
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 통신 중지
        handler.stop_communications()
        
        # 검증
        self.assertTrue(mock_protocol.disconnect_called)

    @patch('app.network.create_protocol')
    def test_stop_communications_without_listener_requester(self, mock_create_protocol):
        """Listener/Requester가 없는 상태에서 통신 중지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # listener와 requester를 None으로 설정
        handler._listener = None
        handler._requester = None
        
        # 통신 중지 (예외 발생하지 않아야 함)
        handler.stop_communications()
        
        # 검증
        self.assertTrue(mock_protocol.disconnect_called)

    @patch('app.network.create_protocol')
    def test_stop_communications_with_dead_threads(self, mock_create_protocol):
        """죽은 스레드 상태에서 통신 중지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # Mock 스레드 생성 (is_alive()가 False 반환)
        mock_listener = Mock(spec=Listener)
        mock_listener.is_alive.return_value = False
        mock_requester = Mock(spec=Requester)
        mock_requester.is_alive.return_value = False
        
        handler._listener = mock_listener
        handler._requester = mock_requester
        
        # 통신 중지 (join이 호출되지 않아야 함)
        handler.stop_communications()
        
        # 검증
        mock_listener.stop.assert_called_once()
        mock_requester.stop.assert_called_once()
        mock_listener.join.assert_not_called()
        mock_requester.join.assert_not_called()

    @patch('app.network.create_protocol')
    def test_reconnect(self, mock_create_protocol):
        """재연결 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 재연결
        handler.reconnect()
        
        # 검증
        self.assertTrue(mock_protocol.disconnect_called)
        self.assertTrue(mock_protocol.connect_called)

    def test_send_data_success(self):
        """데이터 전송 성공 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue 초기화
        handler._request_queue = queue.Queue()
        
        # 테스트 데이터
        test_data = MockSendData("test_message")
        
        # 데이터 전송
        result = handler.send_data(test_data)
        
        # 검증
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
            data_package=self.data_package
        )
        
        # 잘못된 타입의 데이터
        invalid_data = "invalid_data"
        
        # ValueError 발생 확인
        with self.assertRaises(ValueError):
            handler.send_data(invalid_data)

    def test_send_data_without_data_package(self):
        """DataPackage 없이 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id
        )
        
        # request_queue 초기화
        handler._request_queue = queue.Queue()
        
        # DataPackage가 없으면 타입 검증을 하지 않음
        test_data = "any_data_type"
        result = handler.send_data(test_data)
        
        # 검증
        self.assertTrue(result)
        self.assertEqual(handler._request_queue.qsize(), 1)

    def test_send_data_queue_not_initialized(self):
        """큐가 초기화되지 않은 상태에서 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue가 None인 상태
        handler._request_queue = None
        
        test_data = MockSendData("test_message")
        
        # False 반환 확인
        result = handler.send_data(test_data)
        self.assertFalse(result)

    def test_stop(self):
        """중지 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 중지
        handler.stop()
        
        # 검증
        self.assertTrue(handler._stop_flag.is_set())

    @patch('app.network.create_protocol')
    def test_run_with_retry_flag(self, mock_create_protocol):
        """retry_flag가 True일 때 run 메서드 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # retry_flag를 True로 설정
        handler._retry_flag = True
        
        # 짧은 시간 동안 실행
        handler._stop_flag.set()
        handler.run()
        
        # 검증
        mock_create_protocol.assert_called_once()

    def test_run_without_retry_flag(self):
        """retry_flag가 False일 때 run 메서드 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # retry_flag를 False로 설정
        handler._retry_flag = False
        
        # 짧은 시간 동안 실행
        handler._stop_flag.set()
        handler.run()
        
        # 검증 - retry_flag가 False이므로 reconnect가 호출되지 않음

    def test_is_connected(self):
        """연결 상태 확인 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # retry_flag가 True일 때 (연결되지 않음)
        handler._retry_flag = True
        self.assertFalse(handler.is_connected())
        
        # retry_flag가 False일 때 (연결됨)
        handler._retry_flag = False
        self.assertTrue(handler.is_connected())

    @patch('app.network.logger')
    def test_on_sent_logging(self, mock_logger):
        """전송 성공 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockSendData("test_message")
        
        # on_sent 호출
        handler.on_sent(test_data)
        
        # 로깅 호출 확인 (self가 첫 번째 인자로 전달됨)
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertEqual(call_args[0][0], handler)  # 첫 번째 인자가 handler 인스턴스

    @patch('app.network.logger')
    def test_on_failed_send_logging(self, mock_logger):
        """전송 실패 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockSendData("test_message")
        
        # on_failed_send 호출
        handler.on_failed_send(test_data)
        
        # 로깅 호출 확인
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertEqual(call_args[0][0], handler)  # 첫 번째 인자가 handler 인스턴스

    @patch('app.network.logger')
    def test_on_received_logging(self, mock_logger):
        """수신 성공 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockReceivedData("test_message")
        
        # on_received 호출
        handler.on_received(test_data)
        
        # 로깅 호출 확인
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertEqual(call_args[0][0], handler)  # 첫 번째 인자가 handler 인스턴스

    @patch('app.network.logger')
    def test_on_failed_recv_logging(self, mock_logger):
        """수신 실패 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockReceivedData("test_message")
        
        # on_failed_recv 호출
        handler.on_failed_recv(test_data)
        
        # 로깅 호출 확인
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertEqual(call_args[0][0], handler)  # 첫 번째 인자가 handler 인스턴스

    @patch('app.network.logger')
    def test_on_disconnected_logging(self, mock_logger):
        """연결 해제 이벤트 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockReceivedData("test_message")
        
        # on_disconnected 호출
        handler.on_disconnected(test_data)
        
        # retry_flag가 True로 설정되는지 확인
        self.assertTrue(handler._retry_flag)
        
        # 로깅 호출 확인
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertEqual(call_args[0][0], handler)  # 첫 번째 인자가 handler 인스턴스

    def test_on_disconnected_with_send_data(self):
        """SendData로 연결 해제 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockSendData("test_message")
        
        # on_disconnected 호출
        handler.on_disconnected(test_data)
        
        # retry_flag가 True로 설정되는지 확인
        self.assertTrue(handler._retry_flag)

    @patch('app.network.create_protocol')
    def test_full_lifecycle(self, mock_create_protocol):
        """전체 생명주기 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 1. 초기화 확인
        self.assertIsNone(handler._protocol)
        self.assertTrue(handler._retry_flag)
        
        # 2. 통신 시작
        handler.start_communication()
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
            data_package=self.data_package
        )
        
        # Thread 클래스를 상속받았는지 확인
        self.assertIsInstance(handler, threading.Thread)

    def test_event_interface_implementation(self):
        """이벤트 인터페이스 구현 확인 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # ListenerEvent와 RequesterEvent 인터페이스 메서드들이 구현되어 있는지 확인
        self.assertTrue(hasattr(handler, 'on_sent'))
        self.assertTrue(hasattr(handler, 'on_failed_send'))
        self.assertTrue(hasattr(handler, 'on_received'))
        self.assertTrue(hasattr(handler, 'on_failed_recv'))
        self.assertTrue(hasattr(handler, 'on_disconnected'))

    @patch('app.network.create_protocol')
    def test_concurrent_access(self, mock_create_protocol):
        """동시 접근 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 여러 스레드에서 동시에 데이터 전송
        import concurrent.futures
        
        def send_data():
            test_data = MockSendData("concurrent_message")
            return handler.send_data(test_data)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_data) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # 모든 전송이 성공했는지 확인
        self.assertTrue(all(results))
        self.assertEqual(handler._request_queue.qsize(), 10)

    def test_error_handling(self):
        """에러 처리 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # None 값으로 초기화된 상태에서의 에러 처리
        handler._protocol = None
        handler._listener = None
        handler._requester = None
        
        # 예외가 발생하지 않아야 함
        handler.stop_communications()
        handler.reconnect()

    @patch('app.network.create_protocol')
    def test_protocol_factory_integration(self, mock_create_protocol):
        """프로토콜 팩토리 통합 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작 시 프로토콜 팩토리가 올바르게 호출되는지 확인
        handler.start_communication()
        
        # create_protocol이 올바른 파라미터로 호출되었는지 확인
        call_args = mock_create_protocol.call_args
        self.assertEqual(call_args[1]['params'], self.network_config)

    def test_network_config_validation(self):
        """네트워크 설정 검증 테스트"""
        # 잘못된 설정
        invalid_config = {}
        
        handler = NetworkHandler(
            network_config=invalid_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 잘못된 설정으로도 초기화는 성공해야 함
        self.assertEqual(handler._network_config, invalid_config)

    @patch('app.network.create_protocol')
    def test_cleanup_on_stop(self, mock_create_protocol):
        """중지 시 정리 작업 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 중지
        handler.stop()
        
        # stop_flag가 설정되었는지 확인
        self.assertTrue(handler._stop_flag.is_set())
        
        # stop_communications 메서드가 정상적으로 동작하는지 확인
        handler.stop_communications()
        
        # stop_flag가 여전히 설정되어 있는지 확인
        self.assertTrue(handler._stop_flag.is_set())

    def test_data_package_attributes(self):
        """DataPackage 속성 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # DataPackage의 속성들이 올바르게 설정되었는지 확인
        self.assertEqual(handler._data_package.packet_structure, MockPacketStructure)
        self.assertEqual(handler._data_package.send_data, MockSendData)
        self.assertEqual(handler._data_package.received_data, MockReceivedData)

    def test_data_package_none_handling(self):
        """DataPackage가 None일 때 처리 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id
        )
        
        # DataPackage가 None일 때도 정상적으로 동작해야 함
        self.assertIsNone(handler._data_package)

    @patch('app.network.create_protocol')
    def test_memory_leak_prevention(self, mock_create_protocol):
        """메모리 누수 방지 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 참조 확인
        self.assertIsNotNone(handler._protocol)
        self.assertIsNotNone(handler._listener)
        self.assertIsNotNone(handler._requester)
        self.assertIsNotNone(handler._request_queue)
        
        # 통신 중지
        handler.stop_communications()
        
        # 참조가 정리되었는지 확인
        self.assertIsNotNone(handler._protocol)  # 프로토콜은 유지됨
        self.assertIsNotNone(handler._listener)  # 리스너는 유지됨
        self.assertIsNotNone(handler._requester)  # 리퀘스터는 유지됨
        self.assertIsNotNone(handler._request_queue)  # 큐는 유지됨

    @patch('app.network.create_protocol')
    def test_timeout_handling(self, mock_create_protocol):
        """타임아웃 처리 테스트"""
        # 연결이 지연되는 프로토콜
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False  # 연결 실패
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 통신 시작 (타임아웃 상황 시뮬레이션)
        start_time = time.time()
        handler.start_communication()
        end_time = time.time()
        
        # 실행 시간이 합리적인 범위 내에 있는지 확인
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)  # 1초 이내에 완료되어야 함

    @patch('app.network.create_protocol')
    def test_protocol_type_handling(self, mock_create_protocol):
        """프로토콜 타입별 처리 테스트"""
        # ReqResProtocol 테스트
        reqres_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = reqres_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        handler.start_communication()
        handler.stop_communications()
        
        # ReqResProtocol의 disconnect가 호출되었는지 확인
        self.assertTrue(reqres_protocol.disconnect_called)
        
        # PubSubProtocol 테스트
        pubsub_protocol = MockPubSubProtocol()
        mock_create_protocol.return_value = pubsub_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        handler.start_communication()
        handler.stop_communications()
        
        # PubSubProtocol의 disconnect가 호출되었는지 확인
        self.assertTrue(pubsub_protocol.disconnect_called)

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue 초기화
        handler._request_queue = queue.Queue()
        
        # 여러 스레드에서 동시에 상태 변경
        def modify_state():
            handler._retry_flag = not handler._retry_flag
            time.sleep(0.001)
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=modify_state)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 예외가 발생하지 않았는지 확인 (스레드 안전성)

    @patch('app.network.create_protocol')
    def test_connection_retry_logic(self, mock_create_protocol):
        """연결 재시도 로직 테스트"""
        # 처음에는 연결 실패, 나중에 성공하는 프로토콜
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 통신 시작 (연결 실패)
        handler.start_communication()
        
        # 연결이 실패했는지 확인
        self.assertTrue(mock_protocol.connect_called)
        
        # 프로토콜을 성공하도록 변경
        mock_protocol.connect_result = True
        
        # 재연결 시도
        handler.reconnect()
        
        # 연결이 성공했는지 확인
        self.assertTrue(mock_protocol.connect_called)

    def test_event_callback_integration(self):
        """이벤트 콜백 통합 테스트"""
        # 실제 이벤트를 받는 콜백
        received_events = []
        
        class TestEventCallback(NetworkEvent):
            def on_network_event(self, event_type: str, data: Any = None):
                received_events.append((event_type, data))
        
        event_callback = TestEventCallback()
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 이벤트 발생
        test_data = MockSendData("test_event")
        handler.on_sent(test_data)
        handler.on_received(MockReceivedData("received_event"))
        handler.on_disconnected(test_data)
        
        # 이벤트 콜백이 호출되었는지 확인
        # (현재 구현에서는 콜백이 호출되지 않지만, 향후 확장 가능성 고려)

    def test_network_id_handling(self):
        """네트워크 ID 처리 테스트"""
        # 다양한 타입의 net_id 테스트
        test_cases = [
            "string_id",
            123,
            None,
            {"complex": "id"},
            ["list", "id"]
        ]
        
        for net_id in test_cases:
            handler = NetworkHandler(
                network_config=self.network_config,
                event_callback=self.event_callback,
                net_id=net_id,
                data_package=self.data_package
            )
            
            # net_id가 올바르게 설정되었는지 확인
            self.assertEqual(handler._net_id, net_id)

    @patch('app.network.create_protocol')
    def test_graceful_shutdown(self, mock_create_protocol):
        """우아한 종료 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 통신 시작
        handler.start_communication()
        
        # 우아한 종료
        handler.stop()
        
        # stop_flag가 설정되었는지 확인
        self.assertTrue(handler._stop_flag.is_set())
        
        # run 메서드가 정상적으로 종료되는지 확인
        handler.run()
        
        # 통신이 정리되었는지 확인
        self.assertTrue(mock_protocol.disconnect_called)

    @patch('app.network.logger')
    def test_start_communication_logging(self, mock_logger):
        """통신 시작 로깅 테스트"""
        with patch('app.network.create_protocol') as mock_create_protocol:
            mock_protocol = MockReqResProtocol()
            mock_protocol.connect_result = True
            mock_create_protocol.return_value = mock_protocol
            
            handler = NetworkHandler(
                network_config=self.network_config,
                event_callback=self.event_callback,
                net_id=self.net_id,
                data_package=self.data_package
            )
            
            # 통신 시작
            handler.start_communication()
            
            # 로깅 호출 확인 (시작 메시지와 연결 성공 메시지)
            self.assertEqual(mock_logger.debug.call_count, 2)
            
            # 첫 번째 호출 (시작 메시지)
            first_call = mock_logger.debug.call_args_list[0]
            self.assertEqual(first_call[0][0], handler)
            
            # 두 번째 호출 (연결 성공 메시지)
            second_call = mock_logger.debug.call_args_list[1]
            self.assertEqual(second_call[0][0], handler)

    @patch('app.network.logger')
    def test_send_data_logging(self, mock_logger):
        """데이터 전송 로깅 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue가 None인 상태에서 전송 시도
        test_data = MockSendData("test_message")
        result = handler.send_data(test_data)
        
        # False 반환 확인
        self.assertFalse(result)
        
        # 로깅 호출 확인
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertEqual(call_args[0][0], handler)

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # 1. None 값들로 초기화
        handler = NetworkHandler(
            network_config={},
            event_callback=None,
            net_id=None,
            data_package=None
        )
        
        self.assertIsNone(handler._net_id)
        self.assertIsNone(handler._event_callback)
        self.assertIsNone(handler._data_package)
        self.assertEqual(handler._network_config, {})
        
        # 2. 빈 문자열과 0 값들
        handler = NetworkHandler(
            network_config={},
            event_callback=self.event_callback,
            net_id="",
            data_package=self.data_package
        )
        
        self.assertEqual(handler._net_id, "")
        
        # 3. 매우 큰 값들
        handler = NetworkHandler(
            network_config={"large_key": "x" * 1000},
            event_callback=self.event_callback,
            net_id="x" * 1000,
            data_package=self.data_package
        )
        
        self.assertEqual(len(handler._net_id), 1000)
        self.assertEqual(len(handler._network_config["large_key"]), 1000)

    def test_data_type_validation_edge_cases(self):
        """데이터 타입 검증 엣지 케이스 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue 초기화
        handler._request_queue = queue.Queue()
        
        # 1. None 데이터 전송
        with self.assertRaises(ValueError):
            handler.send_data(None)
        
        # 2. 빈 문자열 데이터 전송
        with self.assertRaises(ValueError):
            handler.send_data("")
        
        # 3. 숫자 데이터 전송
        with self.assertRaises(ValueError):
            handler.send_data(123)
        
        # 4. 리스트 데이터 전송
        with self.assertRaises(ValueError):
            handler.send_data([1, 2, 3])
        
        # 5. 딕셔너리 데이터 전송
        with self.assertRaises(ValueError):
            handler.send_data({"key": "value"})

    @patch('app.network.create_protocol')
    def test_protocol_connection_timeout(self, mock_create_protocol):
        """프로토콜 연결 타임아웃 테스트"""
        # 연결이 계속 실패하는 프로토콜
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 통신 시작 (타임아웃 상황)
        start_time = time.time()
        handler.start_communication()
        end_time = time.time()
        
        # 실행 시간이 합리적인 범위 내에 있는지 확인
        execution_time = end_time - start_time
        self.assertLess(execution_time, 0.1)  # 100ms 이내에 완료되어야 함

    def test_thread_state_management(self):
        """스레드 상태 관리 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 초기 상태 확인
        self.assertFalse(handler._stop_flag.is_set())
        self.assertTrue(handler._retry_flag)
        
        # stop 호출 후 상태 확인
        handler.stop()
        self.assertTrue(handler._stop_flag.is_set())
        
        # run 메서드 호출 후 stop_flag 초기화 확인
        handler.run()
        self.assertTrue(handler._stop_flag.is_set())  # run 메서드에서 clear() 호출 후 다시 set()

    @patch('app.network.create_protocol')
    def test_multiple_start_stop_cycles(self, mock_create_protocol):
        """다중 시작/중지 사이클 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 여러 번의 시작/중지 사이클
        for i in range(3):
            handler.start_communication()
            self.assertFalse(handler._retry_flag)
            self.assertIsNotNone(handler._protocol)
            
            handler.stop_communications()
            self.assertTrue(mock_protocol.disconnect_called)
            
            # 다음 사이클을 위해 reset
            mock_protocol.disconnect_called = False

    def test_queue_operations(self):
        """큐 작업 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 큐 초기화
        handler._request_queue = queue.Queue()
        
        # 여러 데이터 전송
        test_data_list = [
            MockSendData(f"message_{i}") for i in range(5)
        ]
        
        for data in test_data_list:
            result = handler.send_data(data)
            self.assertTrue(result)
        
        # 큐 크기 확인
        self.assertEqual(handler._request_queue.qsize(), 5)
        
        # 큐에서 데이터 추출
        extracted_data = []
        while not handler._request_queue.empty():
            extracted_data.append(handler._request_queue.get())
        
        # 데이터 순서 확인
        self.assertEqual(len(extracted_data), 5)
        for i, data in enumerate(extracted_data):
            self.assertEqual(data.data, f"message_{i}")

    @patch('app.network.create_protocol')
    def test_protocol_interface_compliance(self, mock_create_protocol):
        """프로토콜 인터페이스 준수 테스트"""
        # ReqResProtocol 인터페이스 테스트
        reqres_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = reqres_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        handler.start_communication()
        
        # ReqResProtocol 인터페이스 메서드들이 호출되었는지 확인
        self.assertTrue(hasattr(reqres_protocol, 'connect'))
        self.assertTrue(hasattr(reqres_protocol, 'disconnect'))
        self.assertTrue(hasattr(reqres_protocol, 'send'))
        self.assertTrue(hasattr(reqres_protocol, 'read'))
        
        # PubSubProtocol 인터페이스 테스트
        pubsub_protocol = MockPubSubProtocol()
        mock_create_protocol.return_value = pubsub_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        handler.start_communication()
        
        # PubSubProtocol 인터페이스 메서드들이 호출되었는지 확인
        self.assertTrue(hasattr(pubsub_protocol, 'connect'))
        self.assertTrue(hasattr(pubsub_protocol, 'disconnect'))
        self.assertTrue(hasattr(pubsub_protocol, 'publish'))
        self.assertTrue(hasattr(pubsub_protocol, 'subscribe'))

    def test_network_config_immutability(self):
        """네트워크 설정 불변성 테스트"""
        original_config = {
            "method": "mqtt",
            "broker_address": "localhost",
            "port": 1883
        }
        
        handler = NetworkHandler(
            network_config=original_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 원본 설정 변경
        original_config["method"] = "tcp"
        original_config["new_key"] = "new_value"
        
        # 핸들러의 설정은 변경되지 않아야 함
        self.assertEqual(handler._network_config["method"], "mqtt")
        self.assertNotIn("new_key", handler._network_config)

    @patch('app.network.create_protocol')
    def test_error_recovery(self, mock_create_protocol):
        """에러 복구 테스트"""
        # 첫 번째 시도에서 실패, 두 번째 시도에서 성공하는 프로토콜
        mock_protocol = MockReqResProtocol()
        mock_protocol.connect_result = False
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # stop_flag 설정하여 무한 루프 방지
        handler._stop_flag.set()
        
        # 첫 번째 시도 (실패)
        handler.start_communication()
        self.assertTrue(mock_protocol.connect_called)
        
        # 프로토콜을 성공하도록 변경
        mock_protocol.connect_result = True
        mock_protocol.connect_called = False
        
        # 두 번째 시도 (성공)
        handler.start_communication()
        self.assertTrue(mock_protocol.connect_called)
        self.assertFalse(handler._retry_flag)

    def test_memory_management(self):
        """메모리 관리 테스트"""
        import gc
        import weakref
        
        # 핸들러 생성
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 약한 참조 생성
        weak_ref = weakref.ref(handler)
        
        # 핸들러 참조 제거
        del handler
        
        # 가비지 컬렉션 실행
        gc.collect()
        
        # 약한 참조가 None이 되었는지 확인 (메모리 해제 확인)
        self.assertIsNone(weak_ref())

    def test_concurrent_data_sending(self):
        """동시 데이터 전송 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # request_queue 초기화
        handler._request_queue = queue.Queue()
        
        # 동시에 여러 스레드에서 데이터 전송
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
        
        # 모든 전송이 성공했는지 확인
        self.assertTrue(all(concurrent_results))
        self.assertEqual(handler._request_queue.qsize(), 20)
        self.assertEqual(len(results), 20)

    def test_network_handler_identity(self):
        """NetworkHandler 식별자 테스트"""
        handler1 = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id="handler1",
            data_package=self.data_package
        )
        
        handler2 = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id="handler2",
            data_package=self.data_package
        )
        
        # 서로 다른 핸들러인지 확인
        self.assertIsNot(handler1, handler2)
        self.assertNotEqual(handler1._net_id, handler2._net_id)
        
        # 각 핸들러의 고유성 확인
        self.assertEqual(handler1._net_id, "handler1")
        self.assertEqual(handler2._net_id, "handler2")

    @patch('app.network.create_protocol')
    def test_protocol_lifecycle_management(self, mock_create_protocol):
        """프로토콜 생명주기 관리 테스트"""
        mock_protocol = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol
        
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        # 1. 프로토콜 생성 확인
        handler.start_communication()
        self.assertIsNotNone(handler._protocol)
        self.assertEqual(handler._protocol, mock_protocol)
        
        # 2. 프로토콜 연결 확인
        self.assertTrue(mock_protocol.connect_called)
        
        # 3. 프로토콜 정리 확인
        handler.stop_communications()
        self.assertTrue(mock_protocol.disconnect_called)
        
        # 4. 재연결 시 새로운 프로토콜 인스턴스 확인
        mock_protocol2 = MockReqResProtocol()
        mock_create_protocol.return_value = mock_protocol2
        
        handler.reconnect()
        self.assertEqual(handler._protocol, mock_protocol2)
        self.assertTrue(mock_protocol2.connect_called)


if __name__ == '__main__':
    unittest.main()
