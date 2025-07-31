import json
from typing import Dict, Any

from communicator.common.packet.base import PacketStructure
from communicator.common.packet.config import PacketConfig


class TextPacketStructure(PacketStructure):

    def __init__(self, config: PacketConfig, **fields):
        """
        TextPacketStructure 인스턴스를 초기화합니다.
        Args:
            config (PacketConfig): 패킷 구성 정보 (항상 명시적으로 제공)
            **fields: 패킷 빌드에 필요한 필드 데이터
        """
        if not config:
            raise ValueError("config: PacketConfig는 필수입니다.")
        self.config = config
        self._data = fields

    def build(self, config: PacketConfig = None, **kwargs) -> bytes:
        """
        TextPacketStructure를 bytes로 직렬화합니다.
        Args:
            config (PacketConfig, optional): 패킷 구성 정보. None이면 self.config 사용.
            **kwargs: 패킷 빌드에 필요한 추가 정보
        Returns:
            bytes: 직렬화된 패킷 데이터
        Raises:
            ValueError: 필수 필드 누락, config 미지정 등
        """
        config = config or getattr(self, 'config', None)
        if not config or not config.fields:
            raise ValueError("Building packet requires 'fields' to be defined in PacketConfig.")
        data_to_build = kwargs if kwargs else self._data
        parts = []
        if config.head:
            parts.append(config.head)
        field_values = []
        for field_name, field_type in config.fields.items():
            if field_name not in data_to_build:
                raise ValueError(f"Missing required field: {field_name}")
            value = data_to_build[field_name]
            serialized_value = self._serialize_value(value, field_type)
            field_values.append(serialized_value.encode(config.encoding))
        delimiter = config.delimiter if config.delimiter is not None else b','
        parts.append(delimiter.join(field_values))
        if config.tail:
            parts.append(config.tail)
        return b''.join(parts)

    @classmethod
    def parse(cls, raw_data: bytes, config: PacketConfig) -> 'TextPacketStructure':
        """
        bytes 데이터를 config에 따라 파싱하여 TextPacketStructure 인스턴스를 반환합니다.
        Args:
            raw_data (bytes): 원시 패킷 데이터
            config (PacketConfig): 패킷 구성 정보
        Returns:
            TextPacketStructure: 파싱된 패킷 인스턴스
        Raises:
            ValueError: 필수 필드 누락, config 미지정 등
        """
        if not config or not config.fields:
            raise ValueError("Parsing requires 'fields' to be defined in PacketConfig.")
        data = raw_data
        if config.head and data.startswith(config.head):
            data = data[len(config.head):]
        if config.tail and data.endswith(config.tail):
            data = data[:-len(config.tail)]
        delimiter = config.delimiter if config.delimiter is not None else b','
        parts = data.split(delimiter)
        if len(parts) != len(config.fields):
            raise ValueError(f"Packet field count mismatch. Expected {len(config.fields)}, got {len(parts)}.")
        parsed_data = {}
        field_names = list(config.fields.keys())
        field_types = list(config.fields.values())
        for i in range(len(parts)):
            field_name = field_names[i]
            field_type = field_types[i]
            raw_value = parts[i].decode(config.encoding)
            parsed_data[field_name] = cls._deserialize_value(raw_value, field_type)
        return cls(config, **parsed_data)

    @property
    def frame_type(self) -> Any:
        """
        패킷의 frame_type 값을 반환합니다.
        """
        return self._data.get('frame_type')

    @property
    def payload(self) -> bytes:
        """
        패킷의 payload 값을 반환합니다.
        """
        return json.dumps(self._data).encode('utf-8')

    @staticmethod
    def _serialize_value(value: Any, field_type: str) -> str:
        """
        값(value)를 지정된 필드 타입(field_type)에 따라 직렬화합니다.

        Args:
            value (Any): 직렬화할 값
            field_type (str): 필드 타입 ('str', 'int', 'json')

        Returns:
            str: 직렬화된 값
        """
        # Validate field_type to prevent authorization bypass
        allowed_types = {'str', 'int', 'json'}
        if field_type not in allowed_types:
            raise ValueError(f"Invalid field type: {field_type}. Allowed types: {allowed_types}")
            
        if field_type == 'str':
            return str(value)
        elif field_type == 'int':
            return str(int(value))
        elif field_type == 'json':
            return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _deserialize_value(value_str: str, field_type: str) -> Any:
        """
        직렬화된 값(value_str)를 지정된 필드 타입(field_type)에 따라 역직렬화합니다.

        Args:
            value_str (str): 역직렬화할 값
            field_type (str): 필드 타입 ('str', 'int', 'json')

        Returns:
            Any: 역직렬화된 값
        """
        # Validate field_type to prevent authorization bypass
        allowed_types = {'str', 'int', 'json'}
        if field_type not in allowed_types:
            raise ValueError(f"Invalid field type: {field_type}. Allowed types: {allowed_types}")
            
        if field_type == 'str':
            return value_str
        elif field_type == 'int':
            return int(value_str)
        elif field_type == 'json':
            return json.loads(value_str)
