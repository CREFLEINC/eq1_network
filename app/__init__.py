"""
EQ-1 Network Communication Framework

플러그인 기반 통신 프레임워크
"""

__version__ = "1.0.0"
__author__ = "EQ-1 Team"
__email__ = "dev@eq1.com"
__license__ = "MIT"
__description__ = "플러그인 기반 통신 프레임워크"

_FALLBACK_ALL = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
]

try:
    from app.common.exception import (
        ProtocolAuthenticationError,
        ProtocolConnectionError,
        ProtocolDecodeError,
        ProtocolError,
        ProtocolTimeoutError,
        ProtocolValidationError,
    )
    from app.interfaces.protocol import BaseProtocol, PubSubProtocol, ReqResProtocol
    from app.manager.protocol_manager import PubSubManager, ReqResManager

    __all__ = [
        "ReqResManager",
        "PubSubManager",
        "BaseProtocol",
        "PubSubProtocol",
        "ReqResProtocol",
        "ProtocolError",
        "ProtocolConnectionError",
        "ProtocolValidationError",
        "ProtocolTimeoutError",
        "ProtocolDecodeError",
        "ProtocolAuthenticationError",
        "__version__",
        "__author__",
        "__email__",
        "__license__",
        "__description__",
    ]

except ImportError:
    # 임포트 실패 시에도 기본 메타데이터는 사용 가능
    __all__ = _FALLBACK_ALL
