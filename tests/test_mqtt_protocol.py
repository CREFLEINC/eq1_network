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
