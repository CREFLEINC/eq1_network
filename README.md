# EQ-1 Network
다양한 통신 프로토콜을 플러그인 기반으로 확장 가능하게 구성한 통신 프레임워크입니다.

## 지원 프로토콜(확장 예정)
- MQTT

## 주요 기능
- 플러그인 기반 통신 프로토콜 확장 구조
- Req-Res, Pub-Sub 기반 통신 지원
- 통신 재시도, 연결 상태 추적 등 robust한 기능 내장
- 단위 테스트 및 모킹 테스트 지원

## 폴더 구조
communicator/
├── common/         # 공통 모듈 (예외, 로깅 등)
├── interfaces/     # 추상 인터페이스 (Protocol 등)
├── protocols/      # 실제 프로토콜 구현체 (MQTT 등)
├── manager/        # 프로토콜 매니저
├── tests/          # 단위 테스트
├── __init__.py
└── ...
