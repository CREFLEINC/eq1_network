from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class PacketConfig:
    """
    패킷 구성 정보.

    Attributes:
        head (Optional[bytes]): 패킷 헤더
        tail (Optional[bytes]): 패킷 테일
        delimiter (Optional[bytes]): 필드 구분자
        encoding (str): 인코딩
        fields (Optional[Dict[str, str]]): 필드 정보
        extra_args (Optional[Dict[str, Any]]): 추가 인자
        use_length_field (bool): 길이 필드 사용 여부
        use_sync_field (bool): 동기화 필드 사용 여부
        include_frame_type_in_length (bool): 길이 계산에 프레임 타입 포함 여부
        include_sync_in_length (bool): 길이 계산에 동기화 번호 포함 여부
        include_tail_in_length (bool): 길이 계산에 테일 포함 여부
    """
    head: Optional[bytes] = None
    tail: Optional[bytes] = None
    delimiter: Optional[bytes] = None
    encoding: str = 'utf-8'
    fields: Optional[Dict[str, str]] = field(default_factory=dict)
    extra_args: Optional[Dict[str, Any]] = field(default_factory=dict)
    use_length_field: bool = False
    use_sync_field: bool = False
    include_frame_type_in_length: bool = False
    include_sync_in_length: bool = False
    include_tail_in_length: bool = False
    
    def validate(self) -> bool:
        """
        PacketConfig의 유효성을 검증합니다.
        
        Returns:
            bool: 유효한 설정이면 True
            
        Raises:
            ValueError: 잘못된 설정이 있는 경우
        """
        if self.fields:
            allowed_types = {'str', 'int', 'json'}
            for field_name, field_type in self.fields.items():
                if field_type not in allowed_types:
                    raise ValueError(f"Invalid field type '{field_type}' for field '{field_name}'. Allowed types: {allowed_types}")
        
        if self.encoding and not isinstance(self.encoding, str):
            raise ValueError("Encoding must be a string")
            
        logger.debug(f"PacketConfig validation passed: {len(self.fields or {})} fields defined")
        return True
