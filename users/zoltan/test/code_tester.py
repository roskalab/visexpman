import visexpman.engine.generic.utils as utils

def func(arg):
    print arg
    return True

t = utils.Timeout(1.0)
t.wait_timeout(func, 'ok')
