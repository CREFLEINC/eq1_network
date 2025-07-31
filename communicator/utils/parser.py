from typing import Dict, Any, List, get_origin, get_args


def _convert_type(value: str, target_type: Any) -> Any:
    """
    주어진 문자열 값을 명시된 타입으로 변환합니다.

    Args:
        value (str): 변환할 원본 문자열 값입니다.
        target_type (Any): 변환 대상 타입. 
            - 기본 타입: int, float, bool, str
            - 제네릭 타입: List[int], List[str] 등

    Returns:
        Any: 변환된 값. 요청한 타입과 동일한 Python 객체.

    Raises:
        ValueError: 빈 문자열이 비허용 타입으로 들어오거나, 변환 실패 시 발생합니다.
        TypeError: 지원하지 않는 타입이 지정되었거나, 리스트 타입에 요소 타입이 명시되지 않은 경우 발생합니다.

    Examples:
        _convert_type("123", int) -> 123  
        _convert_type("true", bool) -> True  
        _convert_type("1,2,3", List[int]) -> [1, 2, 3]
    """
    if not value and target_type is not str:
        raise ValueError(f"빈 값은 {target_type} 타입으로 변환할 수 없습니다.")

    origin_type = get_origin(target_type)

    try:
        # List[X] 처리
        if origin_type in (list, List):
            if not get_args(target_type):
                raise TypeError(f"리스트 타입의 요소 타입이 지정되지 않았습니다: {target_type}")
            list_item_type = get_args(target_type)[0]
            items = [item.strip() for item in value.split(',') if item.strip()]
            return [_convert_type(item, list_item_type) for item in items]

        # Boolean 변환
        elif target_type is bool:
            return value.strip().upper() in ("TRUE", "1", "YES", "ON")

        # 기본 타입 변환
        elif target_type in (int, float, str):
            return target_type(value)

        # 지원하지 않는 타입
        else:
            raise TypeError(f"지원하지 않는 타입입니다: {target_type}")

    except (ValueError, TypeError) as e:
        raise ValueError(f"'{value}'를 {target_type} 타입으로 변환 중 오류 발생: {e}")


def parse_and_validate(data: Dict[str, str], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    입력된 설정 데이터를 스키마 기반으로 검증하고, 각 항목을 지정된 타입으로 변환합니다.

    Args:
        data (Dict[str, str]): 원본 설정 데이터. 일반적으로 문자열로 구성된 딕셔너리.
        schema (Dict[str, Any]): 각 키에 대해 기대하는 타입을 명시한 딕셔너리.
            예: {"port": int, "enabled": bool, "tags": List[str]}

    Returns:
        Dict[str, Any]: 변환이 완료된 설정 데이터. 스키마에 명시된 타입으로 변환되어 반환됩니다.

    Raises:
        ValueError: 필수 키가 누락되었거나, 값이 비어있을 경우 발생합니다.
        TypeError: 값의 타입이 잘못되었거나 변환 중 오류가 발생한 경우 발생합니다.

    Examples:
        >>> parse_and_validate(
                {"port": "8080", "enabled": "true"},
                {"port": int, "enabled": bool}
            )
        {'port': 8080, 'enabled': True}
    """
    validated_data = {}

    for key, target_type in schema.items():
        if key not in data:
            raise ValueError(f"필수 설정값 '{key}'이(가) 없습니다.")

        raw_value = data[key]
        try:
            validated_data[key] = _convert_type(raw_value, target_type)
        except Exception as e:
            raise TypeError(f"'{key}' 값을 {target_type} 타입으로 변환할 수 없습니다. "
                            f"(값: '{raw_value}', 오류: {e})")

    return validated_data
