import time
import socket
import traceback
import logging
from typing import Optional, Tuple
from app.interfaces.protocol import ReqResProtocol

logger = logging.getLogger(__name__)

class TCPServer(ReqResProtocol):
    def __init__(self, address: str, port: int, timeout: int = 1):
        self._address = address
        self._port = port
        self._timeout = timeout
        self._socket = None
        self._conn = None

    def is_connected(self) -> bool:
        return self._conn is not None

    def connect(self) -> bool:
        if self._conn is not None:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Address already in use Error 방지.
            self._socket.bind((self._address, self._port))
            self._socket.settimeout(self._timeout)
            self._socket.listen(1)  # Client 동시 연결 수 1:1 로 제한 설정.
            self._conn, _ = self._socket.accept()
            self._conn.settimeout(self._timeout)

            return True
        except socket.timeout as te:
            self.disconnect()

            return False
        except socket.error as se:
            logger.error(f"socket error 발생. {se}. {self._address}:{self._port}. retry after {self._timeout}sec. ")
            self.disconnect()
            time.sleep(self._timeout)
            return False
        except Exception as e:
            logger.error(f"failed to connect {self._address}:{self._port}... {traceback.format_exc()}. retry after {self._timeout}sec.")
            self.disconnect()
            time.sleep(self._timeout)
            return False

    def disconnect(self):
        try:
            if self._conn is not None:
                self._conn.close()
            if self._socket is not None:
                self._socket.close()
            self._conn = None
            self._socket = None
        except Exception as e:
            pass

    def send(self, data: bytes) -> bool:
        try:
            self._conn.send(data)
            return True
        except socket.timeout as te:
            return True
        except BrokenPipeError as be:
            print(f'failed to send data. {be}')
            return False
        except AttributeError as ae:
            print(f'failed to send data. {ae}')
            return False

    def read(self) -> Tuple[bool, Optional[bytes]]:
        try:
            data = self._conn.recv(1024)
            if not data:
                raise ConnectionResetError

            return True, data
        except socket.timeout as te:
            return True, None
        except ConnectionResetError as ce:
            print(f'failed to read data. {ce}')
            return False, None
        except AttributeError as ae:
            print(f'failed to read data. {ae}')
            return False, None