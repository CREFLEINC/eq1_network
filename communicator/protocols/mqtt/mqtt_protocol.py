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
        self.broker_address = broker_address
        self.port = port
        self.timeout = timeout
        self.client = mqtt.Client()
        self._is_connected = False
        self._callback: Optional[Callable[[str, bytes], None]] = None
        self._setup_callbacks()

    def _setup_callbacks(self):
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._is_connected = True
            print(f"Connected to MQTT broker ({self.broker_address}:{self.port})")
        elif rc == 5:
            raise ProtocolAuthenticationError("MQTT authentication failed (rc=5)")
        else:
            raise ProtocolConnectionError(f"MQTT connection failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        self._is_connected = False
        print(f"MQTT broker disconnected (rc={rc})")

    def _on_message(self, client, userdata, msg):
        try:
            if self._callback:
                self._callback(msg.topic, msg.payload)
        except Exception as e:
            raise ProtocolDecodeError(f"MQTT message decoding failed: {e}")

    def connect(self) -> bool:
        try:
            self.client.connect(self.broker_address, self.port, self.timeout)
            self.client.loop_start()
            return True
        except mqtt.MQTTException as e:
            raise ProtocolError(f"MQTT connection error: {e}")
        except Exception as e:
            raise ProtocolConnectionError(f"MQTT connection failed: {e}")

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f"Exception occurred while disconnecting MQTT: {e}")
        finally:
            self._is_connected = False

    def publish(self, topic: str, message: str, qos: int = 0) -> bool:
        try:
            result = self.client.publish(topic, message, qos)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT message publish failed (rc={result.rc})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT message publish failed: {e}")

    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 0) -> bool:
        try:
            self._callback = callback
            result, _ = self.client.subscribe(topic, qos)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT subscription failed: {e}")

    def unsubscribe(self, topic: str) -> bool:
        try:
            result, _ = self.client.unsubscribe(topic)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
            return True
        except Exception as e:
            raise ProtocolError(f"MQTT subscription failed: {e}")

    @property
    def is_connected(self) -> bool:
        return self._is_connected
