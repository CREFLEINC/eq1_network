#!/usr/bin/env python3
"""
MQTT 프로토콜 실제 사용 예제
- Publisher와 Subscriber 동시 실행
- 메시지 발행/구독 테스트
"""

import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig

def message_handler(topic: str, payload: bytes):
    """메시지 수신 콜백"""
    print(f"[수신] {topic}: {payload.decode()}")

def run_mqtt_example():
    """MQTT 프로토콜 예제 실행"""
    # 로컬 MQTT 브로커 사용 (mosquitto)
    config = BrokerConfig(
        broker_address="localhost",
        port=1883,
        mode="non-blocking"
    )
    mqtt = MQTTProtocol(config)
    
    try:
        print("MQTT 브로커 연결 중... (자동 연결 활성화)")
        # 자동 연결이 활성화되어 있으므로 connect() 호출 선택사항
        # mqtt.connect()  # 자동 연결로 인해 생략 가능
        time.sleep(2)  # 연결 대기
        print("✓ 자동 연결 시작")
        
        # 토픽 구독
        topic = "test/example"
        mqtt.subscribe(topic, message_handler)
        print(f"✓ 토픽 구독: {topic}")
        
        # 메시지 발행 테스트
        messages = ["Hello MQTT", "Test Message", "Final Message"]
        
        for i, msg in enumerate(messages, 1):
            print(f"[발행] {msg}")
            mqtt.publish(topic, msg)
            time.sleep(1)
        
        # 메시지 수신 대기
        print("메시지 수신 대기 중... (5초)")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        mqtt.disconnect()
        print("✓ 연결 해제")

if __name__ == "__main__":
    run_mqtt_example()