from typing import List
from app.common.params import Params
from app.interfaces.protocol import ReqResProtocol, PubSubProtocol


def valid_params(params: Params, need_params: List[str]):
    """
    프로토콜 생성에 필요한 필수 파라미터가 모두 존재하는지 검증합니다.

    Args:
        params (Params): 파라미터 객체
        need_params (List[str]): 필수 파라미터 이름 목록

    Returns:
        bool: 모든 필수 파라미터가 존재하면 True

    Raises:
        ValueError: 필수 파라미터가 누락된 경우
    """
    for k in need_params:
        if not params.include(k):
            raise ValueError(f"Not found [{k}] in Network Params")

    return True


def create_mqtt_protocol(
    broker_address: str, port: int, keepalive: int = 60
) -> PubSubProtocol:
    """
    MQTT 프로토콜 인스턴스를 생성합니다.

    Args:
        broker_address (str): MQTT 브로커 주소
        port (int): 포트 번호
        keepalive (int, optional): 연결 유지 시간 (기본값: 60)

    Returns:
        PubSubProtocol: MQTT 프로토콜 객체
    """
    from app.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig

    broker_config = BrokerConfig(broker_address=broker_address, port=port, keepalive=keepalive)
    client_config = ClientConfig()
    return MQTTProtocol(broker_config, client_config)


def create_protocol(params: Params):
    """
    파라미터에 따라 적절한 Pub/Sub 프로토콜 인스턴스를 생성합니다.

    Args:
        params (Params): 프로토콜 및 연결 정보가 담긴 파라미터 객체
            - method: 프로토콜 종류 (예: "mqtt")
            - broker_address, port 등 프로토콜별 필수 파라미터

    Returns:
        PubSubProtocol | ReqResProtocol: 생성된 프로토콜 객체

    Raises:
        ValueError: 지원하지 않는 프로토콜이거나 필수 값이 누락된 경우
    """
    if not params.include("method"):
        raise ValueError("Not found [method] value in Network Params")

    method = params["method"]
    if method == "mqtt":
        required = ["broker_address", "port"]
        valid_params(params, required)
        return create_mqtt_protocol(
            broker_address=params["broker_address"],
            port=params["port"],
            keepalive=params.get("keepalive", 60),
        )
    elif method == "tcp":
        # TCP 요청/응답 프로토콜 (클라이언트/서버)
        role = params.get("role", "client").lower()  # client | server
        required = ["host", "port"]
        valid_params(params, required)
        async_mode = params.get("async_mode", False)
        reconnect = params.get("reconnect", True)
        reconnect_attempts = params.get("reconnect_attempts", 3)
        reconnect_delay = params.get("reconnect_delay", 2.0)
        timeout = params.get("timeout", 5.0)

        from app.protocols.tcp.tcp_client import TCPClient
        from app.protocols.tcp.tcp_server import TCPServer

        if role == "client":
            return TCPClient(
                host=params["host"],
                port=params["port"],
                async_mode=async_mode,
                reconnect=reconnect,
                reconnect_attempts=reconnect_attempts,
                reconnect_delay=reconnect_delay,
                timeout=timeout,
            )
        elif role == "server":
            return TCPServer(
                host=params["host"],
                port=params["port"],
                async_mode=async_mode,
                reconnect=reconnect,
                reconnect_attempts=reconnect_attempts,
                reconnect_delay=reconnect_delay,
                timeout=timeout,
            )
        else:
            raise ValueError(f"Unsupported TCP role: {role}")
    else:
        raise ValueError(f"Unsupported protocol method: {method}")
