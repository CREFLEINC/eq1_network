import time

import pytest

from app.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol


@pytest.mark.integration
def test_connection():
    """연결 기능 테스트"""
    print("=== 연결 기능 테스트 ===")
    broker_config = BrokerConfig(broker_address="broker.emqx.io", port=1883)
    client_config = ClientConfig()
    mqtt = MQTTProtocol(broker_config, client_config)

    mqtt.connect()
    time.sleep(2)

    if mqtt.is_connected:
        print("✅ 연결 성공!")
    else:
        print("❌ 연결 실패")

    mqtt.disconnect()
    print("✓ 연결 해제\n")


@pytest.mark.integration
def test_publish_subscribe():
    """메시지 전송 테스트"""
    print("=== 메시지 전송 테스트 ===")

    broker_config = BrokerConfig(broker_address="broker.emqx.io", port=1883)
    client_config = ClientConfig()
    mqtt = MQTTProtocol(broker_config, client_config)

    received_messages = []

    def message_handler(topic: str, payload: bytes):
        received_messages.append(payload.decode())
        print(f"수신: {payload.decode()}")

    mqtt.connect()
    time.sleep(2)

    if not mqtt.is_connected:
        print("❌ 연결 실패")
        return

    topic = f"test/emqx/{int(time.time())}"
    mqtt.subscribe(topic, message_handler)
    time.sleep(1)

    # 메시지 발행
    for i in range(3):
        mqtt.publish(topic, f"Message {i+1}")
        time.sleep(0.2)

    time.sleep(2)

    print(f"✅ 수신한 메시지: {len(received_messages)}개")

    if len(received_messages) >= 1:
        print("✅ 메시지 전송 성공!")
    else:
        print("❌ 메시지 전송 실패")

    mqtt.disconnect()
    print("✓ 연결 해제\n")


@pytest.mark.integration
def test_connection_speed():
    """연결 속도 테스트"""
    print("=== 연결 속도 테스트 ===")

    broker_config = BrokerConfig(broker_address="broker.emqx.io", port=1883)
    client_config = ClientConfig()

    start_time = time.time()
    mqtt = MQTTProtocol(broker_config, client_config)
    mqtt.connect()

    while not mqtt.is_connected and time.time() - start_time < 10:
        time.sleep(0.1)

    connection_time = time.time() - start_time

    if mqtt.is_connected:
        print(f"✅ 연결 성공! 소요 시간: {connection_time:.2f}초")
    else:
        print("❌ 연결 실패")

    mqtt.disconnect()
    print("✓ 연결 해제\n")


@pytest.mark.integration
def test_queue_functionality():
    """큐 기능 테스트"""
    print("=== 큐 기능 테스트 ===")

    broker_config = BrokerConfig(broker_address="broker.emqx.io", port=1883)
    client_config = ClientConfig()
    mqtt = MQTTProtocol(broker_config, client_config)

    # 연결되지 않은 상태에서 메시지 발행
    result = mqtt.publish("test/queue", "queued message")

    if not result and not mqtt._publish_queue.empty():
        print("✅ 메시지가 큐에 저장됨")
    else:
        print("❌ 큐 기능 오류")

    # 연결 후 큐 비우기 테스트
    mqtt.connect()
    time.sleep(3)

    if mqtt.is_connected and mqtt._publish_queue.empty():
        print("✅ 연결 후 큐가 비워짐")
    else:
        print("⚠️ 큐 비우기 실패")

    mqtt.disconnect()
    print("✓ 연결 해제\n")


if __name__ == "__main__":
    print("🚀 MQTT 프로토콜 구현 테스트 시작\n")

    try:
        test_connection()
        test_publish_subscribe()
        test_connection_speed()
        test_queue_functionality()

        print("🎉 모든 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
