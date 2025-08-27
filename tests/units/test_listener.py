import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
import logging
from typing import Type, Union

from app.worker.listener import Listener, ListenerEvent
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol
from app.interfaces.packet import PacketStructureInterface
from app.data import ReceivedData, PacketStructure
from app.common.exception import ProtocolDecodeError, ProtocolValidationError, ProtocolConnectionError, ProtocolTimeoutError, ProtocolAuthenticationError, ProtocolError


class MockListenerEvent(ListenerEvent[ReceivedData]):
    """테스트용 ListenerEvent 구현체"""
    def __init__(self):
        self.received_data = []
        self.failed_recv_data = []
        self.disconnected_data = []

    def on_received(self, received_data: ReceivedData) -> None:
        self.received_data.append(received_data)

    def on_failed_recv(self, data: bytes) -> None:
        self.failed_recv_data.append(data)

    def on_disconnected(self, data: bytes) -> None:
        self.disconnected_data.append(data)


class MockReqResProtocol(ReqResProtocol):
    """테스트용 ReqResProtocol 구현체 - 외부에서 데이터 주입 가능"""
    def __init__(self):
        self.read_results = []
        self.read_index = 0
        self.disconnect_called = False
        self.read_called = False
        self._connected = True

    def inject_read_result(self, success: bool, data: bytes = None):
        """외부에서 읽기 결과를 주입하는 메서드"""
        self.read_results.append((success, data))

    def read(self) -> tuple[bool, bytes | None]:
        self.read_called = True
        if self.read_index < len(self.read_results):
            result = self.read_results[self.read_index]
            self.read_index += 1
            return result
        # 데이터가 없으면 None 반환 (대기 상태)
        return True, None

    def send(self, data: bytes) -> bool:
        return True

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True


class MockPubSubProtocol(PubSubProtocol):
    """테스트용 PubSubProtocol 구현체 - read 메서드 추가"""
    def __init__(self):
        self.read_results = []
        self.read_index = 0
        self.disconnect_called = False
        self.read_called = False
        self._connected = True

    def inject_read_result(self, success: bool, data: bytes = None):
        """외부에서 읽기 결과를 주입하는 메서드"""
        self.read_results.append((success, data))

    def read(self) -> tuple[bool, bytes | None]:
        """PubSubProtocol에 read 메서드 추가 (테스트용)"""
        self.read_called = True
        if self.read_index < len(self.read_results):
            result = self.read_results[self.read_index]
            self.read_index += 1
            return result
        # 데이터가 없으면 None 반환 (대기 상태)
        return True, None

    def publish(self, topic: str, message: bytes, qos: int = 0, retain: bool = False) -> bool:
        return True

    def subscribe(self, topic: str, callback):
        pass

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True


class MockPacketStructure(PacketStructureInterface):
    """테스트용 패킷 구조 구현체 - PacketStructure와 동일"""
    HEAD_PACKET = b"$"
    TAIL_PACKET = b"$"

    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        return cls.HEAD_PACKET + data + cls.TAIL_PACKET

    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        if not cls.is_valid(packet):
            raise ValueError(f"Packet Structure Error : {packet}")
        return packet[1:-1]

    @classmethod
    def is_valid(cls, packet: bytes) -> bool:
        if (cls.TAIL_PACKET + cls.HEAD_PACKET) in packet:
            return False
        if packet[:1] != cls.HEAD_PACKET:
            return False
        if packet[-1:] != cls.TAIL_PACKET:
            return False
        return True

    @classmethod
    def split_packet(cls, packet: bytes) -> list[bytes]:
        results = []
        for _d in packet.split(cls.HEAD_PACKET):
            if len(_d) == 0:
                continue
            results.append(cls.HEAD_PACKET + _d + cls.TAIL_PACKET)
        return results


class MockReceivedData(ReceivedData):
    """테스트용 ReceivedData 구현체"""
    def __init__(self, message: str):
        self.message = message

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MockReceivedData':
        return cls(data.decode('utf-8'))

    def __str__(self) -> str:
        return f"MockReceivedData(message='{self.message}')"


