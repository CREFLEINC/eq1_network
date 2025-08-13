#!/usr/bin/env python3
"""
MQTT 프로토콜 커스터마이징 예제
- client_id 커스터마이징
- 다양한 설정 옵션 활용
"""

from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig
import time
import uuid

def create_custom_mqtt():
    """커스터마이징된 MQTT 클라이언트 생성"""
    
    # 1. 기본 설정
    basic_config = BrokerConfig(
        broker_address="localhost",
        port=1883
    )
    basic_mqtt = MQTTProtocol(basic_config)
    
    # 2. 고급 설정 (재연결, 큐 크기 등)
    advanced_config = BrokerConfig(
        broker_address="localhost",
        port=1883,
        timeout=30,
        keepalive=30,
    )
    advanced_mqtt = MQTTProtocol(advanced_config)
    
    # 3. blocking 모드
    blocking_config = BrokerConfig(
        broker_address="localhost",
        port=1883,
        mode="blocking"
    )
    blocking_mqtt = MQTTProtocol(blocking_config)
    
    return advanced_mqtt

def custom_message_handler(topic: str, payload: bytes):
    """커스텀 메시지 핸들러"""
    try:
        message = payload.decode('utf-8')
        print(f"🔔 [{topic}] {message}")
        
        # 특정 토픽에 대한 커스텀 처리
        if "alert" in topic:
            print("⚠️  Alert message received!")
        elif "data" in topic:
            print("📊 Data message processed")
            
    except Exception as e:
        print(f"❌ Message processing error: {e}")

def run_custom_example():
    """커스터마이징된 MQTT 사용 예제"""
    mqtt = create_custom_mqtt()
    
    try:
        print("커스텀 MQTT 클라이언트 연결... (자동 연결 활성화)")
        # mqtt.connect()  # 자동 연결로 인해 생략 가능
        time.sleep(2)  # 연결 대기
        
        # 다양한 토픽 구독
        topics = [
            ("sensor/temperature", custom_message_handler),
            ("alert/system", custom_message_handler),
            ("data/analytics", custom_message_handler)
        ]
        
        for topic, handler in topics:
            mqtt.subscribe(topic, handler, qos=1)
            print(f"✓ 구독: {topic}")
        
        # 테스트 메시지 발행
        test_messages = [
            ("sensor/temperature", "25.5°C"),
            ("alert/system", "High CPU usage detected"),
            ("data/analytics", "User count: 1250")
        ]
        
        for topic, message in test_messages:
            mqtt.publish(topic, message, qos=1)
            time.sleep(0.5)
        
        print("메시지 처리 대기...")
        time.sleep(3)
        
    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        mqtt.disconnect()
        print("✓ 연결 해제")

if __name__ == "__main__":
    run_custom_example()