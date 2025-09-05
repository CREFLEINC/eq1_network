import queue
import threading
import time
import unittest
from unittest.mock import Mock, patch

import pytest

from eq1_network.common.exception import (
    ProtocolConnectionError,
    ProtocolTimeoutError,
)
from eq1_network.data import SendData
from eq1_network.interfaces.packet import PacketStructureInterface
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol
from eq1_network.worker.requester import Requester, RequesterEvent


class MockRequesterEvent(RequesterEvent[SendData]):
    """테스트용 RequesterEvent 구현체"""

    def __init__(self):
        self.sent_data = []
        self.failed_send_data = []
        self.disconnected_data = []

    def on_sent(self, data: SendData) -> None:
        self.sent_data.append(data)

    def on_failed_send(self, data: SendData) -> None:
        self.failed_send_data.append(data)

    def on_disconnected(self, data: SendData) -> None:
        self.disconnected_data.append(data)


class MockReqResProtocol(ReqResProtocol):
    """테스트용 ReqResProtocol 구현체"""

    def __init__(self):
        self.send_results = []
        self.send_index = 0
        self.disconnect_called = False
        self.send_called = False
        self._connected = True

    def inject_send_result(self, success: bool):
        """외부에서 전송 결과를 주입하는 메서드"""
        self.send_results.append(success)

    def send(self, data: bytes) -> bool:
        self.send_called = True
        if self.send_index < len(self.send_results):
            result = self.send_results[self.send_index]
            self.send_index += 1
            return result
        return False

    def read(self) -> tuple[bool, bytes | None]:
        return True, None

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True


class MockPubSubProtocol(PubSubProtocol):
    """테스트용 PubSubProtocol 구현체"""

    def __init__(self):
        self.send_results = []
        self.send_index = 0
        self.disconnect_called = False
        self.publish_called = False
        self.publish_topic = None
        self.publish_data = None
        self._connected = True

    def inject_send_result(self, success: bool):
        """외부에서 전송 결과를 주입하는 메서드"""
        self.send_results.append(success)

    def publish(self, topic: str, message: bytes, qos: int = 0, retain: bool = False) -> bool:
        self.publish_called = True
        self.publish_topic = topic
        self.publish_data = message
        if self.send_index < len(self.send_results):
            result = self.send_results[self.send_index]
            self.send_index += 1
            return result
        return False

    def subscribe(self, topic: str, callback):
        """구독 메서드 - 콜백 등록"""
        pass

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True


class MockPacketStructure(PacketStructureInterface):
    """테스트용 패킷 구조 구현체"""

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


class MockSendData(SendData):
    """테스트용 SendData 구현체"""

    def __init__(self, message: str, topic: str = None):
        self.message = message
        self.topic = topic

    def to_bytes(self) -> bytes:
        return self.message.encode("utf-8")

    def __str__(self) -> str:
        return f"MockSendData(message='{self.message}', topic='{self.topic}')"


