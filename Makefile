.PHONY: help install test coverage lint format clean build

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  test       Run tests"
	@echo "  coverage   Run tests with coverage report"
	@echo "  lint       Run linting (flake8, mypy)"
	@echo "  format     Format code (black)"
	@echo "  clean      Clean build artifacts"
	@echo "  build      Build package"

install:
	pip install -r requirements.txt
	pip install -e .[dev]

test:
	pytest tests/

coverage:
	pytest --cov=communicator --cov-report=html --cov-report=term-missing tests/
	@echo "Coverage report generated in htmlcov/"

lint:
	flake8 communicator tests
	mypy communicator

format:
	black communicator tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python setup.py sdist bdist_wheel

check: lint test coverage
	@echo "All checks passed!"