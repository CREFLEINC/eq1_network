import pytest
from unittest.mock import MagicMock
from communicator.manager.protocol_manager import ReqResManager, PubSubManager


@pytest.fixture
def mock_reqres_plugin():
    """
    요청-응답 기반 플러그인(mock) 설정 fixture.
    connect/send/receive 메서드에 기본 반환값을 설정합니다.
    """
    plugin = MagicMock()
    plugin.connect.return_value = True
    plugin.send.return_value = True
    plugin.receive.return_value = b"response"
    return plugin


def test_reqres_load_and_get(mock_reqres_plugin):
    """
    ReqResManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    assert ReqResManager.get("tcp") == mock_reqres_plugin


def test_reqres_get_missing():
    """
    등록되지 않은 프로토콜 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    ReqResManager._plugins.clear()
    with pytest.raises(ValueError, match="'abc' 프로토콜이 등록되지 않았습니다."):
        ReqResManager.get("abc")


def test_reqres_connect(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    assert ReqResManager.connect("tcp") is True
    mock_reqres_plugin.connect.assert_called_once()


def test_reqres_send(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 send() 호출 시 플러그인의 send()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    result = ReqResManager.send("tcp", b"data")
    assert result is True
    mock_reqres_plugin.send.assert_called_once_with(b"data")


def test_reqres_receive(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 receive() 호출 시 플러그인의 receive()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.load("tcp", mock_reqres_plugin)
    result = ReqResManager.receive("tcp", buffer_size=2048)
    assert result == b"response"
    mock_reqres_plugin.receive.assert_called_once_with(2048)


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
    MQTT 기반 플러그인(mock) 설정 fixture.
    connect/publish/subscribe/unsubscribe 메서드에 기본 반환값을 설정합니다.
    """
    plugin = MagicMock()
    plugin.connect.return_value = True
    plugin.publish.return_value = True
    plugin.subscribe.return_value = True
    plugin.unsubscribe.return_value = True
    return plugin


def test_pubsub_load_and_get(mock_pubsub_plugin):
    """
    PubSubManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    assert PubSubManager.get("mqtt") == mock_pubsub_plugin


def test_pubsub_get_missing():
    """
    등록되지 않은 플러그인 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    PubSubManager._plugins.clear()
    with pytest.raises(ValueError, match="'xyz' 프로토콜이 등록되지 않았습니다."):
        PubSubManager.get("xyz")


def test_pubsub_connect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    assert PubSubManager.connect("mqtt") is True
    mock_pubsub_plugin.connect.assert_called_once()


def test_pubsub_publish(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 publish() 호출 시 플러그인의 publish()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    result = PubSubManager.publish("mqtt", "topic/a", "hello", qos=1)
    assert result is True
    mock_pubsub_plugin.publish.assert_called_once_with("topic/a", "hello", 1)


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


def test_pubsub_unsubscribe(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 unsubscribe() 호출 시 플러그인의 unsubscribe()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    result = PubSubManager.unsubscribe("mqtt", "topic/c")
    assert result is True
    mock_pubsub_plugin.unsubscribe.assert_called_once_with("topic/c")


def test_pubsub_disconnect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.load("mqtt", mock_pubsub_plugin)
    PubSubManager.disconnect("mqtt")
    mock_pubsub_plugin.disconnect.assert_called_once()
