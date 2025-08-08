from paho.mqtt.client import Client, MQTT_ERR_SUCCESS
from uuid import uuid4
from dataclasses import dataclass, field

import threading
from typing import Optional, Callable, Any
from dataclasses import dataclass
import logging
import time
import queue as Queue
from communicator.interfaces.protocol import PubSubProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)


@dataclass
class BrokerConfig:
    """
    MQTT 브로커 설정

    Attributes:
        broker_address (str): MQTT 브로커 주소
        port (int): 포트 번호 (기본값: 1883)
        keepalive (int): Keepalive 시간 (기본값: 60초)
        mode (str): "blocking" 또는 "non-blocking" 모드 (기본값: "non-blocking")
        username (Optional[str]): 사용자 이름 (선택 사항)
        password (Optional[str]): 비밀번호 (선택 사항)
    """
    broker_address: str
    port: int = 1883
    keepalive: int = 60
    bind_address: Optional[str] = None
    mode: str = "non-blocking"
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class ClientConfig:
    """
    MQTT 클라이언트 설정

    Attributes:
        client_id (str): 클라이언트 ID (기본값: 자동 생성)
        clean_session (bool): 클린 세션 여부 (기본값: False)
        userdata (Any): 사용자 정의 데이터 (기본값: 빈 딕셔너리)
    """
    client_id: str = field(default_factory=lambda: f"mqtt-{uuid4().hex}")
    clean_session: bool = False
    userdata: Any = field(default_factory=dict)


