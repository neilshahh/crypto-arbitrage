import yaml
from functools import wraps
import logging

def load_config(path):

    with open(path, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    return cfg


def retry_if_exception(ex=Exception, max_retries=10):
    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            assert max_retries > 0
            x = max_retries
            while x:
                try:
                    if x < max_retries:
                        logging.debug('trying again due to {}...'.format(ex))
                    return func(*args, **kwargs)
                except ex:
                    x -= 1

        return wrapper

    return outer
