from typing import List, Union, Dict

from eq1_network.common.params import Params
from eq1_network.interfaces.protocol import PubSubProtocol, ReqResProtocol


def valid_params(params: Union[Params, Dict], need_params: List[str]):
    """
    프로토콜 생성에 필요한 필수 파라미터가 모두 존재하는지 검증합니다.

    Args:
        params (Union[Params, Dict]): 파라미터 객체 또는 딕셔너리
        need_params (List[str]): 필수 파라미터 이름 목록

    Returns:
        bool: 모든 필수 파라미터가 존재하면 True

    Raises:
        ValueError: 필수 파라미터가 누락된 경우
    """
    # dict인 경우 Params 객체로 변환
    if isinstance(params, dict):
        params = Params(params)

    for k in need_params:
        if not params.include(k):
            raise ValueError(f"Not found [{k}] in Network Params")

    return True


def create_ethernet_protocol(protocol: str, address: str, port: int, timeout: float = 0.01, mode: str = "client"):
    from eq1_network.protocols.ethernet.tcp_server import TCPServer
    from eq1_network.protocols.ethernet.tcp_client import TCPClient

    if protocol.lower() == "tcp" and mode.lower() == "server":
        return TCPServer(address, port, int(timeout))
    elif protocol.lower() == "tcp" and mode.lower() == "client":
        return TCPClient(address, port, timeout)
    elif protocol.lower() == "udp" and mode.lower() == "server":
        raise NotImplementedError("UDP server protocol not implemented yet")
    elif protocol.lower() == "udp" and mode.lower() == "client":
        raise NotImplementedError("UDP client protocol not implemented yet")
    else:
        raise ValueError(f"Unsupported protocol: {protocol} with mode: {mode}")


def create_serial_protocol(port_name: str, baud_rate: int, timeout: int = 1):
    from eq1_network.protocols.serial.serial_protocol import SerialProtocol

    return SerialProtocol(port_name, baud_rate, timeout)


def create_mqtt_protocol(broker_address: str, port: int, keepalive: int = 60) -> PubSubProtocol:
    """
    MQTT 프로토콜 인스턴스를 생성합니다.

    Args:
        broker_address (str): MQTT 브로커 주소
        port (int): 포트 번호
        keepalive (int, optional): 연결 유지 시간 (기본값: 60)

    Returns:
        PubSubProtocol: MQTT 프로토콜 객체
    """
    from eq1_network.protocols.mqtt.mqtt_protocol import (
        BrokerConfig,
        ClientConfig,
        MQTTProtocol,
    )

    broker_config = BrokerConfig(broker_address=broker_address, port=port, keepalive=keepalive)
    client_config = ClientConfig()
    return MQTTProtocol(broker_config, client_config)


def create_protocol(params: Union[Params, Dict]) -> Union[PubSubProtocol, ReqResProtocol]:
    """
    파라미터에 따라 적절한 프로토콜 인스턴스를 생성합니다.

    Args:
        params (Union[Params, Dict]): 프로토콜 및 연결 정보가 담긴 파라미터 객체 또는 딕셔너리
            - method: 프로토콜 종류 (예: "ethernet", "serial", "mqtt")
            - 각 프로토콜별 필수 파라미터들

    Returns:
        Union[PubSubProtocol, ReqResProtocol]: 생성된 프로토콜 객체

    Raises:
        ValueError: 지원하지 않는 프로토콜이거나 필수 값이 누락된 경우
        NotImplementedError: 아직 구현되지 않은 프로토콜인 경우
    """
    # dict인 경우 Params 객체로 변환
    if isinstance(params, dict):
        params = Params(params)

    if not params.include("method"):
        raise ValueError("Not found [method] value in Network Params")

    method = params["method"]
    if method == "ethernet":
        need_params = ["protocol", "timeout", "address", "port"]
        valid_params(params, need_params)
        # mode는 선택적 파라미터로 처리 (기본값: "client")
        mode = params.get_default("mode", "client")
        return create_ethernet_protocol(
            params['protocol'], params['address'], params['port'], params['timeout'], mode
        )

    elif method == "serial":
        need_params = ["port_name", "baud_rate", "timeout"]
        valid_params(params, need_params)
        return create_serial_protocol(
            params['port_name'], params['baud_rate'], params['timeout']
        )

    elif method == "mqtt":
        required = ["broker_address", "port"]
        valid_params(params, required)
        return create_mqtt_protocol(
            broker_address=params["broker_address"],
            port=params["port"],
            keepalive=params.get_default("keepalive", 60),
        )

    else:
        raise ValueError(f"Unsupported protocol method: {method}")
