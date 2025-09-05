"""
TCP 통신 종합 예제
- 기본 사용법부터 고급 기능까지 모든 TCP 통신 기능을 보여줍니다
"""

import time
import threading
import socket
import json
from datetime import datetime
from eq1_network import ReqResManager
from eq1_network.protocols.ethernet.tcp_client import TCPClient
from eq1_network.protocols.ethernet.tcp_server import TCPServer


class ComprehensiveTCPExample:
    """TCP 통신 종합 예제 클래스"""
    
    def __init__(self):
        self.tcp_client = None
        self.tcp_server = None
        self.running = False
        self.received_data = []
        self.message_count = 0
        
    def setup_basic_tcp(self):
        """기본 TCP 설정"""
        print("=== 1. 기본 TCP 설정 ===")
        
        try:
            # TCP 클라이언트 생성
            self.tcp_client = TCPClient("localhost", 8080, timeout=1)
            ReqResManager.register("tcp_client", self.tcp_client)
            print("✓ 기본 TCP 클라이언트 설정 완료: localhost:8080")
            
            # TCP 서버 생성
            self.tcp_server = TCPServer("localhost", 8081, timeout=1)
            ReqResManager.register("tcp_server", self.tcp_server)
            print("✓ 기본 TCP 서버 설정 완료: localhost:8081")
            
            return True
        except Exception as e:
            print(f"❌ TCP 설정 실패: {e}")
            return False
    
    def setup_advanced_tcp(self):
        """고급 TCP 설정"""
        print("\n=== 2. 고급 TCP 설정 ===")
        
        try:
            # 다양한 포트로 고급 설정
            advanced_client = TCPClient("localhost", 8082, timeout=0.5)
            ReqResManager.register("advanced_client", advanced_client)
            print("✓ 고급 TCP 클라이언트 설정 완료: localhost:8082")
            
            advanced_server = TCPServer("localhost", 8083, timeout=0.5)
            ReqResManager.register("advanced_server", advanced_server)
            print("✓ 고급 TCP 서버 설정 완료: localhost:8083")
            
            return True
        except Exception as e:
            print(f"❌ 고급 TCP 설정 실패: {e}")
            return False
    
    def basic_client_server_example(self):
        """기본 클라이언트-서버 통신 예제"""
        print("\n=== 3. 기본 클라이언트-서버 통신 예제 ===")
        
        def server_handler():
            """TCP 서버 핸들러"""
            print("=== TCP 서버 시작 ===")
            
            try:
                if self.tcp_server.connect():
                    print("✓ 서버 연결됨 (포트: 8081)")
                    
                    while self.running:
                        success, data = self.tcp_server.read()
                        
                        if success and data:
                            message = data.decode('utf-8')
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"📨 [{timestamp}] 서버 수신: {message}")
                            
                            # 응답 전송
                            response = f"서버 응답: {message.upper()}"
                            if self.tcp_server.send(response.encode('utf-8')):
                                print(f"📤 [{timestamp}] 서버 응답: {response}")
                            
                            # 종료 조건
                            if message.lower() == "quit":
                                break
                        elif not success:
                            print("❌ 클라이언트 연결이 끊어짐")
                            break
                            
                        time.sleep(0.1)
                else:
                    print("❌ 서버 연결 실패")
                    
            except Exception as e:
                print(f"❌ 서버 오류: {e}")
            finally:
                self.tcp_server.disconnect()
                print("✓ 서버 종료")
        
        def client_handler():
            """TCP 클라이언트 핸들러"""
            print("=== TCP 클라이언트 시작 ===")
            
            # 서버 시작 대기
            time.sleep(2)
            
            try:
                if self.tcp_client.connect():
                    print("✓ 클라이언트 연결됨 (포트: 8080)")
                    
                    # 테스트 메시지들
                    test_messages = [
                        "Hello Server!",
                        "How are you?",
                        "This is a test message",
                        "quit"
                    ]
                    
                    for message in test_messages:
                        print(f"📤 클라이언트 전송: {message}")
                        
                        if self.tcp_client.send(message.encode('utf-8')):
                            # 서버 응답 대기
                            time.sleep(0.5)
                            
                            success, response = self.tcp_client.read()
                            if success and response:
                                print(f"📨 클라이언트 응답: {response.decode('utf-8')}")
                                self.message_count += 1
                            
                            if message.lower() == "quit":
                                break
                        else:
                            print("❌ 클라이언트 전송 실패")
                            break
                            
                        time.sleep(1)
                else:
                    print("❌ 클라이언트 연결 실패")
                    
            except Exception as e:
                print(f"❌ 클라이언트 오류: {e}")
            finally:
                self.tcp_client.disconnect()
                print("✓ 클라이언트 종료")
        
        try:
            self.running = True
            
            # 서버 스레드 시작
            server_thread = threading.Thread(target=server_handler, daemon=True)
            server_thread.start()
            
            # 클라이언트 실행
            client_handler()
            
            # 서버 종료 대기
            self.running = False
            server_thread.join(timeout=2)
            
        except Exception as e:
            print(f"❌ 기본 클라이언트-서버 예제 오류: {e}")
            self.running = False
    
    def json_data_example(self):
        """JSON 데이터 송수신 예제"""
        print("\n=== 4. JSON 데이터 송수신 예제 ===")
        
        def json_server():
            """JSON 데이터를 처리하는 서버"""
            try:
                if self.tcp_server.connect():
                    print("✓ JSON 서버 시작")
                    
                    while self.running:
                        success, data = self.tcp_server.read()
                        
                        if success and data:
                            try:
                                json_data = json.loads(data.decode('utf-8'))
                                print(f"📨 JSON 수신: {json.dumps(json_data, indent=2)}")
                                
                                # JSON 응답 생성
                                response_data = {
                                    "status": "success",
                                    "timestamp": datetime.now().isoformat(),
                                    "received": json_data,
                                    "processed": True
                                }
                                
                                response = json.dumps(response_data)
                                if self.tcp_server.send(response.encode('utf-8')):
                                    print(f"📤 JSON 응답 전송")
                                
                            except json.JSONDecodeError:
                                print(f"❌ JSON 파싱 오류: {data.decode('utf-8')}")
                                
                        time.sleep(0.1)
                        
                else:
                    print("❌ JSON 서버 연결 실패")
                    
            except Exception as e:
                print(f"❌ JSON 서버 오류: {e}")
        
        def json_client():
            """JSON 데이터를 전송하는 클라이언트"""
            time.sleep(2)
            
            try:
                if self.tcp_client.connect():
                    print("✓ JSON 클라이언트 시작")
                    
                    # JSON 테스트 데이터들
                    json_messages = [
                        {"type": "sensor", "value": 25.5, "unit": "celsius"},
                        {"type": "command", "action": "start", "parameters": {"speed": 100}},
                        {"type": "status", "device": "motor", "state": "running"},
                    ]
                    
                    for i, json_data in enumerate(json_messages, 1):
                        message = json.dumps(json_data)
                        print(f"📤 JSON 전송 #{i}: {message}")
                        
                        if self.tcp_client.send(message.encode('utf-8')):
                            time.sleep(0.5)
                            
                            success, response = self.tcp_client.read()
                            if success and response:
                                try:
                                    response_json = json.loads(response.decode('utf-8'))
                                    print(f"📨 JSON 응답 #{i}: {json.dumps(response_json, indent=2)}")
                                    self.received_data.append(("json", response_json, datetime.now()))
                                    self.message_count += 1
                                except json.JSONDecodeError:
                                    print(f"📨 텍스트 응답 #{i}: {response.decode('utf-8')}")
                        else:
                            print(f"❌ JSON 전송 실패 #{i}")
                        
                        time.sleep(1)
                else:
                    print("❌ JSON 클라이언트 연결 실패")
                    
            except Exception as e:
                print(f"❌ JSON 클라이언트 오류: {e}")
        
        try:
            self.running = True
            
            # JSON 서버 스레드
            server_thread = threading.Thread(target=json_server, daemon=True)
            server_thread.start()
            
            # JSON 클라이언트 실행
            json_client()
            
            # 종료
            self.running = False
            server_thread.join(timeout=2)
            
        except Exception as e:
            print(f"❌ JSON 데이터 예제 오류: {e}")
            self.running = False
    
    def binary_data_example(self):
        """바이너리 데이터 송수신 예제"""
        print("\n=== 5. 바이너리 데이터 송수신 예제 ===")
        
        def binary_server():
            """바이너리 데이터를 처리하는 서버"""
            try:
                if self.tcp_server.connect():
                    print("✓ 바이너리 서버 시작")
                    
                    while self.running:
                        success, data = self.tcp_server.read()
                        
                        if success and data:
                            print(f"📨 바이너리 수신: {data.hex().upper()}")
                            
                            # 바이너리 응답 (에코)
                            if self.tcp_server.send(data):
                                print(f"📤 바이너리 응답 전송: {data.hex().upper()}")
                                
                        time.sleep(0.1)
                        
                else:
                    print("❌ 바이너리 서버 연결 실패")
                    
            except Exception as e:
                print(f"❌ 바이너리 서버 오류: {e}")
        
        def binary_client():
            """바이너리 데이터를 전송하는 클라이언트"""
            time.sleep(2)
            
            try:
                if self.tcp_client.connect():
                    print("✓ 바이너리 클라이언트 시작")
                    
                    # 바이너리 테스트 데이터들
                    binary_messages = [
                        b'\x01\x02\x03\x04\x05',  # 간단한 바이너리
                        b'\xAA\x55\xFF\x00\xAA',  # 패턴 데이터
                        b'\x48\x65\x6C\x6C\x6F',  # "Hello" in ASCII
                    ]
                    
                    for i, binary_data in enumerate(binary_messages, 1):
                        print(f"📤 바이너리 전송 #{i}: {binary_data.hex().upper()}")
                        
                        if self.tcp_client.send(binary_data):
                            time.sleep(0.5)
                            
                            success, response = self.tcp_client.read()
                            if success and response:
                                print(f"📨 바이너리 응답 #{i}: {response.hex().upper()}")
                                self.received_data.append(("binary", response, datetime.now()))
                                self.message_count += 1
                        else:
                            print(f"❌ 바이너리 전송 실패 #{i}")
                        
                        time.sleep(1)
                else:
                    print("❌ 바이너리 클라이언트 연결 실패")
                    
            except Exception as e:
                print(f"❌ 바이너리 클라이언트 오류: {e}")
        
        try:
            self.running = True
            
            # 바이너리 서버 스레드
            server_thread = threading.Thread(target=binary_server, daemon=True)
            server_thread.start()
            
            # 바이너리 클라이언트 실행
            binary_client()
            
            # 종료
            self.running = False
            server_thread.join(timeout=2)
            
        except Exception as e:
            print(f"❌ 바이너리 데이터 예제 오류: {e}")
            self.running = False
    
    def continuous_monitoring(self):
        """연속 모니터링 예제"""
        print("\n=== 6. 연속 모니터링 예제 ===")
        
        def monitoring_server():
            """연속 모니터링 서버"""
            try:
                if self.tcp_server.connect():
                    print("✓ 모니터링 서버 시작")
                    
                    while self.running:
                        success, data = self.tcp_server.read()
                        
                        if success and data:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp}] 📨 모니터링 수신: {data.decode('utf-8')}")
                            
                            # 간단한 응답
                            response = f"ACK:{timestamp}"
                            self.tcp_server.send(response.encode('utf-8'))
                            
                        time.sleep(0.1)
                        
                else:
                    print("❌ 모니터링 서버 연결 실패")
                    
            except Exception as e:
                print(f"❌ 모니터링 서버 오류: {e}")
        
        def monitoring_client():
            """연속 모니터링 클라이언트"""
            time.sleep(2)
            
            try:
                if self.tcp_client.connect():
                    print("✓ 모니터링 클라이언트 시작")
                    
                    # 주기적 데이터 전송
                    for i in range(10):
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        message = f"MONITOR_{i:02d}_{timestamp}"
                        print(f"📤 모니터링 전송: {message}")
                        
                        if self.tcp_client.send(message.encode('utf-8')):
                            time.sleep(0.2)
                            
                            success, response = self.tcp_client.read()
                            if success and response:
                                print(f"📨 모니터링 응답: {response.decode('utf-8')}")
                                self.message_count += 1
                        
                        time.sleep(0.5)
                else:
                    print("❌ 모니터링 클라이언트 연결 실패")
                    
            except Exception as e:
                print(f"❌ 모니터링 클라이언트 오류: {e}")
        
        try:
            self.running = True
            
            # 모니터링 서버 스레드
            server_thread = threading.Thread(target=monitoring_server, daemon=True)
            server_thread.start()
            
            # 모니터링 클라이언트 실행
            monitoring_client()
            
            # 종료
            self.running = False
            server_thread.join(timeout=2)
            
        except Exception as e:
            print(f"❌ 연속 모니터링 오류: {e}")
            self.running = False
    
    def connection_test_example(self):
        """연결 테스트 예제"""
        print("\n=== 7. 연결 테스트 예제 ===")
        
        # 다양한 포트와 설정으로 연결 테스트
        test_configurations = [
            {"host": "localhost", "port": 8084, "timeout": 1, "description": "표준 설정"},
            {"host": "127.0.0.1", "port": 8085, "timeout": 0.5, "description": "IP 주소"},
            {"host": "localhost", "port": 8086, "timeout": 2, "description": "긴 타임아웃"},
        ]
        
        for config in test_configurations:
            print(f"\n--- {config['description']} 테스트 ---")
            print(f"호스트: {config['host']}, 포트: {config['port']}")
            
            try:
                # 서버 생성
                server = TCPServer(config['host'], config['port'], config['timeout'])
                ReqResManager.register(f"test_server_{config['port']}", server)
                
                # 클라이언트 생성
                client = TCPClient(config['host'], config['port'], config['timeout'])
                ReqResManager.register(f"test_client_{config['port']}", client)
                
                # 연결 테스트
                if ReqResManager.connect(f"test_server_{config['port']}"):
                    print("✓ 서버 연결 성공")
                    
                    if ReqResManager.connect(f"test_client_{config['port']}"):
                        print("✓ 클라이언트 연결 성공")
                        
                        # 간단한 테스트
                        test_message = f"TEST_{config['port']}".encode()
                        result = ReqResManager.send(f"test_client_{config['port']}", test_message)
                        if result > 0:
                            print("✓ 테스트 메시지 전송 성공")
                            
                            time.sleep(0.5)
                            response = ReqResManager.read(f"test_client_{config['port']}")
                            if response:
                                print(f"📨 테스트 응답: {response.decode()}")
                                self.message_count += 1
                        
                        ReqResManager.disconnect(f"test_client_{config['port']}")
                    else:
                        print("❌ 클라이언트 연결 실패")
                    
                    ReqResManager.disconnect(f"test_server_{config['port']}")
                else:
                    print("❌ 서버 연결 실패")
                    
            except Exception as e:
                print(f"❌ 연결 테스트 오류: {e}")
    
    def error_handling_example(self):
        """오류 처리 예제"""
        print("\n=== 8. 오류 처리 예제 ===")
        
        # 1. 존재하지 않는 서버 연결 시도
        print("1. 존재하지 않는 서버 연결 테스트")
        try:
            bad_client = TCPClient("192.168.1.999", 9999, timeout=1)
            ReqResManager.register("bad_client", bad_client)
            
            if not ReqResManager.connect("bad_client"):
                print("❌ 예상된 연결 실패")
            else:
                print("⚠️ 예상과 다름: 연결 성공")
                
        except Exception as e:
            print(f"❌ 예상된 오류: {type(e).__name__}: {e}")
        
        # 2. 잘못된 데이터 전송
        print("\n2. 잘못된 데이터 전송 테스트")
        try:
            test_client = TCPClient("localhost", 8087, timeout=1)
            ReqResManager.register("error_test_client", test_client)
            
            if ReqResManager.connect("error_test_client"):
                # None 데이터 전송 시도
                try:
                    result = ReqResManager.send("error_test_client", None)
                    print(f"None 데이터 전송 결과: {'성공' if result else '실패'}")
                except Exception as e:
                    print(f"❌ 예상된 오류: {type(e).__name__}: {e}")
                
                ReqResManager.disconnect("error_test_client")
            else:
                print("❌ 연결 실패로 테스트 불가")
                
        except Exception as e:
            print(f"❌ 오류 처리 테스트 오류: {e}")
    
    def data_analysis_example(self):
        """수신 데이터 분석 예제"""
        print("\n=== 9. 수신 데이터 분석 예제 ===")
        
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
                elif isinstance(data, dict):
                    print(f"  {i}. [{timestamp.strftime('%H:%M:%S')}] {json.dumps(data, indent=4)}")
                else:
                    print(f"  {i}. [{timestamp.strftime('%H:%M:%S')}] {data}")
    
    def run_comprehensive_example(self):
        """종합 예제 실행"""
        print("TCP 통신 종합 예제")
        print("=" * 60)
        
        try:
            # 1. 기본 설정
            self.setup_basic_tcp()
            
            # 2. 고급 설정
            self.setup_advanced_tcp()
            
            # 3. 다양한 예제 실행
            self.basic_client_server_example()
            self.json_data_example()
            self.binary_data_example()
            self.continuous_monitoring()
            self.connection_test_example()
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
                    elif isinstance(data, dict):
                        print(f"  [{timestamp.strftime('%H:%M:%S')}] {data_type}: {json.dumps(data)}")
                    else:
                        print(f"  [{timestamp.strftime('%H:%M:%S')}] {data_type}: {data}")
            
        except Exception as e:
            print(f"❌ 종합 예제 실행 오류: {e}")


