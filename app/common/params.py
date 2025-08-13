class Params:
    """
    파라미터(설정값) 딕셔너리를 다양한 타입으로 안전하게 접근/변환할 수 있도록 지원하는 헬퍼 클래스입니다.

    - 대소문자 구분 없이 키 접근 가능
    - 문자열 값을 int, float, bool, list 등으로 자동 변환
    - 미존재 키나 None 입력에 대한 안전 처리
    - dict-like 및 attribute-style 접근 동시 지원
    """

    def __init__(self, configure):
        """
        파라미터 딕셔너리를 받아 내부에 저장합니다.

        Args:
            configure (dict): 파라미터(설정값) 딕셔너리
        """
        self._configure = configure

    def cast_data_type(self, v: str):
        """
        문자열 값을 int, float, bool, list 등으로 자동 변환합니다.
        변환 불가 시 원본 값을 반환합니다.

        Args:
            v (str): 변환 대상 값
        Returns:
            변환된 값 (int, float, bool, list, str)
        """
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except ValueError:
            pass

        try:
            return float(v)
        except ValueError:
            pass

        if v.upper() == "TRUE":
            return True

        if v.upper() == "FALSE":
            return False

        if "," in v:
            return [self.cast_data_type(_v) for _v in v.split(",")]

        return v

    def __getattr__(self, item):
        """
        attribute-style 접근 시 호출되며, 해당 키가 있으면 변환 후 반환합니다.
        미존재 시 None 반환.

        Args:
            item (str): 접근할 키
        Returns:
            변환된 값 또는 None
        """
        if not self.include(item):
            return None

        return self.cast_data_type(self._configure[item.lower()])

    def __getitem__(self, item):
        """
        dict-style 접근 시 호출되며, 해당 키가 있으면 변환 후 반환합니다.
        미존재 시 None 반환.

        Args:
            item (str): 접근할 키
        Returns:
            변환된 값 또는 None
        """
        if not self.include(item):
            return None

        return self.cast_data_type(self._configure[item.lower()])

    def __contains__(self, item):
        """
        in 연산자 사용 시, 해당 키의 존재 여부를 반환합니다.

        Args:
            item (str): 확인할 키
        Returns:
            bool: 존재 여부
        """
        return self.include(item)

    def include(self, key):
        """
        내부 딕셔너리에 해당 키가 존재하는지 확인합니다.

        Args:
            key (str): 확인할 키
        Returns:
            bool: 존재 여부
        """
        if self._configure is None:
            return False

        return key.lower() in self._configure

    def get_default(self, key, default):
        """
        키가 존재하면 값을 반환, 없으면 기본값(default)을 반환합니다.

        Args:
            key (str): 접근할 키
            default: 키가 없을 때 반환할 기본값
        Returns:
            변환된 값 또는 기본값
        """
        if self.include(key):
            return self[key]
        return default
