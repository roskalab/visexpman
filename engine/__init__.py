import argparse
import warnings

from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import log
from visexpman.engine.generic import introspect

class FreeSpaceError(Exception):
    pass
    
class FreeSpaceWarning(Warning):
    pass
    
class ExperimentConfigError(Exception):
    pass

class AnimalFileError(Exception):
    pass

class MachineConfigError(Exception):
    pass
    
class LoggingError(Exception):
    pass

def application_init(**kwargs):
    '''
        

    '''
    parnames = ['user', 'config', 'application_name']
    args = {}
    if len(kwargs) < 3:#Find user, machine config and application name from command line parameters
        import sys
        if 'unittest_aggregator' not in sys.argv[0]:#Unit
            global argparser
            argparser = argparse.ArgumentParser()
        else:
            from visexpman.users.test import unittest_aggregator
            argparser= unittest_aggregator.argparser
        argparser.add_argument('-u', '--user', help = 'User of the application. A subfolder with this name shall exists visexpman.engine.users folder.')
        argparser.add_argument('-c', '--config', help = 'Machine config that reside in either user\'s folder or in visexpman.users.common')
        argparser.add_argument('-a', '--application_name', help = 'Application to be started: TBD')#TODO: possible application names shall be listed
        parsed_args = argparser.parse_args()
        for parname in parnames:
            args[parname] = getattr(parsed_args,parname).replace(' ', '')
    else:
        for parname in parnames:
            args[parname] = kwargs[parname]
    #Instantiate machine config
    import visexpman.engine.vision_experiment.configuration
    config_class = utils.fetch_classes('visexpman.users.common', classname = args['config'], required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)
    if len(config_class) == 0:#Try user's folder if not found in common folder 
        config_class = utils.fetch_classes('visexpman.users.' + args['user'], classname = args['config'], required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)
        if len(config_class) == 0:#Machine config class not found
            raise RuntimeError('{0} user\'s {1} machine configuration class cannot be found'.format(args['user'], args['config']))
    machine_config = config_class[0][1]()
    #Add app name and user to machine config
    machine_config.user = args['user']
    machine_config.application_name = args['application_name']
    #Check free space
    for parname in dir(machine_config):
        if '_PATH' == parname[-5:]:
            free_space = fileop.free_space(getattr(machine_config, parname))
            if  free_space<machine_config.FREE_SPACE_ERROR_THRESHOLD: 
                raise FreeSpaceError('No free space on {0}. Only {1} MB is available.'
                               .format(getattr(machine_config, parname), fileop.free_space(getattr(machine_config, parname))/2**20))
            elif free_space<machine_config.FREE_SPACE_WARNING_THRESHOLD: 
                warnings.warn('Running out of free space on {0} ({1}). Only {2} MB is available.'
                               .format(getattr(machine_config, parname), parname, fileop.free_space(getattr(machine_config, parname))/2**20))
    #Check network connection
    if not utils.is_network_available():
        warnings.warn('Check network connection')
    #Set up application logging
    logger = log.Logger(machine_config)
    logger.start()
    return machine_config, logger
    
import unittest
class TestApplicationInit(unittest.TestCase):
    def setUp(self):
       pass

    def tearDown(self):
        if hasattr(self, 'log'):
            self.log.terminate()
            del self.log
        
    def test_01_command_line_args(self):
        import sys
        sys.argv.append('-u test')
        sys.argv.append('-c GUITestConfig')
        sys.argv.append('-a elphys')
        mc, self.log = application_init()
        
#    @unittest.skip('')        
    def test_02_no_command_line_args(self):
        mc, self.log = application_init(user='test', config='GUITestConfig', application_name='elphys')
        
    def test_03_invalid_config(self):
        self.assertRaises(RuntimeError,  application_init, user='test', config='GUITestConfig1', application_name='elphys')
        
    def test_04_freespace_warning(self):
        import warnings
        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            mc, self.log = application_init(user='test', config='AppInitTest4Config', application_name='elphys')
            self.assertEqual('Running out of free space on' in str(w[-1].message), True)
        
    def test_05_freespace_error(self):
        self.assertRaises(FreeSpaceError, application_init, user='test', config='AppInitTest5Config', application_name='elphys')
    
if __name__=='__main__':
    unittest.main()
#    runner = unittest.TextTestRunner()
#    itersuite = unittest.TestLoader().loadTestsFromTestCase(TestApplicationInit)
#    runner.run(itersuite)
