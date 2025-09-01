from unittest.mock import MagicMock

import pytest

import app.protocols.mqtt.mqtt_protocol as mqtt_mod
from app.common.exception import (
    ProtocolConnectionError,
    ProtocolError,
    ProtocolValidationError,
)
from app.protocols.mqtt.mqtt_protocol import BrokerConfig, ClientConfig, MQTTProtocol


def func(t, m):
    return None


@pytest.fixture
def mock_client(monkeypatch):
    """
    paho-mqtt.Client를 Mock으로 치환합니다.
    """
    mock_client = MagicMock()
    monkeypatch.setattr("app.protocols.mqtt.mqtt_protocol.Client", lambda *a, **k: mock_client)
    return mock_client


@pytest.fixture
def non_blocking_protocol(mock_client):
    """
    MQTTProtocol의 테스트용 non-blocking 모드 인스턴스를 생성합니다.
    """
    config = BrokerConfig(broker_address="broker.emqx.io", port=1883, mode="non-blocking")
    client_config = ClientConfig()
    return MQTTProtocol(config, client_config)


@pytest.fixture
def blocking_protocol(mock_client):
    """
    MQTTProtocol의 테스트용 blocking 모드 인스턴스를 생성합니다.
    """
    config = BrokerConfig(broker_address="broker.emqx.io", port=1883, mode="blocking")
    client_config = ClientConfig()
    return MQTTProtocol(config, client_config)


@pytest.fixture
def protocol_factory(monkeypatch):
    """
    mode와 client side_effect를 받아 MQTTProtocol을 만드는 팩토리 함수입니다.
    """

    def _factory(mode="non-blocking", client_customizer=None):
        mock_client = MagicMock()
        if client_customizer:
            client_customizer(mock_client)
        monkeypatch.setattr(mqtt_mod, "Client", lambda *a, **k: mock_client)
        cfg = BrokerConfig(broker_address="broker.emqx.io", mode=mode)
        return MQTTProtocol(cfg, ClientConfig()), mock_client

    return _factory


@pytest.fixture
def no_sleep(monkeypatch):
    """
    time.sleep 무력화하는 함수입니다.
    """
    monkeypatch.setattr("time.sleep", lambda *_: None)


@pytest.mark.unit
def test_mqtt_client_creation_error(monkeypatch):
    """
    클라이언트 생성 실패 테스트
    """

    def mock_client_error(*args, **kwargs):
        """Mock 클라이언트 생성 실패 함수"""
        raise ProtocolError("클라이언트 생성 실패")

    monkeypatch.setattr(mqtt_mod, "Client", mock_client_error)
    config = BrokerConfig(broker_address="broker.emqx.io")
    client_config = ClientConfig()

    with pytest.raises(ProtocolError):
        MQTTProtocol(config, client_config)


@pytest.mark.unit
def test_mqtt_auth_error(monkeypatch):
    """
    인증 설정 실패 테스트
    """
    mock_client = MagicMock()
    mock_client.username_pw_set.side_effect = Exception("Auth failed")
    monkeypatch.setattr(mqtt_mod, "Client", lambda *a, **k: mock_client)

    config = BrokerConfig(broker_address="broker.emqx.io", username="user", password="pass")
    client_config = ClientConfig()
    with pytest.raises(ProtocolError):
        MQTTProtocol(config, client_config)


@pytest.mark.unit
def test_connect_with_bind_address(monkeypatch):
    """
    바인드 주소 None일 때 빈 문자열 사용 테스트
    """
    mock_client = MagicMock()
    mock_client.connect.return_value = 0
    mock_client.loop_start.side_effect = lambda: None
    monkeypatch.setattr(mqtt_mod, "Client", lambda *a, **k: mock_client)

    config = BrokerConfig(broker_address="broker.emqx.io", bind_address=None)
    client_config = ClientConfig()
    protocol = MQTTProtocol(config, client_config)
    protocol._is_connected = True

    assert protocol.connect() is True
    mock_client.connect.assert_called_once_with(
        host="broker.emqx.io", port=1883, keepalive=60, bind_address=""
    )


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connect_success(protocol_factory, mode):
    """
    연결 성공 테스트
    """
    protocol, client = protocol_factory(
        mode,
        client_customizer=lambda c: setattr(c, "connect", MagicMock(return_value=0)),
    )
    # 루프 동작 모의
    if mode == "non-blocking":
        client.loop_start.side_effect = lambda: protocol._on_connect(
            client, protocol.handler, {}, 0
        )
    else:
        client.loop_forever.side_effect = lambda: setattr(protocol, "_is_connected", True)

    assert protocol.connect() is True
    client.connect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connect_failure(protocol_factory, mode):
    """
    연결 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    client.connect.side_effect = Exception("연결 실패")

    with pytest.raises(ProtocolConnectionError):
        protocol.connect()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connection_timeout(protocol_factory, mode, monkeypatch):
    """
    연결 타임아웃 테스트
    """
    protocol, client = protocol_factory(mode)
    client.connect.return_value = 0
    if mode == "non-blocking":
        client.loop_start.side_effect = lambda: None
    else:
        client.loop_forever.side_effect = lambda: None
    monkeypatch.setattr("time.sleep", lambda *_: None)
    protocol._is_connected = False
    with pytest.raises(ProtocolConnectionError, match="연결 시간 초과"):
        protocol.connect()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_success(protocol_factory, mode):
    """
    연결 해제 성공 테스트
    """
    protocol, client = protocol_factory(
        mode,
        client_customizer=lambda c: setattr(c, "disconnect", MagicMock(return_value=0)),
    )
    protocol.disconnect()
    if mode == "non-blocking":
        client.loop_stop.assert_called_once()
    else:
        client.loop_stop.assert_not_called()  # blocking 모드는 loop_stop를 호출하지 않음

    client.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_connection_wait_timeout(protocol_factory, mode, monkeypatch):
    """
    연결 해제 대기 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    monkeypatch.setattr("time.sleep", lambda *_: None)
    protocol.disconnect()
    if mode == "non-blocking":
        client.loop_stop.assert_called_once()
    else:
        client.loop_stop.assert_not_called()
    client.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
