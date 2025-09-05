class ProtocolError(Exception):
    """
    모든 프로토콜 관련 예외의 최상위 클래스입니다.
    프로토콜 처리 중 발생하는 일반적인 오류 상황에 사용됩니다.
    """

    def __init__(self, message="프로토콜 처리 중 오류가 발생했습니다."):
        super().__init__(message)


class ProtocolConnectionError(ProtocolError):
    """
    프로토콜 연결 실패 시 발생하는 예외입니다.
    네트워크 또는 엔드포인트 연결 불가 상황에 사용됩니다.
    """

    def __init__(self, message="프로토콜 연결에 실패했습니다."):
        super().__init__(message)


class ProtocolTimeoutError(ProtocolError):
    """
    프로토콜 동작이 제한 시간 내에 완료되지 않을 때 발생하는 예외입니다.
    주로 요청-응답 패턴에서 타임아웃 상황에 사용됩니다.
    """

    def __init__(self, message="프로토콜 응답 시간이 초과되었습니다."):
        super().__init__(message)


class ProtocolDecodeError(ProtocolError):
    """
    수신된 데이터를 정상적으로 디코딩하지 못했을 때 발생하는 예외입니다.
    데이터 포맷 불일치, 인코딩 오류 등에 사용됩니다.
    """

    def __init__(self, message="수신 데이터를 디코딩하는 데 실패했습니다."):
        super().__init__(message)


class ProtocolValidationError(ProtocolError):
    """
    프로토콜 패킷의 유효성 검사에 실패했을 때 발생하는 예외입니다.
    필드 누락, 포맷 위반 등 데이터 무결성 오류에 사용됩니다.
    """

    def __init__(self, message="프로토콜 패킷 유효성 검사에 실패했습니다."):
        super().__init__(message)


class ProtocolAuthenticationError(ProtocolError):
    """
    프로토콜 패킷의 인증에 실패했을 때 발생하는 예외입니다.
    """

    def __init__(self, message="프로토콜 패킷 인증에 실패했습니다."):
        super().__init__(message)
