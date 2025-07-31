import pytest
from communicator.common.packet.builder import SyncNoGenerator


def test_initial_state():
    """
    SyncNoGenerator 인스턴스 생성 시 _sync_no 값이 0으로 초기화되는지 테스트합니다.
    """
    gen = SyncNoGenerator()
    assert gen._sync_no == 0  # 초기값은 0이어야 함


def test_sync_no_increment():
    """
    next() 호출 시 sync 번호가 1씩 증가하는지 테스트합니다.
    """
    gen = SyncNoGenerator()
    assert gen.next() == 1
    assert gen.next() == 2
    assert gen.next() == 3


def test_sync_no_wraps_around():
    """
    sync 번호가 255에서 next() 호출 시 0으로 순환되는지 테스트합니다.
    """
    gen = SyncNoGenerator()
    gen._sync_no = 255  # wrap 직전 상태
    assert gen.next() == 0  # (255 + 1) % 256 == 0
    assert gen.next() == 1


def test_sync_no_never_exceeds_255():
    """
    sync 번호가 항상 0~255 범위 내에 있는지 1000회 반복 테스트합니다.
    """
    gen = SyncNoGenerator()
    for _ in range(1000):
        n = gen.next()
        assert 0 <= n <= 255
