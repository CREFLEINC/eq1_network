import pytest
from unittest.mock import MagicMock
from communicator.manager.protocol_manager import ReqResManager, PubSubManager, ProtocolManager
from communicator.interfaces.protocol import PubSubProtocol, ReqResProtocol


@pytest.fixture
def mock_reqres_plugin():
    """
    요청-응답 기반 플러그인(mock) 설정 fixture
    connect/send/receive 메서드에 기본 반환값을 설정합니다.
    """
    plugin = MagicMock()
    plugin.connect.return_value = True
    plugin.send.return_value = 5
    plugin.receive.return_value = b"response"
    return plugin


@pytest.mark.unit
def test_reqres_load_and_get(mock_reqres_plugin):
    """
    ReqResManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    assert ReqResManager.get("tcp") is mock_reqres_plugin


@pytest.mark.unit
def test_reqres_get_missing():
    """
    등록되지 않은 프로토콜 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    ReqResManager._plugins.clear()
    with pytest.raises(ValueError, match="'abc' 프로토콜이 등록되지 않았습니다."):
        ReqResManager.get("abc")


@pytest.mark.unit
def test_reqres_connect(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    assert ReqResManager.connect("tcp") is True
    mock_reqres_plugin.connect.assert_called_once()


@pytest.mark.unit
def test_reqres_send(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 send() 호출 시 플러그인의 send()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    result = ReqResManager.send("tcp", b"data")
    assert result == 5
    mock_reqres_plugin.send.assert_called_once_with(b"data")


@pytest.mark.unit
def test_reqres_receive(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 receive() 호출 시 플러그인의 receive()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    result = ReqResManager.receive("tcp", buffer_size=2048)
    assert result == b"response"
    mock_reqres_plugin.receive.assert_called_once_with(2048)


@pytest.mark.unit
def test_reqres_disconnect(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    ReqResManager.disconnect("tcp")
    mock_reqres_plugin.disconnect.assert_called_once()


@pytest.fixture
def mock_pubsub_plugin():
    """
    MQTT 기반 플러그인(mock) 설정 fixture
    connect/publish/subscribe/unsubscribe 메서드에 기본 반환값을 설정합니다.
    """
    plugin = MagicMock()
    plugin.connect.return_value = True
    plugin.publish.return_value = True
    plugin.subscribe.return_value = True
    plugin.unsubscribe.return_value = True
    return plugin


@pytest.mark.unit
def test_pubsub_load_and_get(mock_pubsub_plugin):
    """
    PubSubManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    assert PubSubManager.get("mqtt") is mock_pubsub_plugin


@pytest.mark.unit
def test_pubsub_get_missing():
    """
    등록되지 않은 플러그인 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    PubSubManager._plugins.clear()
    with pytest.raises(ValueError, match="'xyz' 프로토콜이 등록되지 않았습니다."):
        PubSubManager.get("xyz")


@pytest.mark.unit
def test_pubsub_connect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    assert PubSubManager.connect("mqtt") is True
    mock_pubsub_plugin.connect.assert_called_once()


@pytest.mark.unit
def test_pubsub_publish(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 publish() 호출 시 플러그인의 publish()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    result = PubSubManager.publish("mqtt", "topic/a", "hello", qos=1)
    assert result is True
    mock_pubsub_plugin.publish.assert_called_once_with("topic/a", "hello", 1)


@pytest.mark.unit
def test_pubsub_subscribe(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 subscribe() 호출 시 플러그인의 subscribe()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    cb = lambda t, p: None
    result = PubSubManager.subscribe("mqtt", "topic/b", cb, qos=2)
    assert result is True
    mock_pubsub_plugin.subscribe.assert_called_once_with("topic/b", cb, 2)


@pytest.mark.unit
def test_pubsub_unsubscribe(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 unsubscribe() 호출 시 플러그인의 unsubscribe()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    result = PubSubManager.unsubscribe("mqtt", "topic/c")
    assert result is True
    mock_pubsub_plugin.unsubscribe.assert_called_once_with("topic/c")


@pytest.mark.unit
def test_pubsub_disconnect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    PubSubManager.disconnect("mqtt")
    mock_pubsub_plugin.disconnect.assert_called_once()


# ProtocolManager 테스트 추가
@pytest.fixture
def mock_pubsub_protocol():
    mock = MagicMock(spec=PubSubProtocol)
    return mock


@pytest.fixture
def mock_reqres_protocol():
    mock = MagicMock(spec=ReqResProtocol)
    return mock


@pytest.mark.unit
def test_protocol_manager_register_pubsub(mock_pubsub_protocol):
    """PubSub 프로토콜 등록 테스트"""
    manager = ProtocolManager()
    manager.register_protocol("mqtt", mock_pubsub_protocol)
    assert manager.get_protocol("mqtt") is mock_pubsub_protocol


@pytest.mark.unit
def test_protocol_manager_register_reqres(mock_reqres_protocol):
    """ReqRes 프로토콜 등록 테스트"""
    manager = ProtocolManager()
    manager.register_protocol("tcp", mock_reqres_protocol)
    assert manager.get_protocol("tcp") is mock_reqres_protocol


@pytest.mark.unit
def test_protocol_manager_register_invalid_protocol():
    """잘못된 프로토콜 타입 등록 시 예외 발생 테스트"""
    manager = ProtocolManager()
    invalid_protocol = MagicMock()
    with pytest.raises(ValueError, match="지원하지 않는 프로토콜 타입"):
        manager.register_protocol("invalid", invalid_protocol)


@pytest.mark.unit
def test_protocol_manager_get_missing():
    """등록되지 않은 프로토콜 조회 시 예외 발생 테스트"""
    manager = ProtocolManager()
    with pytest.raises(ValueError, match="'missing' 프로토콜이 등록되지 않았습니다"):
        manager.get_protocol("missing")


@pytest.mark.unit
def test_protocol_manager_list_protocols(mock_pubsub_protocol, mock_reqres_protocol):
    """프로토콜 목록 조회 테스트"""
    manager = ProtocolManager()
    manager.register_protocol("mqtt", mock_pubsub_protocol)
    manager.register_protocol("tcp", mock_reqres_protocol)
    protocols = manager.list_available_protocols()
    assert sorted(protocols) == ["mqtt", "tcp"]


@pytest.mark.unit
def test_protocol_manager_remove_pubsub(mock_pubsub_protocol):
    """PubSub 프로토콜 제거 테스트"""
    manager = ProtocolManager()
    manager.register_protocol("mqtt", mock_pubsub_protocol)
    manager.remove_protocol("mqtt")
    with pytest.raises(ValueError):
        manager.get_protocol("mqtt")


@pytest.mark.unit
def test_protocol_manager_remove_reqres(mock_reqres_protocol):
    """ReqRes 프로토콜 제거 테스트"""
    manager = ProtocolManager()
    manager.register_protocol("tcp", mock_reqres_protocol)
    manager.remove_protocol("tcp")
    with pytest.raises(ValueError):
        manager.get_protocol("tcp")


@pytest.mark.unit
def test_protocol_manager_remove_missing():
    """등록되지 않은 프로토콜 제거 시 예외 발생 테스트"""
    manager = ProtocolManager()
    with pytest.raises(ValueError, match="'missing' 프로토콜이 등록되지 않았습니다"):
        manager.remove_protocol("missing")