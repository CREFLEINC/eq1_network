import pytest
import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig


@pytest.fixture
def mqtt_config():
    """EMQX 브로커 연결을 위한 설정"""
    return BrokerConfig(
        broker_address="broker.emqx.io",
        port=1883,
        mode="non-blocking",
        keepalive=60,
    )


@pytest.fixture
def protocol(mqtt_config):
    """실제 MQTT 프로토콜 인스턴스"""
    client_config = ClientConfig()
    protocol = MQTTProtocol(mqtt_config, client_config)
    yield protocol
    protocol.disconnect()


@pytest.mark.integration
def test_real_mqtt_connection(protocol):
    """실제 MQTT 브로커 연결 테스트"""
    # 연결 시도
    protocol.connect()
    time.sleep(2)
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker - network issue or broker unavailable")
    
    assert protocol.is_connected


@pytest.mark.integration
def test_real_mqtt_publish_subscribe(protocol):
    """실제 MQTT 브로커에서 publish/subscribe 테스트"""
    received_messages = []
    
    def message_callback(topic, payload):
        received_messages.append((topic, payload))
        print(f"Message received: {topic} -> {payload.decode()}")
    
    # 연결 시도
    protocol.connect()
    time.sleep(2)
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker for pub/sub test")
    
    print("Connected successfully")
    
    # 고유한 토픽 생성
    test_topic = f"test/eq1_network/{int(time.time())}"
    
    # 구독
    try:
        protocol.subscribe(test_topic, message_callback)
        print("Subscription successful")
    except Exception as e:
        print(f"Subscription failed: {e}")
        pytest.fail(f"Failed to subscribe: {e}")
    
    # 구독 완료 대기 (시간 증가)
    time.sleep(3)
    
    # 발행
    test_message = "Hello MQTT Integration Test"
    try:
        result = protocol.publish(test_topic, test_message)
        print(f"Publish result: {result}")
        if not result:
            print("Warning: Publish returned False, but continuing test...")
    except Exception as e:
        print(f"Publish failed: {e}")
        pytest.fail(f"Failed to publish: {e}")
    
    # 메시지 수신 대기
    time.sleep(3)
    
    # 검증
    if len(received_messages) == 0:
        pytest.fail("No messages received")
    
    assert len(received_messages) == 1, f"Expected 1 message, got {len(received_messages)}"
    assert received_messages[0][0] == test_topic, f"Topic mismatch: expected {test_topic}, got {received_messages[0][0]}"
    assert received_messages[0][1].decode() == test_message, f"Message mismatch: expected {test_message}, got {received_messages[0][1].decode()}"
    
    print("Pub/Sub test completed successfully")


@pytest.mark.integration
def test_real_mqtt_reconnection(protocol):
    """실제 MQTT 브로커에서 재연결 테스트"""
    # 연결 시도
    protocol.connect()
    time.sleep(2)
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker for reconnection test")
    
    print("Initial connection established")
    
    # 연결 해제
    protocol.disconnect()
    time.sleep(2)
    
    # 재연결
    protocol.connect()
    time.sleep(2)
    
    assert protocol.is_connected, "재연결 실패"


@pytest.mark.integration
def test_real_mqtt_queue_persistence(protocol):
    """연결 끊어진 상태에서 메시지 큐잉 및 재연결 후 전송 테스트"""
    received_messages = []
    
    def message_callback(topic, payload):
        received_messages.append((topic, payload))
        print(f"Received message: {payload.decode()}")
    
    protocol.connect()
    
    # 연결 대기
    max_wait = 20
    wait_time = 0
    while not protocol.is_connected and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker for queue persistence test")
    
    test_topic = f"test/eq1_network/queue/{int(time.time())}"
    protocol.subscribe(test_topic, message_callback)
    time.sleep(1)
    
    protocol.disconnect()
    
    # 연결이 끊어진 상태에서 메시지 발행
    test_message = "Queued message test"
    result = protocol.publish(test_topic, test_message)
    assert result is False
    assert not protocol._publish_queue.empty()
    
    protocol.connect()
    time.sleep(3)
    
    if not protocol.is_connected:
        pytest.skip("Reconnection failed")
    
    # 큐가 비워질 때까지 대기
    time.sleep(2)
    assert protocol._publish_queue.empty()
    
    # 메시지 수신 확인
    time.sleep(2)
    assert len(received_messages) >= 1


if __name__ == "__main__":
    # 통합 테스트만 실행
    pytest.main([__file__, "-v", "-m", "integration"])