from visexpman.engine.generic import utils

for module_name in utils.version_paths.keys():
    try:
        __import__(module_name)
    except ImportError:
        print '{0} module is not installed' .format(module_name)
        
try:
    import parallel
    p = parallel.Parallel()
    p.setData(0)
except:
    print 'parallel port driver is not loaded'
#TODO:  run unittests
