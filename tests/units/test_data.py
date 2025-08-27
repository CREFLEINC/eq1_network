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


# === 추상 클래스 테스트 ===

@pytest.mark.unit
def test_abstract_classes_cannot_be_instantiated():
    """추상 클래스는 직접 인스턴스화할 수 없음"""
    with pytest.raises(TypeError):
        ReceivedData()
    
    with pytest.raises(TypeError):
        SendData()


@pytest.mark.unit
def test_abstract_classes_inheritance():
    """추상 클래스 상속 테스트"""
    # ReceivedData 상속 확인
    assert issubclass(CmdDataReceivedTestData, ReceivedData)
    
    # SendData 상속 확인
    assert issubclass(CmdDataSendTestData, SendData)


@pytest.mark.unit
def test_abstract_methods_are_implemented():
    """추상 메서드가 올바르게 구현되었는지 테스트"""
    # ReceivedData의 from_bytes 메서드 확인
    assert hasattr(CmdDataReceivedTestData, 'from_bytes')
    assert callable(CmdDataReceivedTestData.from_bytes)
    
    # SendData의 to_bytes 메서드 확인
    test_instance = CmdDataSendTestData("TEST", [])
    assert hasattr(test_instance, 'to_bytes')
    assert callable(test_instance.to_bytes)


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


# === 예외 상황 및 엣지 케이스 테스트 추가 ===

@pytest.mark.unit
def test_senddata_empty_cmd():
    """빈 명령어로 SendData 생성 테스트"""
    test_data = CmdDataSendTestData("", ["hello", "42"])
    payload = test_data.to_bytes()
    assert payload == b"#hello#42"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_senddata_empty_data_list():
    """빈 데이터 리스트로 SendData 생성 테스트"""
    test_data = CmdDataSendTestData("PING", [])
    payload = test_data.to_bytes()
    assert payload == b"PING"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_senddata_empty_strings_in_data():
    """데이터에 빈 문자열이 포함된 경우 테스트"""
    test_data = CmdDataSendTestData("PING", ["hello", "", "world"])
    payload = test_data.to_bytes()
    assert payload == b"PING#hello##world"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_senddata_special_characters():
    """특수 문자와 유니코드가 포함된 데이터 테스트"""
    test_data = CmdDataSendTestData("CMD", ["한글", "test#123", "special@#$%"])
    payload = test_data.to_bytes()
    assert payload == b"CMD#\xed\x95\x9c\xea\xb8\x80#test#123#special@#$%"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_senddata_string_vs_integer_encoding():
    """문자열 "42"와 정수 42의 인코딩 차이 테스트"""
    # 문자열 "42"를 데이터로 사용
    test_data_str = CmdDataSendTestData("TEST", ["42"])
    payload_str = test_data_str.to_bytes()
    assert payload_str == b"TEST#42"
    
    # 정수 42를 문자열로 변환하여 사용
    test_data_int = CmdDataSendTestData("TEST", [str(42)])
    payload_int = test_data_int.to_bytes()
    assert payload_int == b"TEST#42"
    
    # 두 결과가 동일해야 함 (둘 다 문자열로 처리되므로)
    assert payload_str == payload_int


@pytest.mark.unit
def test_receiveddata_empty_bytes():
    """빈 바이트 데이터로 ReceivedData 생성 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"")
    assert test_data.cmd == ""
    assert test_data.data == []
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_only_cmd():
    """명령어만 있는 데이터 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"PING")
    assert test_data.cmd == "PING"
    assert test_data.data == []
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_empty_data_fields():
    """빈 데이터 필드가 포함된 경우 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"PING#hello##world")
    assert test_data.cmd == "PING"
    assert test_data.data == ["hello", "", "world"]
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_trailing_separator():
    """끝에 구분자가 있는 경우 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"PING#hello#world#")
    assert test_data.cmd == "PING"
    assert test_data.data == ["hello", "world", ""]
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_consecutive_separators():
    """연속된 구분자가 있는 경우 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"PING##hello###world")
    assert test_data.cmd == "PING"
    assert test_data.data == ["", "hello", "", "", "world"]
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_unicode_characters():
    """유니코드 문자가 포함된 데이터 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"CMD#\xed\x95\x9c\xea\xb8\x80#test")
    assert test_data.cmd == "CMD"
    assert test_data.data == ["한글", "test"]
    assert isinstance(test_data, ReceivedData)


@pytest.mark.unit
def test_receiveddata_invalid_utf8():
    """잘못된 UTF-8 바이트 시퀀스 테스트"""
    # 잘못된 UTF-8 바이트 시퀀스
    invalid_utf8 = b"PING#hello#\xff\xfe\xfd"
    
    with pytest.raises(UnicodeDecodeError):
        CmdDataReceivedTestData.from_bytes(invalid_utf8)


@pytest.mark.unit
def test_senddata_none_values():
    """None 값이 포함된 데이터 테스트"""
    # None 값을 문자열로 변환하여 처리
    test_data = CmdDataSendTestData("TEST", ["hello", str(None), "world"])
    payload = test_data.to_bytes()
    assert payload == b"TEST#hello#None#world"
    assert isinstance(test_data, SendData)


@pytest.mark.unit
def test_receiveddata_roundtrip():
    """SendData -> bytes -> ReceivedData 순환 테스트"""
    original_data = CmdDataSendTestData("PING", ["hello", "42", "한글"])
    bytes_data = original_data.to_bytes()
    received_data = CmdDataReceivedTestData.from_bytes(bytes_data)
    
    assert received_data.cmd == original_data.cmd
    assert received_data.data == original_data.data


@pytest.mark.unit
def test_receiveddata_large_data():
    """큰 데이터 처리 테스트"""
    large_cmd = "A" * 1000
    large_data = ["B" * 500, "C" * 750]
    
    test_data = CmdDataSendTestData(large_cmd, large_data)
    payload = test_data.to_bytes()
    received_data = CmdDataReceivedTestData.from_bytes(payload)
    
    assert received_data.cmd == large_cmd
    assert received_data.data == large_data


@pytest.mark.unit
def test_senddata_very_long_string():
    """매우 긴 문자열 처리 테스트"""
    very_long_string = "X" * 10000
    test_data = CmdDataSendTestData("LONG", [very_long_string])
    payload = test_data.to_bytes()
    
    assert len(payload) == 10005  # "LONG#" + 10000개 X
    assert payload.startswith(b"LONG#")
    assert payload.endswith(b"X" * 10000)


@pytest.mark.unit
def test_receiveddata_whitespace_handling():
    """공백 문자 처리 테스트"""
    test_data = CmdDataReceivedTestData.from_bytes(b"CMD# hello #world # ")
    assert test_data.cmd == "CMD"
    assert test_data.data == [" hello ", "world ", " "]


@pytest.mark.unit
def test_senddata_whitespace_preservation():
    """공백 문자 보존 테스트"""
    test_data = CmdDataSendTestData("CMD", [" hello ", "world ", " "])
    payload = test_data.to_bytes()
    assert payload == b"CMD# hello #world # "
