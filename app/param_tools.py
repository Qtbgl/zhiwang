def is_key(api_key):
    return api_key == 'ccc'


def check_key(obj: dict):
    assert 'api_key' in obj, 'API key missing'
    api_key = obj['api_key']
    assert is_key(api_key), 'Invalid API key!'
    return api_key


class Params:
    def __init__(self, obj: dict):
        self.obj = obj

    @property
    def pages(self):
        return get_int(self.obj, 'pages', a=1, default=1)

    @property
    def year(self):
        return get_int(self.obj, 'year_low', a=1900, b=2024)

    @property
    def sort_by(self):
        obj = self.obj
        val = obj.get('sort_by')
        if val is None:
            return None

        assert val in ('relevant', 'date', 'cite')
        return val


def get_int(obj, key, default=None, a=None, b=None):
    val = obj.get(key)
    if val is None:
        return default

    val = int(val)
    if a is not None:
        assert a <= val, 'Value must be bigger than or equal to {}'.format(a)
    if b is not None:
        assert b >= val, 'Value must be less than or equal to {}'.format(b)
    return val
