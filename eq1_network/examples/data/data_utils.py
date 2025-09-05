"""
네트워크 메시지 생성 및 처리 유틸리티
"""

import time
from .dataset import MessageType, DataFormat, TextNetworkMessage, BinaryNetworkMessage, IntNetworkMessage
from .data_interface import NetworkPacketStructure


class MessageFactory:
    """메시지 생성 팩토리"""
    
    @staticmethod
    def create_text_message(msg_id: str, msg_type: MessageType, source: str, 
                           destination: str, payload: str) -> TextNetworkMessage:
        return TextNetworkMessage(msg_id, msg_type, time.time(), source, destination, payload)
    
    @staticmethod
    def create_binary_message(msg_id: str, msg_type: MessageType, source: str,
                             destination: str, payload: bytes) -> BinaryNetworkMessage:
        return BinaryNetworkMessage(msg_id, msg_type, time.time(), source, destination, payload)
    
    @staticmethod
    def create_int_message(msg_id: str, msg_type: MessageType, source: str,
                          destination: str, payload: int) -> IntNetworkMessage:
        return IntNetworkMessage(msg_id, msg_type, time.time(), source, destination, payload)


def example_text_communication():
    """텍스트 통신 예시"""
    msg = MessageFactory.create_text_message("msg001", MessageType.COMMAND, "client", "server", "Hello World")
    packet = NetworkPacketStructure.pack_message(msg)
    received = NetworkPacketStructure.unpack_message(packet, DataFormat.TEXT)
    return packet, received


def example_binary_communication():
    """바이너리 통신 예시"""
    msg = MessageFactory.create_binary_message("msg002", MessageType.DATA, "sensor", "controller", b"\x01\x02\x03\x04")
    packet = NetworkPacketStructure.pack_message(msg)
    received = NetworkPacketStructure.unpack_message(packet, DataFormat.BINARY)
    return packet, received


def example_int_communication():
    """정수 통신 예시"""
    msg = MessageFactory.create_int_message("msg003", MessageType.STATUS, "device", "monitor", 42)
    packet = NetworkPacketStructure.pack_message(msg)
    received = NetworkPacketStructure.unpack_message(packet, DataFormat.INT)
    return packet, received


def example_multi_packet_handling():
    """다중 패킷 처리 예시"""
    msg1 = MessageFactory.create_text_message("1", MessageType.HEARTBEAT, "a", "b", "ping")
    msg2 = MessageFactory.create_int_message("2", MessageType.DATA, "c", "d", 100)
    
    packet1 = NetworkPacketStructure.pack_message(msg1)
    packet2 = NetworkPacketStructure.pack_message(msg2)
    combined_packet = packet1 + packet2
    
    packets = NetworkPacketStructure.split_packet(combined_packet)
    
    results = []
    for i, packet in enumerate(packets):
        format_type = DataFormat.TEXT if i == 0 else DataFormat.INT
        received = NetworkPacketStructure.unpack_message(packet, format_type)
        results.append(received)
    
    return results