import argparse
import sys
from typing import List, Optional

from eq1_network import __version__
from eq1_network.manager.protocol_manager import PubSubManager, ReqResManager


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성"""
    parser = argparse.ArgumentParser(
        prog="eq1-network",
        description="EQ-1 Network Communication Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            eq1-network --version                       # 버전 정보 출력
            eq1-network list-protocols                  # 사용 가능한 프로토콜 목록
            eq1-network test-mqtt --broker localhost    # MQTT 연결 테스트
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # list-protocols 서브커맨드
    subparsers.add_parser("list-protocols", help="사용 가능한 프로토콜 목록")

    # test-mqtt 서브커맨드
    mqtt_parser = subparsers.add_parser("test-mqtt", help="MQTT 연결 테스트")
    mqtt_parser.add_argument(
        "--broker", default="localhost", help="MQTT 브로커 주소 (기본값: localhost)"
    )
    mqtt_parser.add_argument(
        "--port", type=int, default=1883, help="MQTT 브로커 포트 (기본값: 1883)"
    )
    mqtt_parser.add_argument(
        "--topic", default="test/topic", help="테스트 토픽 (기본값: test/topic)"
    )

    return parser


def list_protocols() -> None:
    """사용 가능한 프로토콜 목록 출력"""
    try:
        reqres_protocols = list(ReqResManager._plugins.keys())
        pubsub_protocols = list(PubSubManager._plugins.keys())

        print("사용 가능한 프로토콜:")

        if reqres_protocols:
            print("  [Request-Response]:")
            for protocol_name in reqres_protocols:
                print(f"    - {protocol_name}")

        if pubsub_protocols:
            print("  [Publish-Subscribe]:")
            for protocol_name in pubsub_protocols:
                print(f"    - {protocol_name}")

        if not reqres_protocols and not pubsub_protocols:
            print("사용 가능한 프로토콜이 없습니다.")

    except Exception as e:
        print(f"오류: 프로토콜 목록을 가져올 수 없습니다: {e}", file=sys.stderr)
        sys.exit(1)


def test_mqtt(broker: str, port: int, topic: str) -> None:
    """MQTT 연결 테스트"""
    try:
        from eq1_network.protocols.mqtt.mqtt_protocol import (
            BrokerConfig,
            ClientConfig,
            MQTTProtocol,
        )

        print(f"MQTT 브로커 연결 테스트: {broker}:{port}")

        # 설정 생성
        broker_config = BrokerConfig(broker_address=broker, port=port, mode="non-blocking")
        client_config = ClientConfig()

        # 프로토콜 인스턴스 생성
        mqtt = MQTTProtocol(broker_config, client_config)

        # 연결 테스트
        print("연결 중...")
        if mqtt.connect():
            print("✓ 연결 성공")

            # 발행 테스트
            test_message = "Hello from EQ-1 Network CLI"
            print(f"메시지 발행 테스트: {topic}")
            if mqtt.publish(topic, test_message):
                print("✓ 메시지 발행 성공")
            else:
                print("✗ 메시지 발행 실패")

            # 연결 해제
            mqtt.disconnect()
            print("✓ 연결 해제 완료")

        else:
            print("✗ 연결 실패")
            sys.exit(1)

    except ImportError:
        print(
            "오류: MQTT 프로토콜을 사용할 수 없습니다. paho-mqtt를 설치해주세요.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"오류: MQTT 테스트 실패: {e}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[List[str]] = None) -> int:
    """메인 CLI 진입점"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "list-protocols":
            list_protocols()
        elif args.command == "test-mqtt":
            test_mqtt(args.broker, args.port, args.topic)
        else:
            print(f"알 수 없는 명령어: {args.command}", file=sys.stderr)
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n중단되었습니다.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"예상치 못한 오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