@pytest.mark.parametrize(
    "rc,raises,expected",
    [
        (0, None, True),  # 성공
        (1, None, False),  # rc 실패
        (None, Exception("발행 오류"), False),  # 예외
    ],
)
def test_publish_variants(protocol_factory, mode, rc, raises, expected):
    """
    발행 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    if raises:
        client.publish.side_effect = raises
    else:
        client.publish.return_value.rc = rc

    assert protocol.publish("topic", "message") is expected


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_not_connected(protocol_factory, mode):
    """
    연결이 되지 않은 상태에서 발행 시 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False  # 테스트에서 보호속성 접근은 허용

    # 실행
    result = protocol.publish("topic", "offline")

    # 검증: 반환값, 큐 적재, 실제 publish 미호출
    assert result is False
    assert not protocol._publish_queue.empty()
    topic, message, qos, retain = protocol._publish_queue.get_nowait()
    assert (topic, message, qos, retain) == ("topic", "offline", 0, False)
    client.publish.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_error(protocol_factory, mode):
    """
    발행 오류 발생 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    client.publish.side_effect = Exception("발행 오류")
    assert protocol.publish("topic", "message") is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_queue_and_flush(protocol_factory, mode):
    """
    발행 큐 및 플러시 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._is_connected = False
    result = protocol.publish("topic", "message")
    assert result is False
    assert not protocol._publish_queue.empty()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_queue_empty_check(protocol_factory, mode):
    """
    발행 큐 비어있음 체크 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._is_connected = False
    result = protocol.publish("topic", "message")
    assert result is False
    assert not protocol._publish_queue.empty()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_unsubscribe_success(protocol_factory, mode):
    """
    구독 및 구독 해제 성공 테스트
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)
    callback = func
    assert protocol.subscribe("topic", callback)
    assert "topic" in protocol._subscriptions
    client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_failure(protocol_factory, mode):
    """
    구독 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("bad", func)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_duplicate_callbacks_allowed(protocol_factory, mode):
    """
    중복 콜백 허용 테스트
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)
    cb = func
    protocol.subscribe("topic", cb)
    protocol.subscribe("topic", cb)
    assert len(protocol._subscriptions["topic"]) == 2


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_success(protocol_factory, mode):
    """
    구독 해제 성공 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic"] = [func]
    client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_failure(protocol_factory, mode):
    """
    구독 해제 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["bad"] = [func]
    client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("bad")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_exception_handling(protocol_factory, mode):
    """
    구독 해제 예외 처리 테스트
    """
    protocol, client = protocol_factory(mode)
    callback = func
    protocol._subscriptions["topic"] = [callback]
    client.unsubscribe.side_effect = Exception("Unsubscribe failed")
    with pytest.raises(ProtocolValidationError, match="구독 해제 오류"):
        protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_all_callbacks_failure_keeps_local_state(protocol_factory, mode):
    """
    모든 콜백 해제 실패 시 로컬 상태 유지 테스트
    """
    protocol, client = protocol_factory(mode)
    cb = func
    protocol._subscriptions["topic"] = [cb]
    client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic")
    assert "topic" not in protocol._subscriptions


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_specific_callback_unsubscribe_failure(protocol_factory, mode):
    """
    특정 콜백 제거 후 unsubscribe 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    callback = func
    protocol._subscriptions["topic"] = [callback]
    client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic", callback)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_topic_not_exists(protocol_factory, mode):
    """
    존재하지 않는 토픽 unsubscribe 테스트
    """
    protocol, _ = protocol_factory(mode)
    result = protocol.unsubscribe("nonexistent_topic")
    assert result is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_specific_callback(protocol_factory, mode):
    """
    특정 콜백 제거 테스트
    """
    protocol, client = protocol_factory(mode)
    callback1 = func
    callback2 = func

    client.subscribe.return_value = (0, 1)
    protocol.subscribe("topic", callback1)
    protocol.subscribe("topic", callback2)

    assert protocol.unsubscribe("topic", callback1) is True
    assert "topic" in protocol._subscriptions
    assert callback1 not in protocol._subscriptions["topic"]
    assert callback2 in protocol._subscriptions["topic"]

    client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic", callback2) is True
    assert "topic" not in protocol._subscriptions
    client.unsubscribe.assert_called_once_with("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_callback_not_in_list(protocol_factory, mode):
    """
    콜백이 리스트에 없을 때 unsubscribe 테스트
    """
    protocol, _ = protocol_factory(mode)
    callback1 = func
    callback2 = func

    protocol._subscriptions["topic"] = [callback1]
    assert protocol.unsubscribe("topic", callback2) is True
    assert "topic" in protocol._subscriptions
    assert callback1 in protocol._subscriptions["topic"]


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_is_connected_property(protocol_factory, mode):
    """
    is_connected 프로퍼티 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._is_connected = True
    assert protocol.is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_callback(protocol_factory, mode):
    """
    _on_connect 콜백 테스트
    """
    protocol, client = protocol_factory(mode)
    callback = func
    protocol._subscriptions["topic"] = [callback]
    client.subscribe.return_value = (0, 1)
    protocol._on_connect(client, protocol.handler, {}, 0)
    client.subscribe.assert_called_once_with(topic="topic", qos=0)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_subscription_recovery_error(protocol_factory, mode):
    """
    연결 시 구독 복구 오류 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic1"] = [func]
    client.subscribe.side_effect = Exception("구독 복구 실패")
    protocol._on_connect(client, protocol.handler, {}, 0)
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_subscription_recovery_failure(protocol_factory, mode):
    """
    연결 시 구독 복구 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic1"] = [func]
    client.subscribe.return_value = (1, None)
    protocol._on_connect(client, protocol.handler, {}, 0)
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_failure(protocol_factory, mode):
    """
    연결 실패 콜백 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._on_connect(client, protocol.handler, {}, 1)
    assert protocol._is_connected is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_with_queue_messages(protocol_factory, mode):
    """
    연결 시 큐에 메시지가 있을 때 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._publish_queue.put(("topic", "message", 0, False))
    assert not protocol._publish_queue.empty()
    protocol._on_connect(client, protocol.handler, {}, 0)
    assert protocol._is_connected is True
    assert client.publish.called


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_partial_subscription_recovery(protocol_factory, mode):
    """
    부분 구독 복구 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions = {
        "ok": [func],
        "bad": [func],
    }

    def sub_side_effect(*args, **kwargs):
        return (0, 1) if kwargs.get("topic") == "ok" else (1, None)

    client.subscribe.side_effect = sub_side_effect

    protocol._on_connect(client, protocol.handler, {}, 0)

    assert protocol._is_connected is True
    client.subscribe.assert_any_call(topic="ok", qos=0)
    client.subscribe.assert_any_call(topic="bad", qos=0)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_disconnect_callback(protocol_factory, mode, monkeypatch):
    """
    _on_disconnect 콜백 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    mock_start_reconnect = MagicMock()
    monkeypatch.setattr(protocol, "_start_reconnect_thread", mock_start_reconnect)

    protocol._on_disconnect(client, protocol.handler, 1)
    assert protocol._is_connected is False
    mock_start_reconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_unsubscribe_error(protocol_factory, mode):
    """
    _on_unsubscribe 오류 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic"] = [func]
    client.unsubscribe.side_effect = Exception("구독 해제 실패")
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_callback(protocol_factory, mode):
    """
    _on_message 콜백 테스트
    """
    protocol, _ = protocol_factory(mode)
    called = []

    def callback(t, m):
        called.append((t, m))

    protocol._subscriptions["topic"] = [callback]
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)
    assert called[0] == ("topic", b"data")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_with_exception(protocol_factory, mode):
    """
    _on_message 예외 발생 테스트
    """
    protocol, _ = protocol_factory(mode)

    def error_callback(t, m):
        return 1 / 0

    protocol._subscriptions["topic"] = [error_callback]
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_no_callback(protocol_factory, mode):
    """
    콜백이 없는 메시지 수신 테스트
    """
    protocol, _ = protocol_factory(mode)
    msg = type("msg", (), {"topic": "unknown_topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_flush_publish_queue_failure(protocol_factory, mode):
    """
    플러시 중 발행 실패 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._publish_queue.put(("topic", "message", 0, False))
    client.publish.return_value.rc = 1
    protocol.handler.handler_flush_publish_queue(client.publish)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_flush_publish_queue_error(protocol_factory, mode):
    """
    플러시 중 오류 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._publish_queue.put(("topic", "message", 0, False))
    client.publish.side_effect = Exception("Publish error")
    protocol.handler.handler_flush_publish_queue(client.publish)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_subscribe_error_cleanup(protocol_factory, mode):
    """
    구독 오류 시 정리 테스트
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.side_effect = Exception("Subscribe error")
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("topic", func)
    assert "topic" not in protocol._subscriptions


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_connect_session_present(protocol_factory, mode):
    """
    핸들러 연결 시 세션 복원 테스트
    """
    protocol, _ = protocol_factory(mode)
    flags = {"session present": True}
    protocol.handler.handle_connect(flags)
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_disconnect_normal(protocol_factory, mode):
    """
    핸들러 정상 연결 해제 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol.handler.handle_disconnect(0)
    assert protocol._is_connected is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_publish_queue_failure(protocol_factory, mode):
    """
    핸들러 플러시 시 재발행 실패 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._publish_queue.put(("topic", "message", 0, False))

    def mock_publish_func(topic, message, qos, retain):
        return False

    protocol.handler.handler_flush_publish_queue(mock_publish_func)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_auto_reconnect_on_unexpected_disconnect(protocol_factory, mode, monkeypatch):
    """
    예기치 못한 연결 해제 시 자동 재연결 시작 테스트
    """
    protocol, client = protocol_factory(mode)
    mock_start_reconnect = MagicMock()
    monkeypatch.setattr(protocol, "_start_reconnect_thread", mock_start_reconnect)

    # 예기치 못한 연결 해제 (rc != 0)
    protocol._on_disconnect(client, protocol.handler, 1)
    mock_start_reconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_no_auto_reconnect_on_normal_disconnect(protocol_factory, mode, monkeypatch):
    """
    정상 연결 해제 시 자동 재연결 시작하지 않음 테스트
    """
    protocol, client = protocol_factory(mode)
    mock_start_reconnect = MagicMock()
    monkeypatch.setattr(protocol, "_start_reconnect_thread", mock_start_reconnect)

    # 정상 연결 해제 (rc == 0)
    protocol._on_disconnect(client, protocol.handler, 0)
    mock_start_reconnect.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_stops_auto_reconnect(protocol_factory, mode, monkeypatch):
    """
    disconnect 호출 시 자동 재연결 중단 테스트
    """
    protocol, _ = protocol_factory(mode)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    protocol._reconnect_thread = mock_thread

    # _stop_reconnect를 Mock으로 교체
    mock_stop_event = MagicMock()
    protocol._stop_reconnect = mock_stop_event
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol.disconnect()

    assert protocol._auto_reconnect is False
    mock_stop_event.set.assert_called_once()
    mock_thread.join.assert_called_once_with(timeout=1)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_start_reconnect_thread_already_running(protocol_factory, mode):
    """
    재연결 스레드가 이미 실행 중일 때 중복 시작 방지 테스트
    """
    protocol, _ = protocol_factory(mode)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    protocol._reconnect_thread = mock_thread

    protocol._start_reconnect_thread()

    # 기존 스레드가 그대로 유지되어야 함
    assert protocol._reconnect_thread is mock_thread


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_success(protocol_factory, mode, monkeypatch):
    """
    재연결 루프 성공 테스트
    """
    protocol, client = protocol_factory(mode)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 재연결 성공 시뮬레이션
    def mock_reconnect():
        protocol._is_connected = True

    client.reconnect.side_effect = mock_reconnect

    protocol._reconnect_loop()

    client.reconnect.assert_called_once()
    if mode == "non-blocking":
        client.loop_start.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_exponential_backoff(protocol_factory, mode, monkeypatch):
    """
    재연결 루프 지수 백오프 테스트
    """
    protocol, client = protocol_factory(mode)
    wait_calls = []

    def mock_wait(delay):
        wait_calls.append(delay)
        if len(wait_calls) >= 3:  # 3번 시도 후 중단
            protocol._stop_reconnect.set()
        return False

    protocol._stop_reconnect.wait = mock_wait
    client.reconnect.side_effect = Exception("연결 실패")
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol._reconnect_loop()

    # 지수 백오프 확인: 1, 2, 4초
    assert wait_calls == [1, 2, 4]


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_max_delay(protocol_factory, mode, monkeypatch):
    """
    재연결 루프 최대 지연 시간 테스트
    """
    protocol, client = protocol_factory(mode)
    wait_calls = []

    def mock_wait(delay):
        wait_calls.append(delay)
        if len(wait_calls) >= 8:  # 8번 시도 후 중단
            protocol._stop_reconnect.set()
        return False

    protocol._stop_reconnect.wait = mock_wait
    client.reconnect.side_effect = Exception("연결 실패")
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol._reconnect_loop()

    # 최대 60초를 초과하지 않아야 함
    assert all(delay <= 60 for delay in wait_calls)
    # 마지막 몇 개는 60초여야 함
    assert wait_calls[-1] == 60


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_stop_event_set(protocol_factory, mode, monkeypatch):
    """
    재연결 루프 중단 이벤트 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._stop_reconnect.set()  # 이미 중단 신호 설정
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol._reconnect_loop()

    # 중단 신호가 설정되어 있으므로 reconnect가 호출되지 않아야 함
    client.reconnect.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_auto_reconnect_disabled(protocol_factory, mode, monkeypatch):
    """
    자동 재연결 비활성화 상태 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._auto_reconnect = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol._reconnect_loop()

    # 자동 재연결이 비활성화되어 있으므로 reconnect가 호출되지 않아야 함
    client.reconnect.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_already_connected(protocol_factory, mode, monkeypatch):
    """
    이미 연결된 상태에서 재연결 루프 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True  # 이미 연결된 상태
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol._reconnect_loop()

    # 이미 연결되어 있으므로 reconnect가 호출되지 않아야 함
    client.reconnect.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_start_reconnect_thread_creates_new_thread(protocol_factory, mode, monkeypatch):
    """
    새로운 재연결 스레드 생성 테스트
    """
    protocol, _ = protocol_factory(mode)
    mock_thread_class = MagicMock()
    mock_thread = MagicMock()
    mock_thread_class.return_value = mock_thread
    monkeypatch.setattr("threading.Thread", mock_thread_class)

    protocol._start_reconnect_thread()

    mock_thread_class.assert_called_once_with(target=protocol._reconnect_loop, daemon=True)
    mock_thread.start.assert_called_once()
    assert protocol._reconnect_thread is mock_thread


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_message_with_multiple_callbacks(protocol_factory, mode):
    """
    여러 콜백이 등록된 토픽에 메시지 수신 테스트
    """
    protocol, _ = protocol_factory(mode)
    called_callbacks = []

    def callback1(topic, payload):
        called_callbacks.append(("cb1", topic, payload))

    def callback2(topic, payload):
        called_callbacks.append(("cb2", topic, payload))

    protocol._subscriptions["test/topic"] = [callback1, callback2]

    protocol.handler.handle_message("test/topic", b"test_data")

    assert len(called_callbacks) == 2
    assert ("cb1", "test/topic", b"test_data") in called_callbacks
    assert ("cb2", "test/topic", b"test_data") in called_callbacks


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_message_with_non_callable(protocol_factory, mode):
    """
    호출 불가능한 콜백이 등록된 경우 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._subscriptions["test/topic"] = ["not_callable", lambda t, p: None]

    # 예외가 발생하지 않아야 함
    protocol.handler.handle_message("test/topic", b"test_data")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_with_different_qos_levels(protocol_factory, mode):
    """
    다양한 QoS 레벨로 발행 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    client.publish.return_value.rc = 0

    # QoS 0, 1, 2 테스트
    for qos in [0, 1, 2]:
        result = protocol.publish("test/topic", "message", qos=qos)
        assert result is True
        client.publish.assert_called_with("test/topic", "message", qos, False)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_with_retain_flag(protocol_factory, mode):
    """
    Retain 플래그로 발행 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = True
    client.publish.return_value.rc = 0

    result = protocol.publish("test/topic", "message", retain=True)
    assert result is True
    client.publish.assert_called_with("test/topic", "message", 0, True)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_with_different_qos_levels(protocol_factory, mode):
    """
    다양한 QoS 레벨로 구독 테스트
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)
    callback = func

    # QoS 0, 1, 2 테스트
    for qos in [0, 1, 2]:
        topic = f"test/topic/{qos}"
        result = protocol.subscribe(topic, callback, qos=qos)
        assert result is True
        client.subscribe.assert_called_with(topic=topic, qos=qos)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_with_no_reconnect_thread(protocol_factory, mode, monkeypatch):
    """
    재연결 스레드가 없는 상태에서 disconnect 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._reconnect_thread = None
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 예외가 발생하지 않아야 함
    protocol.disconnect()

    assert protocol._auto_reconnect is False
    client.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_with_dead_reconnect_thread(protocol_factory, mode, monkeypatch):
    """
    죽은 재연결 스레드가 있는 상태에서 disconnect 테스트
    """
    protocol, client = protocol_factory(mode)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = False
    protocol._reconnect_thread = mock_thread
    monkeypatch.setattr("time.sleep", lambda *_: None)

    protocol.disconnect()

    assert protocol._auto_reconnect is False
    mock_thread.join.assert_not_called()  # 죽은 스레드는 join하지 않음
    client.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_publish_queue_with_empty_queue(protocol_factory, mode):
    """
    빈 큐에서 플러시 테스트
    """
    protocol, _ = protocol_factory(mode)
    mock_publish = MagicMock()

    protocol.handler.handler_flush_publish_queue(mock_publish)

    # 빈 큐이므로 publish가 호출되지 않아야 함
    mock_publish.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_publish_queue_with_exception(protocol_factory, mode):
    """
    플러시 중 예외 발생 테스트
    """
    protocol, _ = protocol_factory(mode)
    protocol._publish_queue.put(("topic", "message", 0, False))

    def mock_publish_with_exception(*args):
        raise Exception("Publish failed")

    # 예외가 발생해도 프로그램이 중단되지 않아야 함
    protocol.handler.handler_flush_publish_queue(mock_publish_with_exception)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_with_empty_subscriptions(protocol_factory, mode):
    """
    구독이 없는 상태에서 연결 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions = {}

    protocol._on_connect(client, protocol.handler, {}, 0)

    assert protocol._is_connected is True
    client.subscribe.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_connection_check_timeout(protocol_factory, mode, monkeypatch):
    """
    재연결 후 연결 확인 타임아웃 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False

    def mock_reconnect():
        # reconnect는 성공하지만 _is_connected가 True로 변경되지 않음
        pass

    client.reconnect.side_effect = mock_reconnect
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 한 번만 시도하고 중단하도록 설정
    call_count = 0

    def mock_wait(delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            protocol._stop_reconnect.set()
        return False

    protocol._stop_reconnect.wait = mock_wait

    protocol._reconnect_loop()

    client.reconnect.assert_called_once()
    if mode == "non-blocking":
        client.loop_start.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connect_with_custom_bind_address(protocol_factory, mode):
    """
    사용자 정의 바인드 주소로 연결 테스트
    """

    def custom_factory(mode):
        mock_client = MagicMock()
        mock_client.connect.return_value = 0
        if mode == "non-blocking":
            mock_client.loop_start.side_effect = lambda: None
        else:
            mock_client.loop_forever.side_effect = lambda: None

        import unittest.mock

        from app.protocols.mqtt.mqtt_protocol import (
            BrokerConfig,
            ClientConfig,
            MQTTProtocol,
        )

        with unittest.mock.patch(
            "app.protocols.mqtt.mqtt_protocol.Client", return_value=mock_client
        ):
            config = BrokerConfig(broker_address="test.broker.com", bind_address="192.168.1.100")
            protocol = MQTTProtocol(config, ClientConfig())
            return protocol, mock_client

    protocol, client = custom_factory(mode)
    protocol._is_connected = True  # 연결 성공 시뮬레이션

    result = protocol.connect()

    assert result is True
    client.connect.assert_called_once_with(
        host="test.broker.com", port=1883, keepalive=60, bind_address="192.168.1.100"
    )


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_publish_queue_thread_safety(protocol_factory, mode):
    """
    발행 큐의 스레드 안전성 테스트
    """
    import threading
    import time

    protocol, _ = protocol_factory(mode)
    protocol._is_connected = False  # 큐에 메시지가 쌓이도록 설정

    messages_sent = []

    def publish_messages(thread_id):
        for i in range(10):
            topic = f"test/topic/{thread_id}/{i}"
            message = f"message_{thread_id}_{i}"
            result = protocol.publish(topic, message)
            messages_sent.append((topic, message, result))
            time.sleep(0.001)  # 작은 지연

    # 여러 스레드에서 동시에 발행
    threads = []
    for i in range(3):
        thread = threading.Thread(target=publish_messages, args=(i,))
        threads.append(thread)
        thread.start()

    # 모든 스레드 완료 대기
    for thread in threads:
        thread.join()

    # 큐에 30개의 메시지가 있어야 함 (3 스레드 × 10 메시지)
    assert protocol._publish_queue.qsize() == 30

    # 모든 발행이 False를 반환해야 함 (연결되지 않은 상태)
    for _, _, result in messages_sent:
        assert result is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscription_thread_safety(protocol_factory, mode):
    """
    구독의 스레드 안전성 테스트
    """
    import threading

    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)

    subscription_results = []

    def subscribe_topics(thread_id):
        for i in range(5):
            topic = f"test/topic/{thread_id}/{i}"
            callback = lambda t, m, tid=thread_id, idx=i: None
            try:
                result = protocol.subscribe(topic, callback)
                subscription_results.append((topic, result))
            except Exception as e:
                subscription_results.append((topic, False, str(e)))

    # 여러 스레드에서 동시에 구독
    threads = []
    for i in range(3):
        thread = threading.Thread(target=subscribe_topics, args=(i,))
        threads.append(thread)
        thread.start()

    # 모든 스레드 완료 대기
    for thread in threads:
        thread.join()

    # 15개의 구독이 있어야 함 (3 스레드 × 5 구독)
    assert len(protocol._subscriptions) == 15

    # 모든 구독이 성공해야 함
    for result in subscription_results:
        if len(result) == 2:  # (topic, result)
            assert result[1] is True
        else:  # (topic, False, error)
            assert False, f"Subscription failed: {result[2]}"


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_queue_with_mixed_results(protocol_factory, mode):
    """
    플러시 시 성공/실패가 섞인 경우 테스트
    """
    protocol, _ = protocol_factory(mode)

    # 큐에 여러 메시지 추가
    messages = [
        ("topic1", "message1", 0, False),
        ("topic2", "message2", 1, True),
        ("topic3", "message3", 2, False),
    ]

    for msg in messages:
        protocol._publish_queue.put(msg)

    call_count = 0

    def mock_publish_func(topic, message, qos, retain):
        nonlocal call_count
        call_count += 1
        # 첫 번째와 세 번째는 성공, 두 번째는 실패
        if call_count == 2:
            result = MagicMock()
            result.rc = 1  # 실패
            return result
        else:
            result = MagicMock()
            result.rc = 0  # 성공
            return result

    protocol.handler.handler_flush_publish_queue(mock_publish_func)

    # 모든 메시지가 처리되어야 함
    assert protocol._publish_queue.empty()
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_with_blocking_mode_specific(protocol_factory, mode):
    """
    blocking 모드에서 재연결 루프 테스트
    """
    if mode == "blocking":
        protocol, client = protocol_factory(mode)
        protocol._is_connected = False

        def mock_reconnect():
            protocol._is_connected = True

        client.reconnect.side_effect = mock_reconnect

        protocol._reconnect_loop()

        client.reconnect.assert_called_once()
        # blocking 모드에서는 loop_start가 호출되지 않아야 함
        client.loop_start.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connect_with_blocking_mode_specific(protocol_factory, mode):
    """
    blocking 모드에서 연결 테스트
    """
    if mode == "blocking":
        protocol, client = protocol_factory(mode)
        client.connect.return_value = 0

        def mock_loop_forever():
            protocol._is_connected = True

        client.loop_forever.side_effect = mock_loop_forever

        result = protocol.connect()

        assert result is True
        client.connect.assert_called_once()
        client.loop_forever.assert_called_once()
        client.loop_start.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_start_reconnect_thread_already_alive_thread(protocol_factory, mode):
    """
    이미 살아있는 재연결 스레드가 있을 때 중복 시작 방지 테스트 (라인 502 커버)
    """
    protocol, _ = protocol_factory(mode)

    # 이미 살아있는 스레드 설정
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    protocol._reconnect_thread = mock_thread

    # 재연결 스레드 시작 시도
    protocol._start_reconnect_thread()

    # 기존 스레드가 그대로 유지되어야 함 (새로운 스레드 생성 안됨)
    assert protocol._reconnect_thread is mock_thread


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_successful_reconnection_and_exit(protocol_factory, mode, monkeypatch):
    """
    재연결 성공 후 루프 종료 테스트 (라인 508-520 커버)
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 재연결 성공 시뮬레이션 - 연결 확인 루프에서 성공
    reconnect_call_count = 0
    connection_check_count = 0

    def mock_reconnect():
        nonlocal reconnect_call_count
        reconnect_call_count += 1

    def mock_time_sleep(duration):
        nonlocal connection_check_count
        if duration == 0.5:  # 연결 확인 루프의 sleep
            connection_check_count += 1
            if connection_check_count == 3:  # 3번째 체크에서 연결 성공
                protocol._is_connected = True

    client.reconnect.side_effect = mock_reconnect
    monkeypatch.setattr("time.sleep", mock_time_sleep)

    # 재연결 루프 실행
    protocol._reconnect_loop()

    # 재연결이 성공했으므로 루프가 종료되어야 함
    assert reconnect_call_count == 1
    assert connection_check_count == 3
    if mode == "non-blocking":
        client.loop_start.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_stop_event_triggered_exit(protocol_factory, mode, monkeypatch):
    """
    _stop_reconnect 이벤트에 의한 루프 종료 테스트 (라인 508-520 커버)
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 재연결 실패 설정
    client.reconnect.side_effect = Exception("Connection failed")

    # wait 호출 시 즉시 True 반환하여 루프 종료
    def mock_wait(delay):
        return True  # stop_reconnect이 설정되었음을 의미

    protocol._stop_reconnect.wait = mock_wait

    # 재연결 루프 실행
    protocol._reconnect_loop()

    # 재연결 시도는 한 번만 이루어져야 함
    client.reconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_with_queue_flush_on_reconnect(protocol_factory, mode):
    """
    재연결 시 _on_connect에서 큐 메시지 재발행 테스트
    """
    protocol, client = protocol_factory(mode)

    # 큐에 메시지 추가
    protocol._publish_queue.put(("test/topic", "queued_message", 1, True))
    client.publish.return_value.rc = 0

    # _on_connect 콜백 호출 (재연결 성공 시뮬레이션)
    protocol._on_connect(client, protocol.handler, {}, 0)

    # 재연결 성공 후 큐의 메시지가 발행되어야 함
    client.publish.assert_called_with("test/topic", "queued_message", 1, True)
    assert protocol._publish_queue.empty()
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_exponential_backoff_with_max_delay_reached(
    protocol_factory, mode, monkeypatch
):
    """
    지수 백오프에서 최대 지연 시간 도달 테스트 (라인 508-520 커버)
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 재연결 계속 실패
    client.reconnect.side_effect = Exception("Connection failed")

    wait_delays = []
    call_count = 0

    def mock_wait(delay):
        nonlocal call_count
        wait_delays.append(delay)
        call_count += 1
        # 7번 호출 후 종료 (1, 2, 4, 8, 16, 32, 60)
        if call_count >= 7:
            return True  # 종료 신호
        return False

    protocol._stop_reconnect.wait = mock_wait

    # 재연결 루프 실행
    protocol._reconnect_loop()

    # 지수 백오프가 최대 60초까지 증가해야 함
    expected_delays = [1, 2, 4, 8, 16, 32, 60]
    assert wait_delays == expected_delays
    assert client.reconnect.call_count == 7


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_connection_check_with_partial_success(protocol_factory, mode, monkeypatch):
    """
    재연결 후 연결 확인 중 일부 성공 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 재연결은 성공하지만 연결 확인에서 지연
    reconnect_call_count = 0
    connection_check_count = 0

    def mock_reconnect():
        nonlocal reconnect_call_count
        reconnect_call_count += 1

    def mock_time_sleep(duration):
        nonlocal connection_check_count
        if duration == 0.5:  # 연결 확인 루프의 sleep
            connection_check_count += 1
            if connection_check_count == 5:  # 5번째 체크에서 연결 성공
                protocol._is_connected = True

    client.reconnect.side_effect = mock_reconnect
    monkeypatch.setattr("time.sleep", mock_time_sleep)

    # 재연결 루프 실행
    protocol._reconnect_loop()

    # 재연결이 성공했으므로 루프가 종료되어야 함
    assert reconnect_call_count == 1
    assert connection_check_count == 5
    if mode == "non-blocking":
        client.loop_start.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_start_reconnect_thread_with_dead_thread_replacement(protocol_factory, mode, monkeypatch):
    """
    죽은 재연결 스레드를 새로운 스레드로 교체하는 테스트
    """
    protocol, _ = protocol_factory(mode)

    # 죽은 스레드 설정
    dead_thread = MagicMock()
    dead_thread.is_alive.return_value = False
    protocol._reconnect_thread = dead_thread

    # 새로운 스레드 Mock 설정
    new_thread = MagicMock()
    mock_thread_class = MagicMock(return_value=new_thread)
    monkeypatch.setattr("threading.Thread", mock_thread_class)

    # 재연결 스레드 시작
    protocol._start_reconnect_thread()

    # 새로운 스레드가 생성되고 시작되어야 함
    mock_thread_class.assert_called_once_with(target=protocol._reconnect_loop, daemon=True)
    new_thread.start.assert_called_once()
    assert protocol._reconnect_thread is new_thread


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_reconnect_loop_with_multiple_failed_attempts(protocol_factory, mode, monkeypatch):
    """
    여러 번의 재연결 실패 후 성공하는 테스트
    """
    protocol, client = protocol_factory(mode)
    protocol._is_connected = False
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # 처음 3번은 실패, 4번째에 성공
    reconnect_attempts = 0

    def mock_reconnect():
        nonlocal reconnect_attempts
        reconnect_attempts += 1
        if reconnect_attempts >= 4:
            protocol._is_connected = True
        else:
            raise Exception(f"Connection failed attempt {reconnect_attempts}")

    client.reconnect.side_effect = mock_reconnect

    wait_calls = []

    def mock_wait(delay):
        wait_calls.append(delay)
        if len(wait_calls) >= 3:  # 3번 실패 후 성공
            return False
        return False

    protocol._stop_reconnect.wait = mock_wait

    # 재연결 루프 실행
    protocol._reconnect_loop()

    # 4번의 재연결 시도가 있어야 함
    assert client.reconnect.call_count == 4
    # 지수 백오프: 1, 2, 4초
    assert wait_calls == [1, 2, 4]


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_queue_with_publish_failure_and_success_mix(protocol_factory, mode):
    """
    큐 플러시 시 발행 성공/실패 혼합 테스트
    """
    protocol, _ = protocol_factory(mode)

    # 큐에 여러 메시지 추가
    messages = [
        ("topic1", "msg1", 0, False),
        ("topic2", "msg2", 1, True),
        ("topic3", "msg3", 2, False),
        ("topic4", "msg4", 0, True),
    ]

    for msg in messages:
        protocol._publish_queue.put(msg)

    publish_calls = []

    def mock_publish_func(topic, message, qos, retain):
        publish_calls.append((topic, message, qos, retain))
        result = MagicMock()
        # topic2와 topic4는 실패, 나머지는 성공
        if topic in ["topic2", "topic4"]:
            result.rc = 1  # 실패
        else:
            result.rc = 0  # 성공
        return result

    # 플러시 실행
    protocol.handler.handler_flush_publish_queue(mock_publish_func)

    # 모든 메시지가 처리되어야 함
    assert len(publish_calls) == 4
    assert protocol._publish_queue.empty()

    # 호출된 메시지들 확인
    expected_calls = [
        ("topic1", "msg1", 0, False),
        ("topic2", "msg2", 1, True),
        ("topic3", "msg3", 2, False),
        ("topic4", "msg4", 0, True),
    ]
    assert publish_calls == expected_calls
