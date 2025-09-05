#!/usr/bin/env bash
set -e


# 커버리지 캐시 삭제
rm -f .coverage

# pytest 실행 (커버리지 포함)
# pytest --cov=app --cov-report term-missing tests/

# pytest 실행 (유닛 테스트만)
pytest -m "unit" --cov=app --cov-report=term-missing

# pytest 실행 (통합 테스트만)
# pytest -m "integration" --cov=app --cov-report=term-missing
