#!/usr/bin/env python3
"""
PyPI 배포 스크립트

사용법:
    python scripts/deploy.py [--test] [--build-only] [--version VERSION]

옵션:
    --test        TestPyPI에 배포 (기본값: PyPI)
    --build-only  빌드만 수행하고 배포하지 않음
    --version     버전 번호 지정 (기본값: pyproject.toml에서 읽음)
"""

import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """명령어를 실행하고 결과를 반환합니다."""
    print(f"실행 중: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("출력:", result.stdout)
    if result.stderr:
        print("오류:", result.stderr)
    
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    return result


def check_prerequisites() -> None:
    """배포 전 필수 조건을 확인합니다."""
    print("🔍 필수 조건 확인 중...")
    
    # Python 버전 확인
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8 이상이 필요합니다.")
    
    # 필수 패키지 확인
    required_packages = ["build", "twine"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 누락된 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    print("✅ 모든 필수 조건이 충족되었습니다.")


def clean_build_artifacts() -> None:
    """이전 빌드 아티팩트를 정리합니다."""
    print("🧹 빌드 아티팩트 정리 중...")
    
    build_dirs = ["build", "dist", "*.egg-info"]
    for pattern in build_dirs:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"삭제됨: {path}")
            elif path.is_file():
                path.unlink()
                print(f"삭제됨: {path}")


def build_package() -> None:
    """패키지를 빌드합니다."""
    print("🔨 패키지 빌드 중...")
    
    try:
        run_command([sys.executable, "-m", "build"])
        print("✅ 패키지 빌드가 완료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        sys.exit(1)


def check_distribution() -> None:
    """배포 전 배포 파일을 검사합니다."""
    print("🔍 배포 파일 검사 중...")
    
    try:
        run_command([sys.executable, "-m", "twine", "check", "dist/*"])
        print("✅ 배포 파일 검사가 완료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"❌ 배포 파일 검사 실패: {e}")
        sys.exit(1)


def upload_to_pypi(test: bool = False) -> None:
    """PyPI에 업로드합니다."""
    if test:
        print("🚀 TestPyPI에 업로드 중...")
        index_url = "https://test.pypi.org/legacy/"
    else:
        print("🚀 PyPI에 업로드 중...")
        index_url = "https://upload.pypi.org/legacy/"
    
    try:
        run_command([
            sys.executable, "-m", "twine", "upload",
            "--repository-url", index_url,
            "dist/*"
        ])
        print("✅ 업로드가 완료되었습니다.")
        
        if test:
            print("📦 TestPyPI 설치 명령어:")
            print("pip install --index-url https://test.pypi.org/simple/ eq1-network")
        else:
            print("📦 PyPI 설치 명령어:")
            print("pip install eq1-network")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 업로드 실패: {e}")
        sys.exit(1)


def update_version(version: Optional[str]) -> None:
    """버전을 업데이트합니다."""
    if not version:
        return
    
    print(f"📝 버전을 {version}으로 업데이트 중...")
    
    # pyproject.toml에서 버전 업데이트
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        # 버전 라인을 찾아서 교체
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('version = '):
                lines[i] = f'version = "{version}"'
                break
        
        pyproject_path.write_text('\n'.join(lines))
        print(f"✅ pyproject.toml 버전이 {version}으로 업데이트되었습니다.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PyPI 배포 스크립트")
    parser.add_argument("--test", action="store_true", help="TestPyPI에 배포")
    parser.add_argument("--build-only", action="store_true", help="빌드만 수행")
    parser.add_argument("--version", help="버전 번호 지정")
    
    args = parser.parse_args()
    
    print("🚀 EQ-1 Network PyPI 배포 스크립트")
    print("=" * 50)
    
    try:
        # 1. 필수 조건 확인
        check_prerequisites()
        
        # 2. 버전 업데이트 (지정된 경우)
        update_version(args.version)
        
        # 3. 빌드 아티팩트 정리
        clean_build_artifacts()
        
        # 4. 패키지 빌드
        build_package()
        
        # 5. 배포 파일 검사
        check_distribution()
        
        # 6. 업로드 (build-only가 아닌 경우)
        if not args.build_only:
            upload_to_pypi(args.test)
        
        print("🎉 배포 프로세스가 완료되었습니다!")
        
    except KeyboardInterrupt:
        print("\n❌ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
