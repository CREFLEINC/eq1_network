import pytest
from collections import deque
from typing import Tuple, Optional, Deque

from communicator.common.packet.config import PacketConfig
from communicator.interfaces.protocol import ReqResProtocol
from communicator.manager.reqres_manager import ReqResManager
from communicator.common.packet.binary import FrameType, BinaryPacketStructure

class MockProtocol(ReqResProtocol):
    """
    테스트를 위한 Mock Protocol 클래스입니다.
    서버-클라이언트 간 버퍼를 이용해 통신을 시뮬레이션합니다.
    """
    def __init__(self):
        self.server_buffer: Deque[bytes] = deque()
        self.client_buffer: Deque[bytes] = deque()

    def connect(self) -> bool:
        """
        항상 연결에 성공하는 것으로 간주합니다.
        """
        return True

    def disconnect(self):
        """
        연결 해제 동작(실제 동작 없음)
        """
        pass

    def send(self, data: bytes) -> bool:
        """
        서버에서 클라이언트로 데이터 전송을 모의합니다.
        """
        self.client_buffer.append(data)
        return True

    def read(self) -> Tuple[bool, Optional[bytes]]:
        """
        클라이언트가 데이터를 수신하는 동작을 모의합니다.
        """
        if not self.client_buffer:
            return False, None
        return True, self.client_buffer.popleft()

    def client_send(self, data: bytes) -> bool:
        """
        클라이언트에서 서버로 데이터 전송을 모의합니다.
        """
        self.server_buffer.append(data)
        return True

    def server_read(self) -> Tuple[bool, Optional[bytes]]:
        """
        서버가 데이터를 수신하는 동작을 모의합니다.
        """
        if not self.server_buffer:
            return False, None
        return True, self.server_buffer.popleft()

@pytest.fixture
def protocol_pair():
    """
    서버/클라이언트용 MockProtocol 인스턴스와 매니저를 반환합니다.
    """
    config = PacketConfig(head=b'\xAA\x55', tail=b'\x0D\x0A')
    mock_protocol = MockProtocol()
    server_manager = ReqResManager(mock_protocol, config, is_server=True)

    client_protocol_adapter = MockProtocol()
    client_protocol_adapter.send = mock_protocol.client_send
    client_protocol_adapter.read = mock_protocol.read
    client_manager = ReqResManager(client_protocol_adapter, config, is_server=False)
    return server_manager, client_manager, mock_protocol

def test_retransmission_scenario(protocol_pair):
    """
    사용자 요청에 따른 데이터 복구 시나리오를 테스트합니다.
    1. 서버가 5개 패킷 전송
    2. 2번 패킷 유실 시뮬레이션
    3. 클라이언트가 유실 감지 및 재전송 요청
    4. 서버가 재전송 처리, 클라이언트가 정상 수신 확인
    """
    server_manager, client_manager, mock_protocol = protocol_pair
    # 1. 서버가 5개의 패킷 전송 (0, 1, 2, 3, 4)
    for i in range(5):
        packet = BinaryPacketStructure(config=server_manager.config, frame_type=FrameType.GET_INPUT, sync_no=i, payload=f"payload_{i}".encode())
        server_manager.send_packet(packet)
    assert len(mock_protocol.client_buffer) == 5

    # 2. 패킷 유실 시뮬레이션 (sync_no 2번 패킷 유실)
    all_packets = list(mock_protocol.client_buffer)
    mock_protocol.client_buffer.clear()
    mock_protocol.client_buffer.append(all_packets[0]) # sync_no: 0
    mock_protocol.client_buffer.append(all_packets[1]) # sync_no: 1
    # sync_no 2 is lost
    mock_protocol.client_buffer.append(all_packets[3]) # sync_no: 3
    mock_protocol.client_buffer.append(all_packets[4]) # sync_no: 4

    # 3. 클라이언트가 패킷 수신 및 유실 감지
    client_manager.receive_packet() # sync_no: 0
    client_manager.receive_packet() # sync_no: 1
    result = client_manager.receive_packet() # sync_no: 3
    assert 'missing' in result
    assert result['missing'] == [2]
    missing_packets = result['missing']

    # 4. 재전송 요청 및 복구
    client_manager.request_retransmission(missing_packets)
    server_manager.receive_packet() # 서버가 재전송 요청 패킷을 읽음
    recovered_packet_data = client_manager.receive_packet()
    assert isinstance(recovered_packet_data, dict), "receive_packet() 결과가 dict 타입이어야 함"
    assert 'sync_no' in recovered_packet_data, "receive_packet() 결과에 'sync_no' 키가 있어야 함"
    assert 'payload' in recovered_packet_data, "receive_packet() 결과에 'payload' 키가 있어야 함"
    assert recovered_packet_data['sync_no'] == 2, "재전송된 패킷의 sync_no가 2이어야 함"
    assert recovered_packet_data['payload'] == b'payload_2', "재전송된 패킷의 payload가 'payload_2'이어야 함"
