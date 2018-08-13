import visexpman.engine.generic.utils as utils

for module_name in list(utils.version_paths.keys()):
    try:
        __import__(module_name)
    except ImportError:
        print('{0} module is not installed' .format(module_name))
        
try:
    import parallel
    p = parallel.Parallel()
    p.setData(0)
except:
    print('parallel port driver is not loaded')
