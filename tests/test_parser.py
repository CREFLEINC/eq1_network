import pytest
from typing import List
from communicator.utils.parser import parse_and_validate, _convert_type



@pytest.mark.parametrize("value, target_type, expected", [
    ("123", int, 123),
    ("3.14", float, 3.14),
    ("hello", str, "hello"),
    ("true", bool, True),
    ("FALSE", bool, False),
    ("YES", bool, True),
    ("no", bool, False),
    ("1,2,3", List[int], [1, 2, 3]),
    ("on,off", List[str], ["on", "off"]),
])
def test_convert_type_success(value, target_type, expected):
    """
    ✅ 정상 변환 테스트: 문자열 입력값이 명시된 타입으로 올바르게 변환되는지 확인한다.
    """
    assert _convert_type(value, target_type) == expected


def test_convert_type_invalid_empty_value():
    """
    ❌ 빈 문자열이 int, float, bool 등과 같이 str 이외의 타입으로 변환될 때 ValueError가 발생하는지 테스트.
    """
    with pytest.raises(ValueError):
        _convert_type("", int)


def test_convert_type_with_unsupported_type_raises_valueerror():
    """
    ❌ 지원하지 않는 사용자 정의 타입으로 변환 시 ValueError가 발생하는지 테스트.
    """
    class Dummy: pass
    with pytest.raises(ValueError):
        _convert_type("value", Dummy)


def test_convert_type_list_type_without_item_type_raises_valueerror():
    """
    ❌ 리스트 타입인데 내부 요소 타입이 정의되지 않았을 경우 ValueError 발생 확인.
    예: List, list 등 명확한 요소 타입 없이 선언된 경우.
    """
    with pytest.raises(ValueError):
        _convert_type("1,2,3", list)  # 요소 타입 미지정


def test_convert_type_invalid_list_element():
    """
    ❌ 리스트 요소 타입이 명시된 경우, 각 요소가 해당 타입으로 변환되지 못하면 ValueError 발생 여부를 검증.
    예: List[int]인데 'a,b,c' 같은 문자열이 들어오는 경우.
    """
    with pytest.raises(ValueError):
        _convert_type("a,b,c", List[int])


# ✅ parse_and_validate 함수 테스트

def test_parse_and_validate_success():
    """
    ✅ 정상 입력 데이터가 스키마대로 변환되고 반환되는지 검증.
    문자열로 구성된 설정값이 각기 다른 타입으로 정확히 파싱되는지 확인.
    """
    raw = {
        "port": "8000",
        "enabled": "true",
        "tags": "sensor1,sensor2",
        "threshold": "3.5",
    }
    schema = {
        "port": int,
        "enabled": bool,
        "tags": List[str],
        "threshold": float,
    }

    result = parse_and_validate(raw, schema)
    assert result == {
        "port": 8000,
        "enabled": True,
        "tags": ["sensor1", "sensor2"],
        "threshold": 3.5,
    }


def test_parse_and_validate_missing_key():
    """
    ❌ 스키마에 정의된 필드가 입력 데이터에 없을 경우 ValueError 발생 여부를 검증.
    """
    raw = {
        "port": "8000"
    }
    schema = {
        "port": int,
        "enabled": bool
    }
    with pytest.raises(ValueError, match="필수 설정값 'enabled'이\\(가\\) 없습니다."):
        parse_and_validate(raw, schema)


def test_parse_and_validate_type_mismatch():
    """
    ❌ 입력값이 스키마에서 정의한 타입으로 변환 불가능한 경우 TypeError가 발생하는지 확인.
    """
    raw = {
        "port": "not_a_number"
    }
    schema = {
        "port": int
    }
    with pytest.raises(TypeError):
        parse_and_validate(raw, schema)
