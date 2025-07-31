from collections import deque
from typing import List, Optional, Deque, Dict, Any

class PacketBuffer:
    """
    재전송을 위해 전송된 패킷을 저장하는 버퍼 클래스입니다.
    제한된 크기를 가지며, 가장 오래된 패킷부터 제거됩니다.
    """
    def __init__(self, max_size: int = 1000):
        """
        PacketBuffer 인스턴스를 초기화합니다.

        Args:
            max_size (int): 버퍼에 저장할 최대 패킷 수
        """
        if max_size <= 0:
            raise ValueError("max_size는 1 이상이어야 합니다.")
        self.max_size = max_size
        self._buffer: Dict[int, Any] = {}
        self._order: Deque[int] = deque()

    def add(self, sync_no: int, packet: Any):
        """
        버퍼에 패킷을 추가합니다.
        버퍼가 가득 차면 가장 오래된 패킷을 제거합니다.

        Args:
            sync_no (int): 패킷의 동기화 번호
            packet (Any): 저장할 패킷 데이터
        """
        if sync_no in self._buffer:
            return

        if len(self._order) >= self.max_size:
            oldest_sync_no = self._order.popleft()
            del self._buffer[oldest_sync_no]

        self._buffer[sync_no] = packet
        self._order.append(sync_no)

    def get(self, sync_no: int) -> Optional[Any]:
        """
        동기화 번호로 패킷을 조회합니다.

        Args:
            sync_no (int): 조회할 패킷의 동기화 번호

        Returns:
            Optional[Any]: 조회된 패킷 또는 없는 경우 None
        """
        return self._buffer.get(sync_no)


class MissingPacketDetector:
    """
    수신된 패킷의 동기화 번호를 기반으로 유실된 패킷을 감지합니다.
    """
    def __init__(self, max_sync_no: int = 255):
        """
        MissingPacketDetector 인스턴스를 초기화합니다.

        Args:
            max_sync_no (int): 동기화 번호의 최대값 (순환 시작점)
        """
        self._max_sync_no = max_sync_no
        self._last_sync_no: Optional[int] = None

    def detect(self, received_sync_no: int) -> List[int]:
        """
        새로운 동기화 번호를 수신하고 유실된 패킷 번호 목록을 반환합니다.

        Args:
            received_sync_no (int): 새로 수신된 동기화 번호

        Returns:
            List[int]: 유실된 것으로 감지된 동기화 번호 목록
        """
        if self._last_sync_no is None:
            self._last_sync_no = received_sync_no
            return []

        # 동일한 번호가 연속으로 들어온 경우 (중복/재전송)
        if self._last_sync_no == received_sync_no:
            return []

        missing_packets = []
        expected_sync_no = (self._last_sync_no + 1) % (self._max_sync_no + 1)

        # 순환을 고려한 차이 계산
        if expected_sync_no != received_sync_no:
            current = expected_sync_no
            while current != received_sync_no:
                missing_packets.append(current)
                current = (current + 1) % (self._max_sync_no + 1)
                # 무한 루프 방지
                if len(missing_packets) > self._max_sync_no:
                    # 비정상적으로 많은 패킷이 유실된 경우, 리스트를 비우고 마지막 번호만 갱신
                    self._last_sync_no = received_sync_no
                    return []

        self._last_sync_no = received_sync_no
        return missing_packets
