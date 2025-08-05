import paho.mqtt.client as mqtt
import threading
from typing import Optional, Callable
from dataclasses import dataclass
import logging
import time

from communicator.interfaces.protocol import PubSubProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """MQTT 설정"""
    broker_address: str
    port: int = 1883
    keepalive: int = 60
    mode: str = "non-blocking"
    username: Optional[str] = None
    password: Optional[str] = None


class MQTTProtocol(PubSubProtocol):
    """MQTT 프로토콜 구현"""

    def __init__(self, config: MQTTConfig):
        self.config = config
        try:
            self.client = mqtt.Client()
        except Exception as e:
            logging.error(f"MQTT 클라이언트 생성 실패: {e}")
            raise ProtocolError(f"MQTT 클라이언트 생성 실패: {e}")
        self._subscriptions = {}
        self._blocking_thread = None

        # 인증 설정
        if config.username and config.password:
            try:
                self.client.username_pw_set(config.username, config.password)
            except Exception as e:
                logging.error(f"MQTT 인증 설정 실패: {e}")
                raise ProtocolError(f"MQTT 인증 설정 실패: {e}")
        
        # 콜백 설정
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self._is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """
        연결 성공 시 구독 복구
        
        Args:
            client: MQTT 클라이언트 인스턴스
            userdata: 사용자 정의 데이터
            flags: 연결 플래그
            rc: 연결 결과 코드
            
        Returns:
            None
        """
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self._is_connected = True
            # 기존 구독 복구
            for topic, (qos, callback) in self._subscriptions.items():
                try:
                    result, _ = client.subscribe(topic, qos)
                    if result != mqtt.MQTT_ERR_SUCCESS:
                        logger.error(f"Failed to recover subscription for {topic}: {result}")
                except Exception as e:
                    logger.error(f"Error recovering subscription for {topic}: {e}")
        else:
            logger.error(f"MQTT 연결 실패 (rc={rc})")
            self._is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        """연결 해제 시 로그"""
        self._is_connected = False
        if rc != 0:
            logger.warning("Unexpected disconnection")

    def _on_message(self, client, userdata, msg):
        """메시지 수신 시 콜백 호출"""
        topic = msg.topic
        if topic in self._subscriptions:
            _, callback = self._subscriptions[topic]
            if callable(callback):
                try:
                    callback(topic, msg.payload)
                except Exception as e:
                    logger.error(f"Message callback error: {e}")

    def connect(self) -> bool:
        """
        MQTT 브로커에 연결
        
        Returns:
            bool: 연결 성공 여부
            
        Raises:
            ProtocolConnectionError: 연결 실패 시 예외 발생
        """
        try:
            self.client.connect(
                self.config.broker_address, 
                self.config.port, 
                self.config.keepalive
            )
            
            if self.config.mode == "blocking":
                self._blocking_thread = threading.Thread(
                    target=self.client.loop_forever, 
                    daemon=True
                )
                self._blocking_thread.start()
            else:
                self.client.loop_start()
            
            return True
        except Exception as e:
            raise ProtocolConnectionError(f"Connection failed: {e}")

    def disconnect(self):
        """
        브로커 연결 해제
        
        Returns:
            None

        Raises:
            ProtocolError: 연결 해제 중 오류 발생
        """
        if self.config.mode == "non-blocking":
            self.client.loop_stop()
        self.client.disconnect()
        
        # 연결 해제 대기 루프 (최대 5초)
        for _ in range(10):
            if not self._is_connected:
                break
            time.sleep(0.5)
        
        if self._blocking_thread and self._blocking_thread.is_alive():
            self._blocking_thread.join(timeout=2.0)

    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool:
        """
        메시지 발행
        
        Args:
            topic (str): 발행할 토픽
            message (str): 발행할 메시지
            qos (int): QoS 레벨 (0, 1, 2)
            retain (bool): Retain 플래그
            
        Returns:
            bool: 발행 성공 여부
            
        Raises:
            ProtocolValidationError: 발행 실패 시 예외 발생
        """
        try:
            result = self.client.publish(topic, message, qos, retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                logger.error(f"Publish failed: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 0) -> bool:
        """토픽 구독"""
        try:
            # 구독 정보를 먼저 저장 (재연결 시 복구용)
            self._subscriptions[topic] = (qos, callback)
            
            result, _ = self.client.subscribe(topic, qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                # 실패 시 구독 정보 제거
                self._subscriptions.pop(topic, None)
                raise ProtocolValidationError(f"Subscribe failed: {result}")
        except Exception as e:
            # 실패 시 구독 정보 제거
            self._subscriptions.pop(topic, None)
            raise ProtocolValidationError(f"Subscribe error: {e}")

    def unsubscribe(self, topic: str) -> bool:
        """
        구독 해제
        
        Args:
            topic (str): 구독 해제할 토픽
            
        Returns:
            bool: 해제 성공 여부
        """
        try:
            result, _ = self.client.unsubscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self._subscriptions.pop(topic, None)
                return True
            else:
                raise ProtocolValidationError(f"Unsubscribe failed: {result}")
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            raise ProtocolValidationError(f"Unsubscribe error: {e}")

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected