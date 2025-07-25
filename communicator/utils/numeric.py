class Numeric:
    @staticmethod
    def int_to_bytes(value: int, length: int, byteorder: str = 'big') -> bytes:
        return value.to_bytes(length, byteorder)

    @staticmethod
    def bytes_to_int(value: bytes, byteorder: str = 'big') -> int:
        return int.from_bytes(value, byteorder)
