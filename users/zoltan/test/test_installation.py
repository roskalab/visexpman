from visexpman.engine.generic import utils

if __name__=='__main__':
    not_installed_modules = []
    for module_name in utils.version_paths.keys():
        try:
            __import__(module_name)
        except ImportError:
            not_installed_modules.append(module_name)
    if len(not_installed_modules) > 0:
        print 'Not installed modules {0}' .format(not_installed_modules)
    #TODO:  run unittests
