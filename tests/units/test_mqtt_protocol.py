import pytest
from unittest.mock import MagicMock
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, MQTTConfig
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
    config = MQTTConfig(
        broker_address="test.mosquitto.org",
        port=1883,
        mode="non-blocking"
    )
    return MQTTProtocol(config)


def test_connect_success(protocol, mock_client):
    """MQTTProtocol.connect 성공 시나리오 테스트."""
    mock_client.is_connected.return_value = True
    assert protocol.connect() is True
    mock_client.connect.assert_called_once()


def test_connect_failure(protocol, mock_client):
    """MQTTProtocol.connect 실패 시나리오 테스트."""
    mock_client.connect.side_effect = Exception("fail")
    with pytest.raises(ProtocolConnectionError):
        protocol.connect()


def test_disconnect(protocol, mock_client):
    """MQTTProtocol.disconnect 성공 시나리오 테스트."""
    protocol.disconnect()
    mock_client.loop_stop.assert_called_once()
    mock_client.disconnect.assert_called_once()


def test_blocking_thread_cleanup(protocol):
    """blocking thread 정리 테스트"""
    protocol._blocking_thread = MagicMock()
    protocol._blocking_thread.is_alive.return_value = True
    protocol.disconnect()
    protocol._blocking_thread.join.assert_called_once()


def test_publish_success(protocol, mock_client):
    """MQTTProtocol.publish 성공 시나리오 테스트."""
    mock_client.is_connected.return_value = True
    mock_client.publish.return_value.rc = 0
    assert protocol.publish("topic", "message") is True


def test_publish_not_connected(protocol, mock_client):
    """연결이 되지 않은 상태에서 publish 호출 시 실패 테스트"""
    mock_client.is_connected.return_value = False
    assert protocol.publish("topic", "offline") is False


def test_publish_error(protocol, mock_client):
    """MQTTProtocol.publish 오류 발생 테스트."""
    mock_client.is_connected.return_value = True
    mock_client.publish.side_effect = Exception("publish error")
    assert protocol.publish("topic", "message") is False


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
    callback = lambda t, m: called.append((t, m))
    protocol._subscriptions["topic"] = (0, callback)  # (qos, callback) 튜플 형태
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)
    assert called[0] == ("topic", b"data")


def test_on_message_with_exception(protocol):
    """MQTTProtocol._on_message 예외 발생 테스트."""
    error_callback = lambda t, m: 1 / 0
    protocol._subscriptions["topic"] = (0, error_callback)  # (qos, callback) 튜플 형태
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 발생해도 죽지 않아야 함


def test_on_connect_callback(protocol, mock_client):
    """MQTTProtocol._on_connect 콜백 테스트."""
    callback = lambda t, m: None
    protocol._subscriptions["topic"] = (0, callback)  # (qos, callback) 튜플 형태
    mock_client.subscribe.return_value = (0, 1)  # 성공 반환
    protocol._on_connect(mock_client, None, None, 0)
    mock_client.subscribe.assert_called_once_with("topic", 0)


def test_on_disconnect_callback(protocol, mock_client):
    """MQTTProtocol._on_disconnect 콜백 테스트."""
    protocol._on_disconnect(mock_client, None, 1)  # rc != 0이면 unexpected disconnection


def test_is_connected_property(protocol, mock_client):
    """MQTTProtocol.is_connected 프로퍼티 테스트."""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    assert protocol.is_connected is True



