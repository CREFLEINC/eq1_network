from typing import Any, Tuple
import logging
import serial

from app.interfaces.protocol import ReqResProtocol


class SerialProtocol(ReqResProtocol):
    def __init__(self, port_name: str, baud_rate: int, timeout: int = 1):
        super().__init__()
        self._socket = serial.Serial(port_name, baud_rate, timeout=timeout)

    def connect(self) -> bool:
        return True

    def disconnect(self):
        return True

    def send(self, data: Any) -> bool:
        try:
            self._socket.write(data)
            return True
        except Exception as e:
            logging.error(f"failed to send data. {e}")
            return False

    def read(self) -> Tuple[bool, Any]:
        try:
            data = self._socket.readline()

            return True, data
        except serial.SerialTimeoutException as te:
            logging.error(f"failed to read data. {te}")
            return True, None
        except Exception as e:
            logging.error(f"failed to read data. {e}")
            return False, None
