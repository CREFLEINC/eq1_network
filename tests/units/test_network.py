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
    def is_valid(self, data: bytes) -> bool:
        return True
    
    def split_packet(self, data: bytes) -> list[bytes]:
        return [data]
    
    def from_packet(self, packet: bytes) -> bytes:
        return packet
    
    def to_packet(self, data: bytes) -> bytes:
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
        self.packet_structure = MockPacketStructure()
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

    def test_on_sent(self):
        """전송 성공 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockSendData("test_message")
        
        # on_sent 호출
        handler.on_sent(test_data)
        
        # 로그가 정상적으로 출력되는지 확인 (예외 발생하지 않아야 함)
        # 실제로는 로깅 동작을 확인할 수 없으므로 예외가 발생하지 않는지만 확인

    def test_on_failed_send(self):
        """전송 실패 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockSendData("test_message")
        
        # on_failed_send 호출
        handler.on_failed_send(test_data)
        
        # 로그가 정상적으로 출력되는지 확인 (예외 발생하지 않아야 함)

    def test_on_received(self):
        """수신 성공 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockReceivedData("test_message")
        
        # on_received 호출
        handler.on_received(test_data)
        
        # 로그가 정상적으로 출력되는지 확인 (예외 발생하지 않아야 함)

    def test_on_failed_recv(self):
        """수신 실패 이벤트 테스트"""
        handler = NetworkHandler(
            network_config=self.network_config,
            event_callback=self.event_callback,
            net_id=self.net_id,
            data_package=self.data_package
        )
        
        test_data = MockReceivedData("test_message")
        
        # on_failed_recv 호출
        handler.on_failed_recv(test_data)
        
        # 로그가 정상적으로 출력되는지 확인 (예외 발생하지 않아야 함)

    def test_on_disconnected(self):
        """연결 해제 이벤트 테스트"""
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
        
        # 로그가 정상적으로 출력되는지 확인 (예외 발생하지 않아야 함)

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
        mock_create_protocol.assert_called_once_with(params=self.network_config)

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

    def test_cleanup_on_stop(self):
        """중지 시 정리 작업 테스트"""
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
        
        # run 메서드가 정상적으로 종료되는지 확인
        handler.run()

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


if __name__ == '__main__':
    unittest.main()
