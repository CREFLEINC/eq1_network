from unittest.mock import MagicMock, patch

import pytest

from app.common.params import Params
from app.manager.protocol_factory import (
    create_mqtt_protocol,
    create_protocol,
    valid_params,
)


class DummyParams(Params):
    """
    테스트용 파라미터 클래스
    dict 기반으로 동작하며, Params 인터페이스를 구현합니다.
    """

    def __init__(self, data: dict):
        self._data = data

    def include(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.mark.unit
def test_valid_params_success():
    """
    모든 필수 키가 존재할 경우 valid_params()가 True를 반환하는지 테스트합니다.
    """
    params = DummyParams({"a": 1, "b": 2})
    assert valid_params(params, ["a", "b"]) is True


@pytest.mark.unit
def test_valid_params_missing_key():
    """
    일부 키가 누락된 경우 valid_params()가 ValueError를 발생시키는지 테스트합니다.
    """
    params = DummyParams({"a": 1})
    with pytest.raises(ValueError, match=r"Not found \[b\] in Network Params"):
        valid_params(params, ["a", "b"])


@pytest.mark.unit
@patch("app.protocols.mqtt.mqtt_protocol.MQTTProtocol")
@patch("app.protocols.mqtt.mqtt_protocol.ClientConfig")
@patch("app.protocols.mqtt.mqtt_protocol.BrokerConfig")
def test_create_mqtt_protocol_success(mock_broker_cfg_cls, mock_client_cfg_cls, mock_mqtt_cls):
    """
    create_mqtt_protocol()이 BrokerConfig/ClientConfig를 생성해
    MQTTProtocol(BrokerConfig(), ClientConfig())로 호출하는지 검증
    """
    # returns
    mock_broker_cfg = MagicMock()
    mock_client_cfg = MagicMock()
    mock_instance = MagicMock()

    mock_broker_cfg_cls.return_value = mock_broker_cfg
    mock_client_cfg_cls.return_value = mock_client_cfg
    mock_mqtt_cls.return_value = mock_instance

    broker = "broker.emqx.io"
    port = 1883

    result = create_mqtt_protocol(broker, port)

    # BrokerConfig가 올바른 kwargs로 생성됐는지
    mock_broker_cfg_cls.assert_called_once_with(broker_address=broker, port=port, keepalive=60)
    # ClientConfig 생성 호출(파라미터 없다면 빈 호출)
    mock_client_cfg_cls.assert_called_once_with()

    # MQTTProtocol이 두 설정 객체로 호출됐는지
    mock_mqtt_cls.assert_called_once_with(mock_broker_cfg, mock_client_cfg)

    assert result is mock_instance


@pytest.mark.unit
@patch("app.manager.protocol_factory.create_mqtt_protocol")
def test_create_protocol_with_mqtt(mock_create_mqtt):
    """
    method가 'mqtt'일 때 create_protocol()이 create_mqtt_protocol()을 호출하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_create_mqtt.return_value = mock_instance

    params = DummyParams(
        {
            "method": "mqtt",
            "broker_address": "broker.emqx.io",
            "port": 1883,
        }
    )

    result = create_protocol(params)

    mock_create_mqtt.assert_called_once_with(
        broker_address="broker.emqx.io", port=1883, keepalive=60
    )
    assert result is mock_instance


@pytest.mark.unit
def test_create_protocol_missing_method():
    """
    method 키가 누락된 경우 create_protocol()이 ValueError를 발생시키는지 테스트합니다.
    """
    params = DummyParams({"broker_address": "broker.emqx.io", "port": 1883})
    with pytest.raises(ValueError, match="Not found \\[method\\] value in Network Params"):
        create_protocol(params)


@pytest.mark.unit
def test_create_protocol_unsupported_method():
    """
    method가 지원되지 않는 프로토콜일 때 create_protocol()이 ValueError를 발생시키는지 테스트합니다.
    """
    params = DummyParams({"method": "amqp", "broker_address": "broker.emqx.io", "port": 1883})
    with pytest.raises(ValueError, match="Unsupported protocol method: amqp"):
        create_protocol(params)


@pytest.mark.unit
def test_create_protocol_missing_required_params():
    """
    필수 파라미터(broker_address)가 누락된 경우 create_protocol()이 예외를 발생시키는지 테스트합니다.
    """
    params = DummyParams({"method": "mqtt", "port": 1883})
    with pytest.raises(ValueError, match="Not found \\[broker_address\\] in Network Params"):
        create_protocol(params)
