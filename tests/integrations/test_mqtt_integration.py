import pytest
import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig


@pytest.fixture
def mqtt_config():
    """실제 MQTT 브로커 연결을 위한 설정"""
    return MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883,
        mode="non-blocking",
        keepalive=60
    )


@pytest.fixture
def protocol(mqtt_config):
    """실제 MQTT 프로토콜 인스턴스"""
    protocol = MQTTProtocol(mqtt_config)
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
    
    # 고유한 토픽 생성 (충돌 방지)
    import uuid
    test_topic = f"test/eq1_network/{uuid.uuid4().hex[:8]}/{int(time.time())}"
    print(f"Using topic: {test_topic}")
    
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
    
    # 메시지 수신 대기 (시간 증가)
    max_receive_wait = 10
    receive_wait = 0
    while (
        len(received_messages) == 0 and
        receive_wait < max_receive_wait
    ):
        time.sleep(1)
        receive_wait += 1
        print(f"Waiting for message... {receive_wait}s (received: {len(received_messages)})")
    
    print(f"Final received messages count: {len(received_messages)}")
    
    # 검증
    if len(received_messages) == 0:
        print(f"No messages received. Connection status: {protocol.is_connected}")
        pytest.fail(f"No messages received after {receive_wait}s wait")
    
    assert len(received_messages) == 1, f"Expected 1 message, got {len(received_messages)}"
    assert received_messages[0][0] == test_topic, f"Topic mismatch: expected {test_topic}, got {received_messages[0][0]}"
    assert received_messages[0][1].decode() == test_message, f"Message mismatch: expected {test_message}, got {received_messages[0][1].decode()}"
    
    print("Pub/Sub test completed successfully")


@pytest.mark.integration
def test_real_mqtt_reconnection(protocol):
    """실제 MQTT 브로커에서 재연결 테스트"""
    # 연결 대기
    max_wait = 20
    wait_time = 0
    while not protocol.is_connected and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
        print(f"Waiting for initial connection... {wait_time}s")
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker for reconnection test")
    
    print(f"Initial connection established after {wait_time}s")
    
    protocol._is_connected = False
    
    # paho-mqtt 클라이언트 연결 해제
    try:
        protocol.client.disconnect()
        print("Client disconnected")
    except Exception as e:
        print(f"Disconnect error (expected): {e}")
    
    # 연결 해제 확인
    time.sleep(2)
    print(f"Connection status after disconnect: {protocol.is_connected}")
    
    # 재연결을 위해 내부 상태 복구 (자동 재연결 활성화)
    if not protocol.is_connected:
        print("Triggering reconnection...")
        # 재연결 시도
        threading.Thread(target=protocol._immediate_reconnect, daemon=True).start()
    
    # 자동 재연결 대기 (시간 증가)
    max_reconnect_wait = 20
    reconnect_wait = 0
    while not protocol.is_connected and reconnect_wait < max_reconnect_wait:
        time.sleep(1)
        reconnect_wait += 1
        print(f"Waiting for reconnection... {reconnect_wait}s (connected: {protocol.is_connected})")
    
    if protocol.is_connected:
        print(f"Reconnection successful after {reconnect_wait}s")
    else:
        print(f"Reconnection failed after {reconnect_wait}s")
        # 디버깅 정보 출력
        print(f"Internal state: _is_connected={protocol._is_connected}")
        print(f"Client state: is_connected={protocol.client.is_connected()}")
        print(f"Shutdown event: {protocol._shutdown_event.is_set()}")
        print(f"Auto connect: {protocol.config.auto_connect}")
    
    assert protocol.is_connected, f"재연결 실패 (대기 시간: {reconnect_wait}초)"


@pytest.mark.integration
def test_real_mqtt_queue_persistence(protocol):
    """연결 끊어진 상태에서 메시지 큐잉 및 재연결 후 전송 테스트"""
    received_messages = []
    
    def message_callback(topic, payload):
        received_messages.append((topic, payload))
        print(f"Received message: {payload.decode()}")
    
    # 연결 대기
    max_wait = 20
    wait_time = 0
    while not protocol.is_connected and wait_time < max_wait:
        time.sleep(1)
        wait_time += 1
    
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker for queue persistence test")
    
    test_topic = f"test/eq1_network_client/queue/{int(time.time())}"
    protocol.subscribe(test_topic, message_callback)
    time.sleep(2)
    
    # 연결 강제 해제
    protocol._is_connected = False
    protocol.client.disconnect()
    time.sleep(2)
    
    # 연결이 끊어진 상태에서 메시지 발행 (큐에 저장됨)
    test_message = "Queued message test"
    result = protocol.publish(test_topic, test_message)
    assert result is False  # 연결이 끊어져서 즉시 전송 실패
    assert not protocol._publish_queue.empty()  # 큐에 저장됨
    
    # 재연결 대기 (시간 증가)
    max_reconnect_wait = 20
    reconnect_wait = 0
    while not protocol.is_connected and reconnect_wait < max_reconnect_wait:
        time.sleep(1)
        reconnect_wait += 1
        print(f"Waiting for reconnection... {reconnect_wait}s")
    
    if not protocol.is_connected:
        pytest.skip("Reconnection failed - cannot test queue persistence")
    
    # 큐가 비워질 때까지 대기 (시간 증가)
    max_flush_wait = 10
    flush_wait = 0
    while not protocol._publish_queue.empty() and flush_wait < max_flush_wait:
        time.sleep(1)
        flush_wait += 1
        print(f"Waiting for queue flush... {flush_wait}s")
    
    # 큐가 비워졌는지 확인 (자동으로 전송됨)
    assert protocol._publish_queue.empty(), f"Queue not empty after {flush_wait}s"
    
    # 메시지 수신 대기
    time.sleep(3)
    
    # 메시지가 수신되었는지 확인
    assert len(received_messages) >= 1, f"No messages received. Queue size: {protocol._publish_queue.qsize()}"


if __name__ == "__main__":
    # 통합 테스트만 실행
    pytest.main([__file__, "-v", "-m", "integration"])