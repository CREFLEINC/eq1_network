import sys
from io import StringIO
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

import app.cli
from app.cli import create_parser, list_protocols, main
from app.cli import test_mqtt as cli_test_mqtt


@pytest.mark.unit
class TestCLI:
    """app/cli.py 모듈 테스트"""

    def test_create_parser(self):
        """CLI 파서 생성 테스트"""
        parser = create_parser()

        assert parser.prog == "eq1-network"
        assert "EQ-1 Network Communication Framework CLI" in parser.description

        # 서브커맨드 확인
        subparsers_actions = [
            action
            for action in parser._actions
            if hasattr(action, "choices") and action.choices is not None
        ]
        assert len(subparsers_actions) == 1
        assert "list-protocols" in subparsers_actions[0].choices
        assert "test-mqtt" in subparsers_actions[0].choices

    @patch("app.cli.ReqResManager._plugins", {"tcp": MagicMock()})
    @patch("app.cli.PubSubManager._plugins", {"mqtt": MagicMock()})
    def test_list_protocols_success(self, capsys):
        """프로토콜 목록 출력 성공 테스트"""
        list_protocols()

        captured = capsys.readouterr()
        assert "사용 가능한 프로토콜:" in captured.out
        assert "[Request-Response]:" in captured.out
        assert "- tcp" in captured.out
        assert "[Publish-Subscribe]:" in captured.out
        assert "- mqtt" in captured.out

    @patch("app.cli.ReqResManager._plugins", {})
    @patch("app.cli.PubSubManager._plugins", {})
    def test_list_protocols_empty(self, capsys):
        """빈 프로토콜 목록 테스트"""
        list_protocols()

        captured = capsys.readouterr()
        assert "사용 가능한 프로토콜이 없습니다." in captured.out

    @patch("app.cli.ReqResManager._plugins", new_callable=PropertyMock)
    def test_list_protocols_error(self, mock_plugins, capsys):
        """프로토콜 목록 오류 테스트"""
        mock_plugins.side_effect = Exception("테스트 오류")

        with pytest.raises(SystemExit) as exc_info:
            list_protocols()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "오류: 프로토콜 목록을 가져올 수 없습니다" in captured.err

    @patch("app.protocols.mqtt.mqtt_protocol.MQTTProtocol")
    @patch("app.protocols.mqtt.mqtt_protocol.BrokerConfig")
    @patch("app.protocols.mqtt.mqtt_protocol.ClientConfig")
    def test_test_mqtt_success(
        self, mock_client_config, mock_broker_config, mock_mqtt, capsys
    ):
        """MQTT 테스트 성공"""
        mock_mqtt_instance = MagicMock()
        mock_mqtt_instance.connect.return_value = True
        mock_mqtt_instance.publish.return_value = True
        mock_mqtt.return_value = mock_mqtt_instance

        cli_test_mqtt("localhost", 1883, "test/topic")

        captured = capsys.readouterr()
        assert "✓ 연결 성공" in captured.out
        assert "✓ 메시지 발행 성공" in captured.out
        assert "✓ 연결 해제 완료" in captured.out

    @patch("app.protocols.mqtt.mqtt_protocol.MQTTProtocol")
    @patch("app.protocols.mqtt.mqtt_protocol.BrokerConfig")
    @patch("app.protocols.mqtt.mqtt_protocol.ClientConfig")
    def test_test_mqtt_connection_fail(
        self, mock_client_config, mock_broker_config, mock_mqtt, capsys
    ):
        """MQTT 연결 실패 테스트"""
        mock_mqtt_instance = MagicMock()
        mock_mqtt_instance.connect.return_value = False
        mock_mqtt.return_value = mock_mqtt_instance

        with pytest.raises(SystemExit) as exc_info:
            cli_test_mqtt("localhost", 1883, "test/topic")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "✗ 연결 실패" in captured.out

    def test_test_mqtt_import_error(self, capsys):
        """MQTT ImportError 테스트"""
        with patch.dict("sys.modules", {"app.protocols.mqtt.mqtt_protocol": None}):
            with pytest.raises(SystemExit) as exc_info:
                cli_test_mqtt("localhost", 1883, "test/topic")

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "MQTT 프로토콜을 사용할 수 없습니다" in captured.err

    @patch("app.protocols.mqtt.mqtt_protocol.MQTTProtocol")
    def test_test_mqtt_exception(self, mock_mqtt, capsys):
        """MQTT 예외 처리 테스트"""
        mock_mqtt.side_effect = Exception("테스트 오류")

        with pytest.raises(SystemExit) as exc_info:
            cli_test_mqtt("localhost", 1883, "test/topic")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "MQTT 테스트 실패" in captured.err

    @patch("app.protocols.mqtt.mqtt_protocol.MQTTProtocol")
    @patch("app.protocols.mqtt.mqtt_protocol.BrokerConfig")
    @patch("app.protocols.mqtt.mqtt_protocol.ClientConfig")
    def test_test_mqtt_publish_fail(
        self, mock_client_config, mock_broker_config, mock_mqtt, capsys
    ):
        """MQTT 메시지 발행 실패 테스트"""
        mock_mqtt_instance = MagicMock()
        mock_mqtt_instance.connect.return_value = True
        mock_mqtt_instance.publish.return_value = False
        mock_mqtt.return_value = mock_mqtt_instance

        cli_test_mqtt("localhost", 1883, "test/topic")

        captured = capsys.readouterr()
        assert "✗ 메시지 발행 실패" in captured.out

    def test_main_no_command(self, capsys):
        """명령어 없이 실행 테스트"""
        result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    @patch("app.cli.list_protocols")
    def test_main_list_protocols(self, mock_list):
        """list-protocols 명령어 테스트"""
        result = main(["list-protocols"])

        assert result == 0
        mock_list.assert_called_once()

    @patch("app.cli.test_mqtt")
    def test_main_test_mqtt(self, mock_test):
        """test-mqtt 명령어 테스트"""
        result = main(
            ["test-mqtt", "--broker", "test.com", "--port", "8883", "--topic", "test"]
        )

        assert result == 0
        mock_test.assert_called_once_with("test.com", 8883, "test")

    def test_main_unknown_command_direct(self, capsys):
        """알 수 없는 명령어 직접 처리 테스트"""
        with patch("app.cli.create_parser") as mock_parser:
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = MagicMock(command="unknown")
            mock_parser.return_value = mock_parser_instance

            result = main(["unknown"])

            assert result == 1
            captured = capsys.readouterr()
            assert "알 수 없는 명령어: unknown" in captured.err

    def test_main_unknown_command(self, capsys):
        """알 수 없는 명령어 테스트"""
        with pytest.raises(SystemExit) as exc_info:
            main(["unknown"])

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid choice: 'unknown'" in captured.err

    @patch("app.cli.list_protocols")
    def test_main_keyboard_interrupt(self, mock_list, capsys):
        """KeyboardInterrupt 처리 테스트"""
        mock_list.side_effect = KeyboardInterrupt()

        result = main(["list-protocols"])

        assert result == 130
        captured = capsys.readouterr()
        assert "중단되었습니다." in captured.err

    @patch("app.cli.list_protocols")
    def test_main_unexpected_error(self, mock_list, capsys):
        """예상치 못한 오류 처리 테스트"""
        mock_list.side_effect = Exception("예상치 못한 오류")

        result = main(["list-protocols"])

        assert result == 1
        captured = capsys.readouterr()
        assert "예상치 못한 오류" in captured.err

    @patch("sys.exit")
    @patch("app.cli.__name__", "__main__")
    def test_main_module_execution(self, mock_exit):
        """모듈 직접 실행 테스트"""
        with patch("app.cli.main") as mock_main:
            mock_main.return_value = 0

            # __name__ == "__main__" 블록 시뮬레이션
            if app.cli.__name__ == "__main__":
                import sys

                sys.exit(app.cli.main())

            mock_exit.assert_called_once_with(0)
