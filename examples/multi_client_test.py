#!/usr/bin/env python3
"""
멀티 클라이언트 MQTT 테스트
- Publisher와 Subscriber를 별도 프로세스로 실행
- 실제 서버 환경과 유사한 테스트
"""

import sys
import time
import json
from datetime import datetime
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

def run_publisher(broker="localhost", port=1883):
    """Publisher 클라이언트"""
    print("📤 Publisher 시작")
    
    config = MQTTConfig(
        broker_address=broker,
        port=port,
        mode="non-blocking"
    )
    mqtt = MQTTProtocol(config)
    
    try:
        mqtt.connect()
        print(f"✅ Publisher 연결됨: {broker}:{port}")
        
        counter = 1
        while True:
            # 다양한 타입의 메시지 발송
            messages = [
                ("sensor/temperature", f"{20 + counter % 15}"),
                ("sensor/humidity", f"{45 + counter % 30}"),
                ("system/status", f"OK - {counter}"),
                ("data/json", json.dumps({
                    "id": counter,
                    "value": counter * 1.5,
                    "timestamp": datetime.now().isoformat()
                }))
            ]
            
            for topic, message in messages:
                success = mqtt.publish(topic, message, qos=1)
                status = "✅" if success else "❌"
                print(f"{status} [{counter:03d}] {topic}: {message}")
            
            counter += 1
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n📤 Publisher 종료")
    finally:
        mqtt.disconnect()

def run_subscriber(broker="localhost", port=1883):
    """Subscriber 클라이언트"""
    print("📥 Subscriber 시작")
    
    config = MQTTConfig(
        broker_address=broker,
        port=port,
        mode="non-blocking"
    )
    mqtt = MQTTProtocol(config)
    
    def message_handler(topic: str, payload: bytes):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message = payload.decode('utf-8')
        
        # 메시지 타입별 처리
        if topic.startswith("sensor/"):
            print(f"🌡️  [{timestamp}] {topic}: {message}")
        elif topic.startswith("system/"):
            print(f"⚙️  [{timestamp}] {topic}: {message}")
        elif topic.startswith("data/"):
            try:
                data = json.loads(message)
                print(f"📊 [{timestamp}] {topic}: ID={data['id']}, Value={data['value']}")
            except:
                print(f"📊 [{timestamp}] {topic}: {message}")
        else:
            print(f"📨 [{timestamp}] {topic}: {message}")
    
    try:
        mqtt.connect()
        print(f"✅ Subscriber 연결됨: {broker}:{port}")
        
        # 와일드카드로 모든 토픽 구독
        topics = [
            "sensor/+",
            "system/+", 
            "data/+",
            "#"  # 모든 토픽
        ]
        
        for topic in topics[:3]:  # 중복 방지를 위해 처음 3개만
            mqtt.subscribe(topic, message_handler, qos=1)
            print(f"📡 구독: {topic}")
        
        print("\n📥 메시지 수신 대기 중... (Ctrl+C로 종료)")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n📥 Subscriber 종료")
    finally:
        mqtt.disconnect()

def run_monitor(broker="localhost", port=1883):
    """모니터링 클라이언트 (모든 메시지 감시)"""
    print("👁️  Monitor 시작")
    
    config = MQTTConfig(
        broker_address=broker,
        port=port,
        mode="non-blocking"
    )
    mqtt = MQTTProtocol(config)
    
    message_count = 0
    
    def monitor_handler(topic: str, payload: bytes):
        nonlocal message_count
        message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = payload.decode('utf-8')
        print(f"[{message_count:04d}] {timestamp} | {topic} | {message}")
    
    try:
        mqtt.connect()
        print(f"✅ Monitor 연결됨: {broker}:{port}")
        
        # 모든 토픽 모니터링
        mqtt.subscribe("#", monitor_handler, qos=0)
        print("📡 모든 토픽 모니터링 시작")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n👁️  Monitor 종료 - 총 {message_count}개 메시지 감시")
    finally:
        mqtt.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 multi_client_test.py publisher [broker] [port]")
        print("  python3 multi_client_test.py subscriber [broker] [port]") 
        print("  python3 multi_client_test.py monitor [broker] [port]")
        print("\n예시:")
        print("  python3 multi_client_test.py publisher")
        print("  python3 multi_client_test.py subscriber localhost 1883")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    broker = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 1883
    
    print(f"🔧 MQTT 멀티 클라이언트 테스트 - {mode.upper()} 모드")
    print(f"🌐 브로커: {broker}:{port}")
    
    if mode == "publisher":
        run_publisher(broker, port)
    elif mode == "subscriber":
        run_subscriber(broker, port)
    elif mode == "monitor":
        run_monitor(broker, port)
    else:
        print(f"❌ 알 수 없는 모드: {mode}")
        sys.exit(1)