from typing import Dict, Type
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol


class ReqResManager:
    """
    요청-응답 기반 프로토콜(TCP/Serial 등)을 통합 관리하는 매니저
    """

    _plugins: Dict[str, ReqResProtocol] = {}

    @classmethod
    def load(cls, name: str, plugin: ReqResProtocol) -> None:
        """
        프로토콜 인스턴스를 등록합니다.
        """
        cls._plugins[name.lower()] = plugin

    @classmethod
    def get(cls, name: str) -> ReqResProtocol:
        """
        등록된 프로토콜 인스턴스를 반환합니다.
        """
        if name.lower() not in cls._plugins:
            raise ValueError(f"'{name}' 프로토콜이 등록되지 않았습니다.")
        return cls._plugins[name.lower()]

    @classmethod
    def connect(cls, name: str) -> bool:
        """
        등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
        """
        return cls.get(name).connect()

    @classmethod
    def send(cls, name: str, data: bytes) -> int:
        """
        등록된 플러그인 이름으로 send() 호출 시 플러그인의 send()가 호출되는지 테스트합니다.
        """
        return cls.get(name).send(data)

    @classmethod
    def receive(cls, name: str, buffer_size: int = 1024) -> bytes:
        """
        등록된 플러그인 이름으로 receive() 호출 시 플러그인의 receive()가 호출되는지 테스트합니다.
        """
        return cls.get(name).receive(buffer_size)

    @classmethod
    def disconnect(cls, name: str) -> None:
        """
        등록된 플러그인 이름으로 disconnect() 호출 시 플러그인의 disconnect()가 호출되는지 테스트합니다.
        """
        cls.get(name).disconnect()


class PubSubManager:
    """
    Pub/Sub 기반 프로토콜을 통합 관리하는 매니저
    """

    _plugins: Dict[str, PubSubProtocol] = {}

    @classmethod
    def load(cls, name: str, plugin: PubSubProtocol) -> None:
        """
        프로토콜 인스턴스를 등록합니다.
        """
        cls._plugins[name.lower()] = plugin

    @classmethod
    def get(cls, name: str) -> PubSubProtocol:
        """
        등록된 프로토콜 인스턴스를 가져옵니다.
        """
        if name.lower() not in cls._plugins:
            raise ValueError(f"'{name}' 프로토콜이 등록되지 않았습니다.")
        return cls._plugins[name.lower()]

    @classmethod
    def connect(cls, name: str) -> bool:
        """
        등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
        """
        return cls.get(name).connect()

    @classmethod
    def publish(cls, name: str, topic: str, message: str, qos: int = 0) -> bool:
        """
        등록된 플러그인 이름으로 publish() 호출 시 플러그인의 publish()가 호출되는지 테스트합니다.
        """
        return cls.get(name).publish(topic, message, qos)

    @classmethod
    def subscribe(cls, name: str, topic: str, callback, qos: int = 0) -> bool:
        """
        등록된 플러그인 이름으로 subscribe() 호출 시 플러그인의 subscribe()가 호출되는지 테스트합니다.
        """
        return cls.get(name).subscribe(topic, callback, qos)

    @classmethod
    def unsubscribe(cls, name: str, topic: str) -> bool:
        """
        등록된 플러그인 이름으로 unsubscribe() 호출 시 플러그인의 unsubscribe()가 호출되는지 테스트합니다.
        """
        return cls.get(name).unsubscribe(topic)

    @classmethod
    def disconnect(cls, name: str):
        cls.get(name).disconnect()
