#!/usr/bin/env python3
"""
PyPI 배포 전 검증 스크립트

이 스크립트는 배포 전에 다음 사항들을 검증합니다:
1. 필수 파일 존재 여부
2. 패키지 구조 검증
3. 의존성 검증
4. 테스트 실행
5. 코드 품질 검사
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Tuple


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
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


def check_required_files() -> List[str]:
    """필수 파일들의 존재 여부를 확인합니다."""
    print("🔍 필수 파일 확인 중...")
    
    required_files = [
        "pyproject.toml",
        "docs/README.md",
        "LICENSE",
        "MANIFEST.in",
        "eq1_network/__init__.py",
        "eq1_network/py.typed"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ 누락된 파일들: {', '.join(missing_files)}")
    else:
        print("✅ 모든 필수 파일이 존재합니다.")
    
    return missing_files


def check_package_structure() -> List[str]:
    """패키지 구조를 검증합니다."""
    print("\n🔍 패키지 구조 검증 중...")
    
    issues = []
    
    # eq1_network 디렉토리 확인
    eq1_network_dir = Path("eq1_network")
    if not eq1_network_dir.exists():
        issues.append("eq1_network 디렉토리가 존재하지 않습니다.")
        return issues
    
    # __init__.py 파일들 확인
    for py_file in eq1_network_dir.rglob("*.py"):
        if py_file.name != "__init__.py":
            continue
        
        # __init__.py 파일이 있는 디렉토리에 __init__.py가 없는 경우
        parent_dir = py_file.parent
        if not (parent_dir / "__init__.py").exists():
            issues.append(f"{parent_dir}에 __init__.py 파일이 없습니다.")
    
    if issues:
        print(f"❌ 패키지 구조 문제: {', '.join(issues)}")
    else:
        print("✅ 패키지 구조가 올바릅니다.")
    
    return issues


def check_dependencies() -> List[str]:
    """의존성을 검증합니다."""
    print("\n🔍 의존성 검증 중...")
    
    issues = []
    
    # pyproject.toml에서 의존성 확인
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    
    dependencies = config.get("project", {}).get("dependencies", [])
    
    package_import_map = {
        "paho-mqtt": "paho",
        "paho-mqtt-client": "paho",
        "paho-mqtt-python": "paho"
    }
    
    for dep in dependencies:
        package_name = dep.split(">=")[0].split("==")[0].split("~=")[0]
        
        if package_name in package_import_map:
            import_name = package_import_map[package_name]
        else:
            import_name = package_name.replace("-", "_")
        
        try:
            importlib.import_module(import_name)
            print(f"✅ {package_name} (import: {import_name})")
        except ImportError:
            issues.append(f"{package_name} 패키지를 import할 수 없습니다. (시도한 import: {import_name})")
            print(f"❌ {package_name} (import: {import_name})")
    
    if issues:
        print(f"❌ 의존성 문제: {', '.join(issues)}")
    else:
        print("✅ 모든 의존성이 정상적으로 설치되어 있습니다.")
    
    return issues


def run_tests() -> bool:
    """테스트를 실행합니다."""
    print("\n🧪 테스트 실행 중...")
    
    try:
        # pytest 실행
        result = run_command([sys.executable, "-m", "pytest", "tests/", "-v"])
        print("✅ 모든 테스트가 통과했습니다.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 테스트 실패: {e}")
        return False


def check_code_quality() -> List[str]:
    """코드 품질을 검사합니다."""
    print("\n🔍 코드 품질 검사 중...")
    
    issues = []
    
    # flake8 실행
    try:
        run_command([sys.executable, "-m", "flake8", "eq1_network/", "tests/", "--max-line-length=100"])
        print("✅ flake8 검사 통과")
    except subprocess.CalledProcessError:
        issues.append("flake8 검사 실패")
        print("❌ flake8 검사 실패")
    
    # mypy 실행 (타입 힌트 검사)
    try:
        run_command([sys.executable, "-m", "mypy", "eq1_network/", "--ignore-missing-imports"])
        print("✅ mypy 검사 통과")
    except subprocess.CalledProcessError:
        issues.append("mypy 검사 실패")
        print("❌ mypy 검사 실패")
    
    return issues


def check_build() -> bool:
    """패키지 빌드를 테스트합니다."""
    print("\n🔨 빌드 테스트 중...")
    
    try:
        # 이전 빌드 아티팩트 정리
        import shutil
        for path in ["build", "dist", "*.egg-info"]:
            for p in Path(".").glob(path):
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
        
        # 빌드 실행
        run_command([sys.executable, "-m", "build"])
        print("✅ 빌드 테스트 통과")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 테스트 실패: {e}")
        return False


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyPI 배포 전 검증 스크립트")
    parser.add_argument("--skip-tests", action="store_true", help="테스트 실행 건너뛰기")
    parser.add_argument("--skip-quality", action="store_true", help="코드 품질 검사 건너뛰기")
    
    args = parser.parse_args()
    
    print("🔍 EQ-1 Network 배포 전 검증")
    print("=" * 50)
    
    all_issues = []
    
    try:
        # 1. 필수 파일 확인
        missing_files = check_required_files()
        all_issues.extend(missing_files)
        
        # 2. 패키지 구조 검증
        structure_issues = check_package_structure()
        all_issues.extend(structure_issues)
        
        # 3. 의존성 검증
        dependency_issues = check_dependencies()
        all_issues.extend(dependency_issues)
        
        # 4. 코드 품질 검사 (선택적)
        if not args.skip_quality:
            quality_issues = check_code_quality()
            all_issues.extend(quality_issues)
        else:
            print("\n⚠️  코드 품질 검사를 건너뜁니다.")
        
        # 5. 테스트 실행 (선택적)
        if not args.skip_tests:
            tests_passed = run_tests()
        else:
            print("\n⚠️  테스트 실행을 건너뜁니다.")
            tests_passed = True
        
        # 6. 빌드 테스트
        build_passed = check_build()
        
        # 결과 요약
        print("\n" + "=" * 50)
        print("📊 검증 결과 요약")
        print("=" * 50)
        
        if all_issues:
            print(f"❌ 발견된 문제들 ({len(all_issues)}개):")
            for i, issue in enumerate(all_issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("✅ 구조적 문제가 발견되지 않았습니다.")
        
        if not tests_passed:
            print("❌ 테스트가 실패했습니다.")
        
        if not build_passed:
            print("❌ 빌드가 실패했습니다.")
        
        if all_issues or not tests_passed or not build_passed:
            print("\n❌ 배포 전 검증이 실패했습니다. 위의 문제들을 해결한 후 다시 시도하세요.")
            sys.exit(1)
        else:
            print("\n✅ 모든 검증이 통과했습니다. 배포를 진행할 수 있습니다.")
    
    except KeyboardInterrupt:
        print("\n❌ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()