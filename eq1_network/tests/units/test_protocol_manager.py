from unittest.mock import MagicMock

import pytest

from eq1_network.manager.protocol_manager import PubSubManager, ReqResManager


def func(t, p):
    return None


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
def test_reqres_register_and_get(mock_reqres_plugin):
    """
    ReqResManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.register("tcp", mock_reqres_plugin)
    assert ReqResManager.get("tcp") is mock_reqres_plugin


@pytest.mark.unit
def test_reqres_get_missing():
    """
    등록되지 않은 프로토콜 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    ReqResManager._plugins.clear()
    with pytest.raises(LookupError, match="ReqRes plugin not found: abc"):
        ReqResManager.get("abc")


@pytest.mark.unit
def test_reqres_connect(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.register("tcp", mock_reqres_plugin)
    assert ReqResManager.connect("tcp") is True
    mock_reqres_plugin.connect.assert_called_once()


@pytest.mark.unit
def test_reqres_send(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 send() 호출 시 플러그인의 send()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.register("tcp", mock_reqres_plugin)
    result = ReqResManager.send("tcp", b"data")
    assert result == 5
    mock_reqres_plugin.send.assert_called_once_with(b"data")


@pytest.mark.unit
def test_reqres_read(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 read() 호출 시 플러그인의 read()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    mock_reqres_plugin.read.return_value = (True, b"response")
    ReqResManager.register("tcp", mock_reqres_plugin)
    result = ReqResManager.read("tcp")
    assert result == b"response"
    mock_reqres_plugin.read.assert_called_once()


@pytest.mark.unit
def test_reqres_disconnect(mock_reqres_plugin):
    """
    등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.register("tcp", mock_reqres_plugin)
    ReqResManager.disconnect("tcp")
    mock_reqres_plugin.disconnect.assert_called_once()


@pytest.mark.unit
def test_reqres_unregister():
    """
    ReqResManager에서 플러그인을 등록 해제하는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    mock_plugin = MagicMock()
    ReqResManager.register("tcp", mock_plugin)
    assert ReqResManager.has("tcp") is True

    ReqResManager.unregister("tcp")
    assert ReqResManager.has("tcp") is False


@pytest.mark.unit
def test_reqres_unregister_nonexistent():
    """
    존재하지 않는 플러그인을 등록 해제할 때 예외가 발생하지 않는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    # 예외가 발생하지 않아야 함
    ReqResManager.unregister("nonexistent")


@pytest.mark.unit
def test_reqres_has():
    """
    ReqResManager의 has() 메서드가 올바르게 동작하는지 테스트합니다.
    """
    ReqResManager._plugins.clear()
    mock_plugin = MagicMock()

    assert ReqResManager.has("tcp") is False
    ReqResManager.register("tcp", mock_plugin)
    assert ReqResManager.has("tcp") is True


@pytest.mark.unit
def test_reqres_read_failure(mock_reqres_plugin):
    """
    read() 메서드에서 실패 케이스(False 반환 또는 None 데이터)를 테스트합니다.
    """
    ReqResManager._plugins.clear()
    ReqResManager.register("tcp", mock_reqres_plugin)

    # False 반환 케이스
    mock_reqres_plugin.read.return_value = (False, b"error")
    result = ReqResManager.read("tcp")
    assert result == b""

    # None 데이터 케이스
    mock_reqres_plugin.read.return_value = (True, None)
    result = ReqResManager.read("tcp")
    assert result == b""


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
def test_pubsub_register_and_get(mock_pubsub_plugin):
    """
    PubSubManager에 플러그인을 등록하고 정상적으로 조회되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.register("mqtt", mock_pubsub_plugin)
    assert PubSubManager.get("mqtt") is mock_pubsub_plugin


@pytest.mark.unit
def test_pubsub_get_missing():
    """
    등록되지 않은 플러그인 이름으로 get() 호출 시 예외 발생 여부를 테스트합니다.
    """
    PubSubManager._plugins.clear()
    with pytest.raises(LookupError, match="PubSub plugin not found: xyz"):
        PubSubManager.get("xyz")


@pytest.mark.unit
def test_pubsub_connect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.register("mqtt", mock_pubsub_plugin)
    assert PubSubManager.connect("mqtt") is True
    mock_pubsub_plugin.connect.assert_called_once()


@pytest.mark.unit
def test_pubsub_publish(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 publish() 호출 시 플러그인의 publish()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.register("mqtt", mock_pubsub_plugin)
    result = PubSubManager.publish("mqtt", "topic/a", "hello", qos=1)
    assert result is True
    mock_pubsub_plugin.publish.assert_called_once_with("topic/a", b"hello", 1)


@pytest.mark.unit
def test_pubsub_subscribe(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 subscribe() 호출 시 플러그인의 subscribe()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.register("mqtt", mock_pubsub_plugin)
    cb = func
    result = PubSubManager.subscribe("mqtt", "topic/b", cb)
    assert result is True
    mock_pubsub_plugin.subscribe.assert_called_once_with("topic/b", cb)


@pytest.mark.unit
def test_pubsub_disconnect(mock_pubsub_plugin):
    """
    등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    PubSubManager.register("mqtt", mock_pubsub_plugin)
    PubSubManager.disconnect("mqtt")
    mock_pubsub_plugin.disconnect.assert_called_once()


@pytest.mark.unit
def test_pubsub_unregister():
    """
    PubSubManager에서 플러그인을 등록 해제하는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    mock_plugin = MagicMock()
    PubSubManager.register("mqtt", mock_plugin)
    assert PubSubManager.has("mqtt") is True

    PubSubManager.unregister("mqtt")
    assert PubSubManager.has("mqtt") is False


@pytest.mark.unit
def test_pubsub_unregister_nonexistent():
    """
    존재하지 않는 플러그인을 등록 해제할 때 예외가 발생하지 않는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    # 예외가 발생하지 않아야 함
    PubSubManager.unregister("nonexistent")


@pytest.mark.unit
def test_pubsub_has():
    """
    PubSubManager의 has() 메서드가 올바르게 동작하는지 테스트합니다.
    """
    PubSubManager._plugins.clear()
    mock_plugin = MagicMock()

    assert PubSubManager.has("mqtt") is False
    PubSubManager.register("mqtt", mock_plugin)
    assert PubSubManager.has("mqtt") is True
