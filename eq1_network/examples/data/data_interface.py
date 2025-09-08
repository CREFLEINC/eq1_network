"""
네트워크 통신을 위한 패킷 구조 인터페이스
dataset.py의 메시지 클래스들과 연동되는 패킷 처리 기능
"""

import struct
from typing import List, Type, Dict

from eq1_network.data import SendData, ReceivedData, DataPackage
from eq1_network.interfaces.packet import PacketStructureInterface
from .dataset import (
    MessageType, DataFormat,
    TextNetworkMessage, BinaryNetworkMessage, IntNetworkMessage,
    TextNetworkMessageReceived, BinaryNetworkMessageReceived, IntNetworkMessageReceived
)

class NetworkPacketStructure(PacketStructureInterface):
    """네트워크 패킷 구조 정의 - PacketStructureInterface 구현"""
    HEADER_SIZE = 4
    MAX_PAYLOAD_SIZE = 1024 * 1024
    
    # 메시지 타입별 매핑
    MESSAGE_MAP: Dict[DataFormat, Dict[str, Type]] = {
        DataFormat.TEXT: {
            'send': TextNetworkMessage,
            'recv': TextNetworkMessageReceived
        },
        DataFormat.BINARY: {
            'send': BinaryNetworkMessage,
            'recv': BinaryNetworkMessageReceived
        },
        DataFormat.INT: {
            'send': IntNetworkMessage,
            'recv': IntNetworkMessageReceived
        }
    }
    
    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        """데이터를 패킷(bytes)으로 직렬화"""
        if len(data) > cls.MAX_PAYLOAD_SIZE:
            raise ValueError(f"Data size {len(data)} exceeds maximum payload size {cls.MAX_PAYLOAD_SIZE}")
        
        length = len(data)
        header = struct.pack('!I', length)  # 빅엔디안 4바이트 길이 헤더
        return header + data
    
    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        """패킷(bytes)을 데이터로 역직렬화"""
        if not cls.is_valid(packet):
            raise ValueError("Invalid packet format")
        
        length = struct.unpack('!I', packet[:cls.HEADER_SIZE])[0]
        return packet[cls.HEADER_SIZE:cls.HEADER_SIZE + length]
    
    @classmethod
    def is_valid(cls, packet: bytes) -> bool:
        """패킷(bytes)이 유효한지 확인"""
        if len(packet) < cls.HEADER_SIZE:
            return False
        
        try:
            length = struct.unpack('!I', packet[:cls.HEADER_SIZE])[0]
            return 0 <= length <= cls.MAX_PAYLOAD_SIZE and len(packet) >= cls.HEADER_SIZE + length
        except struct.error:
            return False
    
    @classmethod
    def split_packet(cls, packet: bytes) -> List[bytes]:
        """패킷(bytes)을 분할 - 여러 메시지가 포함된 경우"""
        packets = []
        remaining = packet
        
        while len(remaining) >= cls.HEADER_SIZE and cls.is_valid(remaining):
            length = struct.unpack('!I', remaining[:cls.HEADER_SIZE])[0]
            packet_size = cls.HEADER_SIZE + length
            
            if len(remaining) >= packet_size:
                packets.append(remaining[:packet_size])
                remaining = remaining[packet_size:]
            else:
                break
        
        return packets
    
    @classmethod
    def pack_message(cls, message: SendData) -> bytes:
        """메시지를 패킷으로 패킹"""
        return cls.to_packet(message.to_bytes())
    
    @classmethod
    def unpack_message(cls, packet: bytes, format_type: DataFormat = DataFormat.TEXT) -> ReceivedData:
        """패킷에서 메시지로 역직렬화"""
        message_bytes = cls.from_packet(packet)
        recv_class = cls.MESSAGE_MAP[format_type]['recv']
        return recv_class.from_bytes(message_bytes)
    
    @classmethod
    def extract_message_and_remaining(cls, packet: bytes) -> tuple[bytes, bytes]:
        """패킷에서 메시지와 나머지 데이터 추출"""
        if not cls.is_valid(packet):
            return b'', packet
        
        length = struct.unpack('!I', packet[:cls.HEADER_SIZE])[0]
        packet_size = cls.HEADER_SIZE + length
        
        if len(packet) >= packet_size:
            message = packet[cls.HEADER_SIZE:packet_size]
            remaining = packet[packet_size:]
            return message, remaining
        else:
            return b'', packet


# 각 포맷별 DataPackage 정의 (사용 예시)
TEXT_PACKAGE = DataPackage(
    packet_structure=NetworkPacketStructure,
    send_data=TextNetworkMessage,
    received_data=TextNetworkMessageReceived
)

BINARY_PACKAGE = DataPackage(
    packet_structure=NetworkPacketStructure,
    send_data=BinaryNetworkMessage,
    received_data=BinaryNetworkMessageReceived
)

INT_PACKAGE = DataPackage(
    packet_structure=NetworkPacketStructure,
    send_data=IntNetworkMessage,
    received_data=IntNetworkMessageReceived
)


