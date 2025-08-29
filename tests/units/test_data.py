import pytest
from typing import List
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


# 테스트 헬퍼 함수들
def assert_senddata_protocol(test_data, expected_payload):
    """SendData 프로토콜 검증 헬퍼"""
    assert test_data.to_bytes() == expected_payload
    assert isinstance(test_data, SendData)


def assert_receiveddata_protocol(test_data, expected_cmd, expected_data):
    """ReceivedData 프로토콜 검증 헬퍼"""
    assert test_data.cmd == expected_cmd
    assert test_data.data == expected_data
    assert isinstance(test_data, ReceivedData)


class TestDataPackage:
    """DataPackage 클래스 테스트 - 구성 객체"""
    
    def test_data_package_creation(self):
        """DataPackage 기본 생성 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData](
            packet_structure=PacketStructureTestData,
            send_data=SendTestData,
            received_data=ReceivedTestData
        )
        
        assert package.packet_structure == PacketStructureTestData
        assert package.send_data == SendTestData
        assert package.received_data == ReceivedTestData
    
    def test_data_package_type_safety(self):
        """DataPackage 타입 안전성 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData](
            packet_structure=PacketStructureTestData,
            send_data=SendTestData,
            received_data=ReceivedTestData
        )
        
        # 타입이 올바르게 설정되었는지 확인
        assert issubclass(package.packet_structure, PacketStructureInterface)
        assert issubclass(package.send_data, SendData)
        assert issubclass(package.received_data, ReceivedData)
    
    def test_data_package_with_cmd_data(self):
        """CmdData 클래스로 DataPackage 생성 테스트"""
        package = DataPackage[CmdDataSendTestData, CmdDataReceivedTestData](
            packet_structure=PacketStructureTestData,
            send_data=CmdDataSendTestData,
            received_data=CmdDataReceivedTestData
        )
        
        assert package.packet_structure == PacketStructureTestData
        assert package.send_data == CmdDataSendTestData
        assert package.received_data == CmdDataReceivedTestData
    
    def test_data_package_generic_type_safety(self):
        """제네릭 타입 안전성 테스트"""
        package = DataPackage[SendTestData, ReceivedTestData](
            packet_structure=PacketStructureTestData,
            send_data=SendTestData,
            received_data=ReceivedTestData
        )
        assert isinstance(package, DataPackage)
        
        class AnotherSendData(SendData):
            def to_bytes(self) -> bytes:
                return b"another"
        
        class AnotherReceivedData(ReceivedData):
            @classmethod
            def from_bytes(cls, data: bytes) -> 'AnotherReceivedData':
                return cls()
        
        another_package = DataPackage[AnotherSendData, AnotherReceivedData](
            packet_structure=PacketStructureTestData,
            send_data=AnotherSendData,
            received_data=AnotherReceivedData
        )
        assert isinstance(another_package, DataPackage)
    
    def test_data_package_usage_example(self):
        """DataPackage 사용 예시 테스트"""
        package = DataPackage[CmdDataSendTestData, CmdDataReceivedTestData](
            packet_structure=PacketStructureTestData,
            send_data=CmdDataSendTestData,
            received_data=CmdDataReceivedTestData
        )
        
        # SendData 인스턴스 생성
        send_data = package.send_data("PING", ["hello", "42"])
        assert isinstance(send_data, CmdDataSendTestData)
        assert send_data.cmd == "PING"
        assert send_data.data == ["hello", "42"]
        
        # 패킷 변환
        payload = send_data.to_bytes()
        packet = package.packet_structure.to_packet(payload)
        assert packet == b"$PING#hello#42$"
        
        # 패킷에서 데이터 추출
        extracted_payload = package.packet_structure.from_packet(packet)
        received_data = package.received_data.from_bytes(extracted_payload)
        assert isinstance(received_data, CmdDataReceivedTestData)
        assert received_data.cmd == "PING"
        assert received_data.data == ["hello", "42"]