class MQTTProtocol(PubSubProtocol):
    """MQTT 프로토콜 구현"""

    def __init__(self, broker_config: BrokerConfig, client_config: ClientConfig):
        self.broker_config = broker_config
        self.client_config = client_config
        self.handler = self.MQTTHandler(parent=self, name=self, client_id=self.client_config.client_id)

        try:
            self.client = Client(
                client_id=self.client_config.client_id,
                clean_session=self.client_config.clean_session,
                userdata=self.handler
            )
        except Exception as e:
            logging.error(f"MQTT 클라이언트 생성 실패: {e}")
            raise ProtocolError(f"MQTT 클라이언트 생성 실패: {e}")

        # 구독 정보 저장용 딕셔너리 - 토픽별 콜백 리스트
        self._subscriptions: dict[str, list[Callable]] = {}

        # 인증 설정
        if broker_config.username and broker_config.password:
            try:
                self.client.username_pw_set(
                    username=broker_config.username,
                    password=broker_config.password
                )
            except Exception as e:
                logging.error(f"MQTT 인증 설정 실패: {e}")
                raise ProtocolError(f"MQTT 인증 설정 실패: {e}")

        # 콜백 설정
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # 연결 상태 플래그
        self._is_connected = False
        
        self._publish_queue = Queue.Queue()
        self._publish_lock = threading.Lock()


    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected

    class MQTTHandler:
        """
        MQTT 핸들러 클래스
        - 연결, 메시지 수신, 구독 관리 등을 담당
        """

        def __init__(self, client_id: str, parent: "MQTTProtocol", name: str = "Device-A"):
            self.parent = parent
            self.name = name
            self.client_id = client_id

        def handle_connect(self, flags: dict):
            """
            연결 이벤트 핸들링

            Args:
                flags: 연결 플래그

            Returns:
                None
            """
            self.parent._is_connected = True
            logging.info(f"[{self.name}] - [{self.client_id}] MQTT 연결 성공")

            if flags.get("session present", False):
                logging.info(f"[{self.client_id}] 기존 세션 복원되었습니다.")
            else:
                logging.info(f"[{self.client_id}] 새로운 세션으로 연결되었습니다.")

        def handle_connect_failure(self, rc: int):
            """
            연결 실패 시 핸들링

            Args:
                rc: 연결 결과 코드 (연결 실패 시 -1)
                - -1: 소켓 연결 실패 또는 기타 네트워크 오류

            Returns:
                None
            """
            self.parent._is_connected = False
            logging.error(f"[{self.name}] - [{self.client_id}] MQTT 연결 실패 (rc={rc})")

        def handle_disconnect(self, rc: int):
            """
            연결 해제 이벤트 핸들링

            Args:
                client_id: MQTT 클라이언트 ID
                rc: 연결 결과 코드
                - 0: 정상 종료
                - 1: 연결 거부 (잘못된 사용자 이름/비밀번호)
                - 2: 브로커가 연결을 거부함 (클라이언트 ID 중복)
                - 3: 브로커가 연결을 거부함 (프로토콜 버전 불일치)
                - 4: 기타 오류

            Returns:
                None
            """
            self.parent._is_connected = False
            if rc == 0:
                logging.info(f"[{self.client_id}] 정상적으로 연결이 종료되었습니다.")
            else:
                logging.warning(f"[{self.client_id}] 예기치 않은 연결 종료 (rc={rc})")

        def handle_message(self, topic: str, payload: bytes):
            """
            메시지 수신 시 콜백 호출
            
            Args:
                topic (str): 수신한 메시지의 토픽
                payload (bytes): 수신한 메시지의 페이로드

            Returns:
                None
            """
            if topic in self.parent._subscriptions:
                callbacks = self.parent._subscriptions[topic]
                for callback in callbacks:
                    if callable(callback):
                        try:
                            callback(topic, payload)
                        except Exception as e:
                            logging.error(f"[{self.name}] - [{self.client_id}] {topic} 콜백 실행 중 오류 발생: {e}")

        def handler_flush_publish_queue(self, publish_func):
            """
            재연결 후 큐에 남아 있던 메시지를 다시 발행
            이 메서드는 연결이 복구된 후, 큐에 남아 있는 메시지를 발행합니다.

            Args:
                publish_func: MQTT 클라이언트의 publish 메서드

            Returns:
                None
            """
            logging.info("큐에 남아 있는 메시지를 발행합니다.")
            while not self.parent._publish_queue.empty():
                try:
                    topic, message, qos, retain = self.parent._publish_queue.get_nowait()
                    result = publish_func(topic, message, qos, retain)
                    if result.rc != 0:
                        logging.error(f"[{self.name}] - [{self.client_id}] 재발행 실패 - {topic}")
                except Exception as e:
                    logging.error(f"[{self.name}] - [{self.client_id}] 큐 발행 중 예외 발생: {e}")


    def _on_connect(self, client, userdata, flags, rc):
        """
        연결 성공 시 구독 복구

        Args:
            client: MQTT 클라이언트 인스턴스
            userdata: 사용자 정의 데이터
            flags: 연결 플래그
            rc: 연결 결과 코드
            - 0: 실패
            - 1: 성공
            - 2: 브로커가 연결을 거부함
            - 3: 브로커가 연결을 거부함 (잘못된 사용자 이름/비밀번호)
            - 4: 브로커가 연결을 거부함 (클라이언트 ID 중복)
            - 5: 브로커가 연결을 거부함 (프로토콜 버전 불일치)

        Returns:
            None
        """
        client_id = userdata.client_id
        if rc == 0:
            userdata.handle_connect(flags=flags)

            # 연결 성공 시, 기존 구독 복구
            for topic in self._subscriptions.keys():
                try:
                    result, _ = client.subscribe(topic=topic, qos=0)
                    if result != MQTT_ERR_SUCCESS:
                        logging.error(f"[{client_id}] 구독 복구 실패 - {topic}: {result}")
                except Exception as e:
                    logging.error(f"[{client_id}] 구독 복구 중 오류 발생 - {topic}: {e}")
            logging.info("구독 복구 완료")

            # 데이터 유실 방지 - 재연결 후 큐에 남아 있던 메시지를 다시 발행
            if not self._publish_queue.empty():
                logging.info("재연결 후 큐에 남아 있던 메시지를 발행합니다.")
            userdata.handler_flush_publish_queue(client.publish)

        else:
            userdata.handle_connect_failure(rc=rc)


    def _on_disconnect(self, client, userdata, rc):
            """
            연결 해제 시 로그

            Args:
                client: MQTT 클라이언트 인스턴스
                userdata: 사용자 정의 데이터
                rc: 연결 결과 코드
                - 0: 정상 종료
                - 1: 연결 거부 (잘못된 사용자 이름/비밀번호)
                - 2: 브로커가 연결을 거부함 (클라이언트 ID 중복)
                - 3: 브로커가 연결을 거부함 (프로토콜 버전 불일치)
                - 4: 기타 오류

            Returns:
                None
            """
            userdata.handle_disconnect(rc=rc)

    def _on_message(self, client, userdata, msg):
        """
        메시지 수신 시 호출되는 콜백 함수

        Args:
            client: MQTT 클라이언트 인스턴스
            userdata: 사용자 정의 데이터
            msg: 수신한 메시지 객체

        Returns:
            None
        """
        userdata.handle_message(
            topic=msg.topic,
            payload=msg.payload,
        )


    def connect(self) -> bool:
        """
        MQTT 브로커 연결
        이 메서드는 브로커에 연결하고, 연결 성공 시 구독을 복구합니다.

        Args:
            None

        Returns:
            bool: 연결 성공 여부

        Raises:
            ProtocolConnectionError: 연결 실패 시 예외 발생
        """
        try:
            self.client.connect(
                host=self.broker_config.broker_address,
                port=self.broker_config.port,
                keepalive=self.broker_config.keepalive,
                bind_address=self.broker_config.bind_address or ""
            )

            if self.broker_config.mode == "blocking":
                self.client.loop_forever()
            else:
                self.client.loop_start()
            
            for _ in range(10):
                logging.debug(f"브로커 연결 중... {self._is_connected}")
                if self._is_connected:
                    return True
                time.sleep(0.5)
            raise ProtocolConnectionError("연결 시간 초과")

        except Exception as e:
            raise ProtocolConnectionError(f"브로커 연결 실패: {e}")

    def disconnect(self):
        """
        MQTT 브로커 연결 해제
        이 메서드는 연결 해제 후에도 큐에 남아 있는 메시지를 발행합니다.

        Args:
            None

        Returns:
            None

        Raises:
            ProtocolError: 연결 해제 중 오류 발생
        """
        if self.broker_config.mode == "non-blocking":
            self.client.loop_stop()
        self.client.disconnect()
        
        # 연결 해제 대기 루프 (최대 5초)
        for _ in range(10):
            if not self._is_connected:
                break
            time.sleep(0.5)

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
            if not self._is_connected:
                logging.warning(f"디스커넥트 상태에서 메시지 큐에 추가: {topic}")
                self._publish_queue.put((topic, message, qos, retain))
                return False
            
            result = self.client.publish(topic, message, qos, retain)
            return result.rc == MQTT_ERR_SUCCESS
        except Exception as e:
            logging.error(f"Publish error: {e}")
            return False


    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 0) -> bool:
        """토픽 구독"""
        try:
            # 토픽이 처음 구독되는 경우만 브로커에 구독 요청
            is_new_topic = topic not in self._subscriptions
            
            # 콜백 추가
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(callback)

            if is_new_topic:
                result, _ = self.client.subscribe(topic=topic, qos=qos)
                if result != MQTT_ERR_SUCCESS:
                    # 실패 시 콜백 제거
                    self._subscriptions[topic].remove(callback)
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]
                    raise ProtocolValidationError(f"[{self.client_config.client_id}] 구독 실패: {result}")
            
            return True
        except Exception as e:
            # 실패 시 콜백 제거
            if topic in self._subscriptions and callback in self._subscriptions[topic]:
                self._subscriptions[topic].remove(callback)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]
            raise ProtocolValidationError(f"[{self.client_config.client_id}] 구독 오류: {e}")

    def unsubscribe(self, topic: str, callback: Callable[[str, bytes], None] = None) -> bool:
        """
        구독 해제
        
        Args:
            topic (str): 구독 해제할 토픽
            callback (Callable, optional): 특정 콜백만 제거. None이면 모든 콜백 제거
            
        Returns:
            bool: 해제 성공 여부
        """
        try:
            if topic not in self._subscriptions:
                return True
                
            if callback is None:
                # 모든 콜백 제거
                del self._subscriptions[topic]
                result, _ = self.client.unsubscribe(topic)
                if result != MQTT_ERR_SUCCESS:
                    raise ProtocolValidationError(f"[{self.client_config.client_id}] 구독 해제 실패: {result}")
            else:
                # 특정 콜백만 제거
                if callback in self._subscriptions[topic]:
                    self._subscriptions[topic].remove(callback)
                    # 콜백이 모두 제거되면 토픽 구독 해제
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]
                        result, _ = self.client.unsubscribe(topic)
                        if result != MQTT_ERR_SUCCESS:
                            raise ProtocolValidationError(f"[{self.client_config.client_id}] 구독 해제 실패: {result}")
            
            return True
        except Exception as e:
            logging.error(f"Unsubscribe error: {e}")
            raise ProtocolValidationError(f"[{self.client_config.client_id}] 구독 해제 오류: {e}")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    broker_config = BrokerConfig(broker_address="localhost")
    client_config = ClientConfig()
    client = MQTTProtocol(broker_config, client_config)

    connected = client.connect()
    print(f"[DEBUG] Connected: {connected}")
    if connected:
        client.publish("test/topic", "Hello from script")
        time.sleep(1)
        client.disconnect()

