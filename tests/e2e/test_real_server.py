#!/usr/bin/env python3
"""
실제 MQTT 서버와 통신하는 테스트
- 로컬 mosquitto 브로커
- 퍼블릭 테스트 브로커
- 실시간 양방향 통신 테스트
"""

import time
import threading
import json
from datetime import datetime
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig

class MQTTServerTest:
    def __init__(self, broker_address="test.mosquitto.org", port=1883):
        config = MQTTConfig(
            broker_address=broker_address,
            port=port,
            mode="non-blocking"
        )
        self.mqtt = MQTTProtocol(config)
        self.received_messages = []
        self.is_running = False
    
    def message_handler(self, topic: str, payload: bytes):
        """메시지 수신 핸들러"""
        try:
            message = payload.decode('utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 📨 {topic}: {message}")
            self.received_messages.append({
                'topic': topic,
                'message': message,
                'timestamp': timestamp
            })
        except Exception as e:
            print(f"❌ 메시지 처리 오류: {e}")
    
    def connect_and_setup(self):
        """브로커 연결 및 초기 설정"""
        try:
            print(f"🔗 MQTT 브로커 연결 중... ({self.mqtt.config.broker_address}:{self.mqtt.config.port})")
            self.mqtt.connect()
            time.sleep(2)  # 연결 대기
            print("✅ 연결 완료!")
            
            # 테스트용 토픽들 구독
            topics = [
                "test/chat",
                "test/sensor",
                "test/status",
                "test/broadcast"
            ]
            
            for topic in topics:
                self.mqtt.subscribe(topic, self.message_handler, qos=1)
                print(f"📡 구독: {topic}")
            
            return True
            
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            return False
    
    def send_periodic_messages(self):
        """주기적으로 메시지 발송"""
        counter = 1
        while self.is_running:
            try:
                # 센서 데이터 시뮬레이션
                sensor_data = {
                    "temperature": 20 + (counter % 10),
                    "humidity": 50 + (counter % 20),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.mqtt.publish("test/sensor", json.dumps(sensor_data), qos=1)
                print(f"📤 센서 데이터 전송: {sensor_data['temperature']}°C")
                
                # 상태 메시지
                if counter % 5 == 0:
                    status_msg = f"시스템 정상 - {counter}회 전송 완료"
                    self.mqtt.publish("test/status", status_msg, qos=1)
                    print(f"📤 상태 전송: {status_msg}")
                
                counter += 1
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 메시지 전송 오류: {e}")
                time.sleep(1)
    
    def interactive_chat(self):
        """대화형 채팅 모드"""
        print("\n💬 채팅 모드 시작 (quit 입력시 종료)")
        while self.is_running:
            try:
                message = input("메시지 입력: ").strip()
                if message.lower() == 'quit':
                    break
                if message:
                    self.mqtt.publish("test/chat", f"사용자: {message}", qos=1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 입력 오류: {e}")
    
    def run_test(self, duration=30):
        """테스트 실행"""
        if not self.connect_and_setup():
            return
        
        self.is_running = True
        
        # 백그라운드에서 주기적 메시지 전송
        sender_thread = threading.Thread(target=self.send_periodic_messages, daemon=True)
        sender_thread.start()
        
        try:
            print(f"\n🚀 {duration}초간 실시간 통신 테스트 시작...")
            print("Ctrl+C로 중단 가능")
            
            start_time = time.time()
            while time.time() - start_time < duration:
                # 브로드캐스트 메시지 가끔 전송
                if int(time.time() - start_time) % 10 == 0:
                    broadcast_msg = f"브로드캐스트: {int(time.time() - start_time)}초 경과"
                    self.mqtt.publish("test/broadcast", broadcast_msg, qos=1)
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⏹️  사용자가 테스트를 중단했습니다.")
        
        finally:
            self.is_running = False
            self.mqtt.disconnect()
            print(f"\n📊 테스트 완료 - 총 {len(self.received_messages)}개 메시지 수신")

def test_mosquitto_broker():
    """Mosquitto 퍼블릭 브로커 테스트"""
    print("=== Mosquitto 퍼블릭 브로커 테스트 ===")
    test = MQTTServerTest("test.mosquitto.org", 1883)
    test.run_test(20)

def test_public_broker():
    """퍼블릭 브로커 테스트"""
    print("=== 퍼블릭 MQTT 브로커 테스트 ===")
    # Eclipse 퍼블릭 브로커 사용
    test = MQTTServerTest("test.mosquitto.org", 1883)
    test.run_test(15)

def interactive_test():
    """대화형 테스트"""
    print("=== 대화형 MQTT 테스트 ===")
    broker = input("브로커 주소 (기본: test.mosquitto.org): ").strip() or "test.mosquitto.org"
    port = input("포트 (기본: 1883): ").strip() or "1883"
    
    test = MQTTServerTest(broker, int(port))
    if test.connect_and_setup():
        test.is_running = True
        test.interactive_chat()
        test.mqtt.disconnect()

if __name__ == "__main__":
    print("🔧 MQTT 실제 서버 통신 테스트")
    print("1. Mosquitto 퍼블릭 브로커 테스트")
    print("2. 퍼블릭 브로커 테스트") 
    print("3. 대화형 테스트")
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        test_mosquitto_broker()
    elif choice == "2":
        test_public_broker()
    elif choice == "3":
        interactive_test()
    else:
        print("기본값으로 Mosquitto 브로커 테스트 실행")
        test_mosquitto_broker()