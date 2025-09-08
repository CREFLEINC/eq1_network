"""
시리얼 통신 종합 예제
- 기본 사용법부터 고급 기능까지 모든 시리얼 통신 기능을 보여줍니다
"""

import time
import threading
import struct
import serial
from datetime import datetime
from eq1_network import ReqResManager
from eq1_network.protocols.serial.serial_protocol import SerialProtocol


class ComprehensiveSerialExample:
    """시리얼 통신 종합 예제 클래스"""
    
    def __init__(self):
        self.serial_protocol = None
        self.running = False
        self.received_data = []
        self.message_count = 0
        
    def list_available_ports(self):
        """사용 가능한 시리얼 포트 목록 출력"""
        print("=== 사용 가능한 시리얼 포트 ===")
        
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            if not ports:
                print("❌ 사용 가능한 시리얼 포트가 없습니다.")
                print("   USB-시리얼 변환기나 시리얼 장치를 연결해주세요.")
                return []
            
            for i, port in enumerate(ports, 1):
                print(f"{i}. {port.device} - {port.description}")
                if port.manufacturer:
                    print(f"   제조사: {port.manufacturer}")
                if port.hwid:
                    print(f"   하드웨어 ID: {port.hwid}")
                print()
            
            return [port.device for port in ports]
            
        except ImportError:
            print("❌ pyserial이 설치되지 않았습니다.")
            print("   pip install pyserial")
            return []
    
    def setup_basic_serial(self, port_name: str, baud_rate: int = 9600):
        """기본 시리얼 설정"""
        print("=== 1. 기본 시리얼 설정 ===")
        
        try:
            self.serial_protocol = SerialProtocol(port_name, baud_rate, timeout=1)
            ReqResManager.register("serial", self.serial_protocol)
            print(f"✓ 기본 시리얼 프로토콜 설정 완료: {port_name} @ {baud_rate} bps")
            return True
        except Exception as e:
            print(f"❌ 시리얼 프로토콜 설정 실패: {e}")
            return False
    
    def setup_advanced_serial(self, port_name: str, baud_rate: int = 115200):
        """고급 시리얼 설정"""
        print("\n=== 2. 고급 시리얼 설정 ===")
        
        try:
            self.serial_protocol = SerialProtocol(port_name, baud_rate, timeout=0.5)
            ReqResManager.register("advanced_serial", self.serial_protocol)
            print(f"✓ 고급 시리얼 프로토콜 설정 완료: {port_name} @ {baud_rate} bps")
            print(f"  - 타임아웃: 0.5초")
            return True
        except Exception as e:
            print(f"❌ 고급 시리얼 프로토콜 설정 실패: {e}")
            return False
    
    def basic_communication_example(self):
        """기본 통신 예제"""
        print("\n=== 3. 기본 통신 예제 ===")
        
        try:
            if not ReqResManager.connect("serial"):
                print("❌ 연결 실패")
                return
            
            print("✓ 시리얼 포트 연결 성공")
            
            # 기본 텍스트 메시지 전송
            test_messages = [
                b"Hello Serial Device!\r\n",
                b"AT\r\n",  # AT 명령어 예시
                b"STATUS\r\n",
                b"QUIT\r\n"
            ]
            
            for i, message in enumerate(test_messages, 1):
                print(f"\n--- 메시지 {i} 전송 ---")
                print(f"전송: {message.decode().strip()}")
                
                result = ReqResManager.send("serial", message)
                if result > 0:
                    print("✓ 전송 성공")
                    
                    # 응답 대기
                    print("응답 대기 중...")
                    time.sleep(0.5)
                    
                    # 응답 수신
                    response = ReqResManager.read("serial")
                    if response:
                        print(f"📨 응답: {response.decode().strip()}")
                        self.message_count += 1
                    else:
                        print("📨 응답 없음")
                else:
                    print("❌ 전송 실패")
                
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ 기본 통신 오류: {e}")
    
    def serial_echo_test(self):
        """시리얼 에코 테스트"""
        print("\n=== 4. 시리얼 에코 테스트 ===")
        
        try:
            # 직접 pyserial 사용
            with serial.Serial(self.serial_protocol._socket.port, 9600, timeout=1) as ser:
                print("✓ 시리얼 포트 열기 성공")
                
                # 에코 테스트 메시지
                test_message = b"Echo Test Message\r\n"
                print(f"전송: {test_message.decode().strip()}")
                
                # 데이터 전송
                ser.write(test_message)
                ser.flush()  # 버퍼 비우기
                
                # 응답 읽기
                response = ser.readline()
                if response:
                    print(f"📨 응답: {response.decode().strip()}")
                    self.message_count += 1
                else:
                    print("📨 응답 없음 (타임아웃)")
                    
        except Exception as e:
            print(f"❌ 에코 테스트 오류: {e}")
    
    def binary_data_example(self):
        """바이너리 데이터 송수신 예제"""
        print("\n=== 5. 바이너리 데이터 송수신 예제 ===")
        
        try:
            if not ReqResManager.connect("advanced_serial"):
                print("❌ 연결 실패")
                return
            
            # 바이너리 데이터 생성
            test_data = struct.pack('<Iff', 12345, 3.14159, 2.71828)  # uint32, float, float
            print(f"📤 바이너리 데이터 전송: {test_data.hex()}")
            
            result = ReqResManager.send("advanced_serial", test_data)
            if result > 0:
                print("✓ 바이너리 데이터 전송 성공")
                
                # 응답 대기
                time.sleep(0.5)
                response = ReqResManager.read("advanced_serial")
                if response:
                    print(f"📨 바이너리 응답: {response.hex()}")
                    self.received_data.append(("binary", response, datetime.now()))
                    self.message_count += 1
                else:
                    print("📨 바이너리 응답 없음")
            else:
                print("❌ 바이너리 데이터 전송 실패")
                
        except Exception as e:
            print(f"❌ 바이너리 데이터 예제 오류: {e}")
    
    def hex_command_example(self):
        """HEX 명령어 송수신 예제"""
        print("\n=== 6. HEX 명령어 송수신 예제 ===")
        
        try:
            if not ReqResManager.connect("advanced_serial"):
                print("❌ 연결 실패")
                return
            
            # HEX 명령어들
            hex_commands = [
                b'\x01\x03\x00\x00\x00\x0A\xC5\xCD',  # Modbus 읽기 명령
                b'\x02\x06\x00\x01\x00\x64\x48\x0F',  # Modbus 쓰기 명령
                b'\xAA\x55\x01\x02\x03\x04\xFF',      # 커스텀 프로토콜
            ]
            
            for i, command in enumerate(hex_commands, 1):
                print(f"\n--- HEX 명령어 {i} ---")
                print(f"전송: {command.hex().upper()}")
                
                result = ReqResManager.send("advanced_serial", command)
                if result > 0:
                    print("✓ HEX 명령어 전송 성공")
                    
                    time.sleep(0.5)
                    response = ReqResManager.read("advanced_serial")
                    if response:
                        print(f"📨 HEX 응답: {response.hex().upper()}")
                        self.received_data.append(("hex", response, datetime.now()))
                        self.message_count += 1
                    else:
                        print("📨 HEX 응답 없음")
                else:
                    print("❌ HEX 명령어 전송 실패")
                
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ HEX 명령어 예제 오류: {e}")
    
    def continuous_monitoring(self):
        """연속 모니터링 예제"""
        print("\n=== 7. 연속 모니터링 예제 ===")
        
        def monitor_serial():
            """시리얼 포트 모니터링 스레드"""
            count = 0
            while self.running and count < 10:
                try:
                    response = ReqResManager.read("advanced_serial")
                    if response:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp}] 📨 수신: {response.hex().upper()}")
                        self.received_data.append(("monitor", response, datetime.now()))
                        self.message_count += 1
                        count += 1
                    else:
                        time.sleep(0.1)
                        
                except Exception as e:
                    print(f"❌ 모니터링 오류: {e}")
                    break
        
        try:
            if not ReqResManager.connect("advanced_serial"):
                print("❌ 연결 실패")
                return
            
            self.running = True
            
            # 모니터링 스레드 시작
            monitor_thread = threading.Thread(target=monitor_serial, daemon=True)
            monitor_thread.start()
            
            # 주기적 데이터 전송
            for i in range(5):
                test_data = f"MONITOR_{i:02d}\r\n".encode()
                print(f"📤 모니터링 데이터 전송: {test_data.decode().strip()}")
                
                result = ReqResManager.send("advanced_serial", test_data)
                if result > 0:
                    print("✓ 전송 성공")
                else:
                    print("❌ 전송 실패")
                
                time.sleep(1)
            
            # 모니터링 종료
            self.running = False
            monitor_thread.join(timeout=2)
            
        except Exception as e:
            print(f"❌ 연속 모니터링 오류: {e}")
            self.running = False
    
    def serial_configuration_test(self):
        """다양한 시리얼 설정 테스트"""
        print("\n=== 8. 시리얼 설정 테스트 ===")
        
        # 다양한 설정 조합
        configurations = [
            {"baud_rate": 9600, "timeout": 1, "description": "표준 설정"},
            {"baud_rate": 19200, "timeout": 0.5, "description": "중간 속도"},
            {"baud_rate": 115200, "timeout": 0.2, "description": "고속"},
            {"baud_rate": 4800, "timeout": 2, "description": "저속"},
        ]
        
        available_ports = self.list_available_ports()
        if not available_ports:
            return
        
        port_name = available_ports[0]
        
        for config in configurations:
            print(f"\n--- {config['description']} 테스트 ---")
            print(f"통신 속도: {config['baud_rate']} bps")
            print(f"타임아웃: {config['timeout']}초")
            
            try:
                # 새로운 설정으로 프로토콜 생성
                serial_protocol = SerialProtocol(
                    port_name, 
                    config['baud_rate'], 
                    config['timeout']
                )
                
                ReqResManager.register("config_test", serial_protocol)
                
                if ReqResManager.connect("config_test"):
                    print("✓ 연결 성공")
                    
                    # 테스트 데이터 전송
                    test_message = f"CONFIG_{config['baud_rate']}\r\n".encode()
                    result = ReqResManager.send("config_test", test_message)
                    if result > 0:
                        print("✓ 전송 성공")
                        
                        time.sleep(0.5)
                        response = ReqResManager.read("config_test")
                        if response:
                            print(f"📨 응답: {response.decode().strip()}")
                            self.message_count += 1
                        else:
                            print("📨 응답 없음")
                    else:
                        print("❌ 전송 실패")
                    
                    ReqResManager.disconnect("config_test")
                else:
                    print("❌ 연결 실패")
                    
            except Exception as e:
                print(f"❌ 설정 테스트 오류: {e}")
    
    def data_utils_example(self):
        """data_utils.py 사용 예제"""
        print("\n=== 9. data_utils.py 사용 예제 ===")
        
        try:
            from eq1_network.examples.data.data_utils import (
                MessageFactory,
                example_text_communication,
                example_binary_communication
            )
            from eq1_network.examples.data.dataset import MessageType
            
            # MessageFactory로 메시지 생성
            text_msg = MessageFactory.create_text_message(
                "serial_001", MessageType.COMMAND, "serial_client", "serial_device", "AT"
            )
            binary_msg = MessageFactory.create_binary_message(
                "serial_002", MessageType.DATA, "sensor", "serial_controller", b"\xAA\x55\xFF"
            )
            
            print(f"✓ 생성된 메시지:")
            print(f"  - 텍스트: {text_msg.msg_id} -> {text_msg.payload}")
            print(f"  - 바이너리: {binary_msg.msg_id} -> {binary_msg.payload.hex()}")
            
            # Serial로 메시지 전송 예시
            if ReqResManager.connect("advanced_serial"):
                # AT 명령어 전송
                at_command = (text_msg.payload + "\r\n").encode()
                result = ReqResManager.send("advanced_serial", at_command)
                if result > 0:
                    print("✓ data_utils AT 명령어 Serial로 전송 완료")
                
                # 바이너리 데이터 전송
                result = ReqResManager.send("advanced_serial", binary_msg.payload)
                if result > 0:
                    print("✓ data_utils 바이너리 데이터 Serial로 전송 완료")
                
                ReqResManager.disconnect("advanced_serial")
            
            # 통신 예시 실행
            packet, received = example_text_communication()
            print(f"✓ 텍스트 통신 예시: 패킷 크기 {len(packet)} bytes")
            
            packet, received = example_binary_communication()
            print(f"✓ 바이너리 통신 예시: 패킷 크기 {len(packet)} bytes")
            
        except ImportError as e:
            print(f"❌ data_utils 모듈 임포트 실패: {e}")
        except Exception as e:
            print(f"❌ data_utils 예제 오류: {e}")
    
    def error_handling_example(self):
        """오류 처리 예제"""
        print("\n=== 10. 오류 처리 예제 ===")
        
        # 1. 존재하지 않는 포트 연결 시도
        print("1. 존재하지 않는 포트 연결 테스트")
        try:
            bad_protocol = SerialProtocol("/dev/nonexistent", 9600, timeout=1)
            ReqResManager.register("bad_serial", bad_protocol)
            
            if not ReqResManager.connect("bad_serial"):
                print("❌ 예상된 연결 실패")
            else:
                print("⚠️ 예상과 다름: 연결 성공")
                
        except Exception as e:
            print(f"❌ 예상된 오류: {type(e).__name__}: {e}")
        
        # 2. 잘못된 데이터 전송
        print("\n2. 잘못된 데이터 전송 테스트")
        available_ports = self.list_available_ports()
        if available_ports:
            try:
                port_name = available_ports[0]
                serial_protocol = SerialProtocol(port_name, 9600, timeout=1)
                ReqResManager.register("error_test", serial_protocol)
                
                if ReqResManager.connect("error_test"):
                    # None 데이터 전송 시도
                    try:
                        result = ReqResManager.send("error_test", None)
                        print(f"None 데이터 전송 결과: {'성공' if result else '실패'}")
                    except Exception as e:
                        print(f"❌ 예상된 오류: {type(e).__name__}: {e}")
                    
                    ReqResManager.disconnect("error_test")
                else:
                    print("❌ 연결 실패로 테스트 불가")
                    
            except Exception as e:
                print(f"❌ 오류 처리 테스트 오류: {e}")
    
    def data_analysis_example(self):
        """수신 데이터 분석 예제"""
        print("\n=== 10. 수신 데이터 분석 예제 ===")
        
        if not self.received_data:
            print("분석할 데이터가 없습니다.")
            return
        
        print(f"총 수신 데이터: {len(self.received_data)}개")
        
        # 데이터 타입별 분석
        data_types = {}
        for data_type, data, timestamp in self.received_data:
            if data_type not in data_types:
                data_types[data_type] = []
            data_types[data_type].append((data, timestamp))
        
        for data_type, data_list in data_types.items():
            print(f"\n--- {data_type.upper()} 데이터 분석 ---")
            print(f"개수: {len(data_list)}개")
            
            for i, (data, timestamp) in enumerate(data_list[:3], 1):  # 처음 3개만 표시
                if isinstance(data, bytes):
                    print(f"  {i}. [{timestamp.strftime('%H:%M:%S')}] {data.hex().upper()}")
                else:
                    print(f"  {i}. [{timestamp.strftime('%H:%M:%S')}] {data}")
    
    def run_comprehensive_example(self):
        """종합 예제 실행"""
        print("시리얼 통신 종합 예제")
        print("=" * 60)
        
        # 사용 가능한 포트 확인
        available_ports = self.list_available_ports()
        if not available_ports:
            print("❌ 사용 가능한 시리얼 포트가 없습니다.")
            return
        
        # 첫 번째 포트 사용
        port_name = available_ports[0]
        print(f"사용할 포트: {port_name}")
        
        try:
            # 1. 기본 설정
            self.setup_basic_serial(port_name, 9600)
            
            # 2. 고급 설정으로 변경
            self.setup_advanced_serial(port_name, 115200)
            
            # 3. 다양한 예제 실행
            self.basic_communication_example()
            self.serial_echo_test()
            self.binary_data_example()
            self.hex_command_example()
            self.continuous_monitoring()
            self.serial_configuration_test()
            self.data_utils_example()
            self.error_handling_example()
            self.data_analysis_example()
            
            # 4. 결과 요약
            print(f"\n=== 결과 요약 ===")
            print(f"총 처리 메시지: {self.message_count}개")
            print(f"수신된 데이터: {len(self.received_data)}개")
            
            if self.received_data:
                print("\n최근 수신 데이터:")
                for data_type, data, timestamp in self.received_data[-3:]:
                    if isinstance(data, bytes):
                        print(f"  [{timestamp.strftime('%H:%M:%S')}] {data_type}: {data.hex().upper()}")
                    else:
                        print(f"  [{timestamp.strftime('%H:%M:%S')}] {data_type}: {data}")
            
        except Exception as e:
            print(f"❌ 종합 예제 실행 오류: {e}")
        finally:
            if self.serial_protocol:
                ReqResManager.disconnect("advanced_serial")
                print("✓ 시리얼 포트 연결 해제")