def quick_tcp_test():
    """빠른 TCP 테스트"""
    print("=== 빠른 TCP 테스트 ===")
    
    try:
        # 간단한 TCP 서버-클라이언트 테스트
        server = TCPServer("localhost", 8088, timeout=1)
        client = TCPClient("localhost", 8088, timeout=1)
        
        ReqResManager.register("quick_server", server)
        ReqResManager.register("quick_client", client)
        
        # 서버 연결
        if ReqResManager.connect("quick_server"):
            print("✓ 서버 연결 성공")
            
            # 클라이언트 연결
            if ReqResManager.connect("quick_client"):
                print("✓ 클라이언트 연결 성공")
                
                # 테스트 메시지
                test_message = b"Quick TCP Test"
                result = ReqResManager.send("quick_client", test_message)
                if result > 0:
                    print("✓ 메시지 전송 성공")
                    
                    time.sleep(0.5)
                    response = ReqResManager.read("quick_client")
                    if response:
                        print(f"📨 응답: {response.decode()}")
                    else:
                        print("📨 응답 없음")
                else:
                    print("❌ 메시지 전송 실패")
                
                ReqResManager.disconnect("quick_client")
            else:
                print("❌ 클라이언트 연결 실패")
            
            ReqResManager.disconnect("quick_server")
        else:
            print("❌ 서버 연결 실패")
            
    except Exception as e:
        print(f"❌ 빠른 TCP 테스트 실패: {e}")


if __name__ == "__main__":
    print("TCP 통신 종합 예제 시작")
    print("=" * 60)
    
    # 사용자 선택
    print("실행할 예제를 선택하세요:")
    print("1. 종합 예제 (모든 기능)")
    print("2. 빠른 테스트 (기본 기능만)")
    
    try:
        choice = input("선택 (1 또는 2, 기본값: 1): ").strip()
        
        if choice == "2":
            quick_tcp_test()
        else:
            example = ComprehensiveTCPExample()
            example.run_comprehensive_example()
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 예제 실행 오류: {e}")
    
    print("\n" + "=" * 60)
    print("TCP 통신 예제 완료!")
