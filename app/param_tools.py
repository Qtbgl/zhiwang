def is_key(api_key):
    from data import api_config
    return api_key == api_config.app_key


def check_key(obj: dict):
    assert 'api_key' in obj, 'API key missing'
    api_key = obj['api_key']
    assert is_key(api_key), 'Invalid API key!'
    return api_key


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


class ParamError(Exception):
    pass


def param_check(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise ParamError(e)
    return wrapper
