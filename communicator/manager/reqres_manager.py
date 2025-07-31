from typing import Optional, List, Any, Dict
from communicator.common.packet.builder import SyncNoGenerator
from communicator.common.packet.config import PacketConfig
from communicator.common.packet.binary import FrameType, BinaryPacketStructure
from communicator.common.recovery import PacketBuffer, MissingPacketDetector
from communicator.interfaces.protocol import ReqResProtocol
from communicator.utils.numeric import Numeric

class ReqResManager:
    """
    요청/응답 프로토콜 통신과 데이터 복구를 관리하는 클래스.
    """
    def __init__(self, protocol: ReqResProtocol, config: PacketConfig, is_server: bool = False):
        """
        ReqResManager 인스턴스를 초기화합니다.

        Args:
            protocol (ReqResProtocol): 통신에 사용할 프로토콜 인스턴스.
            config (PacketConfig): 패킷 구성 정보.
            is_server (bool): 서버 모드로 동작할지 여부.
        """
        self.protocol = protocol
        self.config = config
        self.is_server = is_server
        self.sync_no_generator = SyncNoGenerator()

        if self.is_server:
            self.packet_buffer = PacketBuffer()
        else:
            self.missing_packet_detector = MissingPacketDetector()

    def send_packet(self, frame_type: FrameType, payload: bytes) -> bool:
        """
        지정된 타입과 페이로드로 패킷을 전송합니다.
        """
        sync_no = self.sync_no_generator.next()
        packet_builder = BinaryPacketStructure(sync_no=sync_no, cmd=frame_type, payload=payload)
        packet_builder.config = self.config
        packet_bytes = packet_builder.build()

        success = self.protocol.send(packet_bytes)
        if success and self.is_server:
            self.packet_buffer.add(sync_no, packet_bytes)
        
        return success

    def receive_packet(self) -> Optional[Dict[str, Any]]:
        """
        패킷을 수신하고 처리합니다.
        """
        success, raw_data = self.protocol.read()
        if not success or not raw_data:
            return None

        try:
            parsed_data = BinaryPacketStructure.parse(raw_data, self.config)
        except ValueError as e:
            print(f"Packet parsing failed: {e}")
            return None

        frame_type = FrameType(parsed_data.get('frame_type'))
        sync_no = parsed_data.get('sync_no')
        payload = parsed_data.get('payload')

        if self.is_server:
            if frame_type == FrameType.RETRANSMISSION_REQUEST:
                self._handle_retransmission_request(payload)
                return None
        else:
            missing_sync_nos = self.missing_packet_detector.detect(sync_no)
            if missing_sync_nos:
                print(f"Missing packets detected: {missing_sync_nos}")
                # 재전송 요청 로직을 호출할 수 있도록 유실 패킷 정보 반환
                parsed_data['missing'] = missing_sync_nos

        return parsed_data

    def request_retransmission(self, missing_sync_nos: List[int]):
        """
        서버에 특정 패킷의 재전송을 요청합니다. (클라이언트용)
        """
        if self.is_server:
            raise RuntimeError("Retransmission can only be requested by a client.")
        
        # 각 sync_no를 1바이트로 변환하여 payload 생성
        payload = b''.join([Numeric.int_to_bytes(sn, 1) for sn in missing_sync_nos])
        self.send_packet(FrameType.RETRANSMISSION_REQUEST, payload)

    def _handle_retransmission_request(self, payload: bytes):
        """
        클라이언트의 재전송 요청을 처리합니다. (서버용)
        """
        # 1바이트씩 읽어 요청된 sync_no 목록을 얻습니다.
        requested_sync_nos = [Numeric.bytes_to_int(payload[i:i+1]) for i in range(len(payload))]
        
        for sync_no in requested_sync_nos:
            packet_to_resend = self.packet_buffer.get(sync_no)
            if packet_to_resend:
                self.protocol.send(packet_to_resend)
