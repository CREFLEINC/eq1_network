#!/usr/bin/env python3
"""
MQTT 재연결 기능 테스트
- 브로커 연결 해제 후 자동 재연결 확인
"""

import time
import signal
import sys
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol

def message_handler(topic: str, payload: bytes):
    print(f"[수신] {topic}: {payload.decode()}")

def signal_handler(sig, frame):
    print('\n프로그램 종료')
    sys.exit(0)

def run_reconnect_test():
    mqtt = MQTTProtocol(
        broker_address="localhost",
        port=1883,
        mode="non-blocking",
        max_reconnect_attempts=5,
        reconnect_initial_delay=2
    )
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("MQTT 연결 및 구독...")
        mqtt.connect()
        mqtt.subscribe("test/reconnect", message_handler)
        
        counter = 0
        while True:
            counter += 1
            status = "연결됨" if mqtt.is_connected else "연결 끊김"
            print(f"[{counter}] 상태: {status}")
            
            if mqtt.is_connected:
                mqtt.publish("test/reconnect", f"메시지 #{counter}")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        mqtt.disconnect()

if __name__ == "__main__":
    print("재연결 테스트 시작 (Ctrl+C로 종료)")
    print("브로커를 중단했다가 다시 시작해보세요")
    run_reconnect_test()