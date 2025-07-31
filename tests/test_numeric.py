import pytest
from communicator.utils.numeric import Numeric

class TestNumeric:
    """
    Numeric 클래스의 정적 메서드들을 테스트합니다.
    """

    @pytest.mark.parametrize("value, length, byteorder, expected", [
        (255, 1, 'big', b'\xff'),
        (255, 2, 'big', b'\x00\xff'),
        (255, 2, 'little', b'\xff\x00'),
        (65535, 2, 'big', b'\xff\xff'),
        (0, 1, 'big', b'\x00'),
    ])
    def test_int_to_bytes(self, value, length, byteorder, expected):
        """
        int_to_bytes 메서드가 정수를 올바른 바이트 시퀀스로 변환하는지 테스트합니다.
        - 다양한 정수 값과 길이, 바이트 순서를 테스트합니다.
        """
        assert Numeric.int_to_bytes(value, length, byteorder) == expected

    @pytest.mark.parametrize("value, byteorder, expected", [
        (b'\xff', 'big', 255),
        (b'\x00\xff', 'big', 255),
        (b'\xff\x00', 'little', 255),
        (b'\xff\xff', 'big', 65535),
        (b'\x00', 'big', 0),
    ])
    def test_bytes_to_int(self, value, byteorder, expected):
        """
        bytes_to_int 메서드가 바이트 시퀀스를 올바른 정수로 변환하는지 테스트합니다.
        - 다양한 바이트 시퀀스와 바이트 순서를 테스트합니다.
        """
        assert Numeric.bytes_to_int(value, byteorder) == expected

    def test_int_to_bytes_with_overflow(self):
        """
        int_to_bytes 메서드에서 변환할 정수가 지정된 길이보다 클 때
        OverflowError가 발생하는지 테스트합니다.
        """
        with pytest.raises(OverflowError):
            Numeric.int_to_bytes(65536, 2, 'big')
