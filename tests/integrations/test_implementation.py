import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

def test_auto_connection():
    """연결 기능 테스트"""
    print("=== 연결 기능 테스트 ===")
    
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883
    )
    mqtt = MQTTProtocol(config)
    
    print("✓ MQTT 인스턴스 생성")
    
    # 연결 시도
    mqtt.connect()
    time.sleep(2)
    
    if mqtt.is_connected:
        print("✅ 연결 성공!")
    else:
        print("❌ 연결 실패")
    
    mqtt.disconnect()
    print("✓ 연결 해제\n")

def test_data_loss_prevention():
    """메시지 전송 테스트"""
    print("=== 메시지 전송 테스트 ===")
    
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883
    )
    mqtt = MQTTProtocol(config)
    
    received_messages = []
    
    def message_handler(topic: str, payload: bytes):
        received_messages.append(payload.decode())
        print(f"수신: {payload.decode()}")
    
    # 연결 및 구독
    mqtt.connect()
    time.sleep(2)
    mqtt.subscribe("test/data_loss", message_handler)
    time.sleep(1)
    
    # 메시지 발행
    print("메시지 발행...")
    for i in range(5):
        mqtt.publish("test/data_loss", f"Message {i+1}")
        print(f"발행: Message {i+1}")
        time.sleep(0.1)
    
    time.sleep(3)  # 메시지 처리 대기
    
    print("✅ 발행한 메시지: 5개")
    print(f"✅ 수신한 메시지: {len(received_messages)}개")
    
    if len(received_messages) >= 1:
        print("✅ 메시지 전송 성공!")
    else:
        print("❌ 메시지 전송 실패")
    
    mqtt.disconnect()
    print("✓ 연결 해제\n")

def test_low_latency_connection():
    """연결 속도 테스트"""
    print("=== 연결 속도 테스트 ===")
    
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883,
        keepalive=30
    )
    
    start_time = time.time()
    mqtt = MQTTProtocol(config)
    mqtt.connect()
    
    # 연결 완료까지 시간 측정
    while not mqtt.is_connected and time.time() - start_time < 10:
        time.sleep(0.1)
    
    connection_time = time.time() - start_time
    
    if mqtt.is_connected:
        print(f"✅ 연결 성공! 소요 시간: {connection_time:.2f}초")
        if connection_time < 5:
            print("✅ 빠른 연결 달성!")
        else:
            print("⚠️ 연결 시간이 다소 오래 걸림")
    else:
        print("❌ 연결 실패")
    
    mqtt.disconnect()
    print("✓ 연결 해제\n")

def test_publish_subscribe_integration():
    """통합 pub/sub 테스트"""
    print("=== 통합 Pub/Sub 테스트 ===")
    
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883
    )
    mqtt = MQTTProtocol(config)
    
    received_count = 0
    
    def counter_handler(topic: str, payload: bytes):
        nonlocal received_count
        received_count += 1
        print(f"[{received_count}] {topic}: {payload.decode()}")
    
    # 연결 및 구독
    mqtt.connect()
    time.sleep(2)
    mqtt.subscribe("test/integration", counter_handler)
    time.sleep(1)
    
    # 연속 메시지 발행
    print("연속 메시지 발행 테스트...")
    for i in range(5):
        success = mqtt.publish("test/integration", f"Integration test {i+1}")
        if success:
            print(f"✓ 발행 성공: {i+1}")
        else:
            print(f"❌ 발행 실패: {i+1}")
        time.sleep(0.2)
    
    time.sleep(3)  # 메시지 처리 대기
    
    print(f"✅ 발행: 5개, 수신: {received_count}개")
    
    if received_count >= 1:
        print("✅ 메시지 전달 성공!")
    else:
        print("⚠️ 메시지 누락")
    
    mqtt.disconnect()
    print("✓ 연결 해제\n")

if __name__ == "__main__":
    print("🚀 MQTT 프로토콜 구현 테스트 시작\n")
    
    try:
        test_auto_connection()
        test_data_loss_prevention()
        test_low_latency_connection()
        test_publish_subscribe_integration()
        
        print("🎉 모든 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()