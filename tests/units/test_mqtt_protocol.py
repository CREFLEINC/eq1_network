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
        broker_address="broker.emqx.io",
        port=1883,
        mode="non-blocking"
    )
    return MQTTProtocol(config)


@pytest.mark.unit
def test_connect_success(protocol, mock_client):
    """MQTTProtocol.connect 성공 시나리오 테스트."""
    mock_client.connect.return_value = 0
    # simulate loop_start triggers on_connect
    mock_client.loop_start.side_effect = lambda: protocol._on_connect(mock_client, None, None, 0)
    assert protocol.connect() is True
    mock_client.connect.assert_called_once()


@pytest.mark.unit
def test_connect_failure(protocol, mock_client):
    """MQTTProtocol.connect 실패 시나리오 테스트."""
    mock_client.connect.side_effect = Exception("fail")
    with pytest.raises(ProtocolConnectionError):
        protocol.connect()


@pytest.mark.unit
def test_disconnect(protocol, mock_client):
    """MQTTProtocol.disconnect 성공 시나리오 테스트."""
    protocol.disconnect()
    mock_client.loop_stop.assert_called_once()
    mock_client.disconnect.assert_called_once()


@pytest.mark.unit
def test_blocking_thread_cleanup(protocol):
    """blocking thread 정리 테스트"""
    protocol._blocking_thread = MagicMock()
    protocol._blocking_thread.is_alive.return_value = True
    protocol.disconnect()
    protocol._blocking_thread.join.assert_called_once()


@pytest.mark.unit
def test_publish_success(protocol, mock_client):
    """MQTTProtocol.publish 성공 시나리오 테스트."""
    protocol._is_connected = True
    mock_client.publish.return_value.rc = 0
    assert protocol.publish("topic", "message") is True


@pytest.mark.unit
def test_publish_not_connected(protocol, mock_client):
    """연결이 되지 않은 상태에서 publish 호출 시 실패 테스트"""
    mock_client.is_connected.return_value = False
    assert protocol.publish("topic", "offline") is False


@pytest.mark.unit
def test_publish_error(protocol, mock_client):
    """MQTTProtocol.publish 오류 발생 테스트."""
    mock_client.is_connected.return_value = True
    mock_client.publish.side_effect = Exception("publish error")
    assert protocol.publish("topic", "message") is False


@pytest.mark.unit
def test_subscribe_unsubscribe_success(protocol, mock_client):
    """MQTTProtocol.subscribe/unsubscribe 성공 시나리오 테스트."""
    mock_client.subscribe.return_value = (0, 1)
    callback = lambda t, m: None
    assert protocol.subscribe("topic", callback)

    assert "topic" in protocol._subscriptions

    mock_client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")



@pytest.mark.unit
def test_subscribe_failure(protocol, mock_client):
    """MQTTProtocol.subscribe 실패 시나리오 테스트."""
    mock_client.subscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("bad", lambda t, m: None)


@pytest.mark.unit
def test_unsubscribe_failure(protocol, mock_client):
    """MQTTProtocol.unsubscribe 실패 시나리오 테스트."""
    mock_client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("bad")


@pytest.mark.unit
def test_on_message_callback(protocol):
    """MQTTProtocol._on_message 콜백 테스트."""
    called = []
    callback = lambda t, m: called.append((t, m))
    protocol._subscriptions["topic"] = (0, callback)  # (qos, callback) 튜플 형태
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)
    assert called[0] == ("topic", b"data")


@pytest.mark.unit
def test_on_message_with_exception(protocol):
    """MQTTProtocol._on_message 예외 발생 테스트."""
    error_callback = lambda t, m: 1 / 0
    protocol._subscriptions["topic"] = (0, error_callback)  # (qos, callback) 튜플 형태
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 발생해도 죽지 않아야 함


@pytest.mark.unit
def test_on_connect_callback(protocol, mock_client):
    """MQTTProtocol._on_connect 콜백 테스트."""
    callback = lambda t, m: None
    protocol._subscriptions["topic"] = (0, callback)  # (qos, callback) 튜플 형태
    mock_client.subscribe.return_value = (0, 1)  # 성공 반환
    protocol._on_connect(mock_client, None, None, 0)
    mock_client.subscribe.assert_called_once_with("topic", 0)


@pytest.mark.unit
def test_on_disconnect_callback(protocol, mock_client):
    """MQTTProtocol._on_disconnect 콜백 테스트."""
    protocol._on_disconnect(mock_client, None, 1)  # rc != 0이면 unexpected disconnection


@pytest.mark.unit
def test_is_connected_property(protocol, mock_client):
    """MQTTProtocol.is_connected 프로퍼티 테스트."""
    protocol._is_connected = True
    mock_client.is_connected.return_value = True
    assert protocol.is_connected is True


@pytest.mark.unit
def test_mqtt_client_creation_error(monkeypatch):
    """클라이언트 생성 실패 테스트"""
    def mock_client_error(*args, **kwargs):
        raise Exception("Client creation failed")

    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.mqtt.Client", mock_client_error)
    config = MQTTConfig(broker_address="broker.emqx.io")
    
    with pytest.raises(ProtocolError):
        MQTTProtocol(config)


@pytest.mark.unit
def test_mqtt_auth_error(monkeypatch):
    """인증 설정 실패 테스트"""
    mock_client = MagicMock()
    mock_client.username_pw_set.side_effect = Exception("Auth failed")
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.mqtt.Client", lambda: mock_client)
    
    config = MQTTConfig(broker_address="broker.emqx.io", username="user", password="pass")
    
    with pytest.raises(ProtocolError):
        MQTTProtocol(config)


