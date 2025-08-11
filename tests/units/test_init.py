import pytest
from unittest.mock import patch


class TestCommunicatorInit:
    """communicator/__init__.py 모듈 테스트"""
    
    def test_package_metadata(self):
        """패키지 메타데이터 테스트"""
        import communicator
        
        assert communicator.__version__ == "1.0.0"
        assert communicator.__author__ == "EQ-1 Team"
        assert communicator.__email__ == "dev@eq1.com"
        assert communicator.__license__ == "MIT"
        assert "플러그인 기반 통신 프레임워크" in communicator.__description__
    
    def test_successful_imports(self):
        """정상적인 임포트 테스트"""
        import communicator
        
        # 성공적으로 임포트된 클래스들 확인
        assert hasattr(communicator, 'ProtocolManager')
        assert hasattr(communicator, 'BaseProtocol')
        assert hasattr(communicator, 'PubSubProtocol')
        assert hasattr(communicator, 'ReqResProtocol')
        assert hasattr(communicator, 'ProtocolError')
        assert hasattr(communicator, 'ProtocolConnectionError')
        assert hasattr(communicator, 'ProtocolValidationError')
        
        # __all__에 포함되어 있는지 확인
        assert 'ProtocolManager' in communicator.__all__
        assert 'BaseProtocol' in communicator.__all__
        assert 'ProtocolError' in communicator.__all__
    
    def test_import_error_handling(self):
        """ImportError 처리 테스트"""
        # 임포트 실패 시뮬레이션
        with patch.dict('sys.modules', {
            'communicator.manager.protocol_manager': None,
            'communicator.interfaces.protocol': None,
            'communicator.common.exception': None
        }):
            # 모듈 재로드를 위해 기존 모듈 제거
            import sys
            if 'communicator' in sys.modules:
                del sys.modules['communicator']
            
            # 임포트 시도 - ImportError가 발생해도 패키지는 로드되어야 함
            import communicator
            
            # 기본 메타데이터는 여전히 사용 가능해야 함
            assert communicator.__version__ == "1.0.0"
            assert len(communicator.__all__) == 5  # 기본 메타데이터만 포함