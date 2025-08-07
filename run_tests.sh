#!/usr/bin/env bash
set -e

# pytest 실행 (커버리지 포함)
pytest --cov=communicator --cov-report term-missing tests/