class TestAbstractClasses:
    """추상 클래스 테스트"""
    
    def test_abstract_classes_cannot_be_instantiated(self):
        """추상 클래스는 직접 인스턴스화할 수 없음"""
        with pytest.raises(TypeError):
            ReceivedData()
        
        with pytest.raises(TypeError):
            SendData()
    
    def test_abstract_classes_inheritance(self):
        """추상 클래스 상속 테스트"""
        assert issubclass(CmdDataReceivedTestData, ReceivedData)
        assert issubclass(CmdDataSendTestData, SendData)
    
    def test_abstract_methods_are_implemented(self):
        """추상 메서드가 올바르게 구현되었는지 테스트"""
        assert hasattr(CmdDataReceivedTestData, 'from_bytes')
        assert callable(CmdDataReceivedTestData.from_bytes)
        
        test_instance = CmdDataSendTestData("TEST", [])
        assert hasattr(test_instance, 'to_bytes')
        assert callable(test_instance.to_bytes)


class TestCmdDataProtocol:
    """CmdData 프로토콜 테스트"""
    
    def test_senddata_protocol(self):
        """SendData 프로토콜 테스트"""
        test_data = CmdDataSendTestData("PING", ["hello", "42"])
        assert_senddata_protocol(test_data, b"PING#hello#42")
    
    def test_receiveddata_protocol(self):
        """ReceivedData 프로토콜 테스트"""
        test_data = CmdDataReceivedTestData.from_bytes(b"PING#hello#42")
        assert_receiveddata_protocol(test_data, "PING", ["hello", "42"])
    
    @pytest.mark.parametrize("cmd,data,expected", [
        ("", ["hello", "42"], b"#hello#42"),
        ("PING", [], b"PING"),
        ("PING", ["hello", "", "world"], b"PING#hello##world"),
    ])
    def test_senddata_edge_cases(self, cmd, data, expected):
        """SendData 엣지 케이스 테스트"""
        test_data = CmdDataSendTestData(cmd, data)
        assert_senddata_protocol(test_data, expected)
    
    @pytest.mark.parametrize("input_bytes,expected_cmd,expected_data", [
        (b"", "", []),
        (b"PING", "PING", []),
        (b"PING#hello##world", "PING", ["hello", "", "world"]),
        (b"PING#hello#world#", "PING", ["hello", "world", ""]),
        (b"PING##hello###world", "PING", ["", "hello", "", "", "world"]),
    ])
    def test_receiveddata_edge_cases(self, input_bytes, expected_cmd, expected_data):
        """ReceivedData 엣지 케이스 테스트"""
        test_data = CmdDataReceivedTestData.from_bytes(input_bytes)
        assert_receiveddata_protocol(test_data, expected_cmd, expected_data)
    
    def test_senddata_special_characters(self):
        """특수 문자와 유니코드가 포함된 데이터 테스트"""
        test_data = CmdDataSendTestData("CMD", ["한글", "test#123", "special@#$%"])
        payload = test_data.to_bytes()
        assert payload == b"CMD#\xed\x95\x9c\xea\xb8\x80#test#123#special@#$%"
        assert isinstance(test_data, SendData)
    
    def test_senddata_string_vs_integer_encoding(self):
        """문자열 "42"와 정수 42의 인코딩 차이 테스트"""
        test_data_str = CmdDataSendTestData("TEST", ["42"])
        payload_str = test_data_str.to_bytes()
        assert payload_str == b"TEST#42"
        
        test_data_int = CmdDataSendTestData("TEST", [str(42)])
        payload_int = test_data_int.to_bytes()
        assert payload_int == b"TEST#42"
        
        assert payload_str == payload_int
    
    def test_receiveddata_unicode_characters(self):
        """유니코드 문자가 포함된 데이터 테스트"""
        test_data = CmdDataReceivedTestData.from_bytes(b"CMD#\xed\x95\x9c\xea\xb8\x80#test")
        assert_receiveddata_protocol(test_data, "CMD", ["한글", "test"])
    
    def test_receiveddata_invalid_utf8(self):
        """잘못된 UTF-8 바이트 시퀀스 테스트"""
        invalid_utf8 = b"PING#hello#\xff\xfe\xfd"
        
        with pytest.raises(UnicodeDecodeError):
            CmdDataReceivedTestData.from_bytes(invalid_utf8)
    
    def test_senddata_none_values(self):
        """None 값이 포함된 데이터 테스트"""
        test_data = CmdDataSendTestData("TEST", ["hello", str(None), "world"])
        assert_senddata_protocol(test_data, b"TEST#hello#None#world")
    
    def test_receiveddata_roundtrip(self):
        """SendData -> bytes -> ReceivedData 순환 테스트"""
        original_data = CmdDataSendTestData("PING", ["hello", "42", "한글"])
        bytes_data = original_data.to_bytes()
        received_data = CmdDataReceivedTestData.from_bytes(bytes_data)
        
        assert received_data.cmd == original_data.cmd
        assert received_data.data == original_data.data
    
    def test_receiveddata_large_data(self):
        """큰 데이터 처리 테스트"""
        large_cmd = "A" * 1000
        large_data = ["B" * 500, "C" * 750]
        
        test_data = CmdDataSendTestData(large_cmd, large_data)
        payload = test_data.to_bytes()
        received_data = CmdDataReceivedTestData.from_bytes(payload)
        
        assert received_data.cmd == large_cmd
        assert received_data.data == large_data
    
    def test_senddata_very_long_string(self):
        """매우 긴 문자열 처리 테스트"""
        very_long_string = "X" * 10000
        test_data = CmdDataSendTestData("LONG", [very_long_string])
        payload = test_data.to_bytes()
        
        assert len(payload) == 10005  # "LONG#" + 10000개 X
        assert payload.startswith(b"LONG#")
        assert payload.endswith(b"X" * 10000)
    
    def test_receiveddata_whitespace_handling(self):
        """공백 문자 처리 테스트"""
        test_data = CmdDataReceivedTestData.from_bytes(b"CMD# hello #world # ")
        assert_receiveddata_protocol(test_data, "CMD", [" hello ", "world ", " "])
    
    def test_senddata_whitespace_preservation(self):
        """공백 문자 보존 테스트"""
        test_data = CmdDataSendTestData("CMD", [" hello ", "world ", " "])
        assert_senddata_protocol(test_data, b"CMD# hello #world # ")


