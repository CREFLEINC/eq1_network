import logging
import socket
import time
from typing import Optional, Tuple

from eq1_network.interfaces.protocol import ReqResProtocol


class TCPServer(ReqResProtocol):
    def __init__(self, address: str, port: int, timeout: int = 1):
        self._address = address
        self._port = port
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._conn: Optional[socket.socket] = None

    def is_connected(self) -> bool:
        return self._conn is not None

    def connect(self) -> bool:
        if self._conn is not None:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )  # Address already in use Error 방지.
            self._socket.bind((self._address, self._port))
            self._socket.settimeout(self._timeout)
            self._socket.listen(1)  # Client 동시 연결 수 1:1 로 제한 설정.
            self._conn, _ = self._socket.accept()
            self._conn.settimeout(self._timeout)

            return True
        except socket.timeout as te:
            logging.error(f"failed to connect {self._address}:{self._port}... {te}")
            self.disconnect()

            return False
        except socket.error as se:
            logging.error(
                f"failed to connect {self._address}:{self._port}... {se}. retry after {self._timeout}sec. "
            )
            self.disconnect()
            time.sleep(self._timeout)
            return False
        except Exception as e:
            logging.error(
                f"failed to connect {self._address}:{self._port}... {e}. retry after {self._timeout}sec."
            )
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
            logging.error(f"failed to disconnect {self._address}:{self._port}... {e}")
            pass

    def send(self, data: bytes) -> bool:
        try:
            self._conn.send(data)
            return True
        except socket.timeout as te:
            logging.error(f"failed to send data. {te}")
            return True
        except BrokenPipeError as be:
            print(f"failed to send data. {be}")
            return False
        except AttributeError as ae:
            print(f"failed to send data. {ae}")
            return False

    def read(self) -> Tuple[bool, Optional[bytes]]:
        try:
            data = self._conn.recv(1024)
            if not data:
                raise ConnectionResetError

            return True, data
        except socket.timeout as te:
            logging.error(f"failed to read data. {te}")
            return True, None
        except ConnectionResetError as ce:
            print(f"failed to read data. {ce}")
            return False, None
        except AttributeError as ae:
            print(f"failed to read data. {ae}")
            return False, None