@pytest.mark.unit
class TestRequester(unittest.TestCase):
    def setUp(self):
        """테스트 초기화"""
        self.event_callback = MockRequesterEvent()
        self.protocol = MockReqResProtocol()
        self.packet_structure = MockPacketStructure

    def test_requester_initialization(self):
        """Requester 초기화 테스트"""
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
        )

        self.assertEqual(requester._protocol, self.protocol)
        self.assertEqual(requester._event_callback, self.event_callback)
        self.assertEqual(requester._packet_structure, self.packet_structure)
        self.assertFalse(requester._stop_flag.is_set())
        self.assertEqual(requester._queue_wait_time, 0.1)

    def test_requester_initialization_with_custom_queue(self):
        """커스텀 큐로 Requester 초기화 테스트"""
        custom_queue = queue.Queue()
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            request_queue=custom_queue,
            packet_structure_interface=self.packet_structure,
        )

        self.assertEqual(requester._request_queue, custom_queue)

    def test_requester_initialization_with_custom_parameters(self):
        """커스텀 파라미터로 Requester 초기화 테스트"""
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
            queue_wait_time=0.5,
        )

        self.assertEqual(requester._queue_wait_time, 0.5)

    def test_stop_method(self):
        """stop 메서드 테스트"""
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
        )

        requester.stop()

        self.assertTrue(requester._stop_flag.is_set())

    def test_put_method(self):
        """put 메서드 테스트"""
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        queued_data = requester._request_queue.get_nowait()
        self.assertEqual(queued_data, test_data)

    def test_put_method_with_queue_full_exception(self):
        """큐가 가득 찼을 때 put 메서드 예외 처리 테스트"""
        small_queue = queue.Queue(maxsize=1)
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            request_queue=small_queue,
            packet_structure_interface=self.packet_structure,
        )

        test_data1 = MockSendData("first message")
        requester.put(test_data1)

        test_data2 = MockSendData("second message")
        with self.assertRaises(queue.Full):
            requester.put(test_data2)

    def test_run_with_invalid_protocol(self):
        """잘못된 프로토콜로 run 실행 시 ValueError 발생 테스트"""
        invalid_protocol = Mock()
        requester = Requester(
            event_callback=self.event_callback,
            protocol=invalid_protocol,
            packet_structure_interface=self.packet_structure,
        )

        with self.assertRaises(ValueError) as context:
            requester.run()

        self.assertIn("Protocol is not initialized", str(context.exception))

    def test_run_with_invalid_event_callback(self):
        """잘못된 이벤트 콜백으로 run 실행 시 ValueError 발생 테스트"""
        invalid_callback = Mock()
        requester = Requester(
            event_callback=invalid_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
        )

        with self.assertRaises(ValueError) as context:
            requester.run()

        self.assertIn("Event callback is not initialized", str(context.exception))

    def test_run_with_successful_send(self):
        """성공적인 전송 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.05)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 1)
        self.assertEqual(self.event_callback.sent_data[0], test_data)
        self.assertEqual(len(self.event_callback.failed_send_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_failed_send(self):
        """전송 실패 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(False)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_none_send_result(self):
        """None 전송 결과 테스트 (실패로 처리)"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(None)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_queue_empty(self):
        """큐가 비어있을 때 동작 테스트"""
        protocol = MockReqResProtocol()

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertEqual(len(self.event_callback.failed_send_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_multiple_data(self):
        """여러 데이터 전송 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)
        protocol.inject_send_result(False)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data1 = MockSendData("first message")
        test_data2 = MockSendData("second message")
        requester.put(test_data1)
        requester.put(test_data2)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 1)
        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.sent_data[0], test_data1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data2)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_protocol_connection_error(self):
        """프로토콜 연결 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.send = Mock(side_effect=ProtocolConnectionError("Connection error"))

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.disconnected_data), 1)
        self.assertEqual(self.event_callback.disconnected_data[0], test_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertEqual(len(self.event_callback.failed_send_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_protocol_errors(self):
        """프로토콜 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.send = Mock(side_effect=ProtocolTimeoutError("Timeout error"))

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertEqual(len(self.event_callback.disconnected_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_data_serialization_error(self):
        """데이터 직렬화 오류 테스트"""
        protocol = MockReqResProtocol()

        error_data = Mock()
        error_data.to_bytes = Mock(side_effect=Exception("Serialization error"))

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        requester.put(error_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], error_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_packet_creation_error(self):
        """패킷 생성 오류 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)

        with patch.object(
            self.packet_structure, "to_packet", side_effect=Exception("Packet creation error")
        ):
            requester = Requester(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure,
            )

            test_data = MockSendData("test message")
            requester.put(test_data)

            requester.start()
            time.sleep(0.01)
            requester.stop()
            requester.join(timeout=0.5)

            self.assertEqual(len(self.event_callback.failed_send_data), 1)
            self.assertEqual(self.event_callback.failed_send_data[0], test_data)
            self.assertEqual(len(self.event_callback.sent_data), 0)
            self.assertTrue(protocol.disconnect_called)

    def test_run_with_general_exception(self):
        """일반 예외 처리 테스트"""
        protocol = MockReqResProtocol()
        protocol.send = Mock(side_effect=Exception("General error"))

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_run_with_stop_flag_set_immediately(self):
        """즉시 중지 플래그가 설정된 경우 테스트"""
        protocol = MockReqResProtocol()
        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        requester.stop()
        requester.run()

        self.assertFalse(protocol.send_called)
        self.assertTrue(protocol.disconnect_called)

    def test_pubsub_protocol_with_topic(self):
        """PubSub 프로토콜에서 토픽이 있는 데이터 전송 테스트"""
        protocol = MockPubSubProtocol()
        protocol.inject_send_result(True)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message", topic="test/topic")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertTrue(protocol.publish_called)
        self.assertEqual(protocol.publish_topic, "test/topic")
        self.assertEqual(protocol.publish_data, b"$test message$")
        self.assertEqual(len(self.event_callback.sent_data), 1)
        self.assertEqual(self.event_callback.sent_data[0], test_data)
        self.assertTrue(protocol.disconnect_called)

    def test_pubsub_protocol_without_topic(self):
        """PubSub 프로토콜에서 토픽이 없는 데이터 전송 실패 테스트"""
        protocol = MockPubSubProtocol()

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertFalse(protocol.publish_called)
        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertTrue(protocol.disconnect_called)

    def test_pubsub_protocol_publish_failure(self):
        """PubSub 프로토콜에서 publish 실패 테스트"""
        protocol = MockPubSubProtocol()
        protocol.inject_send_result(False)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message", topic="test/topic")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertTrue(protocol.publish_called)
        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data)
        self.assertTrue(protocol.disconnect_called)

    def test_mixed_protocol_types(self):
        """ReqRes와 PubSub 프로토콜 혼합 사용 테스트"""
        reqres_protocol = MockReqResProtocol()
        reqres_protocol.inject_send_result(True)

        requester_reqres = Requester(
            event_callback=self.event_callback,
            protocol=reqres_protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data_reqres = MockSendData("reqres message")
        requester_reqres.put(test_data_reqres)

        requester_reqres.start()
        time.sleep(0.01)
        requester_reqres.stop()
        requester_reqres.join(timeout=0.5)

        self.assertTrue(reqres_protocol.send_called)

        event_callback_pubsub = MockRequesterEvent()
        pubsub_protocol = MockPubSubProtocol()
        pubsub_protocol.inject_send_result(True)

        requester_pubsub = Requester(
            event_callback=event_callback_pubsub,
            protocol=pubsub_protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data_pubsub = MockSendData("pubsub message", topic="test/topic")
        requester_pubsub.put(test_data_pubsub)

        requester_pubsub.start()
        time.sleep(0.01)
        requester_pubsub.stop()
        requester_pubsub.join(timeout=0.5)

        self.assertTrue(pubsub_protocol.publish_called)

    def test_requester_event_abstract_methods(self):
        """RequesterEvent 추상 메서드 테스트"""
        with self.assertRaises(TypeError):
            RequesterEvent()

    def test_requester_inheritance(self):
        """Requester가 Thread를 상속하는지 테스트"""
        requester = Requester(
            event_callback=self.event_callback,
            protocol=self.protocol,
            packet_structure_interface=self.packet_structure,
        )

        self.assertIsInstance(requester, threading.Thread)

    def test_requester_with_reqres_protocol(self):
        """ReqResProtocol과 함께 사용하는 테스트"""
        reqres_protocol = MockReqResProtocol()
        reqres_protocol.inject_send_result(True)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=reqres_protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertTrue(reqres_protocol.send_called)
        self.assertTrue(reqres_protocol.disconnect_called)

    def test_requester_with_pubsub_protocol(self):
        """PubSubProtocol과 함께 사용하는 테스트"""
        pubsub_protocol = MockPubSubProtocol()
        pubsub_protocol.inject_send_result(True)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=pubsub_protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message", topic="test/topic")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertTrue(pubsub_protocol.publish_called)
        self.assertEqual(pubsub_protocol.publish_topic, "test/topic")
        self.assertEqual(pubsub_protocol.publish_data, b"$test message$")
        self.assertTrue(pubsub_protocol.disconnect_called)

    def test_packet_structure_interface_integration(self):
        """PacketStructureInterface 통합 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data = MockSendData("test message")
        requester.put(test_data)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 1)
        self.assertEqual(self.event_callback.sent_data[0], test_data)
        self.assertTrue(protocol.disconnect_called)

    def test_packet_structure_interface_methods_called_correctly(self):
        """PacketStructureInterface 메서드들이 올바르게 호출되는지 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)

        with patch.object(self.packet_structure, "to_packet") as mock_to_packet:
            mock_to_packet.return_value = b"$test message$"

            requester = Requester(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure,
            )

            test_data = MockSendData("test message")
            requester.put(test_data)

            requester.start()
            time.sleep(0.01)
            requester.stop()
            requester.join(timeout=0.5)

            mock_to_packet.assert_called_once_with(b"test message")
            self.assertTrue(protocol.disconnect_called)

    def test_queue_timeout_behavior(self):
        """큐 타임아웃 동작 테스트"""
        protocol = MockReqResProtocol()

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
            queue_wait_time=0.01,
        )

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 0)
        self.assertEqual(len(self.event_callback.failed_send_data), 0)
        self.assertTrue(protocol.disconnect_called)

    def test_protocol_disconnect_exception_handling(self):
        """프로토콜 disconnect 중 예외 발생 테스트"""
        protocol = MockReqResProtocol()
        protocol.disconnect = Mock(side_effect=Exception("Disconnect exception"))

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertTrue(protocol.disconnect.called)

    def test_sequential_data_processing(self):
        """순차적 데이터 처리 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)
        protocol.inject_send_result(True)
        protocol.inject_send_result(False)

        requester = Requester(
            event_callback=self.event_callback,
            protocol=protocol,
            packet_structure_interface=self.packet_structure,
        )

        test_data1 = MockSendData("first message")
        test_data2 = MockSendData("second message")
        test_data3 = MockSendData("third message")

        requester.put(test_data1)
        requester.put(test_data2)
        requester.put(test_data3)

        requester.start()
        time.sleep(0.01)
        requester.stop()
        requester.join(timeout=0.5)

        self.assertEqual(len(self.event_callback.sent_data), 2)
        self.assertEqual(len(self.event_callback.failed_send_data), 1)
        self.assertEqual(self.event_callback.sent_data[0], test_data1)
        self.assertEqual(self.event_callback.sent_data[1], test_data2)
        self.assertEqual(self.event_callback.failed_send_data[0], test_data3)
        self.assertTrue(protocol.disconnect_called)

    def test_logger_debug_calls(self):
        """Logger debug 호출 테스트"""
        protocol = MockReqResProtocol()
        protocol.inject_send_result(True)

        with patch("eq1_network.worker.requester.logger") as mock_logger:
            requester = Requester(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure,
            )

            # stop 메서드에서 debug 호출 테스트
            requester.stop()
            mock_logger.debug.assert_called_with("Set Stop flag for Requester")

            # put 메서드에서 debug 호출 테스트
            test_data = MockSendData("test message")
            requester.put(test_data)
            debug_calls = [put_call.args[0] for put_call in mock_logger.debug.call_args_list]
            self.assertIn("Put data to Requester", debug_calls)

            # run 메서드에서 debug 호출 테스트
            requester.start()
            time.sleep(0.01)
            requester.stop()
            requester.join(timeout=0.5)

            # "Terminated Requester Thread" debug 호출 확인
            debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
            self.assertIn("Set Stop flag for Requester", debug_calls)
            self.assertIn("Terminated Requester Thread", debug_calls)

    def test_logger_error_calls(self):
        """Logger error 호출 테스트"""
        protocol = MockReqResProtocol()
        protocol.disconnect = Mock(side_effect=Exception("Disconnect error"))

        with patch("eq1_network.worker.requester.logger") as mock_logger:
            requester = Requester(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure,
            )

            requester.start()
            time.sleep(0.01)
            requester.stop()
            requester.join(timeout=0.5)

            # disconnect 중 예외 발생 시 error 로그 확인
            error_calls = [disconnect_call.args[0] for disconnect_call in mock_logger.error.call_args_list]
            self.assertTrue(
                any("Error disconnecting protocol in Requester" in call for call in error_calls)
            )

    def test_logger_error_calls_for_general_exception(self):
        """일반 예외 발생 시 Logger error 호출 테스트"""
        protocol = MockReqResProtocol()
        protocol.send = Mock(side_effect=Exception("General error"))

        with patch("eq1_network.worker.requester.logger") as mock_logger:
            requester = Requester(
                event_callback=self.event_callback,
                protocol=protocol,
                packet_structure_interface=self.packet_structure,
            )

            test_data = MockSendData("test message")
            requester.put(test_data)

            requester.start()
            time.sleep(0.01)
            requester.stop()
            requester.join(timeout=0.5)

            # 일반 예외 발생 시 error 로그 확인
            error_calls = [error_call.args[0] for error_call in mock_logger.error.call_args_list]
            self.assertTrue(any("Error in Requester" in call for call in error_calls))


if __name__ == "__main__":
    unittest.main()