class TestPacketStructureInterface:
    """PacketStructureInterface 테스트"""
    
    def test_packet_structure_interface_methods(self):
        """PacketStructureInterface 메서드 테스트"""
        packet_structure = PacketStructureTestData
        
        # to_packet 테스트
        data = b"hello"
        packet = packet_structure.to_packet(data)
        assert packet == b"$hello$"
        
        # from_packet 테스트
        extracted_data = packet_structure.from_packet(packet)
        assert extracted_data == data
        
        # is_valid 테스트
        assert packet_structure.is_valid(packet) is True
        assert packet_structure.is_valid(b"invalid") is False
        
        # split_packet 테스트
        stream = b"$hello$$world$"
        packets = packet_structure.split_packet(stream)
        assert packets == [b"$hello$", b"$world$"]
    
    def test_packet_structure_invalid_packet(self):
        """잘못된 패킷 처리 테스트"""
        packet_structure = PacketStructureTestData
        
        with pytest.raises(ValueError, match="Packet Structure Error"):
            packet_structure.from_packet(b"invalid_packet")
    
    def test_packet_structure_edge_cases(self):
        """패킷 구조 엣지 케이스 테스트"""
        packet_structure = PacketStructureTestData
        
        # 빈 데이터
        empty_packet = packet_structure.to_packet(b"")
        assert empty_packet == b"$$"
        assert packet_structure.is_valid(empty_packet) is False
        
        # 빈 스트림 분할
        empty_stream = b""
        packets = packet_structure.split_packet(empty_stream)
        assert packets == []