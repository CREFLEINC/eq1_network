import socket
from unittest.mock import MagicMock, patch
import pytest

from eq1_network.protocols.ethernet.tcp_client import TCPClient


class TestTCPClient:
    """TCPClient 클래스 테스트"""

    @pytest.mark.unit
    def test_init(self):
        """TCPClient 초기화 테스트"""
        client = TCPClient("127.0.0.1", 8080, 0.01)

        assert client._address == "127.0.0.1"
        assert client._port == 8080
        assert client._timeout == 0.01
        assert client._socket is None

    @pytest.mark.unit
    def test_init_default_timeout(self):
        """TCPClient 기본 timeout 값 테스트"""
        client = TCPClient("127.0.0.1", 8080)

        assert client._timeout == 0.01

    @pytest.mark.unit
    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class):
        """connect 메서드 성공 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = TCPClient("127.0.0.1", 8080, 0.01)
        result = client.connect()

        assert result is True
        assert client._socket is mock_socket
        mock_socket.settimeout.assert_called_once_with(0.01)
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 8080))

    @pytest.mark.unit
    @patch('socket.socket')
    def test_connect_connection_refused(self, mock_socket_class):
        """connect 메서드 ConnectionRefusedError 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        result = client.connect()

        assert result is False
        assert client._socket is None
        mock_socket.close.assert_called_once()

    @pytest.mark.unit
    @patch('socket.socket')
    def test_connect_os_error(self, mock_socket_class):
        """connect 메서드 OSError 테스트"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = OSError("Network unreachable")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        result = client.connect()

        assert result is False
        assert client._socket is None
        mock_socket.close.assert_called_once()

    @pytest.mark.unit
    def test_disconnect_with_socket(self):
        """disconnect 메서드 소켓이 있는 경우 테스트"""
        mock_socket = MagicMock()
        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        client.disconnect()

        mock_socket.close.assert_called_once()

    @pytest.mark.unit
    def test_disconnect_without_socket(self):
        """disconnect 메서드 소켓이 없는 경우 테스트"""
        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = None

        # 예외가 발생하지 않아야 함
        client.disconnect()

    @pytest.mark.unit
    def test_disconnect_exception(self):
        """disconnect 메서드 예외 발생 테스트"""
        mock_socket = MagicMock()
        mock_socket.close.side_effect = Exception("Close failed")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        # 예외가 발생해도 처리되어야 함
        client.disconnect()

    @pytest.mark.unit
    def test_send_success(self):
        """send 메서드 성공 테스트"""
        mock_socket = MagicMock()
        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        data = b"test data"
        result = client.send(data)

        assert result is True
        mock_socket.send.assert_called_once_with(data)

    @pytest.mark.unit
    def test_send_no_socket(self):
        """send 메서드 소켓이 없는 경우 테스트"""
        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = None

        data = b"test data"
        result = client.send(data)

        assert result is False

    @pytest.mark.unit
    def test_send_broken_pipe_error(self):
        """send 메서드 BrokenPipeError 테스트"""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = BrokenPipeError("Broken pipe")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        data = b"test data"
        result = client.send(data)

        assert result is False

    @pytest.mark.unit
    def test_send_attribute_error(self):
        """send 메서드 AttributeError 테스트"""
        mock_socket = MagicMock()
        mock_socket.send.side_effect = AttributeError("No send method")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        data = b"test data"
        result = client.send(data)

        assert result is False

    @pytest.mark.unit
    def test_read_success(self):
        """read 메서드 성공 테스트"""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"response data"

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        success, data = client.read()

        assert success is True
        assert data == b"response data"
        mock_socket.recv.assert_called_once_with(1024)

    @pytest.mark.unit
    def test_read_no_socket(self):
        """read 메서드 소켓이 없는 경우 테스트"""
        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = None

        success, data = client.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_empty_data(self):
        """read 메서드 빈 데이터 수신 테스트"""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b""

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        success, data = client.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_socket_timeout(self):
        """read 메서드 socket.timeout 테스트"""
        mock_socket = MagicMock()
        mock_socket.recv.side_effect = socket.timeout("Timeout")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        success, data = client.read()

        assert success is True
        assert data is None

    @pytest.mark.unit
    def test_read_connection_reset_error(self):
        """read 메서드 ConnectionResetError 테스트"""
        mock_socket = MagicMock()
        mock_socket.recv.side_effect = ConnectionResetError("Connection reset")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        success, data = client.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_read_attribute_error(self):
        """read 메서드 AttributeError 테스트"""
        mock_socket = MagicMock()
        mock_socket.recv.side_effect = AttributeError("No recv method")

        client = TCPClient("127.0.0.1", 8080, 0.01)
        client._socket = mock_socket

        success, data = client.read()

        assert success is False
        assert data is None

    @pytest.mark.unit
    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket
            mock_socket.recv.return_value = b"response"

            client = TCPClient("127.0.0.1", 8080, 0.01)

            # 연결
            assert client.connect() is True

            # 데이터 전송
            assert client.send(b"test") is True

            # 데이터 수신
            success, data = client.read()
            assert success is True
            assert data == b"response"

            # 연결 해제
            client.disconnect()

            # 모든 메서드가 올바르게 호출되었는지 확인
            mock_socket.settimeout.assert_called_once_with(0.01)
            mock_socket.connect.assert_called_once_with(("127.0.0.1", 8080))
            mock_socket.send.assert_called_once_with(b"test")
            mock_socket.recv.assert_called_once_with(1024)
            mock_socket.close.assert_called_once()
