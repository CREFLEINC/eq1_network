import pytest
import paho.mqtt.client as mqtt
from unittest.mock import MagicMock

from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolDecodeError,
    ProtocolAuthenticationError,
    ProtocolError,
)


@pytest.fixture
def mock_paho_client(mocker):
    """paho.mqtt.Client의 모의(Mock) 객체를 생성하고 반환합니다."""
    mock_client_class = mocker.patch('paho.mqtt.client.Client')
    mock_client_instance = MagicMock()

    # 각 메소드의 기본 반환 값을 설정합니다.
    mock_client_instance.publish.return_value = MagicMock(rc=mqtt.MQTT_ERR_SUCCESS)
    mock_client_instance.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)
    mock_client_instance.unsubscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)

    mock_client_class.return_value = mock_client_instance
    return mock_client_instance

@pytest.fixture
def mqtt_protocol(mock_paho_client):
    """테스트를 위한 MQTTProtocol 인스턴스를 생성합니다."""
    protocol = MQTTProtocol(broker_address="localhost", port=1883)
    return protocol


def test_initialization(mqtt_protocol, mock_paho_client):
    """__init__: 클래스 초기화가 올바르게 수행되는지 테스트합니다."""
    assert mqtt_protocol.broker_address == "localhost"
    assert mqtt_protocol.port == 1883
    assert not mqtt_protocol.is_connected
    # paho.mqtt.Client()가 호출되었는지 확인
    assert mock_paho_client.on_connect is not None
    assert mock_paho_client.on_disconnect is not None
    assert mock_paho_client.on_message is not None

class TestConnection:
    """연결 및 연결 해제 관련 테스트"""
    def test_connect_success(self, mqtt_protocol, mock_paho_client):
        """connect: 연결 성공 시나리오"""
        assert mqtt_protocol.connect() is True
        mock_paho_client.connect.assert_called_once_with("localhost", 1883, 60)
        mock_paho_client.loop_start.assert_called_once()

    def test_connect_paho_exception(self, mqtt_protocol, mock_paho_client):
        """connect: paho-mqtt 예외 발생 시 ProtocolConnectionError 발생 테스트"""
        mock_paho_client.connect.side_effect = Exception("Connection error")
        with pytest.raises(ProtocolConnectionError, match="MQTT connection failed"):
            mqtt_protocol.connect()

    def test_disconnect(self, mqtt_protocol, mock_paho_client):
        """disconnect: 정상 연결 해제 시나리오"""
        mqtt_protocol._is_connected = True
        mqtt_protocol.disconnect()
        mock_paho_client.loop_stop.assert_called_once()
        mock_paho_client.disconnect.assert_called_once()
        assert not mqtt_protocol.is_connected

class TestCallbacks:
    """내부 콜백 메소드 테스트"""
    def test_on_connect_success(self, mqtt_protocol):
        """_on_connect: 성공(rc=0) 시 is_connected가 True로 변경되는지 테스트"""
        mqtt_protocol._on_connect(None, None, None, 0)
        assert mqtt_protocol.is_connected

    def test_on_connect_auth_error(self, mqtt_protocol):
        """_on_connect: 인증 실패(rc=5) 시 ProtocolAuthenticationError 발생 테스트"""
        with pytest.raises(ProtocolAuthenticationError):
            mqtt_protocol._on_connect(None, None, None, 5)

    def test_on_disconnect(self, mqtt_protocol):
        """_on_disconnect: 호출 시 is_connected가 False로 변경되는지 테스트"""
        mqtt_protocol._is_connected = True
        mqtt_protocol._on_disconnect(None, None, 0)
        assert not mqtt_protocol.is_connected

    def test_on_message(self, mqtt_protocol, mocker):
        """_on_message: 등록된 콜백 함수가 올바르게 호출되는지 테스트"""
        mock_callback = mocker.Mock()
        mqtt_protocol._callback = mock_callback
        mock_msg = MagicMock(topic="test/topic", payload=b'{"key": "value"}')

        mqtt_protocol._on_message(None, None, mock_msg)
        mock_callback.assert_called_once_with("test/topic", b'{"key": "value"}')

    def test_on_message_decode_error(self, mqtt_protocol):
        """_on_message: 콜백 함수 실행 중 예외 발생 시 ProtocolDecodeError 발생 테스트"""
        def faulty_callback(topic, payload):
            raise ValueError("faulty")
        
        mqtt_protocol._callback = faulty_callback
        mock_msg = MagicMock()
        with pytest.raises(ProtocolDecodeError, match="decoding failed"):
            mqtt_protocol._on_message(None, None, mock_msg)

class TestPubSub:
    """발행/구독 관련 메소드 테스트"""
    def test_publish_success(self, mqtt_protocol, mock_paho_client):
        """publish: 성공 시나리오"""
        assert mqtt_protocol.publish("topic", "message") is True
        mock_paho_client.publish.assert_called_with("topic", "message", 0)

    def test_publish_fail_rc(self, mqtt_protocol, mock_paho_client):
        """publish: 실패 코드를 반환할 때 ProtocolError가 발생하는지 테스트 (현재 코드 기준)"""
        mock_paho_client.publish.return_value.rc = mqtt.MQTT_ERR_NO_CONN
        # 현재 코드의 로직상 ProtocolValidationError가 ProtocolError로 다시 싸여서 raise 됨
        with pytest.raises(ProtocolError, match="MQTT message publish failed:"):
            mqtt_protocol.publish("topic", "message")

    def test_subscribe_success(self, mqtt_protocol, mock_paho_client):
        """subscribe: 성공 시나리오"""
        def my_callback(t, p): pass
        assert mqtt_protocol.subscribe("topic", my_callback) is True
        mock_paho_client.subscribe.assert_called_with("topic", 0)
        assert mqtt_protocol._callback == my_callback

    def test_subscribe_fail_rc(self, mqtt_protocol, mock_paho_client):
        """subscribe: 실패 코드를 반환할 때 ProtocolError가 발생하는지 테스트 (현재 코드 기준)"""
        mock_paho_client.subscribe.return_value = (mqtt.MQTT_ERR_NO_CONN, 1)
        with pytest.raises(ProtocolError, match="MQTT subscription failed:"):
            mqtt_protocol.subscribe("topic", lambda t, p: None)