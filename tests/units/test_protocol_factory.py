from unittest.mock import MagicMock, patch

import pytest

from eq1_network.common.params import Params
from eq1_network.manager.protocol_factory import (
    create_ethernet_protocol,
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
    
    def get_default(self, key, default):
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
def test_valid_params_with_dict():
    """
    dict 타입 파라미터가 Params 객체로 변환되어 처리되는지 테스트합니다.
    """
    params_dict = {"a": 1, "b": 2}
    assert valid_params(params_dict, ["a", "b"]) is True


@pytest.mark.unit
def test_valid_params_with_dict_missing_key():
    """
    dict 타입 파라미터에서 키가 누락된 경우 ValueError를 발생시키는지 테스트합니다.
    """
    params_dict = {"a": 1}
    with pytest.raises(ValueError, match=r"Not found \[b\] in Network Params"):
        valid_params(params_dict, ["a", "b"])


@pytest.mark.unit
@patch("eq1_network.protocols.mqtt.mqtt_protocol.MQTTProtocol")
@patch("eq1_network.protocols.mqtt.mqtt_protocol.ClientConfig")
@patch("eq1_network.protocols.mqtt.mqtt_protocol.BrokerConfig")
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
@patch("eq1_network.manager.protocol_factory.create_mqtt_protocol")
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


@pytest.mark.unit
@patch("eq1_network.protocols.ethernet.tcp_server.TCPServer")
def test_create_ethernet_protocol_tcp_server(mock_tcp_server):
    """
    create_ethernet_protocol()이 TCP 서버 모드에서 TCPServer를 생성하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_tcp_server.return_value = mock_instance

    result = create_ethernet_protocol("tcp", "127.0.0.1", 8080, 0.01, "server")

    mock_tcp_server.assert_called_once_with("127.0.0.1", 8080, 0)
    assert result is mock_instance


@pytest.mark.unit
@patch("eq1_network.protocols.ethernet.tcp_client.TCPClient")
def test_create_ethernet_protocol_tcp_client(mock_tcp_client):
    """
    create_ethernet_protocol()이 TCP 클라이언트 모드에서 TCPClient를 생성하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_tcp_client.return_value = mock_instance

    result = create_ethernet_protocol("tcp", "127.0.0.1", 8080, 0.01, "client")

    mock_tcp_client.assert_called_once_with("127.0.0.1", 8080, 0.01)
    assert result is mock_instance


@pytest.mark.unit
def test_create_ethernet_protocol_udp_server():
    """
    create_ethernet_protocol()이 UDP 서버 모드에서 NotImplementedError를 발생시키는지 테스트합니다.
    """
    with pytest.raises(NotImplementedError, match="UDP server protocol not implemented yet"):
        create_ethernet_protocol("udp", "127.0.0.1", 8080, 0.01, "server")


@pytest.mark.unit
def test_create_ethernet_protocol_udp_client():
    """
    create_ethernet_protocol()이 UDP 클라이언트 모드에서 NotImplementedError를 발생시키는지 테스트합니다.
    """
    with pytest.raises(NotImplementedError, match="UDP client protocol not implemented yet"):
        create_ethernet_protocol("udp", "127.0.0.1", 8080, 0.01, "client")


@pytest.mark.unit
def test_create_ethernet_protocol_unsupported_protocol():
    """
    create_ethernet_protocol()이 지원하지 않는 프로토콜에서 ValueError를 발생시키는지 테스트합니다.
    """
    with pytest.raises(ValueError, match="Unsupported protocol: http with mode: client"):
        create_ethernet_protocol("http", "127.0.0.1", 8080, 0.01, "client")


@pytest.mark.unit
def test_create_ethernet_protocol_unsupported_mode():
    """
    create_ethernet_protocol()이 지원하지 않는 모드에서 ValueError를 발생시키는지 테스트합니다.
    """
    with pytest.raises(ValueError, match="Unsupported protocol: tcp with mode: proxy"):
        create_ethernet_protocol("tcp", "127.0.0.1", 8080, 0.01, "proxy")


@pytest.mark.unit
@patch("eq1_network.manager.protocol_factory.create_mqtt_protocol")
def test_create_protocol_with_dict_params(mock_create_mqtt):
    """
    create_protocol()이 dict 타입 파라미터를 Params 객체로 변환하여 처리하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_create_mqtt.return_value = mock_instance

    params_dict = {
        "method": "mqtt",
        "broker_address": "broker.emqx.io",
        "port": 1883,
    }

    result = create_protocol(params_dict)

    mock_create_mqtt.assert_called_once_with(
        broker_address="broker.emqx.io", port=1883, keepalive=60
    )
    assert result is mock_instance


@pytest.mark.unit
@patch("eq1_network.manager.protocol_factory.create_ethernet_protocol")
def test_create_protocol_with_ethernet(mock_create_ethernet):
    """
    method가 'ethernet'일 때 create_protocol()이 create_ethernet_protocol()을 호출하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_create_ethernet.return_value = mock_instance

    params = DummyParams(
        {
            "method": "ethernet",
            "protocol": "tcp",
            "address": "127.0.0.1",
            "port": 8080,
            "timeout": 0.01,
            "mode": "client",
        }
    )

    result = create_protocol(params)

    mock_create_ethernet.assert_called_once_with("tcp", "127.0.0.1", 8080, 0.01, "client")
    assert result is mock_instance


@pytest.mark.unit
@patch("eq1_network.manager.protocol_factory.create_ethernet_protocol")
def test_create_protocol_with_ethernet_default_mode(mock_create_ethernet):
    """
    method가 'ethernet'이고 mode가 없을 때 기본값 'client'로 create_ethernet_protocol()을 호출하는지 테스트합니다.
    """
    mock_instance = MagicMock()
    mock_create_ethernet.return_value = mock_instance

    params = DummyParams(
        {
            "method": "ethernet",
            "protocol": "tcp",
            "address": "127.0.0.1",
            "port": 8080,
            "timeout": 0.01,
        }
    )

    result = create_protocol(params)

    mock_create_ethernet.assert_called_once_with("tcp", "127.0.0.1", 8080, 0.01, "client")
    assert result is mock_instance


@pytest.mark.unit
def test_create_protocol_ethernet_missing_required_params():
    """
    ethernet 프로토콜에서 필수 파라미터가 누락된 경우 create_protocol()이 예외를 발생시키는지 테스트합니다.
    """
    params = DummyParams({"method": "ethernet", "protocol": "tcp", "address": "127.0.0.1"})
    with pytest.raises(ValueError, match="Not found \\[timeout\\] in Network Params"):
        create_protocol(params)
