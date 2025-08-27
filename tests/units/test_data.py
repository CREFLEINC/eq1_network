import pytest
from unittest.mock import Mock, MagicMock
from typing import Optional, List
from dataclasses import dataclass, field
import time

from app.data import DataPackage, SendData, ReceivedData
from app.interfaces.packet import PacketStructureInterface


class SendTestData(SendData):
    def __init__(self, content: str):
        self.content = content
    
    def to_bytes(self) -> bytes:
        return self.content.encode('utf-8')


class ReceivedTestData(ReceivedData):
    def __init__(self, content: str):
        self.content = content
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReceivedTestData':
        return cls(data.decode('utf-8'))


class PacketStructureTestData(PacketStructureInterface):
    HEAD_PACKET = b"$"
    TAIL_PACKET = b"$"

    @classmethod
    def to_packet(cls, data: bytes) -> bytes:
        return cls.HEAD_PACKET + data + cls.TAIL_PACKET

    @classmethod
    def from_packet(cls, packet: bytes) -> bytes:
        if not cls.is_valid(packet):
            raise ValueError(f"Packet Structure Error : {packet}")
        return packet[1:-1]

    @classmethod
    def is_valid(cls, packet: bytes) -> bool:
        if (cls.TAIL_PACKET + cls.HEAD_PACKET) in packet:
            return False
        if packet[:1] != cls.HEAD_PACKET:
            return False
        if packet[-1:] != cls.TAIL_PACKET:
            return False
        return True

    @classmethod
    def split_packet(cls, packet: bytes) -> list[bytes]:
        results = []
        for _d in packet.split(cls.HEAD_PACKET):
            if len(_d) == 0:
                continue
            results.append(cls.HEAD_PACKET + _d + cls.TAIL_PACKET)
        return results


