import re
import unicodedata
from .decorators import was_decorated_without_parenthesis


def slugify(string):
    string = re.sub(r'[^\w\s-]', '',
                    unicodedata.normalize('NFKD', string.strip()))
    return re.sub(r'[-\s]+', '-', string).lower()


def title_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def pluralize(name):
    if name.endswith('y'):
        # right replace 'y' with 'ies'
        return 'ies'.join(name.rsplit('y', 1))
    elif name.endswith('s'):
        return f'{name}es'
    return f'{name}s'


def camel_to_snake_case(name):
    return title_case(name)
