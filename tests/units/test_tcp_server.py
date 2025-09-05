import socket
from unittest.mock import MagicMock, patch
import pytest

from eq1_network.protocols.ethernet.tcp_server import TCPServer


class TestTCPServer:
    """TCPServer 클래스 테스트"""

    @pytest.mark.unit
    def test_init(self):
        """TCPServer 초기화 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)

        assert server._address == "127.0.0.1"
        assert server._port == 8080
        assert server._timeout == 1
        assert server._socket is None
        assert server._conn is None

    @pytest.mark.unit
    def test_init_default_timeout(self):
        """TCPServer 기본 timeout 값 테스트"""
        server = TCPServer("127.0.0.1", 8080)

        assert server._timeout == 1

    @pytest.mark.unit
    def test_is_connected_true(self):
        """is_connected 메서드 연결된 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = MagicMock()

        assert server.is_connected() is True

    @pytest.mark.unit
    def test_is_connected_false(self):
        """is_connected 메서드 연결되지 않은 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = None

        assert server.is_connected() is False

    @pytest.mark.unit
    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class):
        """connect 메서드 성공 테스트"""
        mock_socket = MagicMock()
        mock_conn = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.accept.return_value = (mock_conn, ("127.0.0.1", 12345))

        server = TCPServer("127.0.0.1", 8080, 1)
        result = server.connect()

        assert result is True
        assert server._socket is mock_socket
        assert server._conn is mock_conn

        # 소켓 설정 확인
        mock_socket.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 8080))
        mock_socket.settimeout.assert_called_once_with(1)
        mock_socket.listen.assert_called_once_with(1)
        mock_socket.accept.assert_called_once()
        mock_conn.settimeout.assert_called_once_with(1)

    @pytest.mark.unit
    def test_connect_already_connected(self):
        """connect 메서드 이미 연결된 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = MagicMock()

        result = server.connect()

        assert result is True

    @pytest.mark.unit
    @patch('socket.socket')
    @patch('time.sleep')
    def test_connect_socket_timeout(self, mock_sleep, mock_socket_class):
        """connect 메서드 socket.timeout 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.accept.side_effect = socket.timeout("Timeout")

        server = TCPServer("127.0.0.1", 8080, 1)
        result = server.connect()

        assert result is False
        assert server._socket is None
        assert server._conn is None

    @pytest.mark.unit
    @patch('socket.socket')
    @patch('time.sleep')
    def test_connect_socket_error(self, mock_sleep, mock_socket_class):
        """connect 메서드 socket.error 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.side_effect = socket.error("Address already in use")

        server = TCPServer("127.0.0.1", 8080, 1)
        result = server.connect()

        assert result is False
        assert server._socket is None
        assert server._conn is None
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.unit
    @patch('socket.socket')
    @patch('time.sleep')
    def test_connect_general_exception(self, mock_sleep, mock_socket_class):
        """connect 메서드 일반 예외 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.side_effect = Exception("Unexpected error")

        server = TCPServer("127.0.0.1", 8080, 1)
        result = server.connect()

        assert result is False
        assert server._socket is None
        assert server._conn is None
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.unit
    def test_disconnect_with_connections(self):
        """disconnect 메서드 연결이 있는 경우 테스트"""
        mock_socket = MagicMock()
        mock_conn = MagicMock()

        server = TCPServer("127.0.0.1", 8080, 1)
        server._socket = mock_socket
        server._conn = mock_conn

        server.disconnect()

        mock_conn.close.assert_called_once()
        mock_socket.close.assert_called_once()
        assert server._conn is None
        assert server._socket is None

    @pytest.mark.unit
    def test_disconnect_without_connections(self):
        """disconnect 메서드 연결이 없는 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._socket = None
        server._conn = None

        # 예외가 발생하지 않아야 함
        server.disconnect()

    @pytest.mark.unit
    def test_disconnect_exception(self):
        """disconnect 메서드 예외 발생 테스트"""
        mock_socket = MagicMock()
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Close failed")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._socket = mock_socket
        server._conn = mock_conn

        # 예외가 발생해도 처리되어야 함
        server.disconnect()

    @pytest.mark.unit
    def test_send_success(self):
        """send 메서드 성공 테스트"""
        mock_conn = MagicMock()
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        data = b"test data"
        result = server.send(data)

        assert result is True
        mock_conn.send.assert_called_once_with(data)

    @pytest.mark.unit
    def test_send_no_connection(self):
        """send 메서드 연결이 없는 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = None

        data = b"test data"
        result = server.send(data)

        assert result is False

    @pytest.mark.unit
    def test_send_socket_timeout(self):
        """send 메서드 socket.timeout 테스트"""
        mock_conn = MagicMock()
        mock_conn.send.side_effect = socket.timeout("Timeout")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        data = b"test data"
        result = server.send(data)

        assert result is True  # timeout은 True를 반환

    @pytest.mark.unit
    def test_send_broken_pipe_error(self):
        """send 메서드 BrokenPipeError 테스트"""
        mock_conn = MagicMock()
        mock_conn.send.side_effect = BrokenPipeError("Broken pipe")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        data = b"test data"
        result = server.send(data)

        assert result is False

    @pytest.mark.unit
    def test_send_attribute_error(self):
        """send 메서드 AttributeError 테스트"""
        mock_conn = MagicMock()
        mock_conn.send.side_effect = AttributeError("No send method")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        data = b"test data"
        result = server.send(data)

        assert result is False

    @pytest.mark.unit
    def test_read_success(self):
        """read 메서드 성공 테스트"""
        mock_conn = MagicMock()
        mock_conn.recv.return_value = b"response data"

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        success, data = server.read()

        assert success is True
        assert data == b"response data"
        mock_conn.recv.assert_called_once_with(1024)

    @pytest.mark.unit
    def test_read_no_connection(self):
        """read 메서드 연결이 없는 경우 테스트"""
        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = None

        success, data = server.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_empty_data(self):
        """read 메서드 빈 데이터 수신 테스트"""
        mock_conn = MagicMock()
        mock_conn.recv.return_value = b""

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        success, data = server.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_socket_timeout(self):
        """read 메서드 socket.timeout 테스트"""
        mock_conn = MagicMock()
        mock_conn.recv.side_effect = socket.timeout("Timeout")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        success, data = server.read()

        assert success is True
        assert data is None

    @pytest.mark.unit
    def test_read_connection_reset_error(self):
        """read 메서드 ConnectionResetError 테스트"""
        mock_conn = MagicMock()
        mock_conn.recv.side_effect = ConnectionResetError("Connection reset")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        success, data = server.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_attribute_error(self):
        """read 메서드 AttributeError 테스트"""
        mock_conn = MagicMock()
        mock_conn.recv.side_effect = AttributeError("No recv method")

        server = TCPServer("127.0.0.1", 8080, 1)
        server._conn = mock_conn

        success, data = server.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    @patch('socket.socket')
    def test_full_workflow(self, mock_socket_class):
        """전체 워크플로우 테스트"""
        mock_socket = MagicMock()
        mock_conn = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.accept.return_value = (mock_conn, ("127.0.0.1", 12345))
        mock_conn.recv.return_value = b"response"

        server = TCPServer("127.0.0.1", 8080, 1)

        # 연결 상태 확인
        assert server.is_connected() is False

        # 연결
        assert server.connect() is True
        assert server.is_connected() is True

        # 데이터 전송
        assert server.send(b"test") is True

        # 데이터 수신
        success, data = server.read()
        assert success is True
        assert data == b"response"

        # 연결 해제
        server.disconnect()
        assert server.is_connected() is False

        # 모든 메서드가 올바르게 호출되었는지 확인
        mock_socket.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 8080))
        mock_socket.settimeout.assert_called_once_with(1)
        mock_socket.listen.assert_called_once_with(1)
        mock_socket.accept.assert_called_once()
        mock_conn.settimeout.assert_called_once_with(1)
        mock_conn.send.assert_called_once_with(b"test")
        mock_conn.recv.assert_called_once_with(1024)
        mock_conn.close.assert_called_once()
        mock_socket.close.assert_called_once()

    @pytest.mark.unit
    @patch('socket.socket')
    def test_connect_retry_behavior(self, mock_socket_class):
        """연결 재시도 동작 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.side_effect = socket.error("Address already in use")
        server = TCPServer("127.0.0.1", 8080, 1)

        with patch('time.sleep') as mock_sleep:
            result = server.connect()

            assert result is False
            mock_sleep.assert_called_once_with(1)
