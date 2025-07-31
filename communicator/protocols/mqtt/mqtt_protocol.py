import paho.mqtt.client as mqtt
import threading
import time
from typing import Optional, Callable, Dict
from communicator.interfaces.protocol import PubSubProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolDecodeError,
    ProtocolAuthenticationError,
    ProtocolError,
)
import logging

logger = logging.getLogger(__name__)
import queue


class MQTTProtocol(PubSubProtocol):
    """
    범용 MQTT 프로토콜 구현 클래스 (paho-mqtt 기반)

    주요 기능 및 신뢰성 보장:
    - 자동 재연결 시 구독 복구 (subscribe 정보 내부 저장 및 재연결 후 자동 재구독)
    - publish 실패 시 내부 큐에 저장, 연결 복구 시 순차 재전송 (데이터 유실 방지)
    - blocking/non-blocking 모드 모두 지원, blocking 모드 graceful shutdown 지원
    - 내부 동시성 제어를 위한 Lock/Queue 활용 (thread-safe)

    사용법/제약사항:
    - subscribe와 publish는 thread-safe하게 동작합니다.
    - blocking 모드(loop_forever)는 stop_loop()로 안전하게 종료 가능
    - subscribe 시 topic/qos/callback이 내부에 저장되며, 재연결 시 자동 복구됩니다.
    - publish 실패(네트워크 단절 등) 시 메시지는 큐에 저장되어 복구 후 자동 재전송됩니다.
    - publish queue의 최대 크기, 재시도 정책 등은 필요에 따라 확장 가능
    """

    def __init__(
        self,
        broker_address: str,
        port: int = 1883,
        timeout: int = 60,
        keepalive: int = 60,
        mode: str = "non-blocking",
        session_expiry_interval: int = 3600,
        max_reconnect_attempts: int = 10,
        reconnect_initial_delay: int = 1,
        reconnect_max_delay: int = 60,
        heartbeat_check_ratio: float = 0.5,
        publish_queue_maxsize: int = 1000,
    ):
        """
        MQTTProtocol 인스턴스를 초기화합니다.

        Args:
            broker_address (str): MQTT 브로커 주소
            port (int, optional): 포트 번호 (기본값: 1883)
            timeout (int, optional): 연결 타임아웃 (기본값: 60초)
            keepalive (int, optional): Keep-alive 간격 (기본값: 60초)
            mode (str, optional): 'blocking' 또는 'non-blocking' (기본값: 'non-blocking')
            publish_queue_maxsize (int, optional): publish 큐 최대 크기
            session_expiry_interval (int, optional): 세션 만료 시간 (기본값: 3600초)
            max_reconnect_attempts (int, optional): 재연결 최대 시도 횟수 (기본값: 10)
            reconnect_initial_delay (int, optional): 재연결 초기 지연 시간 (기본값: 1초)
            reconnect_max_delay (int, optional): 재연결 최대 지연 시간 (기본값: 60초)
            heartbeat_check_ratio (float, optional): heartbeat 확인 비율 (기본값: 0.5)
        """
        self.broker_address = broker_address
        self.port = port
        self.timeout = timeout
        self.keepalive = keepalive
        self.mode = mode
        self.client = mqtt.Client(clean_session=False)
        self._is_connected = False
        self._callback: Optional[Callable[[str, bytes], None]] = None
        self._heartbeat_thread = None
        self._heartbeat_stop_event = threading.Event()
        self._last_heartbeat = time.time()
        self.session_expiry_interval = session_expiry_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_initial_delay = reconnect_initial_delay
        self.reconnect_max_delay = reconnect_max_delay
        self.heartbeat_check_ratio = heartbeat_check_ratio

        self._subscriptions: Dict[str, Dict] = {}
        self._publish_queue = queue.Queue(maxsize=publish_queue_maxsize)
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._blocking_thread: Optional[threading.Thread] = None

        self._setup_callbacks()
    
    def _update_heartbeat(self):
        """브로커 이벤트가 발생할 때마다 heartbeat 갱신."""
        self._last_heartbeat = time.time()

    def _setup_callbacks(self):
        """
        paho-mqtt 클라이언트에 콜백 함수를 등록합니다.
        (on_connect, on_disconnect, on_message)
        """
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = lambda *a, **k: self._update_heartbeat()
        self.client.on_subscribe = lambda *a, **k: self._update_heartbeat()
        self.client.on_log = lambda *a, **k: self._update_heartbeat()

    def _on_connect(self, client, userdata, flags, rc):
        """
        MQTT 브로커 연결 시 호출되는 콜백 함수입니다.
        연결 성공/실패/인증오류에 따라 상태를 갱신하거나 예외를 발생시킵니다.

        연결 성공 시 내부 상태를 갱신하고, 실패 시 에러를 로깅합니다.
        paho-mqtt 콜백 내에서 예외를 직접 raise하는 것은 paho-mqtt의 네트워크 루프를
        중단시킬 수 있으므로, 여기서는 로깅만 수행하고 연결 상태 관리는 connect 메서드와
        heartbeat 모니터에서 처리합니다.
        """
        if rc == 0:
            self._is_connected = True
            self._update_heartbeat()
            logger.info(f"Connected to MQTT broker ({self.broker_address}:{self.port})")
        else:
            logger.error("MQTT connection failed (rc=%s)", rc)

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
        self._update_heartbeat()
        logger.info("Disconnected from MQTT broker (rc=%s)", rc)

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
        self._update_heartbeat()
        try:
            sub = self._subscriptions.get(msg.topic)
            if sub and "callback" in sub:
                sub["callback"](msg.topic, msg.payload)
        except Exception as e:
            logger.exception("MQTT message decoding failed on topic %s: %s", msg.topic, e)

    def _wait_for_connection(self):
        """
        지정된 타임아웃 시간 동안 연결이 수립되기를 기다립니다.

        Raises:
            ProtocolConnectionError: 타임아웃 발생 시
        """
        start_time = time.time()
        while not self._is_connected and time.time() - start_time < self.timeout:
            time.sleep(0.1)

        if not self._is_connected:
            self.client.loop_stop() # 연결 실패 시 루프 정리
            raise ProtocolConnectionError("MQTT connection timeout")

    def connect(self) -> bool:
        """
        MQTT 브로커에 연결을 시도합니다.

        - blocking 모드: 사용자가 connect()만 호출하면 내부적으로 loop_forever()를 메인 스레드에서 직접 실행하며, KeyboardInterrupt 등으로 graceful shutdown이 자동 처리됩니다.
        - non-blocking 모드: 내부적으로 loop_start() 및 heartbeat 모니터를 사용합니다.
        - 사용자는 mode만 지정하면 되고, 별도의 루프/스레드/종료 관리가 필요 없습니다.

        Returns:
            bool: 연결 성공 시 True
        Raises:
            ProtocolError: paho-mqtt 예외 발생 시
            ProtocolConnectionError: 기타 예외 발생 시
        """
        try:
            props = None
            if hasattr(mqtt, "Properties") and hasattr(mqtt, "SESSION_EXPIRY_INTERVAL"):
                props = mqtt.Properties(mqtt.PacketTypes.CONNECT)
                props.SessionExpiryInterval = self.session_expiry_interval
                self.client.connect(
                    self.broker_address,
                    self.port,
                    self.keepalive,
                    clean_session=False,
                    properties=props,
                )
            else:
                self.client.connect(
                    self.broker_address,
                    self.port,
                    self.keepalive,
                    clean_session=False,
                )
            if self.mode == "blocking":
                self._wait_for_connection()

                self._start_heartbeat_monitor()

                try:
                    self.client.loop_forever()
                except KeyboardInterrupt:
                    logger.info("MQTT blocking loop interrupted by user.")
                    self.disconnect()

                # loop_forever()는 무한루프라 보통 이 아래 코드는 실행되지 않음
                return True

            else:
                self.client.loop_start()
                self._wait_for_connection()
                self._start_heartbeat_monitor()
                return True

        except Exception as e:
            raise ProtocolConnectionError(f"MQTT connection failed: {e}")

    def disconnect(self):
        """
        MQTT 브로커와의 연결을 해제합니다.
        내부 상태를 초기화합니다.
        shutdown 이벤트를 발생시켜 blocking 모드도 안전하게 종료합니다.
        """
        try:
            self._shutdown_event.set()
            self._stop_heartbeat_monitor()
            self.client.loop_stop()
            self.client.disconnect()

            if self._blocking_thread and self._blocking_thread.is_alive():
                self._blocking_thread.join(timeout=2.0)

        except Exception as e:
            logger.exception(f"Exception occurred while disconnecting MQTT: {e}")
        finally:
            self._is_connected = False

    def publish(self, topic: str, message: str, qos: int = 1) -> bool:
        """
        지정한 토픽에 메시지를 발행(Publish)합니다.
        실패 시 메시지는 내부 큐에 저장되어, 연결 복구 후 자동 재전송됩니다.
        Thread-safe하게 동작합니다.
        """
        with self._lock:
            if not self.is_connected:
                # 연결이 안 되어 있으면 큐잉
                try:
                    self._publish_queue.put_nowait((topic, message, qos))
                except queue.Full:
                    logger.error("Publish queue is full. Message to %s dropped.", topic)
                    raise ProtocolError("Publish queue is full. Message dropped.")
                return False
            try:
                result = self.client.publish(topic, message, qos)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    # 발행 실패 시 큐잉
                    self._publish_queue.put_nowait((topic, message, qos))
                    raise ProtocolValidationError(f"MQTT message publish failed (rc={result.rc})")
                return True
            except ProtocolValidationError:
                raise ProtocolValidationError("MQTT message publish failed")
            except Exception as e:
                # 예외 발생 시 큐잉
                try:
                    self._publish_queue.put_nowait((topic, message, qos))
                except queue.Full:
                    logger.error("Publish queue is full. Message dropped.")
                raise ProtocolError(f"MQTT message publish failed: {e}")

    def subscribe(self, topic: str, callback: Callable[[str, bytes], None], qos: int = 1) -> bool:
        """
        지정한 토픽을 구독(Subscribe)하며, 메시지 수신 시 콜백을 등록합니다.
        구독 정보는 내부에 저장되어 재연결 시 자동 복구됩니다.
        Thread-safe하게 동작합니다.
        """
        with self._lock:
            self._subscriptions[topic] = {"qos": qos, "callback": callback}
            result, _ = self.client.subscribe(topic, qos)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
            return True

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
        result, _ = self.client.unsubscribe(topic)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise ProtocolValidationError(f"MQTT subscription failed (rc={result})")
        self._subscriptions.pop(topic, None)
        return True

    def _start_heartbeat_monitor(self):
        """
        Keep-alive 모니터링 스레드를 시작합니다.
        """
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_stop_event.clear()
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
            self._heartbeat_thread.start()

    def _stop_heartbeat_monitor(self):
        """
        Keep-alive 모니터링 스레드를 중지합니다.
        """
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_stop_event.set()
            self._heartbeat_thread.join(timeout=1.0)

    def _heartbeat_monitor(self):
        """
        Keep-alive 모니터링을 수행하는 백그라운드 스레드입니다.
        연결이 끊어진 것을 감지하면 자동으로 재연결을 시도합니다.
        shutdown 이벤트가 발생하면 안전하게 종료됩니다.
        """
        delay = self.reconnect_initial_delay
        max_delay = self.reconnect_max_delay
        attempts = 0
        while not self._heartbeat_stop_event.is_set() and not self._shutdown_event.is_set():
            try:
                if self._is_connected:
                    current_time = time.time()
                    if current_time - self._last_heartbeat > self.keepalive * 1.5:
                        logger.warning("Keep-alive timeout detected, attempting reconnection...")
                        if self._attempt_reconnection():
                            delay = self.reconnect_initial_delay
                            attempts = 0
                            self._last_heartbeat = time.time()
                        else:
                            attempts += 1
                            if attempts >= self.max_reconnect_attempts:
                                logger.error("Max reconnection attempts reached. Stopping monitor.")
                                break
                            logger.warning("Reconnection failed. Retrying in %d seconds...", delay)
                            time.sleep(delay)
                            delay = min(delay * 2, max_delay)
                        self._last_heartbeat = current_time
                self._heartbeat_stop_event.wait(self.keepalive * self.heartbeat_check_ratio)
            except Exception as e:
                logger.exception(f"Heartbeat monitor error: {e}")
                time.sleep(5)

    def _attempt_reconnection(self) -> bool:
        """
        연결이 끊어졌을 때 자동 재연결을 시도합니다.
        성공 시 구독 복구 및 publish 큐 재전송을 수행합니다.
        """
        try:
            if self._is_connected:
                self.client.disconnect()
            self.client.reconnect()
            self._is_connected = True
            self._update_heartbeat()
            logger.info(f"MQTT reconnection successful to {self.broker_address}:{self.port}")
            # 구독 복구
            self._recover_subscriptions()
            time.sleep(0.5)
            # publish 큐 재전송
            self._flush_publish_queue()
            return True
        except Exception as e:
            logger.error("MQTT reconnection failed: %s", str(e).replace('\n', ' ').replace('\r', ' '))
            self._is_connected = False
            return False

    def _recover_subscriptions(self):
        """
        내부에 저장된 구독 정보를 모두 재구독합니다.
        """
        with self._lock:
            for topic, sub in self._subscriptions.items():
                try:
                    self.client.subscribe(topic, sub["qos"])
                except Exception as e:
                    logger.warning(f"Failed to recover subscription for topic {topic}: {e}")

    def _flush_publish_queue(self):
        """
        publish 큐에 쌓인 메시지를 모두 재전송합니다.
        """
        with self._lock:
            while not self._publish_queue.empty() and self.is_connected:
                try:
                    topic, message, qos = self._publish_queue.get_nowait()
                    self.client.publish(topic, message, qos)
                except Exception as e:
                    logger.warning(f"Failed to resend queued message: {e}")
                    break

    def stop_loop(self):
        """
        blocking 모드에서 안전하게 종료하려면 이 메서드를 호출하세요.
        shutdown 이벤트를 발생시키고, 내부 스레드를 안전하게 정리합니다.
        """
        self._shutdown_event.set()
        if self._blocking_thread and self._blocking_thread.is_alive():
            self._blocking_thread.join(timeout=2.0)

    @property
    def is_connected(self) -> bool:
        """
        현재 MQTT 브로커와의 연결 상태를 반환합니다.

        Returns:
            bool: 연결되어 있으면 True, 아니면 False
        """
        return self._is_connected and self.client.is_connected()