@pytest.mark.unit
def test_blocking_mode_connect(monkeypatch):
    """blocking 모드 연결 테스트"""
    mock_client = MagicMock()
    mock_client.connect.return_value = 0
    mock_threading = MagicMock()
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.mqtt.Client", lambda: mock_client)
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.threading.Thread", mock_threading)
    
    config = MQTTConfig(broker_address="broker.emqx.io", mode="blocking")
    protocol = MQTTProtocol(config)
    protocol._is_connected = True
    
    assert protocol.connect() is True
    mock_threading.assert_called_once()


@pytest.mark.unit
def test_connection_timeout(protocol, mock_client):
    """연결 타임아웃 테스트"""
    mock_client.connect.return_value = 0
    # loop_start는 아무것도 하지 않도록
    mock_client.loop_start.side_effect = lambda: None

    # _is_connected는 끝까지 False여야 함
    protocol._is_connected = False

    with pytest.raises(ProtocolConnectionError, match="Connection timed out"):
        protocol.connect()

@pytest.mark.unit
def test_on_connect_subscription_recovery_error(protocol, mock_client):
    """연결 시 구독 복구 오류 테스트"""
    protocol._subscriptions["topic1"] = (0, lambda t, m: None)
    mock_client.subscribe.side_effect = Exception("Subscribe error")
    
    protocol._on_connect(mock_client, None, None, 0)
    # 예외가 발생해도 연결은 성공
    assert protocol._is_connected is True


@pytest.mark.unit
def test_on_connect_subscription_recovery_failure(protocol, mock_client):
    """연결 시 구독 복구 실패 테스트"""
    protocol._subscriptions["topic1"] = (0, lambda t, m: None)
    mock_client.subscribe.return_value = (1, None)  # 실패
    
    protocol._on_connect(mock_client, None, None, 0)
    assert protocol._is_connected is True


@pytest.mark.unit
def test_on_connect_failure(protocol, mock_client):
    """연결 실패 콜백 테스트"""
    protocol._on_connect(mock_client, None, None, 1)  # rc != 0
    assert protocol._is_connected is False


@pytest.mark.unit
def test_publish_queue_and_flush(protocol, mock_client):
    """발행 큐 및 플러시 테스트"""
    protocol._is_connected = False
    
    # 연결되지 않은 상태에서 발행 시도 (큐에 저장)
    result = protocol.publish("topic", "message")
    assert result is False
    
    # 플러시 테스트
    mock_client.publish.return_value.rc = 0
    protocol._flush_publish_queue()
    mock_client.publish.assert_called_once_with("topic", "message", 0, False)


@pytest.mark.unit
def test_flush_publish_queue_error(protocol, mock_client):
    """플러시 중 오류 테스트"""
    protocol._publish_queue.put(("topic", "message", 0, False))
    mock_client.publish.side_effect = Exception("Publish error")
    
    protocol._flush_publish_queue()  # 예외가 발생해도 죽지 않아야 함


@pytest.mark.unit
def test_subscribe_error_cleanup(protocol, mock_client):
    """구독 오류 시 정리 테스트"""
    mock_client.subscribe.side_effect = Exception("Subscribe error")
    
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("topic", lambda t, m: None)
    
    # 오류 발생 시 구독 정보가 제거되어야 함
    assert "topic" not in protocol._subscriptions


@pytest.mark.unit
def test_unsubscribe_error(protocol, mock_client):
    """구독 해제 오류 테스트"""
    mock_client.unsubscribe.side_effect = Exception("Unsubscribe error")
    
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic")


@pytest.mark.unit
def test_on_message_no_callback(protocol):
    """콜백이 없는 메시지 수신 테스트"""
    msg = type("msg", (), {"topic": "unknown_topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 발생하지 않아야 함


@pytest.mark.unit
def test_on_message_non_callable(protocol):
    """콜백이 callable이 아닌 경우 테스트"""
    protocol._subscriptions["topic"] = (0, "not_callable")
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, None, msg)  # 예외 발생하지 않아야 함


@pytest.mark.unit
def test_flush_publish_queue_failure(protocol, mock_client):
    """플러시 중 발행 실패 테스트"""
    protocol._publish_queue.put(("topic", "message", 0, False))
    mock_client.publish.return_value.rc = 1  # 실패
    
    protocol._flush_publish_queue()
    # 실패해도 예외 발생하지 않아야 함


@pytest.mark.unit
def test_subscribe_result_failure_cleanup(protocol, mock_client):
    """구독 결과 실패 시 정리 테스트"""
    mock_client.subscribe.return_value = (1, None)  # 실패
    
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("topic", lambda t, m: None)
    
    # 실패 시 구독 정보가 제거되어야 함
    assert "topic" not in protocol._subscriptions


@pytest.mark.unit
def test_flush_publish_queue_get_nowait_empty(protocol, mock_client):
    """빈 큐에서 get_nowait 호출 테스트"""
    # 빈 큐에서 플러시 호출
    protocol._flush_publish_queue()
    # 예외 발생하지 않아야 함


@pytest.mark.unit
def test_flush_publish_queue_re_publish_failure(protocol, mock_client):
    """재발행 실패 테스트 (라인 190-192)"""
    # 큐에 메시지 추가
    protocol._publish_queue.put(("topic", "message", 0, False))
    
    # 재발행 실패 시뮤레이션
    mock_result = MagicMock()
    mock_result.rc = 1  # 실패
    mock_client.publish.return_value = mock_result
    
    protocol._flush_publish_queue()
    # 실패해도 예외 발생하지 않아야 함
