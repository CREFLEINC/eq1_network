import socket
import time

import pytest

from eq1_network.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol


@pytest.mark.integration
def is_port_open(host, port):
    """포트가 열려있는지 확인"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except socket.error:
        return False


@pytest.mark.integration
@pytest.fixture(scope="session")
def local_broker():
    """로컬 브로커 시작 (있는 경우)"""
    if not is_port_open("localhost", 1883):
        pytest.skip("Local MQTT broker not available")
    yield


@pytest.mark.integration
@pytest.fixture
def local_config():
    """로컬 MQTT 브로커 설정"""
    return BrokerConfig(broker_address="localhost", port=1883, mode="non-blocking", keepalive=10)


@pytest.mark.integration
@pytest.fixture
def protocol(local_config, local_broker):
    """로컬 MQTT 프로토콜 인스턴스"""
    client_config = ClientConfig()
    protocol = MQTTProtocol(local_config, client_config)
    yield protocol
    protocol.disconnect()


@pytest.mark.integration
def test_local_mqtt_basic_functionality(protocol):
    """로컬 MQTT 브로커 기본 기능 테스트"""
    received_messages = []

    def callback(topic, payload):
        received_messages.append((topic, payload.decode()))

    # 연결
    protocol.connect()
    time.sleep(2)
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker")

    # 구독
    test_topic = "test/local/basic"
    protocol.subscribe(test_topic, callback)
    time.sleep(0.5)

    # 발행
    test_message = "Hello Local MQTT"
    assert protocol.publish(test_topic, test_message)
    time.sleep(0.5)

    # 검증
    assert len(received_messages) == 1
    assert received_messages[0] == (test_topic, test_message)


@pytest.mark.integration
def test_local_mqtt_multiple_messages(protocol):
    """로컬 MQTT 브로커 다중 메시지 테스트"""
    received_messages = []

    def callback(topic, payload):
        received_messages.append(payload.decode())

    protocol.connect()
    time.sleep(2)
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker")

    test_topic = "test/local/multiple"
    protocol.subscribe(test_topic, callback)
    time.sleep(0.5)

    # 여러 메시지 발행
    messages = ["msg1", "msg2", "msg3", "msg4", "msg5"]
    for msg in messages:
        assert protocol.publish(test_topic, msg)
        time.sleep(0.1)

    time.sleep(1)

    # 모든 메시지가 수신되었는지 확인
    assert len(received_messages) == len(messages)
    for msg in messages:
        assert msg in received_messages


@pytest.mark.integration
def test_local_mqtt_qos_levels(protocol):
    """로컬 MQTT 브로커 QoS 레벨 테스트"""
    received_messages = []

    def callback(topic, payload):
        received_messages.append(payload.decode())

    protocol.connect()
    time.sleep(2)
    if not protocol.is_connected:
        pytest.skip("Cannot connect to MQTT broker")

    # 다양한 QoS 레벨로 구독/발행
    for qos in [0, 1, 2]:
        topic = f"test/local/qos{qos}"
        protocol.subscribe(topic, callback, qos=qos)
        time.sleep(0.2)

        message = f"QoS {qos} message"
        assert protocol.publish(topic, message, qos=qos)
        time.sleep(0.3)

    time.sleep(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