class TestListener(unittest.TestCase):
    def setUp(self):
        """각 테스트마다 새로운 인스턴스 생성"""
        self.event_callback = MockListenerEvent()
        self.protocol = MockReqResProtocol()
        self.packet_structure = MockPacketStructure

    def test_listener_initialization(self):
        """Listener 초기화 테스트"""
        listener = Listener(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure
        )
        
        self.assertEqual(listener._protocol, self.protocol)
        self.assertEqual(listener._event_callback, self.event_callback)
        self.assertEqual(listener._packet_structure_interface, self.packet_structure)
        self.assertFalse(listener._stop_flag.is_set())
        self.assertIsNone(listener._received_data_class)

    def test_listener_initialization_with_received_data_class(self):
        """ReceivedData 클래스와 함께 Listener 초기화 테스트"""
        listener = Listener(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
            received_data_class=MockReceivedData
        )
        
        self.assertEqual(listener._received_data_class, MockReceivedData)

    def test_stop_method(self):
        """stop 메서드 테스트"""
        listener = Listener(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure
        )
        
        listener.stop()
        
        self.assertTrue(listener._stop_flag.is_set())

    def test_run_with_invalid_protocol(self):
        """잘못된 프로토콜로 run 실행 시 ValueError 발생 테스트"""
        invalid_protocol = Mock()
        listener = Listener(
            event_callback=self.event_callback,
            protocol=invalid_protocol,
            packet_structure_interface=self.packet_structure
        )
        
        with self.assertRaises(ValueError) as context:
            listener.run()
        
        self.assertIn("Protocol is not initialized", str(context.exception))

    def test_run_with_invalid_event_callback(self):
        """잘못된 이벤트 콜백으로 run 실행 시 ValueError 발생 테스트"""
        # 먼저 유효한 프로토콜을 설정하여 프로토콜 검증을 통과시킴
        valid_protocol = MockReqResProtocol()
        valid_protocol.inject_read_result(True, b"$test$")
        
        invalid_callback = Mock()
        listener = Listener(
            event_callback=invalid_callback,
            protocol=valid_protocol,
            packet_structure_interface=self.packet_structure
        )
        
        with self.assertRaises(ValueError) as context:
            listener.run()
        
        self.assertIn("Event callback is not initialized", str(context.exception))

    def test_run_with_successful_single_packet(self):
        """단일 패킷 성공적 수신 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test message$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertEqual(len(self.event_callback.received_data), 1)
        self.assertEqual(self.event_callback.received_data[0], b"test message")
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_successful_single_packet_with_received_data_class(self):
        """ReceivedData 클래스와 함께 단일 패킷 성공적 수신 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test message$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
            received_data_class=MockReceivedData
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertEqual(len(self.event_callback.received_data), 1)
        self.assertIsInstance(self.event_callback.received_data[0], MockReceivedData)
        self.assertEqual(self.event_callback.received_data[0].message, "test message")
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_failed_read(self):
        """읽기 실패 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(False, b"error data")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertEqual(len(self.event_callback.failed_recv_data), 1)
        self.assertEqual(self.event_callback.failed_recv_data[0], b"error data")
        self.assertEqual(len(self.event_callback.received_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 1)
        self.assertEqual(self.event_callback.disconnected_data[0], b"error data")
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_none_data(self):
        """None 데이터 수신 테스트 (대기 상태)"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, None)
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # None 데이터는 무시되어야 함
        self.assertEqual(len(self.event_callback.received_data), 0)
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_invalid_packet(self):
        """유효하지 않은 패킷 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"invalid packet")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 유효하지 않은 패킷은 split_packet으로 처리되어야 함
        self.assertEqual(len(self.event_callback.received_data), 0)
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_multiple_packets(self):
        """여러 패킷 수신 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$first$second$third$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 여러 패킷이 분할되어 처리되어야 함
        self.assertEqual(len(self.event_callback.received_data), 3)
        self.assertEqual(self.event_callback.received_data[0], b"first")
        self.assertEqual(self.event_callback.received_data[1], b"second")
        self.assertEqual(self.event_callback.received_data[2], b"third")
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_packet_decode_error(self):
        """패킷 디코드 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test$")
        
        # from_packet에서 예외 발생하도록 모킹
        with patch.object(self.packet_structure, 'from_packet', side_effect=ProtocolDecodeError("Decode error")):
            listener = Listener(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure
            )
            
            # 스레드를 시작하고 짧은 대기 후 중지
            listener.start()
            time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
            listener.stop()
            listener.join(timeout=0.5)
            
            self.assertEqual(len(self.event_callback.failed_recv_data), 1)
            self.assertEqual(self.event_callback.failed_recv_data[0], b"$test$")
            self.assertEqual(len(self.event_callback.received_data), 0)
            self.assertEqual(len(self.event_callback.disconnected_data), 0)
            self.assertTrue(protocol.disconnect_called)

    def test_run_with_packet_validation_error(self):
        """패킷 검증 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test$")
        
        # from_packet에서 예외 발생하도록 모킹
        with patch.object(self.packet_structure, 'from_packet', side_effect=ProtocolValidationError("Validation error")):
            listener = Listener(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure
            )
            
            # 스레드를 시작하고 짧은 대기 후 중지
            listener.start()
            time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
            listener.stop()
            listener.join(timeout=0.5)
            
            self.assertEqual(len(self.event_callback.failed_recv_data), 1)
            self.assertEqual(self.event_callback.failed_recv_data[0], b"$test$")
            self.assertEqual(len(self.event_callback.received_data), 0)
            self.assertEqual(len(self.event_callback.disconnected_data), 0)
            self.assertTrue(protocol.disconnect_called)

    def test_run_with_received_data_class_error(self):
        """ReceivedData 클래스 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test$")
        
        # from_bytes에서 예외 발생하는 ReceivedData 클래스
        error_data_class = Mock()
        error_data_class.from_bytes = Mock(side_effect=Exception("Data class error"))
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
            received_data_class=error_data_class
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertEqual(len(self.event_callback.failed_recv_data), 1)
        self.assertEqual(self.event_callback.failed_recv_data[0], b"$test$")
        self.assertEqual(len(self.event_callback.received_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_general_exception(self):
        """일반 예외 처리 테스트"""
        protocol = MockReqResProtocol()
        protocol.read = Mock(side_effect=Exception("General error"))
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 일반 예외가 발생해도 스레드는 정상 종료되어야 함
        self.assertEqual(len(self.event_callback.received_data), 0)
        self.assertEqual(len(self.event_callback.failed_recv_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_stop_flag_set_immediately(self):
        """즉시 중지 플래그가 설정된 경우 테스트"""
        protocol = MockReqResProtocol()
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 중지 플래그를 먼저 설정하고 run() 직접 호출
        listener.stop()
        listener.run()
        
        # 프로토콜이 호출되지 않아야 함
        self.assertFalse(protocol.read_called)
        self.assertTrue(protocol.disconnect_called)

    def test_listener_event_abstract_methods(self):
        """ListenerEvent 추상 메서드 테스트"""
        # 추상 클래스의 인스턴스화 시도
        with self.assertRaises(TypeError):
            ListenerEvent()

    def test_listener_inheritance(self):
        """Listener가 Thread를 상속하는지 테스트"""
        listener = Listener(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure
        )
        
        self.assertIsInstance(listener, threading.Thread)

    def test_listener_with_reqres_protocol(self):
        """ReqResProtocol과 함께 사용하는 테스트"""
        reqres_protocol = MockReqResProtocol()
        reqres_protocol.inject_read_result(True, b"$test$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=reqres_protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertTrue(reqres_protocol.read_called)
        self.assertTrue(reqres_protocol.disconnect_called)

    def test_listener_with_pubsub_protocol(self):
        """PubSubProtocol과 함께 사용하는 테스트"""
        pubsub_protocol = MockPubSubProtocol()
        pubsub_protocol.inject_read_result(True, b"$test$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=pubsub_protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        self.assertTrue(pubsub_protocol.read_called)
        self.assertTrue(pubsub_protocol.disconnect_called)

    def test_packet_structure_interface_integration(self):
        """PacketStructureInterface 통합 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test message$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # PacketStructureInterface가 올바르게 작동하는지 확인
        self.assertEqual(len(self.event_callback.received_data), 1)
        self.assertEqual(self.event_callback.received_data[0], b"test message")
        self.assertTrue(protocol.disconnect_called)

    def test_packet_structure_interface_methods_called_correctly(self):
        """PacketStructureInterface 메서드들이 올바르게 호출되는지 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$test message$")
        
        # 각 메서드가 호출되는지 확인
        with patch.object(self.packet_structure, 'is_valid') as mock_is_valid, \
             patch.object(self.packet_structure, 'from_packet') as mock_from_packet:
            
            mock_is_valid.return_value = True
            mock_from_packet.return_value = b"test message"
            
            listener = Listener(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure
            )
            
            # 스레드를 시작하고 짧은 대기 후 중지
            listener.start()
            time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
            listener.stop()
            listener.join(timeout=0.5)
            
            # 메서드들이 올바르게 호출되었는지 확인
            mock_is_valid.assert_called_once_with(b"$test message$")
            mock_from_packet.assert_called_once_with(b"$test message$")
            self.assertTrue(protocol.disconnect_called)

    def test_protocol_disconnect_exception_handling(self):
        """프로토콜 disconnect 중 예외 발생 테스트"""
        protocol = MockReqResProtocol()
        protocol.disconnect = Mock(side_effect=Exception("Disconnect exception"))
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # disconnect 예외가 발생해도 스레드는 정상 종료되어야 함
        self.assertTrue(protocol.disconnect_called)

    def test_sequential_data_processing(self):
        """순차적 데이터 처리 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$first$")
        protocol.inject_read_result(True, b"$second$")
        protocol.inject_read_result(True, b"$third$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 모든 데이터가 순서대로 처리되었는지 확인
        self.assertEqual(len(self.event_callback.received_data), 3)
        self.assertEqual(self.event_callback.received_data[0], b"first")
        self.assertEqual(self.event_callback.received_data[1], b"second")
        self.assertEqual(self.event_callback.received_data[2], b"third")
        self.assertTrue(protocol.disconnect_called)

    def test_mixed_success_and_failure_scenarios(self):
        """성공과 실패가 혼재된 시나리오 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$success1$")  # 성공
        protocol.inject_read_result(False, b"failure1")   # 실패
        protocol.inject_read_result(True, b"$success2$")  # 성공
        protocol.inject_read_result(True, None)           # None (대기)
        protocol.inject_read_result(True, b"$success3$")  # 성공
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 결과 확인
        self.assertEqual(len(self.event_callback.received_data), 3)
        self.assertEqual(self.event_callback.received_data[0], b"success1")
        self.assertEqual(self.event_callback.received_data[1], b"success2")
        self.assertEqual(self.event_callback.received_data[2], b"success3")
        
        self.assertEqual(len(self.event_callback.failed_recv_data), 1)
        self.assertEqual(self.event_callback.failed_recv_data[0], b"failure1")
        
        self.assertEqual(len(self.event_callback.disconnected_data), 1)
        self.assertEqual(self.event_callback.disconnected_data[0], b"failure1")
        
        self.assertTrue(protocol.disconnect_called)

    def test_packet_structure_split_functionality(self):
        """PacketStructure의 split_packet 기능 테스트"""
        protocol = MockReqResProtocol()
        # 여러 패킷이 하나의 데이터로 들어오는 경우
        protocol.inject_read_result(True, b"$packet1$$packet2$$packet3$")
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # split_packet이 올바르게 작동하는지 확인
        self.assertEqual(len(self.event_callback.received_data), 3)
        self.assertEqual(self.event_callback.received_data[0], b"packet1")
        self.assertEqual(self.event_callback.received_data[1], b"packet2")
        self.assertEqual(self.event_callback.received_data[2], b"packet3")
        self.assertTrue(protocol.disconnect_called)

    def test_empty_packet_handling(self):
        """빈 패킷 처리 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_read_result(True, b"$$")  # 빈 패킷
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 빈 패킷도 올바르게 처리되어야 함
        self.assertEqual(len(self.event_callback.received_data), 1)
        self.assertEqual(self.event_callback.received_data[0], b"")
        self.assertTrue(protocol.disconnect_called)

    def test_continuous_reading_behavior(self):
        """연속적인 읽기 동작 테스트"""
        protocol = MockReqResProtocol()
        # 여러 번의 읽기 시도
        for i in range(5):
            protocol.inject_read_result(True, f"$message{i}$".encode())
        
        listener = Listener(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure
        )
        
        # 스레드를 시작하고 짧은 대기 후 중지
        listener.start()
        time.sleep(0.05)  # 데이터 처리 대기 (짧게 조정)
        listener.stop()
        listener.join(timeout=0.5)
        
        # 모든 메시지가 처리되었는지 확인
        self.assertEqual(len(self.event_callback.received_data), 5)
        for i in range(5):
            self.assertEqual(self.event_callback.received_data[i], f"message{i}".encode())
        self.assertTrue(protocol.disconnect_called)


if __name__ == '__main__':
    unittest.main()
