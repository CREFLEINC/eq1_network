import socket
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Union, Awaitable

from app.interfaces.protocol import ReqResProtocol
from app.common.exception import (
    TCPConnectionError,
    TCPTimeoutError,
    TCPTransmissionError,
)

logger = logging.getLogger(__name__)

THRESHOLD_BYTES = 4096


@dataclass
class TCPClientConfig:
    """
    TCP 클라이언트 설정
    Attributes:
        host (str): 대상 호스트 (연결할 서버 IP 또는 도메인)
        port (int): 대상 포트
        timeout (float): 소켓 타임아웃 초
        keepalive (bool): SO_KEEPALIVE 활성화 여부
    """
    host: str
    port: int
    timeout: float = 5.0
    keepalive: bool = True


class TCPClient(ReqResProtocol):
    """요청/응답 패턴의 TCP 클라이언트 구현"""
    def __init__(self, tcp_client_config: TCPClientConfig):
        self._host = tcp_client_config.host
        self._port = tcp_client_config.port
        self._timeout = tcp_client_config.timeout
        self._keepalive = tcp_client_config.keepalive

        self._socket = None
        self._connected: bool = False


    def connect(self) -> bool:
        """
        서버에 연결을 시도합니다.
        
        Returns:
            bool: 연결 성공 여부(성공 시 True)

        Raises:
            TCPConnectionError: 모든 시도에 실패한 경우
        """
        if self._connected and self._socket is not None:
            return True

        try:
            socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket.settimeout(self._timeout)

            if self._keepalive:
                socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            socket.connect((self._host, self._port))
            
            self._socket = socket
            self._connected = True
            
            logger.info("서버 연결 성공 (%s:%d)", self._host, self._port)
            print("서버 연결 성공 (%s:%d)", self._host, self._port)
            return True
        
        except (ConnectionRefusedError, OSError) as e:
            try:
                if self._socket is not None:
                    self._socket.close()
            except Exception:
                pass
            self._socket = None
            self._connected = False
            logger.error("서버 연결 실패: %s", e)
            raise TCPConnectionError(f"서버 연결 실패: {e}") from e


    def disconnect(self) -> None:
        """
        현재 연결을 종료합니다.
        연결이 이미 끊어진 경우 아무 작업도 하지 않습니다.

        Returns:
            None
        
        Raises:
            TCPConnectionError: 소켓 미연결 상태
        """
        if self._socket is None:
            self._connected = False
            return

        try:
            self._socket.close()
            print("연결 종료")

        finally:
            self._socket = None            
            self._connected = False            
            logger.info("연결 종료 (%s:%d)", self._host, self._port)
            print("연결 종료 (%s:%d)", self._host, self._port)
    

    def _ensure_connected(self) -> socket.socket:
        if not self._connected or self._socket is None:
            print("소켓 미연결 상태")
            raise TCPConnectionError("소켓 미연결 상태")
        return self._socket


    def send(self, data: bytes) -> bool:
        """
        데이터를 송신합니다.

        Args:
            data: 전송할 바이트 데이터

        Returns:
            bool: 전송 성공 여부

        Raises:
            TCPTimeoutError: 송신 타임아웃
            TCPTransmissionError: 기타 송신 실패(재연결 시도 포함)
            TCPConnectionError: 소켓 미연결 상태
        """
        socket = self._ensure_connected()
        try:
            if len(data) <= THRESHOLD_BYTES:   # SEND_THRESHOLD 바이트가 넘어가지 않는다면 sendall 메서드 사용
                socket.sendall(data)

            else:
                view = memoryview(data)

                while view:
                    sent = socket.send(view)

                    if sent == 0:
                        self._connected = False
                        raise RuntimeError("소켓 연결이 끊어졌습니다")

                    view = view[sent:]
                return True

        except Exception as e:
            print(f"송신 실패: {e}")
            raise TCPTransmissionError(f"송신 실패: {e}")

        except (socket.error, OSError) as e:
            self._connected = False
            raise TCPTransmissionError(f"송신 실패: {e}") from e
        
        return False


    def read(self) -> Tuple[bool, Optional[bytes]]:
        """
        호환성을 위한 별칭 메서드입니다.

        Returns:
            Tuple[bool, Optional[bytes]]: 수신된 데이터

        Raises:
            TCPTimeoutError: 수신 타임아웃
            TCPConnectionError: 소켓 미연결 상태
        """
        socket = self._ensure_connected()
        try:
            data = socket.recv(THRESHOLD_BYTES)

            if not data:
                self._connected = False
                raise TCPConnectionError("Read 연결 종료")

            return True, data
        
        except socket.timeout as te:
            raise TCPTimeoutError(f"Read 타임아웃: {te}")
        
        except (socket.error, OSError) as e:
            self._connected = False
            raise TCPConnectionError(f"Read 실패: {e}") from e


    def receive_exact(self, total_size: int) -> bytes:
        """
        정확히 total_size 바이트를 수신합니다. 부족하면 계속 읽고, 연결 종료 시 예외를 발생시킵니다.

        Args:
            total_size (int): 수신할 바이트 크기

        Returns:
            bytes: 수신된 바이트 데이터

        Raises:
            TCPTimeoutError: 수신 타임아웃
            TCPConnectionError: 소켓 미연결 상태
        """
        if total_size <= 0:
            return b""
        
        socket = self._ensure_connected()

        buffer = bytearray(total_size)
        buffer_view = memoryview(buffer)
        total_read = 0

        while total_read < total_size:
            try:
                bytes_read = socket.recv_info(buffer_view[total_read:], total_size - total_read)

            except socket.timeout as e:
                raise TCPTimeoutError(f"ReceiveExact 타임아웃: {e}")

            except (socket.error, OSError) as e:
                self._connected = False
                raise TCPTransmissionError(f"ReceiveExact 실패: {e}") from e

            if bytes_read == 0:
                self._connected = False
                raise TCPConnectionError("ReceiveExact 중 상대방이 연결을 종료했습니다")

            total_read += bytes_read

        return bytes(buffer)
