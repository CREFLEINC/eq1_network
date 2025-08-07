#!/usr/bin/env python3
"""
RFC 준수 MQTT 프로토콜 사용 예제
"""

from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol

def message_callback(topic: str, payload: bytes):
    print(f"Received: [{topic}] {payload.decode()}")

# RFC 준수 기능들을 포함한 MQTT 클라이언트 생성
mqtt = MQTTProtocol(
    broker_address="localhost",
    port=1883,
    username="user",           # RFC 준수: 인증
    password="pass",           # RFC 준수: 인증
    ca_certs="/path/to/ca.crt", # RFC 준수: TLS 보안
    timeout=30
)

# RFC 준수: Will Message 설정
mqtt.set_will(
    topic="device/status", 
    payload="offline", 
    qos=1, 
    retain=True
)

# 연결
mqtt.connect()

# 구독
mqtt.subscribe("test/topic", message_callback, qos=1)

# RFC 준수: Retained Message 발행
mqtt.publish("test/topic", "Hello MQTT", qos=1, retain=True)

# 연결 해제
mqtt.disconnect()