def quick_serial_test():
    """빠른 시리얼 테스트"""
    print("=== 빠른 시리얼 테스트 ===")
    
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            print("❌ 사용 가능한 시리얼 포트가 없습니다.")
            return
        
        port_name = ports[0].device
        print(f"테스트 포트: {port_name}")
        
        # 간단한 시리얼 테스트
        serial_protocol = SerialProtocol(port_name, 9600, timeout=1)
        ReqResManager.register("quick_serial", serial_protocol)
        
        if ReqResManager.connect("quick_serial"):
            test_message = b"Quick Test\r\n"
            if ReqResManager.send("quick_serial", test_message):
                print("✓ 전송 성공")
                
                time.sleep(0.5)
                response = ReqResManager.read("quick_serial")
                if response:
                    print(f"📨 응답: {response.decode().strip()}")
                else:
                    print("📨 응답 없음")
            else:
                print("❌ 전송 실패")
            
            ReqResManager.disconnect("quick_serial")
        else:
            print("❌ 연결 실패")
            
    except Exception as e:
        print(f"❌ 빠른 테스트 실패: {e}")


if __name__ == "__main__":
    print("시리얼 통신 종합 예제 시작")
    print("=" * 60)
    
    # 사용자 선택
    print("실행할 예제를 선택하세요:")
    print("1. 종합 예제 (모든 기능)")
    print("2. 빠른 테스트 (기본 기능만)")
    
    try:
        choice = input("선택 (1 또는 2, 기본값: 1): ").strip()
        
        if choice == "2":
            quick_serial_test()
        else:
            example = ComprehensiveSerialExample()
            example.run_comprehensive_example()
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 예제 실행 오류: {e}")
    
    print("\n" + "=" * 60)
    print("시리얼 통신 예제 완료!")
    print("\n💡 참고사항:")
    print("- 실제 시리얼 장치가 연결되어 있어야 합니다.")
    print("- USB-시리얼 변환기를 사용할 수 있습니다.")
    print("- 포트 권한 문제가 있을 수 있습니다.")
    print("- pyserial 라이브러리가 필요합니다: pip install pyserial")
