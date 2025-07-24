class Params:
    def __init__(self, configure):
        self._configure = configure

    def cast_data_type(self, v: str):
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except ValueError as e:
            pass

        try:
            return float(v)
        except ValueError as e:
            pass

        if v.upper() == "TRUE":
            return True

        if v.upper() == "FALSE":
            return False

        if ',' in v:
            return [self.cast_data_type(_v) for _v in v.split(",")]

        return v

    def __getattr__(self, item):
        if not self.include(item):
            return None

        return self.cast_data_type(self._configure[item.lower()])

    def __getitem__(self, item):
        if not self.include(item):
            return None

        return self.cast_data_type(self._configure[item.lower()])

    def __contains__(self, item):
        return self.include(item)

    def include(self, key):
        if self._configure is None:
            return False

        return key.lower() in self._configure

    def get_default(self, key, default):
        if self.include(key):
            return self[key]
        return default