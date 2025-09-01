#!/bin/bash

# EQ-1 Network PyPI 배포 스크립트
# 사용법: ./scripts/deploy.sh [--test] [--build-only] [--version VERSION]

set -e  # 오류 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 도움말 출력
show_help() {
    cat << EOF
EQ-1 Network PyPI 배포 스크립트

사용법:
    $0 [옵션]

옵션:
    --test        TestPyPI에 배포 (기본값: PyPI)
    --build-only  빌드만 수행하고 배포하지 않음
    --version     버전 번호 지정
    --help        이 도움말 출력

예시:
    $0                    # PyPI에 배포
    $0 --test            # TestPyPI에 배포
    $0 --build-only      # 빌드만 수행
    $0 --version 1.0.2   # 버전 1.0.2로 배포
    $0 --test --version 1.0.2  # TestPyPI에 버전 1.0.2로 배포

EOF
}

# 변수 초기화
TEST_PYPI=false
BUILD_ONLY=false
VERSION=""

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_PYPI=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# 메인 배포 함수
main() {
    log_info "🚀 EQ-1 Network PyPI 배포 시작"
    echo "=================================================="
    
    # 1. Python 환경 확인
    log_info "Python 환경 확인 중..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되지 않았습니다."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python 버전: $PYTHON_VERSION"
    
    # 2. 필수 패키지 확인 및 설치
    log_info "필수 패키지 확인 중..."
    REQUIRED_PACKAGES=("build" "twine")
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! python3 -c "import ${package//-/_}" 2>/dev/null; then
            log_warning "$package 패키지가 설치되지 않았습니다. 설치 중..."
            pip install "$package"
        fi
    done
    log_success "모든 필수 패키지가 준비되었습니다."
    
    # 3. 이전 빌드 아티팩트 정리
    log_info "이전 빌드 아티팩트 정리 중..."
    rm -rf build/ dist/ *.egg-info/
    log_success "빌드 아티팩트가 정리되었습니다."
    
    # 4. 버전 업데이트 (지정된 경우)
    if [[ -n "$VERSION" ]]; then
        log_info "버전을 $VERSION으로 업데이트 중..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
        else
            # Linux
            sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
        fi
        log_success "버전이 $VERSION으로 업데이트되었습니다."
    fi
    
    # 5. 패키지 빌드
    log_info "패키지 빌드 중..."
    python3 -m build
    log_success "패키지 빌드가 완료되었습니다."
    
    # 6. 배포 파일 검사
    log_info "배포 파일 검사 중..."
    python3 -m twine check dist/*
    log_success "배포 파일 검사가 완료되었습니다."
    
    # 7. 업로드 (build-only가 아닌 경우)
    if [[ "$BUILD_ONLY" == false ]]; then
        if [[ "$TEST_PYPI" == true ]]; then
            log_info "TestPyPI에 업로드 중..."
            python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
            log_success "TestPyPI 업로드가 완료되었습니다."
            echo ""
            log_info "📦 TestPyPI 설치 명령어:"
            echo "pip install --index-url https://test.pypi.org/simple/ eq1-network"
        else
            log_info "PyPI에 업로드 중..."
            python3 -m twine upload dist/*
            log_success "PyPI 업로드가 완료되었습니다."
            echo ""
            log_info "📦 PyPI 설치 명령어:"
            echo "pip install eq1-network"
        fi
    else
        log_info "빌드만 수행되었습니다. 업로드는 건너뜁니다."
    fi
    
    echo ""
    log_success "🎉 배포 프로세스가 완료되었습니다!"
}

# 스크립트 실행
main "$@"
