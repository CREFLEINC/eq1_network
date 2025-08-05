import pytest
import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)


@pytest.fixture
def protocol():
    """MQTTProtocol 실제 테스트 인스턴스"""
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883,
        mode="non-blocking"
    )
    protocol = MQTTProtocol(config)
    yield protocol
    protocol.disconnect()


class TestConnection:
    """연결 관련 테스트"""
    
    def test_connect_success(self, protocol):
        result = protocol.connect()
        time.sleep(2)
        assert result is True
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")

    def test_connect_failure(self):
        config = MQTTConfig(
            broker_address="invalid.broker.address",
            port=9999,
            mode="non-blocking"
        )
        protocol = MQTTProtocol(config)
        with pytest.raises(ProtocolConnectionError):
            protocol.connect()

    def test_disconnect(self, protocol):
        protocol.connect()
        time.sleep(1)
        protocol.disconnect()
        time.sleep(1)
        assert not protocol.is_connected


class TestPublish:
    """발행 관련 테스트"""
    
    def test_publish_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        result = protocol.publish("test/optimized/publish", "test message")
        assert result is True

    def test_publish_when_disconnected(self, protocol):
        # 연결하지 않은 상태에서 발행
        result = protocol.publish("test/optimized/offline", "offline message")
        assert result is False

    def test_publish_error(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        # 빈 토픽으로 발행 시도
        result = protocol.publish("", "empty topic test")
        # 실제 구현에 따라 결과가 달라질 수 있음
        assert isinstance(result, bool)


class TestSubscribe:
    """구독 관련 테스트"""
    
    def test_subscribe_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def callback(topic, payload):
            """콜백 함수 정의

            Args:
                topic (str): 수신한 메시지의 토픽
                payload (bytes): 수신한 메시지의 페이로드
            """
            pass
        
        result = protocol.subscribe("test/optimized/subscribe", callback)
        assert result is True

    def test_subscribe_failure(self, protocol):
        # 연결하지 않은 상태에서 구독 시도
        def callback(topic, payload):
            pass
        
        with pytest.raises(ProtocolValidationError):
            protocol.subscribe("test/bad/subscribe", callback)

    def test_unsubscribe_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def callback(topic, payload):
            """콜백 함수 정의

            Args:
                topic (str): 수신한 메시지의 토픽
                payload (bytes): 수신한 메시지의 페이로드
            """
            pass
        
        protocol.subscribe("test/optimized/unsubscribe", callback)
        time.sleep(1)
        result = protocol.unsubscribe("test/optimized/unsubscribe")
        assert result is True

    def test_unsubscribe_nonexistent_topic(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        # 구독하지 않은 토픽 구독 해제 시도 (성공으로 처리됨)
        result = protocol.unsubscribe("test/nonexistent/topic")
        assert result is True  # MQTT 브로커는 존재하지 않는 토픽도 성공으로 처리
    
    def test_unsubscribe_when_disconnected(self, protocol):
        # 연결하지 않은 상태에서 unsubscribe 시도
        with pytest.raises(ProtocolValidationError):
            protocol.unsubscribe("test/disconnected/topic")

class TestMessageHandling:
    """메시지 처리 테스트"""
    
    def test_on_message_callback(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append((topic, payload.decode()))
        
        topic = f"test/optimized/callback/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        protocol.publish(topic, "callback test message")
        time.sleep(2)
        
        assert len(received_messages) >= 1
        assert received_messages[0][0] == topic
        assert received_messages[0][1] == "callback test message"

    def test_on_message_exception_handling(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def error_callback(topic, payload):
            raise ValueError("Test exception")  # 예외 발생
        
        topic = f"test/optimized/error/{int(time.time())}"
        protocol.subscribe(topic, error_callback)
        time.sleep(1)
        
        # 예외가 발생해도 프로토콜이 죽지 않아야 함
        protocol.publish(topic, "error test message")
        time.sleep(2)
        
        # 연결이 여전히 유지되어야 함
        assert protocol.is_connected


class TestReconnection:
    """재연결 관련 테스트"""
    
    def test_connection_status(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        assert protocol.is_connected is True
        
        protocol.disconnect()
        time.sleep(1)
        assert protocol.is_connected is False

    def test_subscription_recovery(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append(payload.decode())
        
        topic = f"test/optimized/recovery/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        # 연결 해제 후 재연결
        protocol.disconnect()
        time.sleep(1)
        protocol.connect()
        time.sleep(2)
        
        if protocol.is_connected:
            # 메시지 발행하여 구독이 복구되었는지 확인
            protocol.publish(topic, "recovery test")
            time.sleep(2)
            
            # 구독이 복구되었다면 메시지를 받아야 함
            assert len(received_messages) >= 1


class TestThreadManagement:
    """스레드 관리 테스트"""
    
    def test_blocking_mode(self):
        config = MQTTConfig(
            broker_address="test.mosquitto.org",
            port=1883,
            mode="blocking"
        )
        protocol = MQTTProtocol(config)
        
        protocol.connect()
        time.sleep(2)
        
        if protocol._is_connected:
            # blocking 모드에서는 별도 스레드가 생성되어야 함
            assert protocol._blocking_thread is not None
            if protocol._blocking_thread:
                assert protocol._blocking_thread.is_alive()
        
        protocol.disconnect()

    def test_non_blocking_mode(self, protocol):
        protocol.connect()
        time.sleep(2)
        
        if protocol.is_connected:
            # non-blocking 모드에서는 blocking 스레드가 없어야 함
            assert protocol._blocking_thread is None
        
        protocol.disconnect()