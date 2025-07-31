class SyncNoGenerator:
    """
    패킷 송수신용 동기화 번호를 생성하는 클래스입니다.
    기본적으로 0~255(1바이트) 또는 0~65535(2바이트) 범위를 순환합니다.
    """
    def __init__(self, max_value: int = 255):
        """
        SyncNoGenerator 인스턴스를 초기화합니다.

        Args:
            max_value (
                int): 최대 sync 번호 값.
                기본값 255 (1바이트 full range
                ).
            필요시 65535로 변경 가능.
        """
        if max_value <= 0:
            raise ValueError("max_value는 1 이상이어야 합니다.")
        self._sync_no = 0
        self._max_value = max_value

    def next(self) -> int:
        """
        다음 sync 번호를 반환합니다.
        max_value에 도달하면 0으로 순환합니다.

        Returns:
            int: 다음 sync 번호
        """
        self._sync_no = (self._sync_no + 1) % (self._max_value + 1)
        return self._sync_no
