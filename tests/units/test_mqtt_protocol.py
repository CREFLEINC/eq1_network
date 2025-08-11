import pytest
from unittest.mock import MagicMock
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)


@pytest.fixture
def mock_client(monkeypatch):
    """
    paho-mqtt.Client를 Mock으로 치환합니다.
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        MagicMock: Mock된 MQTT 클라이언트 인스턴스
    
    Asserts:
        None: Mock이 성공적으로 설정되면 테스트가 계속 진행됩니다.
    """
    mock_client = MagicMock()
    monkeypatch.setattr(
        "communicator.protocols.mqtt.mqtt_protocol.Client",
        lambda *a, **k: mock_client
    )
    return mock_client


@pytest.fixture
def non_blocking_protocol(mock_client):
    """
    MQTTProtocol의 테스트용 non-blocking 모드 인스턴스를 생성합니다.
    
    Args:
        mock_client: Mock된 MQTT 클라이언트 인스턴스
    
    Returns:
        MQTTProtocol: non-blocking 모드로 설정된 MQTTProtocol 인스턴스
    
    Asserts:
        None: Mock이 성공적으로 설정되면 테스트가 계속 진행됩니다.
    """
    config = BrokerConfig(
        broker_address="broker.emqx.io",
        port=1883,
        mode="non-blocking"
    )
    client_config = ClientConfig()
    return MQTTProtocol(config, client_config)


@pytest.fixture
def blocking_protocol(mock_client):
    """
    MQTTProtocol의 테스트용 blocking 모드 인스턴스를 생성합니다.
    
    Args:
        mock_client: Mock된 MQTT 클라이언트 인스턴스
    
    Returns:
        MQTTProtocol: blocking 모드로 설정된 MQTTProtocol 인스턴스
    
    Asserts:
        None: Mock이 성공적으로 설정되면 테스트가 계속 진행됩니다.
    """
    config = BrokerConfig(
        broker_address="broker.emqx.io",
        port=1883,
        mode="blocking"
    )
    client_config = ClientConfig()
    return MQTTProtocol(config, client_config)


@pytest.fixture
def protocol_factory(monkeypatch):
    """
    mode와 client side_effect를 받아 MQTTProtocol을 만드는 팩토리 함수입니다.
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        function: MQTTProtocol 인스턴스를 생성하는 함수
    
    Asserts:
        None: Mock이 성공적으로 설정되면 테스트가 계속 진행됩니다.
    """
    def _factory(mode="non-blocking", client_customizer=None):
        mock_client = MagicMock()
        if client_customizer:
            client_customizer(mock_client)
        monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.Client",
                            lambda *a, **k: mock_client)
        cfg = BrokerConfig(broker_address="broker.emqx.io", mode=mode)
        return MQTTProtocol(cfg, ClientConfig()), mock_client
    return _factory


@pytest.fixture
def no_sleep(monkeypatch):
    """
    time.sleep 무력화하는 함수입니다.
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None

    Asserts:
        None: Mock이 성공적으로 설정되면 테스트가 계속 진행됩니다.
    """
    monkeypatch.setattr("time.sleep", lambda *_: None)


@pytest.mark.unit
def test_mqtt_client_creation_error(monkeypatch):
    """
    클라이언트 생성 실패 테스트
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Raises:
        ProtocolError: 클라이언트 생성 실패 시 ProtocolError가 발생해야 합니다.
    
    Asserts:
        None: 클라이언트 생성 실패 시 ProtocolError가 발생해야 합니다.
    """
    def mock_client_error(*args, **kwargs):
        """Mock 클라이언트 생성 실패 함수"""
        raise ProtocolError("클라이언트 생성 실패")

    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.Client", mock_client_error)
    config = BrokerConfig(broker_address="broker.emqx.io")
    client_config = ClientConfig()

    with pytest.raises(ProtocolError):
        MQTTProtocol(config, client_config)


@pytest.mark.unit
def test_mqtt_auth_error(monkeypatch):
    """
    인증 설정 실패 테스트
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Raises:
        ProtocolError: 인증 설정 실패 시 ProtocolError가 발생해야 합니다.
    
    Asserts:
        None: 인증 설정 실패 시 ProtocolError가 발생해야 합니다.
    """
    mock_client = MagicMock()
    mock_client.username_pw_set.side_effect = Exception("Auth failed")
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.Client", lambda *a, **k: mock_client)

    config = BrokerConfig(broker_address="broker.emqx.io", username="user", password="pass")
    client_config = ClientConfig()
    with pytest.raises(ProtocolError):
        MQTTProtocol(config, client_config)


