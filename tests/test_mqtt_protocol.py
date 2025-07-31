import pytest
import time
import queue
from unittest.mock import MagicMock
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)


@pytest.fixture
def mock_client(monkeypatch):
    """paho-mqtt.Client를 Mock으로 치환"""
    mock_client = MagicMock()
    monkeypatch.setattr(
        "communicator.protocols.mqtt.mqtt_protocol.mqtt.Client",
        lambda *a, **k: mock_client
    )
    return mock_client


@pytest.fixture
def protocol(mock_client):
    """MQTTProtocol의 테스트용 인스턴스를 생성합니다."""
    return MQTTProtocol("localhost", port=1883, mode="non-blocking", publish_queue_maxsize=5)


def test_connect_success(protocol, mock_client):
    """MQTTProtocol.connect 성공 시나리오 테스트."""
    mock_client.is_connected.return_value = True
    protocol._is_connected = True
    assert protocol.connect() is True
    mock_client.connect.assert_called_once()


def test_connect_failure(protocol, mock_client):
    """MQTTProtocol.connect 실패 시나리오 테스트."""
    mock_client.connect.side_effect = Exception("fail")
    with pytest.raises(ProtocolConnectionError):
        protocol.connect()


def test_disconnect(protocol, mock_client):
    """MQTTProtocol.disconnect 성공 시나리오 테스트."""
    protocol._is_connected = True
    protocol.disconnect()
    assert protocol._is_connected is False
    mock_client.loop_stop.assert_called_once()
    mock_client.disconnect.assert_called_once()


def test_stop_loop(protocol):
    """stop_loop() 호출 시 shutdown_event 세팅과 join 동작 테스트"""
    protocol._blocking_thread = MagicMock()
    protocol._blocking_thread.is_alive.return_value = True
    protocol.stop_loop()
    assert protocol._shutdown_event.is_set()


def test_publish_success(protocol, mock_client):
    """MQTTProtocol.publish 성공 시나리오 테스트."""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    mock_client.publish.return_value.rc = 0
    assert protocol.publish("topic", "message") is True


def test_publish_failure_queue(protocol, mock_client):
    """MQTTProtocol.publish 실패 시나리오 테스트."""
    protocol._is_connected = False
    assert protocol.publish("topic", "offline") is False
    assert not protocol._publish_queue.empty()


def test_publish_queue_full(protocol, mock_client):
    """MQTTProtocol.publish 큐가 가득 차는 경우 테스트."""
    protocol._is_connected = False
    for _ in range(5):
        protocol._publish_queue.put_nowait(("t", "m", 1))
    with pytest.raises(ProtocolError):
        protocol.publish("topic", "overflow")


def test_subscribe_unsubscribe_success(protocol, mock_client):
    """MQTTProtocol.subscribe/unsubscribe 성공 시나리오 테스트."""
    mock_client.subscribe.return_value = (0, 1)
    assert protocol.subscribe("topic", lambda t, m: None)
    mock_client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")


def test_subscribe_failure(protocol, mock_client):
    """MQTTProtocol.subscribe 실패 시나리오 테스트."""
    mock_client.subscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("bad", lambda t, m: None)


def test_unsubscribe_failure(protocol, mock_client):
    """MQTTProtocol.unsubscribe 실패 시나리오 테스트."""
    mock_client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("bad")


def test_on_message_callback(protocol):
    """MQTTProtocol._on_message 콜백 테스트."""
    called = []
    protocol._subscriptions["topic"] = {"qos": 1, "callback": lambda t, m: called.append((t, m))}
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)
    assert called[0] == ("topic", b"data")


def test_on_message_with_exception(protocol):
    """MQTTProtocol._on_message 예외 발생 테스트."""
    protocol._subscriptions["topic"] = {"qos": 1, "callback": lambda t, m: 1 / 0}
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 발생해도 죽지 않아야 함


