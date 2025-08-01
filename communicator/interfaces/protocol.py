from typing import Tuple, Optional, Callable
from abc import ABC, abstractmethod


class BaseProtocol(ABC):
    """통신 프로토콜의 공통 동작(connect/disconnect)을 정의한 추상 기반 클래스입니다.

    이 클래스는 요청-응답 또는 Pub/Sub 방식에 관계없이
    모든 통신 프로토콜 구현체에서 공통적으로 제공되어야 할
    연결 및 해제 기능을 정의합니다.
    """

    @abstractmethod
    def connect(self) -> bool:
        """서버 또는 브로커와의 네트워크 연결을 시도합니다.

        Returns:
            bool: 연결에 성공하면 True, 실패하면 False를 반환합니다.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """현재 활성화된 연결을 종료합니다."""
        pass


class ReqResProtocol(BaseProtocol):
    """요청/응답(Req/Res) 기반 통신 프로토콜을 위한 추상 인터페이스입니다.

    이 인터페이스는 TCP, 시리얼 통신 등 1:1 연결을 기반으로 동작하는
    프로토콜에서 송수신 기능을 일관되게 구현하기 위해 사용됩니다.
    """

    @abstractmethod
    def send(self, data: bytes) -> bool:
        """지정된 바이트 데이터를 대상 장치에 전송합니다.

        Args:
            data (bytes): 전송할 원시 바이트 데이터

        Returns:
            bool: 전송 성공 시 True, 실패 시 False
        """
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[bytes]]:
        """장치로부터 데이터를 수신합니다. 블로킹 없이 즉시 반환되어야 합니다.

        Returns:
            Tuple[bool, Optional[bytes]]:
                - 첫 번째 요소: 수신 성공 여부 (bool)
                - 두 번째 요소: 수신된 데이터 (bytes) 또는 실패 시 None
        """
        pass


class PubSubProtocol(BaseProtocol):
    """발행/구독(Pub/Sub) 기반 통신 프로토콜을 위한 추상 인터페이스입니다.

    MQTT와 같이 브로커를 통해 다대다 메시징을 수행하는 구조에서 사용되며,
    토픽 기반 메시지 발행과 콜백 기반 수신 처리 기능을 제공합니다.
    """

    @abstractmethod
    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool:
        """특정 토픽에 메시지를 발행(Publish)합니다.

        Args:
            topic (str): 발행할 토픽 이름
            message (bytes): 전송할 메시지 바이트 데이터
            qos (int, optional): 메시지 전송 보장 수준 (0, 1, 2 중 선택)
            retain (bool, optional): Retain 플래그 (기본값: False)
        
        Returns:
            bool: 발행 성공 시 True
>>>>>>> Stashed changes
        """
        pass

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[str, bytes], None]):
        """지정된 토픽을 구독하고, 메시지 수신 시 콜백 함수를 호출합니다.

        Args:
            topic (str): 구독 대상 토픽 이름 (와일드카드 지원 가능)
            callback (Callable[[str, bytes], None]):
                - 메시지 수신 시 호출될 함수
                - 인자: 수신된 토픽(str), 메시지(bytes)
                - 반환값 없음
        """
        pass