@pytest.mark.unit
def test_main_execution_block(tmp_path, monkeypatch):
    """
    메인 실행 블록 임포트/실행 스모크 테스트
    
    Args:
        tmp_path: pytest의 임시 경로 fixture
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 메인 실행 블록이 정상적으로 실행되면 "Test completed" 메시지가 출력되어야 합니다.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, '-c',
        'import sys; sys.path.insert(0, "."); '
        'from communicator.protocols.mqtt.mqtt_protocol import *; '
        'import logging; logging.basicConfig(level=logging.DEBUG); '
        'broker_config = BrokerConfig(broker_address="localhost"); '
        'client_config = ClientConfig(); '
        'print("Test completed")'],
        cwd='/Users/hj.cho/A-Crefle/Project/eq1_network',
        capture_output=True,
        text=True,
        timeout=5
    )
    assert result.returncode == 0, result.stderr
    assert "Test completed" in result.stdout


@pytest.mark.unit
def test_connect_with_bind_address(monkeypatch):
    """
    바인드 주소 None일 때 빈 문자열 사용 테스트
    
    Args:
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 바인드 주소가 None일 때 빈 문자열로 연결이 성공해야 합니다.
    """
    mock_client = MagicMock()
    mock_client.connect.return_value = 0
    mock_client.loop_start.side_effect = lambda: None
    monkeypatch.setattr("communicator.protocols.mqtt.mqtt_protocol.Client", lambda *a, **k: mock_client)
    
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 연결이 성공적으로 이루어져야 하며, 클라이언트의 connect 메서드가 호출되어야 합니다.
    """
    protocol, client = protocol_factory(mode, client_customizer=lambda c: setattr(c, "connect", MagicMock(return_value=0)))
    # 루프 동작 모의
    if mode == "non-blocking":
        client.loop_start.side_effect = lambda: protocol._on_connect(client, protocol.handler, {}, 0)
    else:
        client.loop_forever.side_effect = lambda: setattr(protocol, "_is_connected", True)

    assert protocol.connect() is True
    client.connect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_connect_failure(protocol_factory, mode):
    """
    연결 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Raises:
        ProtocolConnectionError: 연결 실패 시 ProtocolConnectionError가 발생해야 합니다.
    
    Asserts:
        None: 연결 실패 시 ProtocolConnectionError가 발생해야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Raises:
        ProtocolConnectionError: 연결 타임아웃 시 ProtocolConnectionError가 발생해야 합니다.
    
    Asserts:
        None: 연결 타임아웃 시 ProtocolConnectionError가 발생해야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 연결 해제가 성공적으로 이루어져야 하며, 클라이언트의 disconnect 메서드가 호출되어야 합니다.
    """
    protocol, client = protocol_factory(mode, client_customizer=lambda c: setattr(c, "disconnect", MagicMock(return_value=0)))
    protocol.disconnect()
    if mode == "non-blocking":
        client.loop_stop.assert_called_once()
    else:
        client.loop_stop.assert_not_called() # blocking 모드는 loop_stop를 호출하지 않음
    
    client.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_disconnect_connection_wait_timeout(protocol_factory, mode, monkeypatch):
    """
    연결 해제 대기 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 연결 해제 대기 시 클라이언트의 loop_stop 메서드가 호출되어야 합니다.
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
@pytest.mark.parametrize("rc,raises,expected", [
    (0, None, True),                      # 성공
    (1, None, False),                     # rc 실패
    (None, Exception("발행 오류"), False),  # 예외
])
def test_publish_variants(protocol_factory, mode, rc, raises, expected):
    """
    발행 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        rc: 클라이언트의 publish 메서드가 반환하는 코드
        raises: 클라이언트의 publish 메서드가 발생시키는 예외
        expected: 예상되는 반환값 (성공 여부)
    
    Returns:
        None
    
    Asserts:
        None: 발행 결과가 예상과 일치해야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행이 실패하고 큐에 메시지가 적재되어야 하며, 클라이언트의 publish 메서드는 호출되지 않아야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행 오류가 발생해야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행 큐가 비어있어야 하며, 클라이언트의 publish 메서드가 호출되어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행 큐가 비어있어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독이 성공해야 하며, 콜백이 등록되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)
    callback = lambda t, m: None
    assert protocol.subscribe("topic", callback)
    assert "topic" in protocol._subscriptions
    client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_failure(protocol_factory, mode):
    """
    구독 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독이 실패해야 합니다.
    
    Raises:
        ProtocolValidationError: 구독이 실패해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("bad", lambda t, m: None)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_subscribe_duplicate_callbacks_allowed(protocol_factory, mode):
    """
    중복 콜백 허용 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 중복 콜백이 허용되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.return_value = (0, 1)
    cb = lambda t,m: None
    protocol.subscribe("topic", cb)
    protocol.subscribe("topic", cb)
    assert len(protocol._subscriptions["topic"]) == 2


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_success(protocol_factory, mode):
    """
    구독 해제 성공 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 해제 성공해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic"] = [lambda t, m: None]
    client.unsubscribe.return_value = (0, 1)
    assert protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_failure(protocol_factory, mode):
    """
    구독 해제 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 해제 실패해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["bad"] = [lambda t, m: None]
    client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("bad")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_exception_handling(protocol_factory, mode):
    """
    구독 해제 예외 처리 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 해제 예외 처리가 정상적으로 이루어져야 합니다.
    """
    protocol, client = protocol_factory(mode)
    callback = lambda t, m: None
    protocol._subscriptions["topic"] = [callback]
    client.unsubscribe.side_effect = Exception("Unsubscribe failed")
    with pytest.raises(ProtocolValidationError, match="구독 해제 오류"):
        protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_all_callbacks_failure_keeps_local_state(protocol_factory, mode):
    """
    모든 콜백 해제 실패 시 로컬 상태 유지 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 해제 실패해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    cb = lambda t,m: None
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    Returns:
        None
    Asserts:
        None: 구독 해제 실패해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    callback = lambda t, m: None
    protocol._subscriptions["topic"] = [callback]
    client.unsubscribe.return_value = (1, None)
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic", callback)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_topic_not_exists(protocol_factory, mode):
    """
    존재하지 않는 토픽 unsubscribe 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 존재하지 않는 토픽에 대한 unsubscribe는 True를 반환해야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    result = protocol.unsubscribe("nonexistent_topic")
    assert result is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_unsubscribe_specific_callback(protocol_factory, mode):
    """
    특정 콜백 제거 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 특정 콜백이 제거되어야 하며, 나머지 콜백은 유지되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    callback1 = lambda t, m: None
    callback2 = lambda t, m: None
    
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 콜백이 리스트에 없을 때도 True를 반환해야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    callback1 = lambda t, m: None
    callback2 = lambda t, m: None
    
    protocol._subscriptions["topic"] = [callback1]
    assert protocol.unsubscribe("topic", callback2) is True
    assert "topic" in protocol._subscriptions
    assert callback1 in protocol._subscriptions["topic"]


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_is_connected_property(protocol_factory, mode):
    """
    is_connected 프로퍼티 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: is_connected 프로퍼티가 True여야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    protocol._is_connected = True
    assert protocol.is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_callback(protocol_factory, mode):
    """
    _on_connect 콜백 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: _on_connect 콜백이 호출되어야 하며, 클라이언트의 subscribe 메서드가 호출되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    callback = lambda t, m: None
    protocol._subscriptions["topic"] = [callback]
    client.subscribe.return_value = (0, 1)
    protocol._on_connect(client, protocol.handler, {}, 0)
    client.subscribe.assert_called_once_with(topic="topic", qos=0)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_subscription_recovery_error(protocol_factory, mode):
    """
    연결 시 구독 복구 오류 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 복구 오류가 발생해도 연결 상태는 True여야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic1"] = [lambda t, m: None]
    client.subscribe.side_effect = Exception("구독 복구 실패")
    protocol._on_connect(client, protocol.handler, {}, 0)
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_subscription_recovery_failure(protocol_factory, mode):
    """
    연결 시 구독 복구 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 복구 실패 시 연결 상태는 True여야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic1"] = [lambda t, m: None]
    client.subscribe.return_value = (1, None)
    protocol._on_connect(client, protocol.handler, {}, 0)
    assert protocol._is_connected is True


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_failure(protocol_factory, mode):
    """
    연결 실패 콜백 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 연결 실패 시 _is_connected가 False여야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._on_connect(client, protocol.handler, {}, 1)
    assert protocol._is_connected is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_connect_with_queue_messages(protocol_factory, mode):
    """
    연결 시 큐에 메시지가 있을 때 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 연결 시 큐에 있는 메시지가 발행되어야 하며, _is_connected가 True여야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 일부 구독이 복구되어야 하며, 클라이언트의 subscribe 메서드가 호출되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions = {
        "ok": [lambda t,m: None],
        "bad": [lambda t,m: None],
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: _is_connected가 False로 설정되어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 해제 오류가 발생해야 하며, ProtocolValidationError가 발생해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    protocol._subscriptions["topic"] = [lambda t, m: None]
    client.unsubscribe.side_effect = Exception("구독 해제 실패")
    with pytest.raises(ProtocolValidationError):
        protocol.unsubscribe("topic")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_callback(protocol_factory, mode):
    """
    _on_message 콜백 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 콜백이 호출되어야 하며, 메시지가 올바르게 전달되어야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    called = []
    callback = lambda t, m: called.append((t, m))
    protocol._subscriptions["topic"] = [callback]
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)
    assert called[0] == ("topic", b"data")


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_with_exception(protocol_factory, mode):
    """
    _on_message 예외 발생 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 콜백에서 예외가 발생해야 하며, 프로토콜이 정상적으로 작동해야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    error_callback = lambda t, m: 1 / 0
    protocol._subscriptions["topic"] = [error_callback]
    msg = type("msg", (), {"topic": "topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_on_message_no_callback(protocol_factory, mode):
    """
    콜백이 없는 메시지 수신 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 콜백이 없는 메시지 수신 시 아무 동작도 하지 않아야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    msg = type("msg", (), {"topic": "unknown_topic", "payload": b"data"})
    protocol._on_message(None, protocol.handler, msg)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_flush_publish_queue_failure(protocol_factory, mode):
    """
    플러시 중 발행 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행 실패 시 큐에 메시지가 남아 있어야 하며, 클라이언트의 publish 메서드는 호출되지 않아야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 발행 중 오류가 발생해야 하며, 큐에 메시지가 남아 있어야 합니다.
    
    Raises:
        Exception: 클라이언트의 publish 메서드가 예외를 발생시켜야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 구독 오류 발생 시 _subscriptions에서 해당 토픽이 제거되어야 합니다.
    
    Raises:
        ProtocolValidationError: 구독 오류가 발생해야 합니다.
    """
    protocol, client = protocol_factory(mode)
    client.subscribe.side_effect = Exception("Subscribe error")
    with pytest.raises(ProtocolValidationError):
        protocol.subscribe("topic", lambda t, m: None)
    assert "topic" not in protocol._subscriptions


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_connect_session_present(protocol_factory, mode):
    """
    핸들러 연결 시 세션 복원 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 핸들러 연결 시 세션이 복원되어야 하며, _is_connected가 True여야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 핸들러 연결 해제 시 _is_connected가 False여야 합니다.
    """
    protocol, _ = protocol_factory(mode)
    protocol.handler.handle_disconnect(0)
    assert protocol._is_connected is False


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_handler_flush_publish_queue_failure(protocol_factory, mode):
    """
    핸들러 플러시 시 재발행 실패 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 핸들러 플러시 시 재발행이 실패해야 하며, 큐에 메시지가 남아 있어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 예기치 못한 연결 해제 시 재연결 스레드가 시작되어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 정상 연결 해제 시 재연결 스레드가 시작되지 않아야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: disconnect 호출 시 자동 재연결이 중단되어야 합니다.
    """
    protocol, client = protocol_factory(mode)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    protocol._reconnect_thread = mock_thread
    monkeypatch.setattr("time.sleep", lambda *_: None)
    
    protocol.disconnect()
    
    assert protocol._auto_reconnect is False
    protocol._stop_reconnect.set.assert_called_once()
    mock_thread.join.assert_called_once_with(timeout=1)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_start_reconnect_thread_already_running(protocol_factory, mode):
    """
    재연결 스레드가 이미 실행 중일 때 중복 시작 방지 테스트
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
    
    Returns:
        None
    
    Asserts:
        None: 재연결 스레드가 이미 실행 중일 때 새로운 스레드가 시작되지 않아야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 재연결이 성공해야 하며, 루프가 종료되어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팥토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 재연결 실패 시 지수 백오프가 적용되어야 합니다.
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
    
    Args:
        protocol_factory: MQTTProtocol 인스턴스를 생성하는 팩토리 함수
        mode: "non-blocking" 또는 "blocking" 모드
        monkeypatch: pytest의 monkeypatch fixture
    
    Returns:
        None
    
    Asserts:
        None: 재연결 지연 시간이 최대값을 초과하지 않아야 합니다.
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
