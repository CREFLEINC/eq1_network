from dataclasses import dataclass, field
from typing import Optional, Dict, Any


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
    """
    head: Optional[bytes] = None
    tail: Optional[bytes] = None
    delimiter: Optional[bytes] = None
    encoding: str = 'utf-8'
    fields: Optional[Dict[str, str]] = field(default_factory=dict)
    extra_args: Optional[Dict[str, Any]] = field(default_factory=dict)
