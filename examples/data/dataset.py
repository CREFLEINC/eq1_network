"""
네트워크 통신을 위한 데이터 타입 정의
순수한 데이터 구조만 포함
"""

import struct
import time
from dataclasses import dataclass
from typing import Any
from enum import Enum

from app.data import SendData, ReceivedData


class MessageType(Enum):
    """메시지 타입 정의"""
    COMMAND = "CMD"          # 명령 메시지
    DATA = "DATA"            # 데이터 메시지
    RESPONSE = "RESP"        # 응답 메시지
    STATUS = "STATUS"        # 상태 메시지
    ERROR = "ERROR"          # 오류 메시지
    HEARTBEAT = "HEARTBEAT"  # 하트비트 메시지
    FILE_TRANSFER = "FILE"   # 파일 전송 메시지
    BULK_DATA = "BULK"       # 대용량 데이터 메시지


class DataFormat(Enum):
    """데이터 포맷 정의"""
    BINARY = "BINARY"        # 바이너리 형식
    TEXT = "TEXT"            # 텍스트 형식
    INT = "INT"              # 정수 형식


@dataclass
class TextNetworkMessage(SendData):
    """텍스트 포맷 네트워크 메시지"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: str
    
    def to_bytes(self) -> bytes:
        """텍스트 포맷으로 직렬화"""
        text_data = f"ID:{self.message_id}|TYPE:{self.message_type.value}|TIME:{self.timestamp}|SRC:{self.source}|DST:{self.destination}|DATA:{self.payload}"
        return text_data.encode('utf-8')


@dataclass
class BinaryNetworkMessage(SendData):
    """바이너리 포맷 네트워크 메시지"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: bytes
    
    def to_bytes(self) -> bytes:
        """바이너리 포맷으로 직렬화"""
        msg_id_bytes = self.message_id.encode('utf-8')[:32].ljust(32, b'\x00')
        msg_type_bytes = struct.pack('!I', list(MessageType).index(self.message_type))
        timestamp_bytes = struct.pack('!d', self.timestamp)
        source_bytes = self.source.encode('utf-8')[:32].ljust(32, b'\x00')
        dest_bytes = self.destination.encode('utf-8')[:32].ljust(32, b'\x00')
        payload_size_bytes = struct.pack('!I', len(self.payload))
        return msg_id_bytes + msg_type_bytes + timestamp_bytes + source_bytes + dest_bytes + payload_size_bytes + self.payload


@dataclass
class IntNetworkMessage(SendData):
    """정수 포맷 네트워크 메시지"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: int
    
    def to_bytes(self) -> bytes:
        """정수 포맷으로 직렬화"""
        msg_id_bytes = self.message_id.encode('utf-8')[:32].ljust(32, b'\x00')
        msg_type_bytes = struct.pack('!I', list(MessageType).index(self.message_type))
        timestamp_bytes = struct.pack('!d', self.timestamp)
        source_bytes = self.source.encode('utf-8')[:32].ljust(32, b'\x00')
        dest_bytes = self.destination.encode('utf-8')[:32].ljust(32, b'\x00')
        payload_bytes = struct.pack('!i', self.payload)  # 4바이트 정수
        return msg_id_bytes + msg_type_bytes + timestamp_bytes + source_bytes + dest_bytes + payload_bytes


@dataclass
class TextNetworkMessageReceived(ReceivedData):
    """텍스트 포맷 네트워크 메시지 수신"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: str
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'TextNetworkMessageReceived':
        """텍스트 포맷에서 역직렬화"""
        try:
            text = data.decode('utf-8')
            parts = text.split('|')
            
            data_dict = {}
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    data_dict[key] = value
            
            return cls(
                message_id=data_dict.get("ID", ""),
                message_type=MessageType(data_dict.get("TYPE", "CMD")),
                timestamp=float(data_dict.get("TIME", time.time())),
                source=data_dict.get("SRC", ""),
                destination=data_dict.get("DST", ""),
                payload=data_dict.get("DATA", "")
            )
        except Exception as e:
            raise ValueError(f"Failed to parse text message: {e}")


