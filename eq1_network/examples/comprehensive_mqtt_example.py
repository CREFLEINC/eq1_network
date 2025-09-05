"""
MQTT 프로토콜 종합 예제
- 기본 사용법부터 고급 기능까지 모든 MQTT 기능을 보여줍니다
"""

import json
import time
import threading
import uuid
from datetime import datetime
from eq1_network.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol


class ComprehensiveMQTTExample:
    """MQTT 프로토콜 종합 예제 클래스"""
    
    def __init__(self):
        self.mqtt = None
        self.message_count = 0
        self.received_messages = []
        
    def setup_basic_mqtt(self):
        """기본 MQTT 설정"""
        print("=== 1. 기본 MQTT 설정 ===")
        
        config = BrokerConfig(
            broker_address="localhost",
            port=1883,
            mode="non-blocking"
        )
        self.mqtt = MQTTProtocol(config)
        print("✓ 기본 MQTT 클라이언트 생성 완료")
    
    def setup_advanced_mqtt(self):
        """고급 MQTT 설정"""
        print("\n=== 2. 고급 MQTT 설정 ===")
        
        # 브로커 설정
        broker_config = BrokerConfig(
            broker_address="localhost",
            port=1883,
            keepalive=60,
            mode="non-blocking",
            # 인증이 필요한 경우 주석 해제
            # username="your_username",
            # password="your_password"
        )
        
        # 클라이언트 설정
        client_config = ClientConfig(
            client_id=f"comprehensive-example-{int(time.time())}",
            clean_session=True,
            userdata={"example_type": "comprehensive"}
        )
        
        self.mqtt = MQTTProtocol(broker_config, client_config)
        print("✓ 고급 MQTT 클라이언트 생성 완료")
        print(f"  - Client ID: {client_config.client_id}")
        print(f"  - Clean Session: {client_config.clean_session}")
    
    def basic_message_handler(self, topic: str, payload: bytes):
        """기본 메시지 핸들러"""
        try:
            message = payload.decode('utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"📨 [{timestamp}] {topic}: {message}")
            self.message_count += 1
            
        except Exception as e:
            print(f"❌ 메시지 처리 오류: {e}")
    
    def custom_message_handler(self, topic: str, payload: bytes):
        """커스텀 메시지 핸들러"""
        try:
            message = payload.decode('utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"🔔 [{timestamp}] {topic}: {message}")
            
            # 특정 토픽에 대한 커스텀 처리
            if "alert" in topic:
                print("⚠️  Alert message received!")
            elif "data" in topic:
                print("📊 Data message processed")
            elif "sensor" in topic:
                print("🌡️  Sensor data received")
            
            self.message_count += 1
            
        except Exception as e:
            print(f"❌ 커스텀 메시지 처리 오류: {e}")
    
    def advanced_message_handler(self, topic: str, payload: bytes):
        """고급 메시지 핸들러 (JSON 파싱 포함)"""
        try:
            message = payload.decode('utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # JSON 메시지 파싱 시도
            try:
                json_data = json.loads(message)
                formatted_message = f"[{timestamp}] {topic}: {json.dumps(json_data, indent=2)}"
            except json.JSONDecodeError:
                formatted_message = f"[{timestamp}] {topic}: {message}"
            
            print(f"📨 {formatted_message}")
            self.received_messages.append((topic, message, timestamp))
            self.message_count += 1
            
        except Exception as e:
            print(f"❌ 고급 메시지 처리 오류: {e}")
    
    def basic_mqtt_example(self):
        """기본 MQTT 사용법"""
        print("\n=== 3. 기본 MQTT 사용법 ===")
        
        try:
            # 연결 대기
            time.sleep(2)
            print("✓ 자동 연결 시작")
            
            # 토픽 구독
            topic = "test/basic"
            self.mqtt.subscribe(topic, self.basic_message_handler)
            print(f"✓ 토픽 구독: {topic}")
            
            # 메시지 발행 테스트
            messages = ["Hello MQTT", "Test Message", "Final Message"]
            
            for i, msg in enumerate(messages, 1):
                print(f"[발행] {msg}")
                self.mqtt.publish(topic, msg)
                time.sleep(1)
            
            # 메시지 수신 대기
            print("메시지 수신 대기 중... (3초)")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 기본 MQTT 오류: {e}")
    
    def custom_mqtt_example(self):
        """커스텀 MQTT 사용법"""
        print("\n=== 4. 커스텀 MQTT 사용법 ===")
        
        try:
            # 다양한 토픽 구독
            topics = [
                ("sensor/temperature", self.custom_message_handler),
                ("alert/system", self.custom_message_handler),
                ("data/analytics", self.custom_message_handler),
            ]
            
            for topic, handler in topics:
                self.mqtt.subscribe(topic, handler, qos=1)
                print(f"✓ 구독: {topic} (QoS=1)")
            
            # 테스트 메시지 발행
            test_messages = [
                ("sensor/temperature", "25.5°C"),
                ("alert/system", "High CPU usage detected"),
                ("data/analytics", "User count: 1250"),
            ]
            
            for topic, message in test_messages:
                self.mqtt.publish(topic, message, qos=1)
                print(f"📤 발행: {topic} -> {message}")
                time.sleep(0.5)
            
            print("메시지 처리 대기... (3초)")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 커스텀 MQTT 오류: {e}")
    
    def wildcard_subscription_example(self):
        """와일드카드 토픽 구독 예제"""
        print("\n=== 5. 와일드카드 토픽 구독 예제 ===")
        
        try:
            # 다양한 와일드카드 패턴 구독
            wildcard_topics = [
                "sensor/+/temperature",  # 단일 레벨 와일드카드
                "device/#",              # 다중 레벨 와일드카드
                "alert/+/+/status",      # 복합 와일드카드
            ]
            
            for topic in wildcard_topics:
                self.mqtt.subscribe(topic, self.advanced_message_handler, qos=1)
                print(f"✓ 와일드카드 구독: {topic}")
            
            # 테스트 메시지 발행
            test_messages = [
                ("sensor/room1/temperature", {"value": 25.5, "unit": "celsius"}),
                ("sensor/room2/temperature", {"value": 23.8, "unit": "celsius"}),
                ("device/thermostat/status", {"state": "active", "mode": "cool"}),
                ("device/light/status", {"state": "off", "brightness": 0}),
                ("alert/system/error/status", {"level": "warning", "message": "High CPU usage"}),
            ]
            
            for topic, data in test_messages:
                message = json.dumps(data)
                self.mqtt.publish(topic, message, qos=1)
                print(f"📤 발행: {topic} -> {message}")
                time.sleep(0.5)
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 와일드카드 구독 오류: {e}")
    
    def qos_example(self):
        """QoS 레벨 예제"""
        print("\n=== 6. QoS 레벨 예제 ===")
        
        try:
            # QoS 0: 최대 한 번 전달 (At most once)
            self.mqtt.publish("qos/test/0", "QoS 0 - 최대 한 번 전달", qos=0)
            print("📤 QoS 0 메시지 발행")
            
            # QoS 1: 최소 한 번 전달 (At least once)
            self.mqtt.publish("qos/test/1", "QoS 1 - 최소 한 번 전달", qos=1)
            print("📤 QoS 1 메시지 발행")
            
            # QoS 2: 정확히 한 번 전달 (Exactly once)
            self.mqtt.publish("qos/test/2", "QoS 2 - 정확히 한 번 전달", qos=2)
            print("📤 QoS 2 메시지 발행")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ QoS 예제 오류: {e}")
    
    def retain_message_example(self):
        """Retain 메시지 예제"""
        print("\n=== 7. Retain 메시지 예제 ===")
        
        try:
            # Retain 메시지 발행
            retain_messages = [
                ("config/system/version", "v1.2.3"),
                ("status/device/online", "true"),
                ("settings/temperature/threshold", "26.0"),
            ]
            
            for topic, message in retain_messages:
                self.mqtt.publish(topic, message, qos=1, retain=True)
                print(f"📤 Retain 메시지 발행: {topic} -> {message}")
            
            time.sleep(1)
            
            # Retain 메시지 구독 (새로운 구독자가 마지막 retain 메시지를 받음)
            print("Retain 메시지 구독 테스트...")
            for topic, _ in retain_messages:
                self.mqtt.subscribe(topic, self.advanced_message_handler, qos=1)
                print(f"✓ Retain 토픽 구독: {topic}")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Retain 메시지 오류: {e}")
    
    def periodic_publisher(self):
        """주기적 메시지 발행"""
        print("\n=== 8. 주기적 메시지 발행 ===")
        
        def publish_sensor_data():
            count = 0
            while count < 5:
                sensor_data = {
                    "timestamp": datetime.now().isoformat(),
                    "sensor_id": f"sensor_{count:03d}",
                    "temperature": 20 + (count * 2),
                    "humidity": 50 + (count * 5),
                    "sequence": count + 1
                }
                
                message = json.dumps(sensor_data)
                self.mqtt.publish("sensor/periodic/data", message, qos=1)
                print(f"📤 주기적 데이터 발행 #{count+1}: {message}")
                
                count += 1
                time.sleep(2)
        
        try:
            # 구독
            self.mqtt.subscribe("sensor/periodic/data", self.advanced_message_handler, qos=1)
            print("✓ 주기적 데이터 구독")
            
            # 별도 스레드에서 주기적 발행
            publisher_thread = threading.Thread(target=publish_sensor_data, daemon=True)
            publisher_thread.start()
            
            # 발행 완료 대기
            publisher_thread.join()
            
        except Exception as e:
            print(f"❌ 주기적 발행 오류: {e}")
    
    def error_handling_example(self):
        """오류 처리 예제"""
        print("\n=== 9. 오류 처리 예제 ===")
        
        try:
            # 잘못된 브로커 주소로 연결 시도
            print("잘못된 브로커에 연결 시도...")
            bad_config = BrokerConfig(
                broker_address="invalid.broker.address",
                port=1883,
                mode="non-blocking"
            )
            bad_mqtt = MQTTProtocol(bad_config)
            
            # 연결 시도 (타임아웃 발생 예상)
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 예상된 오류: {type(e).__name__}: {e}")
        
        # 정상적인 오류 복구
        print("정상 브로커로 재연결...")
        self.setup_advanced_mqtt()
    
    def run_comprehensive_example(self):
        """종합 예제 실행"""
        print("MQTT 프로토콜 종합 예제")
        print("=" * 60)
        
        try:
            # 1. 기본 설정
            self.setup_basic_mqtt()
            
            # 2. 고급 설정으로 변경
            self.setup_advanced_mqtt()
            
            # 3. 연결 대기
            print("\n연결 대기 중...")
            time.sleep(3)
            
            # 4. 다양한 예제 실행
            self.basic_mqtt_example()
            self.custom_mqtt_example()
            self.wildcard_subscription_example()
            self.qos_example()
            self.retain_message_example()
            self.periodic_publisher()
            self.error_handling_example()
            
            # 5. 결과 요약
            print(f"\n=== 결과 요약 ===")
            print(f"총 수신 메시지: {self.message_count}개")
            print(f"수신된 토픽들: {list(set(msg[0] for msg in self.received_messages))}")
            
            if self.received_messages:
                print("\n최근 수신 메시지:")
                for topic, message, timestamp in self.received_messages[-3:]:
                    print(f"  [{timestamp}] {topic}: {message[:50]}...")
            
        except Exception as e:
            print(f"❌ 종합 예제 실행 오류: {e}")
        finally:
            if self.mqtt:
                self.mqtt.disconnect()
                print("✓ MQTT 연결 해제")


def quick_mqtt_test():
    """빠른 MQTT 테스트"""
    print("=== 빠른 MQTT 테스트 ===")
    
    try:
        # 간단한 MQTT 테스트
        config = BrokerConfig("localhost", 1883)
        mqtt = MQTTProtocol(config)
        
        def simple_handler(topic: str, payload: bytes):
            print(f"📨 수신: {topic} -> {payload.decode()}")
        
        # 연결 대기
        time.sleep(2)
        
        # 구독 및 발행
        mqtt.subscribe("test/quick", simple_handler)
        mqtt.publish("test/quick", "Quick test message")
        
        time.sleep(2)
        mqtt.disconnect()
        print("✓ 빠른 테스트 완료")
        
    except Exception as e:
        print(f"❌ 빠른 테스트 실패: {e}")


if __name__ == "__main__":
    print("MQTT 프로토콜 종합 예제 시작")
    print("=" * 60)
    
    # 사용자 선택
    print("실행할 예제를 선택하세요:")
    print("1. 종합 예제 (모든 기능)")
    print("2. 빠른 테스트 (기본 기능만)")
    
    try:
        choice = input("선택 (1 또는 2, 기본값: 1): ").strip()
        
        if choice == "2":
            quick_mqtt_test()
        else:
            example = ComprehensiveMQTTExample()
            example.run_comprehensive_example()
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 예제 실행 오류: {e}")
    
    print("\n" + "=" * 60)
    print("MQTT 예제 완료!")
