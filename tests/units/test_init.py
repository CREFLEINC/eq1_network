import sys
from unittest.mock import patch
import pytest

from app.common.exception import (
    ProtocolAuthenticationError,
    ProtocolConnectionError,
    ProtocolDecodeError,
    ProtocolError,
    ProtocolTimeoutError,
    ProtocolValidationError,
)
from app.interfaces.protocol import (
    BaseProtocol,
    PubSubProtocol,
    ReqResProtocol,
)
from app.manager.protocol_manager import PubSubManager, ReqResManager


@pytest.mark.unit
class TestAppInit:
    """app/__init__.py 모듈 테스트"""

    def test_version_info(self):
        """버전 정보 테스트"""
        import app

        assert app.__version__ == "1.0.0"
        assert app.__author__ == "EQ-1 Team"
        assert app.__email__ == "dev@eq1.com"
        assert app.__license__ == "MIT"
        assert app.__description__ == "플러그인 기반 통신 프레임워크"

    def test_successful_imports(self):
        """성공적인 임포트 테스트"""
        import app

        # 성공적인 임포트 시 __all__에 포함되는 항목들 확인
        expected_items = [
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
        ]

        for item in expected_items:
            in_all = hasattr(app, "__all__") and (item in app.__all__)
            available = hasattr(app, item)
            assert (
                in_all or available
            ), f"{item} should be exported via __all__ or available as attribute on app"

    def test_import_error_handling(self):
        """임포트 에러 처리 테스트"""
        # 모듈을 다시 로드하기 위해 sys.modules에서 제거
        modules_to_remove = [
            "app",
            "app.manager.protocol_manager",
            "app.interfaces.protocol",
            "app.common.exception",
        ]

        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

        # ImportError 발생 시뮬레이션
        with patch.dict(
            "sys.modules",
            {
                "app.manager.protocol_manager": None,
                "app.interfaces.protocol": None,
                "app.common.exception": None,
            },
        ):
            import importlib

            import app

            importlib.reload(app)

            # Fallback: 메타데이터만 __all__에 포함
            expected_fallback = [
                "__version__",
                "__author__",
                "__email__",
                "__license__",
                "__description__",
            ]
            assert app.__all__ == expected_fallback

            # API 심볼들이 노출되지 않아야 함(선택적 검증)
            for sym in [
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
            ]:
                assert not hasattr(app, sym)