@dataclass
class BinaryNetworkMessageReceived(ReceivedData):
    """바이너리 포맷 네트워크 메시지 수신"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: bytes
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BinaryNetworkMessageReceived':
        """바이너리 포맷에서 역직렬화"""
        try:
            if len(data) < 108:  # 최소 헤더 크기
                raise ValueError("Insufficient data for binary message")
            
            # 메시지 ID (32바이트)
            msg_id_bytes = data[0:32]
            message_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8')
            
            # 메시지 타입 (4바이트)
            msg_type_index = struct.unpack('!I', data[32:36])[0]
            message_type = list(MessageType)[msg_type_index]
            
            # 타임스탬프 (8바이트)
            timestamp = struct.unpack('!d', data[36:44])[0]
            
            # 소스/목적지 (각 32바이트)
            source = data[44:76].rstrip(b'\x00').decode('utf-8')
            destination = data[76:108].rstrip(b'\x00').decode('utf-8')
            
            # 페이로드 크기 (4바이트)
            payload_size = struct.unpack('!I', data[108:112])[0]
            
            # 페이로드
            payload = data[112:112+payload_size]
            
            return cls(
                message_id=message_id,
                message_type=message_type,
                timestamp=timestamp,
                source=source,
                destination=destination,
                payload=payload
            )
        except Exception as e:
            raise ValueError(f"Failed to parse binary message: {e}")


@dataclass
class IntNetworkMessageReceived(ReceivedData):
    """정수 포맷 네트워크 메시지 수신"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: int
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'IntNetworkMessageReceived':
        """정수 포맷에서 역직렬화"""
        try:
            if len(data) < 104:  # 최소 헤더 크기 (정수는 4바이트 고정)
                raise ValueError("Insufficient data for integer message")
            
            # 메시지 ID (32바이트)
            msg_id_bytes = data[0:32]
            message_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8')
            
            # 메시지 타입 (4바이트)
            msg_type_index = struct.unpack('!I', data[32:36])[0]
            message_type = list(MessageType)[msg_type_index]
            
            # 타임스탬프 (8바이트)
            timestamp = struct.unpack('!d', data[36:44])[0]
            
            # 소스/목적지 (각 32바이트)
            source = data[44:76].rstrip(b'\x00').decode('utf-8')
            destination = data[76:108].rstrip(b'\x00').decode('utf-8')
            
            # 페이로드 (4바이트 정수)
            payload = struct.unpack('!i', data[108:112])[0]
            
            return cls(
                message_id=message_id,
                message_type=message_type,
                timestamp=timestamp,
                source=source,
                destination=destination,
                payload=payload
            )
        except Exception as e:
            raise ValueError(f"Failed to parse integer message: {e}")


@dataclass
class NetworkMessageSendData(SendData):
    """네트워크 메시지 송신 데이터 (호환성 유지)"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: Any
    format: DataFormat
    
    def to_bytes(self) -> bytes:
        """메시지를 바이트로 직렬화"""
        if self.format == DataFormat.TEXT:
            return str(self.payload).encode('utf-8')
        elif self.format == DataFormat.BINARY:
            if isinstance(self.payload, bytes):
                return self.payload
            else:
                return str(self.payload).encode('utf-8')
        elif self.format == DataFormat.INT:
            if isinstance(self.payload, int):
                return struct.pack('!i', self.payload)
            else:
                return str(self.payload).encode('utf-8')
        else:
            return str(self.payload).encode('utf-8')


@dataclass
class NetworkMessageReceivedData(ReceivedData):
    """네트워크 메시지 수신 데이터 (호환성 유지)"""
    message_id: str
    message_type: MessageType
    timestamp: float
    source: str
    destination: str
    payload: Any
    format: DataFormat = DataFormat.TEXT
    
    @classmethod
    def from_bytes(cls, data: bytes, format: DataFormat = DataFormat.TEXT) -> 'NetworkMessageReceivedData':
        """바이트에서 메시지로 역직렬화"""
        try:
            if format == DataFormat.TEXT:
                text = data.decode('utf-8')
                return cls(
                    message_id="",
                    message_type=MessageType.DATA,
                    timestamp=time.time(),
                    source="",
                    destination="",
                    payload=text,
                    format=format
                )
            elif format == DataFormat.BINARY:
                return cls(
                    message_id="",
                    message_type=MessageType.DATA,
                    timestamp=time.time(),
                    source="",
                    destination="",
                    payload=data,
                    format=format
                )
            elif format == DataFormat.INT:
                if len(data) >= 4:
                    integer_value = struct.unpack('!i', data[:4])[0]
                    return cls(
                        message_id="",
                        message_type=MessageType.DATA,
                        timestamp=time.time(),
                        source="",
                        destination="",
                        payload=integer_value,
                        format=format
                    )
                else:
                    raise ValueError("Insufficient data for integer format")
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            raise ValueError(f"Failed to parse message: {e}")