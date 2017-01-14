# If hug module isn't available, provide alternatives
# See https://github.com/timothycrosley/hug/issues/435
# Thanks to http://www.saltycrane.com/blog/2010/03/simple-python-decorator-examples/

def decorator_generator(*args, **kwargs):
    def identity_decorator(f):
        return f
    return identity_decorator

get = decorator_generator
local = decorator_generator
cli = decorator_generator

class types:
    number = None
    float_number = None
    boolean = None

"""
def identity_decorator(f):
    return f

def get(*args, **kwargs):
    return identity_decorator

def local(*args, **kwargs):
    return identity_decorator

def cli(*args, **kwargs):
    return identity_decorator

class types:
    number = None
    float_number = None
"""

# Got very confused by http://stackoverflow.com/questions/19812570/how-to-mock-a-decorated-function

"""
def get(*args, **kwargs):
    def wrapped_f(func):
        func(*args, **kwargs)
    return wrapped_f

def local(func, *args, **kwargs):
    return func

"""

# Alternate decorators

"""
class API(object):
    def get(self, *args, **kwargs):
        return self

get = API.get
"""

