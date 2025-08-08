import pytest
from communicator.common.exception import (
    ProtocolError,
    ProtocolConnectionError,
    ProtocolTimeoutError,
    ProtocolDecodeError,
    ProtocolValidationError,
    ProtocolAuthenticationError,
)


@pytest.mark.unit
def test_protocol_error_default_message():
    """
    ProtocolError가 기본 메시지로 초기화되고 메시지가 정확히 포함되는지 확인합니다.
    
    Args:
        None
    
    Raises:
        ProtocolError: 기본 메시지로 초기화된 예외가 발생해야 합니다.
    
    Asserts:
        str(exc_info.value): 기본 메시지가 "프로토콜 처리 중 오류가 발생했습니다."인지 확인합니다.
        isinstance(exc_info.value, ProtocolError): 예외가 ProtocolError의 인스턴스인지 확인합니다.
    """
    with pytest.raises(ProtocolError) as exc_info:
        raise ProtocolError()
    assert str(exc_info.value) == "프로토콜 처리 중 오류가 발생했습니다."


@pytest.mark.unit
def test_protocol_error_custom_message():
    """
    ProtocolError가 커스텀 메시지로 초기화되는지 확인합니다.
    
    Args:
        None
    
    Raises:
        ProtocolError: 커스텀 메시지로 초기화된 예외가 발생해야 합니다.
    
    Asserts:
        str(exc_info.value): 커스텀 메시지가 정확히 설정되었는지 확인합니다.
        isinstance(exc_info.value, ProtocolError): 예외가 ProtocolError의 인스턴스인지 확인합니다.
    """
    with pytest.raises(ProtocolError) as exc_info:
        raise ProtocolError("사용자 정의 오류")
    assert str(exc_info.value) == "사용자 정의 오류"


@pytest.mark.unit
@pytest.mark.parametrize("exception_class, expected_message", [
    (ProtocolConnectionError, "프로토콜 연결에 실패했습니다."),
    (ProtocolTimeoutError, "프로토콜 응답 시간이 초과되었습니다."),
    (ProtocolDecodeError, "수신 데이터를 디코딩하는 데 실패했습니다."),
    (ProtocolValidationError, "프로토콜 패킷 유효성 검사에 실패했습니다."),
    (ProtocolAuthenticationError, "프로토콜 패킷 인증에 실패했습니다."),
])
def test_default_messages(exception_class, expected_message):
    """
    모든 하위 예외 클래스가 기본 메시지를 정확히 반환하는지 확인합니다.
    
    Args:
        exception_class: 테스트할 예외 클래스 (ProtocolConnectionError, ProtocolTimeoutError 등)
        expected_message: 해당 예외 클래스의 기본 메시지
    
    Raises:
        ProtocolError: 기본 메시지로 초기화된 예외가 발생해야 합니다.
    
    Asserts:
        str(exc_info.value): 기본 메시지가 정확히 설정되었는지 확인합니다.
        isinstance(exc_info.value, ProtocolError): 예외가 ProtocolError의 하위 클래스인지 확인합니다.
    """
    with pytest.raises(exception_class) as exc_info:
        raise exception_class()
    assert str(exc_info.value) == expected_message
    assert isinstance(exc_info.value, ProtocolError)


@pytest.mark.unit
@pytest.mark.parametrize("exception_class", [
    ProtocolConnectionError,
    ProtocolTimeoutError,
    ProtocolDecodeError,
    ProtocolValidationError,
    ProtocolAuthenticationError,
])
def test_custom_messages(exception_class):
    """
    모든 하위 예외 클래스가 커스텀 메시지를 정확히 설정할 수 있는지 확인합니다.
    
    Args:
        exception_class: 테스트할 예외 클래스 (ProtocolConnectionError, ProtocolTimeoutError 등)
    
    Raises:
        ProtocolError: 커스텀 메시지로 초기화된 예외가 발생해야 합니다.
    
    Asserts:
        str(exc_info.value): 커스텀 메시지가 정확히 설정되었는지 확인합니다.
        isinstance(exc_info.value, ProtocolError): 예외가 ProtocolError의 하위 클래스인지 확인합니다.
    """
    custom_msg = f"테스트 메시지 - {exception_class.__name__}"
    with pytest.raises(exception_class) as exc_info:
        raise exception_class(custom_msg)
    assert str(exc_info.value) == custom_msg
    assert isinstance(exc_info.value, ProtocolError)
