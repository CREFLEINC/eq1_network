class SyncNoGenerator:
    """
    패킷 송수신용 동기화 번호를 생성하는 클래스입니다.
    프로토콜에 따라 sync 번호를 순환 생성합니다.
    """
    def __init__(self):
        """
        SyncNoGenerator 인스턴스를 초기화합니다.
        """
        self._sync_no = 0

    def next(self) -> int:
        """
        다음 sync 번호를 반환합니다.
        251에서 다시 0으로 순환합니다.

        Returns:
            int: 다음 sync 번호
        """
        self._sync_no = (self._sync_no + 1) % 251
        return self._sync_no
