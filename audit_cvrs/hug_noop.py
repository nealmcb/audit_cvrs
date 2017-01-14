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
