"""
EQ-1 Network 기본 사용법 예제
- 프레임워크의 기본 구조와 사용법을 보여줍니다
"""

import time
from eq1_network import PubSubManager, ReqResManager
from eq1_network.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol
from eq1_network.protocols.ethernet.tcp_client import TCPClient
from eq1_network.examples.data.dataset import MessageType

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


def message_type_communication_example():
    """MessageType을 활용한 통신 예제"""
    print("\n=== MessageType 통신 예제 ===")
    
    try:
        from eq1_network.examples.data.data_utils import MessageFactory
        from eq1_network.examples.data.data_interface import NetworkPacketStructure
        from eq1_network.examples.data.dataset import DataFormat
        
        # 1. 명령 메시지 생성 및 전송
        command_msg = MessageFactory.create_text_message(
            "cmd_001", MessageType.COMMAND, "client", "server", "START_PROCESS"
        )
        command_packet = NetworkPacketStructure.pack_message(command_msg)
        print(f"✓ 명령 메시지 생성: {command_msg.payload} ({len(command_packet)} bytes)")
        
        # 2. 데이터 메시지 생성 및 전송
        sensor_data = MessageFactory.create_binary_message(
            "data_001", MessageType.DATA, "sensor_01", "controller", b"\x01\x02\x03\x04"
        )
        data_packet = NetworkPacketStructure.pack_message(sensor_data)
        print(f"✓ 센서 데이터 생성: {sensor_data.payload.hex()} ({len(data_packet)} bytes)")
        
        # 3. 상태 메시지 생성 및 전송
        status_msg = MessageFactory.create_int_message(
            "status_001", MessageType.STATUS, "device_01", "monitor", 100
        )
        status_packet = NetworkPacketStructure.pack_message(status_msg)
        print(f"✓ 상태 메시지 생성: {status_msg.payload}% ({len(status_packet)} bytes)")
        
        # 4. 하트비트 메시지 생성
        heartbeat_msg = MessageFactory.create_text_message(
            "hb_001", MessageType.HEARTBEAT, "client", "server", "ALIVE"
        )
        heartbeat_packet = NetworkPacketStructure.pack_message(heartbeat_msg)
        print(f"✓ 하트비트 메시지 생성: {heartbeat_msg.payload} ({len(heartbeat_packet)} bytes)")
        
        # 5. 응답 메시지 생성
        response_msg = MessageFactory.create_text_message(
            "resp_001", MessageType.RESPONSE, "server", "client", "PROCESS_STARTED"
        )
        response_packet = NetworkPacketStructure.pack_message(response_msg)
        print(f"✓ 응답 메시지 생성: {response_msg.payload} ({len(response_packet)} bytes)")
        
        # 6. 패킷 역직렬화 테스트
        print("\n패킷 역직렬화 테스트:")
        received_command = NetworkPacketStructure.unpack_message(command_packet, DataFormat.TEXT)
        print(f"  - 명령 수신: {received_command.payload}")
        
        received_data = NetworkPacketStructure.unpack_message(data_packet, DataFormat.BINARY)
        print(f"  - 데이터 수신: {received_data.payload.hex()}")
        
        received_status = NetworkPacketStructure.unpack_message(status_packet, DataFormat.INT)
        print(f"  - 상태 수신: {received_status.payload}%")
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
    except Exception as e:
        print(f"❌ MessageType 통신 예제 오류: {e}")


def mqtt_with_message_types_example():
    """MQTT와 MessageType 연동 예제"""
    print("\n=== MQTT + MessageType 연동 예제 ===")
    
    try:
        from eq1_network.examples.data.data_utils import MessageFactory
        from eq1_network.examples.data.data_interface import NetworkPacketStructure
        from eq1_network.examples.data.dataset import DataFormat
        
        # MQTT 프로토콜 설정
        broker_config = BrokerConfig("localhost", 1883, "non-blocking")
        client_config = ClientConfig()
        mqtt = MQTTProtocol(broker_config, client_config)
        PubSubManager.register("mqtt_typed", mqtt)
        
        if PubSubManager.connect("mqtt_typed"):
            print("✓ MQTT 연결 성공")
            
            # 메시지 타입별 핸들러 정의
            def command_handler(topic: str, payload: bytes):
                try:
                    received = NetworkPacketStructure.unpack_message(payload, DataFormat.TEXT)
                    print(f"📨 명령 수신: {received.payload}")
                except Exception as e:
                    print(f"❌ 명령 파싱 오류: {e}")
            
            def data_handler(topic: str, payload: bytes):
                try:
                    received = NetworkPacketStructure.unpack_message(payload, DataFormat.BINARY)
                    print(f"📨 데이터 수신: {received.payload.hex()}")
                except Exception as e:
                    print(f"❌ 데이터 파싱 오류: {e}")
            
            def status_handler(topic: str, payload: bytes):
                try:
                    received = NetworkPacketStructure.unpack_message(payload, DataFormat.INT)
                    print(f"📨 상태 수신: {received.payload}%")
                except Exception as e:
                    print(f"❌ 상태 파싱 오류: {e}")
            
            # 토픽별 구독
            PubSubManager.subscribe("mqtt_typed", "device/command", command_handler)
            PubSubManager.subscribe("mqtt_typed", "sensor/data", data_handler)
            PubSubManager.subscribe("mqtt_typed", "system/status", status_handler)
            
            # 메시지 발행
            command_msg = MessageFactory.create_text_message(
                "cmd_002", MessageType.COMMAND, "controller", "device", "RESET"
            )
            command_packet = NetworkPacketStructure.pack_message(command_msg)
            PubSubManager.publish("mqtt_typed", "device/command", command_packet)
            
            data_msg = MessageFactory.create_binary_message(
                "data_002", MessageType.DATA, "sensor", "logger", b"\xFF\xFE\xFD"
            )
            data_packet = NetworkPacketStructure.pack_message(data_msg)
            PubSubManager.publish("mqtt_typed", "sensor/data", data_packet)
            
            status_msg = MessageFactory.create_int_message(
                "status_002", MessageType.STATUS, "system", "monitor", 85
            )
            status_packet = NetworkPacketStructure.pack_message(status_msg)
            PubSubManager.publish("mqtt_typed", "system/status", status_packet)
            
            time.sleep(2)
            mqtt.disconnect()
            print("✓ MQTT 연결 해제")
        else:
            print("❌ MQTT 연결 실패")
            
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
    except Exception as e:
        print(f"❌ MQTT + MessageType 예제 오류: {e}")


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
    message_type_communication_example()
    mqtt_with_message_types_example()
    protocol_management_example()
    
    print("\n" + "=" * 50)
    print("예제 완료!")
