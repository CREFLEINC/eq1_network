"""
EQ-1 Network 기본 사용법 예제
- 프레임워크의 기본 구조와 사용법을 보여줍니다
"""

import time
from eq1_network import PubSubManager, ReqResManager
from eq1_network.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol
from eq1_network.protocols.ethernet.tcp_client import TCPClient
from eq1_network.protocols.ethernet.tcp_server import TCPServer
from eq1_network.examples.data.dataset import MessageType   # TODO: uitls 파일 추가 시, 사용할 것

def basic_mqtt_example():
    """MQTT 기본 사용법"""
    print("=== MQTT 기본 사용법 ===")
    
    # 1. MQTT 프로토콜 생성
    broker_config = BrokerConfig(
        broker_address="localhost",
        port=1883,
        mode="non-blocking"
    )
    client_config = ClientConfig()
    mqtt = MQTTProtocol(broker_config, client_config)
    
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


def data_utils_example():
    """data_utils.py 사용 예제"""
    print("\n=== data_utils.py 사용 예제 ===")
    
    try:
        from eq1_network.examples.data.data_utils import (
            MessageFactory, 
            example_text_communication,
            example_binary_communication,
            example_int_communication,
            example_multi_packet_handling
        )
        from eq1_network.examples.data.dataset import MessageType
        
        # 메시지 팩토리 사용
        print("1. MessageFactory 사용")
        text_msg = MessageFactory.create_text_message("msg001", MessageType.COMMAND, "client", "server", "Hello")
        binary_msg = MessageFactory.create_binary_message("msg002", MessageType.DATA, "sensor", "controller", b"\x01\x02")
        int_msg = MessageFactory.create_int_message("msg003", MessageType.STATUS, "device", "monitor", 42)
        
        print(f"✓ 텍스트 메시지: {text_msg.msg_id} - {text_msg.payload}")
        print(f"✓ 바이너리 메시지: {binary_msg.msg_id} - {binary_msg.payload.hex()}")
        print(f"✓ 정수 메시지: {int_msg.msg_id} - {int_msg.payload}")
        
        # 통신 예시 실행
        print("\n2. 통신 예시 실행")
        packet, _ = example_text_communication()
        print(f"✓ 텍스트 통신: 패킷 크기 {len(packet)} bytes")
        
        packet, _ = example_binary_communication()
        print(f"✓ 바이너리 통신: 패킷 크기 {len(packet)} bytes")
        
        packet, _ = example_int_communication()
        print(f"✓ 정수 통신: 패킷 크기 {len(packet)} bytes")
        
        results = example_multi_packet_handling()
        print(f"✓ 다중 패킷 처리: {len(results)}개 메시지 처리")
        
    except ImportError as e:
        print(f"❌ data_utils 모듈 임포트 실패: {e}")
    except Exception as e:
        print(f"❌ data_utils 예제 오류: {e}")


def protocol_management_example():
    """프로토콜 관리 예제"""
    print("\n=== 프로토콜 관리 예제 ===")
    
    # 여러 프로토콜 등록
    mqtt1 = MQTTProtocol(BrokerConfig("localhost", 1883), ClientConfig())
    mqtt2 = MQTTProtocol(BrokerConfig("localhost", 1884), ClientConfig())
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
    data_utils_example()
    protocol_management_example()
    
    print("\n" + "=" * 50)
    print("예제 완료!")