class TestDataPackage:
    """DataPackage 클래스 테스트"""
    
    def test_data_package_creation(self):
        """DataPackage 기본 생성 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        assert package.send_data is None
        assert package.received_data is None
        assert package.packet_structure is None
        assert package.source is None
        assert package.destination is None
        assert isinstance(package.timestamp, float)
    
    def test_data_package_with_initial_data(self):
        """초기 데이터로 DataPackage 생성 테스트"""
        send_data = SendTestData("test_send")
        received_data = ReceivedTestData("test_receive")
        packet_structure = PacketStructureTestData
        
        package = DataPackage[SendTestData, ReceivedTestData](
            send_data=send_data,
            received_data=received_data,
            packet_structure=packet_structure,
            source="client1",
            destination="server1"
        )
        
        assert package.send_data == send_data
        assert package.received_data == received_data
        assert package.packet_structure == packet_structure
        assert package.source == "client1"
        assert package.destination == "server1"
    
    def test_is_outgoing(self):
        """is_outgoing 메서드 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        assert package.is_outgoing() is False
        
        package.set_send_data(SendTestData("test"))
        assert package.is_outgoing() is True
    
    def test_is_incoming(self):
        """is_incoming 메서드 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        assert package.is_incoming() is False
        
        package.set_received_data(ReceivedTestData("test"))
        assert package.is_incoming() is True
    
    def test_set_send_data(self):
        """set_send_data 메서드 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        send_data = SendTestData("test_data")
        
        result = package.set_send_data(send_data)
        
        assert result is package
        assert package.send_data == send_data
    
    def test_set_received_data(self):
        """set_received_data 메서드 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        received_data = ReceivedTestData("test_data")
        
        result = package.set_received_data(received_data)
        
        assert result is package
        assert package.received_data == received_data
    
    def test_set_packet_structure(self):
        """set_packet_structure 메서드 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        packet_structure = PacketStructureTestData
        
        result = package.set_packet_structure(packet_structure)
        
        assert result is package
        assert package.packet_structure == packet_structure
    
    def test_build_packet_success(self):
        """build_packet 성공 케이스 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        send_data = SendTestData("hello")
        package.set_send_data(send_data).set_packet_structure(PacketStructureTestData)
        
        result = package.build_packet()
        expected = b"$hello$"
        assert result == expected
    
    def test_build_packet_no_send_data(self):
        """build_packet - send_data가 없는 경우 예외 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        package.set_packet_structure(PacketStructureTestData)
        
        with pytest.raises(ValueError, match="send_data가 없습니다"):
            package.build_packet()
    
    def test_build_packet_no_packet_structure(self):
        """build_packet - packet_structure가 없는 경우 예외 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        package.set_send_data(SendTestData("test"))
        
        with pytest.raises(ValueError, match="packet_structure가 없습니다"):
            package.build_packet()
    
    def test_parse_packet_success(self):
        """parse_packet 성공 케이스 테스트"""
        packet = b"$world$"
        source = "client1"
        destination = "server1"
        
        result = DataPackage.parse_packet(
            packet,
            receiver_type=ReceivedTestData,
            packet_structure=PacketStructureTestData,
            source=source,
            destination=destination
        )
        
        assert isinstance(result, DataPackage)
        assert result.received_data is not None
        assert result.received_data.content == "world"
        assert result.packet_structure == PacketStructureTestData
        assert result.source == source
        assert result.destination == destination
        assert result.send_data is None
    
    def test_parse_packet_invalid_packet(self):
        """parse_packet - 잘못된 패킷 형식 예외 테스트"""
        invalid_packet = b"invalid_packet"
        
        with pytest.raises(ValueError, match="Packet Structure Error"):
            DataPackage.parse_packet(
                invalid_packet,
                receiver_type=ReceivedTestData,
                packet_structure=PacketStructureTestData
            )
    
    def test_parse_packets_success(self):
        """parse_packets 성공 케이스 테스트"""
        stream = b"$hello$$world$$test$"
        
        results = DataPackage.parse_packets(
            stream,
            receiver_type=ReceivedTestData,
            packet_structure=PacketStructureTestData
        )
        
        assert len(results) == 3
        assert results[0].received_data.content == "hello"
        assert results[1].received_data.content == "world"
        assert results[2].received_data.content == "test"
    
    def test_parse_packets_with_empty_packets(self):
        """parse_packets - 빈 패킷 포함 테스트"""
        stream = b"$hello$$$$world$"
        results = DataPackage.parse_packets(
            stream,
            receiver_type=ReceivedTestData,
            packet_structure=PacketStructureTestData,
            drop_empty=True
        )
        
        assert len(results) == 2
        assert results[0].received_data.content == "hello"
        assert results[1].received_data.content == "world"
    
    def test_parse_packets_empty_stream(self):
        """parse_packets - 빈 스트림 테스트"""
        stream = b""
        
        results = DataPackage.parse_packets(
            stream,
            receiver_type=ReceivedTestData,
            packet_structure=PacketStructureTestData
        )
        
        assert len(results) == 0
    
    def test_timestamp_generation(self):
        """타임스탬프 생성 테스트"""
        before_time = time.time()
        package = DataPackage[SendTestData, ReceivedTestData]()
        after_time = time.time()
        
        assert before_time <= package.timestamp <= after_time
    
    def test_custom_timestamp(self):
        """사용자 정의 타임스탬프 테스트"""
        custom_time = 1234567890.0
        package = DataPackage[SendTestData, ReceivedTestData](timestamp=custom_time)
        
        assert package.timestamp == custom_time
    
    def test_method_chaining(self):
        """메서드 체이닝 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        send_data = SendTestData("test")
        received_data = ReceivedTestData("test")
        packet_structure = PacketStructureTestData
        
        result = (package
                .set_send_data(send_data)
                .set_received_data(received_data)
                .set_packet_structure(packet_structure))
        
        assert result is package
        assert package.send_data == send_data
        assert package.received_data == received_data
        assert package.packet_structure == packet_structure
    
    def test_generic_type_safety(self):
        """제네릭 타입 안전성 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData]()
        assert isinstance(package, DataPackage)
        
        class AnotherSendData(SendData):
            def to_bytes(self) -> bytes:
                return b"another"
        
        class AnotherReceivedData(ReceivedData):
            @classmethod
            def from_bytes(cls, data: bytes) -> 'AnotherReceivedData':
                return cls()
        
        another_package = DataPackage[AnotherSendData, AnotherReceivedData]()
        assert isinstance(another_package, DataPackage)


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
def test_abstract_classes_cannot_be_instantiated():
    """추상 클래스는 직접 인스턴스화할 수 없음"""
    with pytest.raises(TypeError):
        ReceivedData()
    
    with pytest.raises(TypeError):
        SendData()


@pytest.mark.unit
def test_abstract_classes_inheritance():
    """추상 클래스 상속 테스트"""
    assert issubclass(CmdDataReceivedTestData, ReceivedData)
    assert issubclass(CmdDataSendTestData, SendData)


@pytest.mark.unit
def test_abstract_methods_are_implemented():
    """추상 메서드가 올바르게 구현되었는지 테스트"""
    assert hasattr(CmdDataReceivedTestData, 'from_bytes')
    assert callable(CmdDataReceivedTestData.from_bytes)
    
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
    test_data_str = CmdDataSendTestData("TEST", ["42"])
    payload_str = test_data_str.to_bytes()
    assert payload_str == b"TEST#42"
    
    test_data_int = CmdDataSendTestData("TEST", [str(42)])
    payload_int = test_data_int.to_bytes()
    assert payload_int == b"TEST#42"
    
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