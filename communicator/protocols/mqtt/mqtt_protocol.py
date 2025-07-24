import paho.mqtt.client as mqtt
from typing import Optional, Callable
from communicator.interfaces.protocol import PubSubProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolDecodeError,
    ProtocolAuthenticationError,
    ProtocolError,
)


class MQTTProtocol(PubSubProtocol):
    """
    범용 MQTT 프로토콜 구현 클래스 (paho-mqtt 기반)

    - Pub/Sub 패턴 기반의 메시지 통신을 지원합니다.
    - 다양한 환경(브로커 주소/포트/타임아웃 등)에 맞게 유연하게 사용 가능합니다.
    - 커스텀 예외 및 콜백 구조를 통해 확장성과 유지보수성을 높였습니다.
    """

    def __init__(self, broker_address: str, port: int = 1883, timeout: int = 60):
        """
        MQTTProtocol 인스턴스를 초기화합니다.

        Args:
            broker_address (str): MQTT 브로커 주소
            port (int, optional): 포트 번호 (기본값: 1883)
            timeout (int, optional): 연결 타임아웃 (기본값: 60초)
        """
        self.broker_address = broker_address
        self.port = port
        self.timeout = timeout
        self.client = mqtt.Client()
        self._is_connected = False
        self._callback: Optional[Callable[[str, bytes], None]] = None
        self._setup_callbacks()

    def _setup_callbacks(self):
        """
        paho-mqtt 클라이언트에 콜백 함수를 등록합니다.
        (on_connect, on_disconnect, on_message)
        """
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        """
        MQTT 브로커 연결 시 호출되는 콜백 함수입니다.
        연결 성공/실패/인증오류에 따라 상태를 갱신하거나 예외를 발생시킵니다.

        Args:
            client: paho-mqtt client 인스턴스
            userdata: 사용자 데이터
            flags: 연결 플래그
            rc (int): 연결 결과 코드
        Raises:
            ProtocolAuthenticationError: 인증 실패 시
            ProtocolConnectionError: 기타 연결 실패 시
        """
        if rc == 0:
            self._is_connected = True
            print(f"Connected to MQTT broker ({self.broker_address}:{self.port})")
        elif rc == 5:
            raise ProtocolAuthenticationError("MQTT authentication failed (rc=5)")
        else:
            raise ProtocolConnectionError(f"MQTT connection failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        """
        MQTT 브로커 연결 해제 시 호출되는 콜백 함수입니다.
        내부 연결 상태를 False로 변경합니다.

        Args:
            client: paho-mqtt client 인스턴스
            userdata: 사용자 데이터
            rc (int): 연결 해제 코드
        """
        self._is_connected = False
        print(f"MQTT broker disconnected (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """
        구독한 토픽의 메시지 수신 시 호출되는 콜백 함수입니다.
        등록된 사용자 콜백이 있으면 호출하며, 디코딩 실패 시 예외를 발생시킵니다.

        Args:
            client: paho-mqtt client 인스턴스
            userdata: 사용자 데이터
            msg: 수신된 메시지 객체
        Raises:
            ProtocolDecodeError: 메시지 디코딩 실패 시
        """
        try:
            if self._callback:
                self._callback(msg.topic, msg.payload)
        except Exception as e:
            raise ProtocolDecodeError(f"MQTT message decoding failed: {e}")

    def connect(self) -> bool:
        """
        MQTT 브로커에 연결을 시도합니다.

        Returns:
            bool: 연결 성공 시 True
        Raises:
            ProtocolError: paho-mqtt 예외 발생 시
            ProtocolConnectionError: 기타 예외 발생 시
        """
        try:
            self.client.connect(self.broker_address, self.port, self.timeout)
            self.client.loop_start()
            return True
        except Exception as e:
            raise ProtocolConnectionError(f"MQTT connection failed: {e}")

    def disconnect(self):
        """
        MQTT 브로커와의 연결을 해제합니다.
        내부 상태를 초기화합니다.

        예외 발생 시 로그만 출력하며, 항상 _is_connected를 False로 만듭니다.
        """
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f"Exception occurred while disconnecting MQTT: {e}")
        finally:
            self._is_connected = False

    def publish(self, topic: str, message: str, qos: int = 0) -> bool:
        """
        지정한 토픽에 메시지를 발행(Publish)합니다.

        Args:
            topic (str): 발행할 토픽명
            message (str): 발행할 메시지
            qos (int, optional): QoS 레벨 (기본값: 0)
        Returns:
            bool: 발행 성공 시 True
        Raises:
            ProtocolValidationError: 발행 실패 시
            ProtocolError: 기타 예외 발생 시
        """
        try:
            result = self.client.publish(topic, message, qos)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT message publish failed (rc={result.rc})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT message publish failed: {e}")

    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 0) -> bool:
        """
        지정한 토픽을 구독(Subscribe)하며, 메시지 수신 시 콜백을 등록합니다.

        Args:
            topic (str): 구독할 토픽명
            callback (Callable[[str, bytes], None]): 메시지 수신 시 호출될 콜백 함수
            qos (int, optional): QoS 레벨 (기본값: 0)
        Returns:
            bool: 구독 성공 시 True
        Raises:
            ProtocolValidationError: 구독 실패 시
            ProtocolError: 기타 예외 발생 시
        """
        try:
            self._callback = callback
            result, _ = self.client.subscribe(topic, qos)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT subscription failed: {e}")

    def unsubscribe(self, topic: str) -> bool:
        """
        지정한 토픽에 대한 구독을 해제합니다.

        Args:
            topic (str): 구독 해제할 토픽명
        Returns:
            bool: 구독 해제 성공 시 True
        Raises:
            ProtocolValidationError: 해제 실패 시
            ProtocolError: 기타 예외 발생 시
        """
        try:
            result, _ = self.client.unsubscribe(topic)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT subscription failed: {e}")

    @property
    def is_connected(self) -> bool:
        """
        현재 MQTT 브로커와의 연결 상태를 반환합니다.

        Returns:
            bool: 연결되어 있으면 True, 아니면 False
        """
        return self._is_connected
