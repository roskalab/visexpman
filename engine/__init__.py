import argparse
import warnings
import platform
import sys
import multiprocessing

from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import log
from visexpman.engine.generic import introspect
from visexpman.engine.hardware_interface import queued_socket

class FreeSpaceError(Exception):
    '''
    Not enough freespace on volume where path parameter in machine config points
    '''
        
class ExperimentConfigError(Exception):
    '''
    Experiment config related errors: redundant declaration 
    '''

class AnimalFileError(Exception):
    '''
    Problem with animal file or with the data stored in
    '''

class MachineConfigError(Exception):
    '''
    Machine config related error. A machine config parameter determined function causes error
    '''

class ApplicationError(Exception):
    '''
    TBD
    '''
    
class HardwareError(Exception):
    '''
    Raised when there is a problem with a hardware or a hardware setting might not be correct. E. g . screen frame rate is not correct
    '''

def application_init(**kwargs):
    '''
    All vision experiment manager application starts with calling this function.
    Parses command line parameters, instantiates corresponding machine config, checks if data storage places have enough free space.
    Logger process started.

    '''
    parnames = ['user', 'config', 'user_interface_name']
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
        argparser.add_argument('-a', '--user_interface_name', help = 'Application to be started: main_ui, stim, ca_imaging')
        argparser.add_argument('--testmode', help = 'Test mode')
        argparser.add_argument('--kill', help = 'Kill other python processes before software starts')
        argparser.add_argument('--nofullscreen', help = '')
        parsed_args = argparser.parse_args()
        for parname in parnames:
            if getattr(parsed_args,parname) is None:
                raise ApplicationError('{0} parameter not provided'.format(parname))
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
    machine_config.user_interface_name = args['user_interface_name']
    #Add testmode
    if 'parsed_args' in locals():
        tm=getattr(parsed_args,'testmode')
        if tm is not None:
            machine_config.testmode = int(tm)
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
    if not hasattr(machine_config,'REMOTE_LOG_PATH'):
        remote_logpath = ''
    else:
        remote_logpath = machine_config.REMOTE_LOG_PATH
    logger = log.Logger(filename=log.get_logfilename(machine_config), 
                                    remote_logpath = remote_logpath)
    log_sources = utils.get_key(kwargs, 'log_sources')
    if log_sources is not None:
        map(logger.add_source, log_sources)
    logger.add_source(machine_config.user_interface_name)
    #add application specific log sources
    if machine_config.user_interface_name=='ca_imaging' or machine_config.user_interface_name=='main_ui':
        logger.add_source('daq')
    #Set up network connections
    sockets = queued_socket.start_sockets(machine_config.user_interface_name, machine_config, logger, kwargs.get('enable_sockets', True))
    if machine_config.PLATFORM == 'rc_cortical' or machine_config.PLATFORM == 'ac_cortical' :
        raise NotImplementedError('Here comes the initialization of MES non zmq sockets')
    if utils.get_key(kwargs, 'log_start') :
        logger.start()
    context = {}
    context['machine_config'] = machine_config
    context['logger'] = logger
    context['sockets'] = sockets
    context['socket_queues'] = queued_socket.get_queues(sockets)
    context['user_interface_name'] = args['user_interface_name']
    context['command'] = multiprocessing.Queue()
    context['warning'] = []
    if machine_config.PLATFORM=='ao_cortical':
        from visexpman.engine.hardware_interface import network_interface
        command_relay_server = network_interface.CommandRelayServer(machine_config)
        mes_command=multiprocessing.Queue()
        mes_response=multiprocessing.Queue()
        context['mes_socket'] = network_interface.start_client(machine_config, 'STIM', 'STIM_MES', queue_in=mes_response, queue_out=mes_command)
        context['command_relay_server'] = command_relay_server
        context['mes_command']=mes_command
        context['mes_response']=mes_response
    return context
    
def stop_application(context):
    if context.has_key('command_relay_server'):
        context['mes_command'].put('stop_client')
        context['command_relay_server'].shutdown_servers()
    #Terminate sockets
    queued_socket.stop_sockets(context['sockets'])
    #Terminate logger process
    context['logger'].terminate()
    
import unittest
class TestApplicationInit(unittest.TestCase):
    def setUp(self):
       pass

    def tearDown(self):
        if hasattr(self, 'context'):
            stop_application(self.context)
        
    @unittest.skipIf(platform.system()=='Windows' and 'unittest_aggregator' in sys.argv[0],  'Does not work on windows system')
    def test_01_command_line_args(self):
        sys.argv.append('-u test')
        sys.argv.append('-c GUITestConfig')
        sys.argv.append('-a main_ui')
        self.context = application_init(log_start=True)
        
  # @unittest.skip('')
    def test_02_no_command_line_args(self):

        self.context = application_init(user='test', config='GUITestConfig', user_interface_name='main_ui',log_start=True)
        
#    @unittest.skip('')
    def test_03_invalid_config(self):
        self.assertRaises(RuntimeError,  application_init, user='test', config='GUITestConfig1', user_interface_name='main_ui',log_start = True)
        
#    @unittest.skip('')
    def test_04_freespace_warning(self):
        import warnings
        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            self.context = application_init(user='test', config='AppInitTest4Config', user_interface_name='main_ui',log_start=True)
            self.assertEqual('Running out of free space on' in str(w[-1].message), True)
        
#    @unittest.skip('')
    def test_05_freespace_error(self):
        self.assertRaises(FreeSpaceError, application_init, user='test', config='AppInitTest5Config', user_interface_name='main_ui',log_start=True)
    
if __name__=='__main__':
    unittest.main()
#    runner = unittest.TextTestRunner()
#    itersuite = unittest.TestLoader().loadTestsFromTestCase(TestApplicationInit)
#    runner.run(itersuite)