def test_on_message_no_subscription(protocol):
    """구독되지 않은 토픽의 메시지 수신 테스트"""
    msg = type("msg", (), {"topic": "unknown", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 없이 통과해야 함


def test_on_message_no_callback(protocol):
    """콜백이 없는 구독의 메시지 수신 테스트"""
    protocol._subscriptions["topic"] = {"qos": 1}  # callback 없음
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 없이 통과해야 함


def test_attempt_reconnection(protocol, mock_client):
    """MQTTProtocol._attempt_reconnection 성공 시나리오 테스트."""
    protocol._subscriptions["topic"] = {"qos": 1, "callback": lambda t, m: None}
    protocol._publish_queue.put(("topic", "msg", 1))
    assert protocol._attempt_reconnection()
    assert protocol._publish_queue.empty()


def test_flush_publish_queue(protocol, mock_client):
    """MQTTProtocol._flush_publish_queue 성공 시나리오 테스트."""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    protocol._publish_queue.put(("topic", "msg", 1))
    protocol._flush_publish_queue()
    assert protocol._publish_queue.empty()


def test_recover_subscriptions(protocol, mock_client):
    """MQTTProtocol._recover_subscriptions 성공 시나리오 테스트."""
    protocol._subscriptions = {"topic": {"qos": 1, "callback": lambda t, m: None}}
    protocol._recover_subscriptions()
    mock_client.subscribe.assert_called_once_with("topic", 1)


def test_is_connected_property(protocol, mock_client):
    """MQTTProtocol.is_connected 프로퍼티 테스트."""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    assert protocol.is_connected is True


def test_start_and_stop_heartbeat_monitor(protocol):
    """MQTTProtocol._start_heartbeat_monitor와 _stop_heartbeat_monitor가 정상 동작하는지 테스트"""
    protocol._start_heartbeat_monitor()
    assert protocol._heartbeat_thread.is_alive()
    protocol._stop_heartbeat_monitor()
    assert not protocol._heartbeat_thread.is_alive()


def test_heartbeat_monitor_loop(protocol):
    """MQTTProtocol._heartbeat_monitor를 한 번 실행하고 종료 이벤트로 빠르게 빠져나오는 경로 테스트"""
    # 설정: 연결된 상태, 이벤트 즉시 종료
    protocol._is_connected = True
    protocol._heartbeat_stop_event.set()
    # 강제로 한 번만 실행하도록 호출
    protocol._heartbeat_monitor()


def test_on_connect_success(protocol):
    """_on_connect 성공 시나리오 테스트"""
    protocol._on_connect(None, None, None, 0)
    assert protocol._is_connected is True


def test_on_connect_failure(protocol):
    """_on_connect 실패 시나리오 테스트"""
    protocol._on_connect(None, None, None, 1)
    assert protocol._is_connected is False


def test_on_disconnect(protocol):
    """_on_disconnect 콜백 테스트"""
    protocol._is_connected = True
    protocol._on_disconnect(None, None, 0)
    assert protocol._is_connected is False


def test_wait_for_connection_timeout(protocol, mock_client):
    """_wait_for_connection 타임아웃 테스트"""
    protocol.timeout = 0.1
    protocol._is_connected = False
    with pytest.raises(ProtocolConnectionError):
        protocol._wait_for_connection()


def test_wait_for_connection_success(protocol):
    """_wait_for_connection 성공 테스트"""
    protocol._is_connected = True
    protocol._wait_for_connection()  # 예외 없이 통과해야 함


def test_publish_rc_failure(protocol, mock_client):
    """publish에서 rc 실패 시나리오 테스트"""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    mock_client.publish.return_value.rc = 1  # 실패 코드
    with pytest.raises(ProtocolValidationError):
        protocol.publish("topic", "message")


def test_publish_exception(protocol, mock_client):
    """publish에서 예외 발생 시나리오 테스트"""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    mock_client.publish.side_effect = Exception("test error")
    with pytest.raises(ProtocolError):
        protocol.publish("topic", "message")


def test_publish_exception_queue_full(protocol, mock_client):
    """publish 예외 발생 시 큐가 가득 찬 경우 테스트"""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    mock_client.publish.side_effect = Exception("test error")
    # 큐를 가득 채움
    for _ in range(5):
        protocol._publish_queue.put_nowait(("t", "m", 1))
    with pytest.raises(ProtocolError):
        protocol.publish("topic", "message")


def test_attempt_reconnection_failure(protocol, mock_client):
    """_attempt_reconnection 실패 시나리오 테스트"""
    mock_client.reconnect.side_effect = Exception("reconnect failed")
    assert protocol._attempt_reconnection() is False
    assert protocol._is_connected is False


def test_recover_subscriptions_failure(protocol, mock_client):
    """_recover_subscriptions에서 예외 발생 테스트"""
    protocol._subscriptions = {"topic": {"qos": 1, "callback": lambda t, m: None}}
    mock_client.subscribe.side_effect = Exception("subscribe failed")
    protocol._recover_subscriptions()  # 예외 발생해도 죽지 않아야 함


def test_flush_publish_queue_failure(protocol, mock_client):
    """_flush_publish_queue에서 예외 발생 테스트"""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    protocol._publish_queue.put(("topic", "msg", 1))
    mock_client.publish.side_effect = Exception("publish failed")
    protocol._flush_publish_queue()  # 예외 발생해도 죽지 않아야 함


def test_heartbeat_monitor_timeout_and_reconnect(protocol, mock_client):
    """heartbeat 타임아웃 감지 및 재연결 시나리오 테스트"""
    protocol._is_connected = True
    protocol._last_heartbeat = time.time() - 200  # 오래된 heartbeat
    protocol._attempt_reconnection = MagicMock(return_value=True)
    
    # wait 메서드를 mock하여 즉시 리턴하도록 설정
    original_wait = protocol._heartbeat_stop_event.wait
    call_count = 0
    def mock_wait(timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return False  # 첫 번째는 타임아웃 체크 실행
        return True  # 두 번째부터는 종료
    
    protocol._heartbeat_stop_event.wait = mock_wait
    protocol._heartbeat_monitor()
    protocol._attempt_reconnection.assert_called_once()


def test_heartbeat_monitor_max_attempts(protocol, mock_client):
    """heartbeat 모니터에서 최대 재연결 시도 횟수 초과 테스트"""
    protocol._is_connected = True
    protocol._last_heartbeat = time.time() - 200
    protocol._attempt_reconnection = MagicMock(return_value=False)
    protocol.max_reconnect_attempts = 1
    
    # wait 메서드를 mock하여 즉시 리턴하도록 설정
    call_count = 0
    def mock_wait(timeout):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # 첫 번째와 두 번째는 실행
            return False
        return True  # 세 번째부터는 종료
    
    protocol._heartbeat_stop_event.wait = mock_wait
    protocol._heartbeat_monitor()


def test_heartbeat_monitor_exception(protocol, monkeypatch):
    """heartbeat 모니터에서 예외 발생 테스트"""
    protocol._is_connected = True
    
    # time.time()에서 예외 발생하도록 설정
    call_count = 0
    def mock_time():
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # 두 번째 호출에서 예외 발생
            raise Exception("time error")
        return time.time()
    
    monkeypatch.setattr("time.time", mock_time)
    
    # wait 메서드를 mock하여 즉시 리턴하도록 설정
    wait_count = 0
    def mock_wait(timeout):
        nonlocal wait_count
        wait_count += 1
        if wait_count <= 2:  # 두 번 실행 후 종료
            return False
        return True
    
    protocol._heartbeat_stop_event.wait = mock_wait
    protocol._heartbeat_monitor()  # 예외 발생해도 죽지 않아야 함


def test_disconnect_with_blocking_thread(protocol):
    """blocking 스레드가 있을 때 disconnect 테스트"""
    protocol._blocking_thread = MagicMock()
    protocol._blocking_thread.is_alive.return_value = True
    protocol.disconnect()
    protocol._blocking_thread.join.assert_called_once_with(timeout=2.0)


def test_disconnect_exception(protocol, mock_client):
    """disconnect에서 예외 발생 테스트"""
    mock_client.disconnect.side_effect = Exception("disconnect failed")
    protocol.disconnect()  # 예외 발생해도 죽지 않아야 함
    assert protocol._is_connected is False


def test_connect_blocking_mode(protocol, mock_client):
    """blocking 모드 connect 테스트"""
    protocol.mode = "blocking"
    protocol._is_connected = True
    mock_client.loop_forever.side_effect = KeyboardInterrupt()
    protocol.connect()
    mock_client.loop_forever.assert_called_once()


def test_connect_with_properties(protocol, mock_client, monkeypatch):
    """MQTT Properties를 사용한 connect 테스트"""
    # mqtt 모듈에 Properties 속성이 있는 것처럼 설정
    mock_mqtt = MagicMock()
    mock_mqtt.Properties = MagicMock()
    mock_mqtt.PacketTypes.CONNECT = "CONNECT"
    mock_mqtt.SESSION_EXPIRY_INTERVAL = "SESSION_EXPIRY_INTERVAL"
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.mqtt", mock_mqtt)
    
    protocol._is_connected = True
    protocol.connect()
    mock_mqtt.Properties.assert_called_once()


def test_update_heartbeat(protocol):
    """_update_heartbeat 메서드 테스트"""
    old_time = protocol._last_heartbeat
    time.sleep(0.01)
    protocol._update_heartbeat()
    assert protocol._last_heartbeat > old_time


def test_setup_callbacks(protocol, mock_client):
    """_setup_callbacks 메서드 테스트"""
    protocol._setup_callbacks()
    assert mock_client.on_connect is not None
    assert mock_client.on_disconnect is not None
    assert mock_client.on_message is not None
    assert mock_client.on_publish is not None
    assert mock_client.on_subscribe is not None
    assert mock_client.on_log is not None
