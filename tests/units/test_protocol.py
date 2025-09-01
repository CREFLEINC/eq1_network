from typing import Optional, Tuple

import pytest

from app.interfaces.protocol import BaseProtocol, PubSubProtocol, ReqResProtocol


class MockReqResProtocol(ReqResProtocol):
    """
    ReqResProtocol의 동작을 시뮬레이션하기 위한 테스트용 Mock 클래스입니다.

    - connect/disconnect 상태를 가짐
    - send 시 내부 버퍼에 데이터를 저장하고
    - read 시 해당 버퍼 값을 반환합니다.
    """

    def __init__(self):
        self.connected = False
        self._data = b"mock response"

    def connect(self) -> bool:
        """연결 상태를 True로 설정"""
        self.connected = True
        return self.connected

    def disconnect(self):
        """연결 상태를 False로 설정"""
        self.connected = False

    def send(self, data: bytes) -> bool:
        """연결된 상태일 경우 데이터를 내부 버퍼에 저장"""
        if not self.connected:
            return False
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        self._data = data
        return True

    def read(self) -> Tuple[bool, Optional[bytes]]:
        """연결된 경우 저장된 데이터를 반환, 아닐 경우 실패"""
        if not self.connected:
            return False, None
        return True, self._data


class MockPubSubProtocol(PubSubProtocol):
    """
    PubSubProtocol의 동작을 시뮬레이션하기 위한 테스트용 Mock 클래스입니다.

    - 연결 상태 및 구독 토픽 목록을 저장
    - subscribe 호출 시 콜백을 즉시 실행시켜 테스트
    """

    def __init__(self):
        self.connected = False
        self.subscribed_topics = {}
        self.last_published = None

    def connect(self) -> bool:
        """연결 상태를 True로 설정"""
        self.connected = True
        return self.connected

    def disconnect(self):
        """연결 상태를 False로 설정"""
        self.connected = False

    def publish(self, topic: str, message: bytes, qos: int = 0, retain: bool = False) -> bool:
        """토픽, 메시지, QoS를 튜플로 저장"""
        if not isinstance(topic, str) or not isinstance(message, bytes):
            raise TypeError("Invalid publish parameters")
        self.last_published = (topic, message, qos)

    def subscribe(self, topic: str, callback):
        """토픽 등록 및 테스트 콜백 즉시 실행"""
        if not callable(callback):
            raise TypeError("callback must be callable")
        self.subscribed_topics[topic] = callback
        callback(topic, b"test message")


@pytest.mark.unit
def test_reqres_protocol():
    """
    ReqResProtocol: 정상적인 연결 후 send-read 흐름이 성공적으로 작동하는지 테스트
    """
    proto = MockReqResProtocol()
    assert proto.connect() is True
    assert proto.send(b"hello") is True
    success, data = proto.read()
    assert success is True
    assert data == b"hello"
    proto.disconnect()
    assert proto.connected is False


@pytest.mark.unit
def test_pubsub_protocol():
    """
    PubSubProtocol: subscribe 후 콜백이 호출되고 publish 동작이 정상적으로 기록되는지 테스트
    """
    received = {}

    def callback(topic, msg):
        received["topic"] = topic
        received["message"] = msg

    proto = MockPubSubProtocol()
    assert proto.connect() is True
    proto.subscribe("test/topic", callback)
    assert received["topic"] == "test/topic"
    assert received["message"] == b"test message"

    proto.publish("test/topic", b"hello pubsub", qos=1)
    assert proto.last_published == ("test/topic", b"hello pubsub", 1)

    proto.disconnect()
    assert proto.connected is False


@pytest.mark.unit
def test_reqres_protocol_send_without_connect():
    """
    ReqResProtocol: 연결되지 않은 상태에서 send 호출 시 False 반환
    """
    proto = MockReqResProtocol()
    assert proto.send(b"data") is False


@pytest.mark.unit
def test_reqres_protocol_read_without_connect():
    """
    ReqResProtocol: 연결되지 않은 상태에서 read 호출 시 (False, None) 반환
    """
    proto = MockReqResProtocol()
    success, data = proto.read()
    assert success is False
    assert data is None


@pytest.mark.unit
def test_pubsub_callback_error_handling():
    """
    PubSubProtocol: 콜백 내부에서 예외가 발생할 경우에도 시스템이 콜백 호출을 시도했는지 확인
    """
    error_flag = {"called": False}

    def bad_callback(topic, msg):
        error_flag["called"] = True
        raise RuntimeError("callback failed")

    proto = MockPubSubProtocol()
    proto.connect()
    with pytest.raises(RuntimeError):
        proto.subscribe("bad/topic", bad_callback)

    assert error_flag["called"] is True


@pytest.mark.unit
def test_reqres_send_invalid_type():
    """
    ReqResProtocol: send에 bytes가 아닌 값을 넘기면 TypeError 발생
    """
    proto = MockReqResProtocol()
    proto.connect()
    with pytest.raises(TypeError):
        proto.send("not_bytes")  # type: ignore


@pytest.mark.unit
def test_pubsub_invalid_publish_args():
    """
    PubSubProtocol: publish 인자에 잘못된 타입이 들어갈 경우 TypeError 발생
    """
    proto = MockPubSubProtocol()
    proto.connect()
    with pytest.raises(TypeError):
        proto.publish(123, b"msg")  # type: ignore
    with pytest.raises(TypeError):
        proto.publish("topic", "not_bytes")  # type: ignore


@pytest.mark.unit
def test_pubsub_subscribe_with_non_callable():
    """
    PubSubProtocol: subscribe에 callable이 아닌 값을 넘길 경우 TypeError 발생
    """
    proto = MockPubSubProtocol()
    proto.connect()
    with pytest.raises(TypeError):
        proto.subscribe("topic", "not_callable")  # type: ignore


class ConcreteBaseProtocol(BaseProtocol):
    def connect(self) -> bool:
        return super().connect()

    def disconnect(self):
        return super().disconnect()


class ConcreteReqResProtocol(ReqResProtocol):
    def connect(self) -> bool:
        return super().connect()

    def disconnect(self):
        return super().disconnect()

    def send(self, data: bytes) -> bool:
        return super().send(data)

    def read(self) -> Tuple[bool, Optional[bytes]]:
        return super().read()


class ConcretePubSubProtocol(PubSubProtocol):
    def connect(self) -> bool:
        return super().connect()

    def disconnect(self):
        return super().disconnect()

    def publish(self, topic: str, message: bytes, qos: int = 0, retain: bool = False) -> bool:
        return super().publish(topic, message, qos, retain)

    def subscribe(self, topic: str, callback):
        return super().subscribe(topic, callback)


@pytest.mark.unit
def test_base_protocol_pass_statements():
    """BaseProtocol의 pass 문들을 커버하는 테스트"""
    proto = ConcreteBaseProtocol()
    assert proto.connect() is None
    assert proto.disconnect() is None


@pytest.mark.unit
def test_reqres_protocol_pass_statements():
    """ReqResProtocol의 pass 문들을 커버하는 테스트"""
    proto = ConcreteReqResProtocol()
    assert proto.send(b"test") is None
    assert proto.read() is None


@pytest.mark.unit
def test_pubsub_protocol_pass_statements():
    """PubSubProtocol의 pass 문들을 커버하는 테스트"""
    proto = ConcretePubSubProtocol()
    assert proto.publish("topic", b"msg") is None
    assert proto.subscribe("topic", lambda t, m: None) is None
