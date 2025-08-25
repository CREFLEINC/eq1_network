import pytest
from dataclasses import dataclass, field
from typing import List

from app.data import ReceivedData, SendData


@dataclass(frozen=True)
class CmdDataReceivedTestData(ReceivedData):
    """테스트 수신 데이터"""
    cmd: str
    data: List[str]

    @classmethod
    def from_bytes(cls, data: bytes):
        data = data.decode('utf-8')
        split_data = data.split('#')

        if len(split_data) == 1:
            return cls(cmd=split_data[0], data=[])

        return cls(cmd=split_data[0], data=split_data[1:])


@dataclass(frozen=True)
class CmdDataSendTestData(SendData):
    """테스트 송신 데이터"""
    cmd: str
    data: List[str] = field(default_factory=list)

    def to_bytes(self) -> bytes:
        result = self.cmd
        for datum in self.data:
            result += f"#{datum}"

        return result.encode('utf-8')


@pytest.mark.unit
def test_senddata_protocol():
    """SendData 프로토콜 테스트"""
    test_data = CmdDataSendTestData("PING", ["hello", "42"])
    payload = test_data.to_bytes()
    assert payload == b"PING#hello#42"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_receiveddata_protocol():
    """ReceivedData 프로토콜 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"PING#hello#42")
    assert test_data.cmd == "PING"
    assert test_data.data == ["hello", "42"]
    assert isinstance(test_data, ReceivedData)
