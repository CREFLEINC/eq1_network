import pytest
from pytest import approx

from communicator.common.params import Params


@pytest.fixture
def sample_config():
    """
    테스트를 위한 샘플 설정 데이터
    """
    return {
        "int_value": "10",
        "float_value": "3.14",
        "bool_true": "TRUE",
        "bool_false": "FALSE",
        "list_value": "1,2,3",
        "str_value": "hello",
        "mixed_list": "1,TRUE,3.5,FALSE,text",
        "int_direct": 20
    }


@pytest.mark.unit
def test_cast_data_type_int_str(sample_config):
    """문자열 정수 → int로 변환되는지 확인"""
    p = Params(sample_config)
    assert p.cast_data_type("42") == 42


@pytest.mark.unit
def test_cast_data_type_float_str(sample_config):
    """문자열 실수 → float로 변환되는지 확인"""
    p = Params(sample_config)
    assert p.cast_data_type("2.718") == approx(2.718)


@pytest.mark.unit
def test_cast_data_type_bool_true_false(sample_config):
    """문자열 'TRUE'/'FALSE' → bool로 변환되는지 확인"""
    p = Params(sample_config)
    assert p.cast_data_type("TRUE") is True
    assert p.cast_data_type("FALSE") is False


@pytest.mark.unit
def test_cast_data_type_list(sample_config):
    """쉼표 포함 문자열 → list로 변환되고 내부 값도 형변환되는지 확인"""
    p = Params(sample_config)
    result = p.cast_data_type("1,2,3")
    assert result == [1, 2, 3]


@pytest.mark.unit
def test_cast_data_type_mixed_list(sample_config):
    """혼합형 리스트 문자열 → 타입 자동 추론"""
    p = Params(sample_config)
    assert p.cast_data_type("1,TRUE,3.5,FALSE,text") == [1, True, 3.5, False, "text"]


@pytest.mark.unit
def test_cast_data_type_already_int(sample_config):
    """int 타입 그대로 반환되는지 확인"""
    p = Params(sample_config)
    assert p.cast_data_type(123) == 123


@pytest.mark.unit
def test_getitem_with_cast(sample_config):
    """getitem 방식으로 접근 시 자동 형변환 동작 여부 확인"""
    p = Params(sample_config)
    assert p["int_value"] == 10
    assert p["float_value"] == approx(3.14)
    assert p["bool_true"] is True
    assert p["bool_false"] is False
    assert p["list_value"] == [1, 2, 3]
    assert p["str_value"] == "hello"
    assert p["mixed_list"] == [1, True, 3.5, False, "text"]
    assert p["int_direct"] == 20


@pytest.mark.unit
def test_getattr_access(sample_config):
    """getattr 방식으로 접근 시 자동 형변환 동작 여부 확인"""
    p = Params(sample_config)
    assert p.int_value == 10
    assert p.float_value == approx(3.14)
    assert p.bool_true is True
    assert p.bool_false is False
    assert p.list_value == [1, 2, 3]
    assert p.str_value == "hello"
    assert p.mixed_list == [1, True, 3.5, False, "text"]


@pytest.mark.unit
def test_include_method(sample_config):
    """include 메서드가 키 존재 여부를 정확히 판단하는지 확인"""
    p = Params(sample_config)
    assert p.include("int_value") is True
    assert p.include("non_existent") is False


@pytest.mark.unit
def test_contains_magic_method(sample_config):
    """'in' 연산자 사용 가능 여부 확인 (__contains__)"""
    p = Params(sample_config)
    assert "float_value" in p
    assert "nonexistent" not in p


@pytest.mark.unit
def test_get_default_existing_key(sample_config):
    """기존 키에 대해 get_default가 올바르게 작동하는지 확인"""
    p = Params(sample_config)
    assert p.get_default("int_value", 999) == 10


@pytest.mark.unit
def test_get_default_missing_key(sample_config):
    """키가 없을 경우 default 값을 반환하는지 확인"""
    p = Params(sample_config)
    assert p.get_default("not_found", "default") == "default"


@pytest.mark.unit
def test_none_configure():
    """configure가 None일 때 include 메서드 동작 확인"""
    p = Params(None)
    assert p.include("any_key") is False
    assert p.include("UPPER_KEY") is False


@pytest.mark.unit
def test_getitem_missing_key(sample_config):
    """존재하지 않는 키로 getitem 접근 시 None 반환 확인"""
    p = Params(sample_config)
    assert p["missing_key"] is None


@pytest.mark.unit
def test_get_default_existing_key_false_condition(sample_config):
    """get_default에서 키가 존재하지 않을 때 조건 확인"""
    p = Params(sample_config)
    assert p.get_default("nonexistent_key", 42) == 42


@pytest.mark.unit
def test_getattr_missing_key(sample_config):
    """존재하지 않는 키로 getattr 접근 시 None 반환 확인"""
    p = Params(sample_config)
    assert p.missing_key is None


@pytest.mark.unit
def test_cast_data_type_edge_cases(sample_config):
    """cast_data_type의 엣지 케이스들 확인"""
    p = Params(sample_config)
    # 빈 문자열
    assert p.cast_data_type("") == ""
    # 공백만 있는 문자열
    assert p.cast_data_type(" ") == " "
    # 대소문자 혼합 bool
    assert p.cast_data_type("true") is True
    assert p.cast_data_type("false") is False