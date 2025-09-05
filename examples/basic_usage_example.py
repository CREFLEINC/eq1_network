"""
EQ-1 Network 기본 사용법 예제
- 프레임워크의 기본 구조와 사용법을 보여줍니다
"""

import time
from app import PubSubManager, ReqResManager
from app.protocols.mqtt.mqtt_protocol import BrokerConfig, MQTTProtocol
from app.protocols.ethernet.tcp_client import TCPClient
from app.protocols.ethernet.tcp_server import TCPServer


def basic_mqtt_example():
    """MQTT 기본 사용법"""
    print("=== MQTT 기본 사용법 ===")
    
    # 1. MQTT 프로토콜 생성
    config = BrokerConfig(
        broker_address="localhost",
        port=1883,
        mode="non-blocking"
    )
    mqtt = MQTTProtocol(config)
    
    # 2. 매니저에 등록
    PubSubManager.register("mqtt", mqtt)
    
    # 3. 연결
    if PubSubManager.connect("mqtt"):
        print("✓ MQTT 연결 성공")
        
        # 4. 메시지 핸들러 정의
        def message_handler(topic: str, payload: bytes):
            print(f"📨 수신: {topic} -> {payload.decode()}")
        
        # 5. 구독
        PubSubManager.subscribe("mqtt", "test/topic", message_handler)
        
        # 6. 메시지 발행
        PubSubManager.publish("mqtt", "test/topic", "Hello EQ-1 Network!")
        
        time.sleep(2)
        
        # 7. 연결 해제
        mqtt.disconnect()
        print("✓ MQTT 연결 해제")
    else:
        print("❌ MQTT 연결 실패")


def basic_tcp_example():
    """TCP 기본 사용법"""
    print("\n=== TCP 기본 사용법 ===")
    
    # 1. TCP 클라이언트 생성
    tcp_client = TCPClient("localhost", 8080)
    
    # 2. 매니저에 등록
    ReqResManager.register("tcp_client", tcp_client)
    
    # 3. 연결
    if ReqResManager.connect("tcp_client"):
        print("✓ TCP 클라이언트 연결 성공")
        
        # 4. 데이터 전송
        message = "Hello TCP Server!"
        result = ReqResManager.send("tcp_client", message.encode())
        if result > 0:
            print(f"✓ 메시지 전송: {message}")
        
        # 5. 응답 수신
        response = ReqResManager.read("tcp_client")
        if response:
            print(f"📨 응답 수신: {response.decode()}")
        
        # 6. 연결 해제
        ReqResManager.disconnect("tcp_client")
        print("✓ TCP 클라이언트 연결 해제")
    else:
        print("❌ TCP 클라이언트 연결 실패")


def protocol_management_example():
    """프로토콜 관리 예제"""
    print("\n=== 프로토콜 관리 예제 ===")
    
    # 여러 프로토콜 등록
    mqtt1 = MQTTProtocol(BrokerConfig("localhost", 1883))
    mqtt2 = MQTTProtocol(BrokerConfig("localhost", 1884))
    tcp_client = TCPClient("localhost", 8080)
    
    # 매니저에 등록
    PubSubManager.register("mqtt_primary", mqtt1)
    PubSubManager.register("mqtt_backup", mqtt2)
    ReqResManager.register("tcp_client", tcp_client)
    
    # 등록된 프로토콜 확인
    print("등록된 Pub/Sub 프로토콜:")
    for name in ["mqtt_primary", "mqtt_backup"]:
        try:
            protocol = PubSubManager.get(name)
            print(f"  - {name}: {type(protocol).__name__}")
        except ValueError:
            print(f"  - {name}: 등록되지 않음")
    
    print("등록된 Req/Res 프로토콜:")
    try:
        protocol = ReqResManager.get("tcp_client")
        print(f"  - tcp_client: {type(protocol).__name__}")
    except ValueError:
        print("  - tcp_client: 등록되지 않음")


if __name__ == "__main__":
    print("EQ-1 Network 기본 사용법 예제")
    print("=" * 50)
    
    # 기본 사용법 예제들
    basic_mqtt_example()
    basic_tcp_example()
    protocol_management_example()
    
    print("\n" + "=" * 50)
    print("예제 완료!")
