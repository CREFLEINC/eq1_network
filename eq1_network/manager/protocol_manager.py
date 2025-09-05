from typing import Dict

from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol


class ReqResManager:
    """
    요청-응답 기반 프로토콜(TCP/Serial 등)을 통합 관리하는 매니저
    """

    _plugins: Dict[str, ReqResProtocol] = {}

    @classmethod
    def register(cls, name: str, plugin: ReqResProtocol) -> None:
        cls._plugins[name] = plugin

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._plugins.pop(name, None)

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._plugins

    @classmethod
    def get(cls, name: str) -> ReqResProtocol:
        try:
            return cls._plugins[name]
        except KeyError:
            # 필요 시 커스텀 예외로 바꿔도 됨
            raise LookupError(f"ReqRes plugin not found: {name}")

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
    def read(cls, name: str) -> bytes:
        """
        등록된 플러그인 이름으로 read() 호출 시 플러그인의 read()가 호출되는지 테스트합니다.
        """
        success, data = cls.get(name).read()
        if success and data is not None:
            return data
        return b""

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
    def register(cls, name: str, plugin: PubSubProtocol) -> None:
        cls._plugins[name] = plugin

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._plugins.pop(name, None)

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._plugins

    @classmethod
    def get(cls, name: str) -> PubSubProtocol:
        try:
            return cls._plugins[name]
        except KeyError:
            # 필요 시 커스텀 예외로 바꿔도 됨
            raise LookupError(f"PubSub plugin not found: {name}")

    @classmethod
    def connect(cls, name: str) -> bool:
        """
        등록된 플러그인 이름으로 connect() 호출 시 플러그인의 connect()가 호출되는지 테스트합니다.
        """
        return cls.get(name).connect()

    @classmethod
    def publish(cls, name: str, topic: str, message: str, qos: int = 0, retain: bool = False) -> bool:
        """
        등록된 플러그인 이름으로 publish() 호출 시 플러그인의 publish()가 호출되는지 테스트합니다.
        """
        return cls.get(name).publish(topic, message.encode(), qos)

    @classmethod
    def subscribe(cls, name: str, topic: str, callback, qos: int = 0) -> bool:
        """
        등록된 플러그인 이름으로 subscribe() 호출 시 플러그인의 subscribe()가 호출되는지 테스트합니다.
        """
        cls.get(name).subscribe(topic, callback, qos)
        return True

    @classmethod
    def disconnect(cls, name: str):
        cls.get(name).disconnect()
