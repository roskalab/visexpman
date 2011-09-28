import sys
import visexpman
import threading
import time
import unittest
import visexpman.engine.generic.utils as utils
import visexpman.engine.visual_stimulation.configuration
import visexpman.engine.visual_stimulation.experiment
import visexpman.engine.visual_stimulation.user_interface as user_interface
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.visual_stimulation.command_handler as command_handler
import Queue
import socket
import logging
import os
import random
import zipfile

test_mode = True #In test_mode the network operations are disabled

class VisExpRunner(object):
    '''
    This class is responsible for running vision experiment.
    '''
    def __init__(self, user, config_class):        
        self.state = 'init'
        #== Find and instantiate machine configuration ==
        try:
            self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.visual_stimulation.configuration.VisualStimulationConfig)[0][1]()
        except IndexError:
            raise RuntimeError('Configuration class does not exist.')
        #Save user name
        if user == '':
            self.config.user = 'undefined'
        else:
            self.config.user = user
        #== Fetch experiment classes ==        
        if self.config.user != 'undefined':
            self.experiment_config_list = utils.fetch_classes('visexpman.users.' + self.config.user,  required_ancestors = visexpman.engine.visual_stimulation.experiment.ExperimentConfig)
        else:
            #In case of SafestartConfig, no experiment configs are loaded
            #TODO: Create some default experiments (mostly visual stimulation) linked to SafestartConfig
            self.experiment_config_list = []
        #Since 0-9 buttons can be used for experiment config (experiment) selection, maximum 10 experiment configs are allowed.
        if len(self.experiment_config_list) > 10: 
            raise RuntimeError('Maximum 10 different experiment types are allowed')        
        #Loading configurations is ready.
        #== Starting up application ==
        self._init_logging()
        self.log.info('Visexpman started')
        #Reference to experiment control class which is instantiated when the start of the experiment is evoked
        self.experiment_control = None
        #Create screen and keyboard handler
        self.screen_and_keyboard = user_interface.ScreenAndKeyboardHandler(self.config, self)
        #Select and instantiate stimulus as specified in machine config, This is necessary to ensure that pre-experiment will run immediately after startup        
        if len(self.experiment_config_list) > 0:
            self.selected_experiment_config = [ex1[1] for ex1 in self.experiment_config_list if ex1[1].__name__ == self.config.EXPERIMENT_CONFIG][0](self.config, self)            
        #start listening on tcp ip for receiving commands
        self.command_queue = Queue.Queue()        
        if not test_mode:            
            self.tcpip_listener = network_interface.NetworkListener(self.config, self, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT)
            self.tcpip_listener.start()            
        #Start udp listener
        if self.config.ENABLE_UDP and not test_mode:            
            self.udp_listener = network_interface.NetworkListener(self.config, self, socket.SOCK_DGRAM, self.config.UDP_PORT)
            self.udp_listener.start()            
        #Set up command handler
        self.command_handler =  command_handler.CommandHandler(self.config, self)
        self.loop_state = 'running'
        #create list of imported python modules
        module_info = utils.imported_modules()        
        self.visexpman_module_paths  = module_info[1]
        self.visexpman_module_paths.append(os.path.join(self.config.PACKAGE_PATH, 'engine', 'visexp_runner.py'))        
        self.module_versions = utils.module_versions(module_info[0])
        #When initialization is done, visexpman state is 'ready'
        self.state = 'ready'
        self.log.info('Visexpman initialized')        

    def run_loop(self):        
        while self.loop_state == 'running':
            self.screen_and_keyboard.clear_screen_to_background()            
            if hasattr(self.selected_experiment_config, 'pre_runnable') and self.selected_experiment_config.pre_runnable is not None:
                self.selected_experiment_config.pre_runnable.run()
            self.screen_and_keyboard.user_interface_handler()
            self.command_handler.process_command_buffer()
            #To avoid race condition
            time.sleep(0.1)
        self.close()
            
    def close(self):
        if not test_mode:
#            self.tcpip_listener.socket.shutdown(socket.SHUT_RDWR)
            self.tcpip_listener.close()
        self.log.info('Visexpman quit')
            
    def _init_logging(self):
        #TODO: make folder to store all the files created by this run
        #set up logging
        self.logfile_path = utils.generate_filename(self.config.LOG_PATH + os.sep + 'log_' +  utils.date_string() + '.txt')
        self.log = logging.getLogger('visexpman log')
        handler = logging.FileHandler(self.logfile_path)
        formatter = logging.Formatter('%(asctime)s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

def find_out_config():
    '''
    Finds out configuration from the calling arguments. The following options are supported:
    - No argument: SafestartConfig is loaded
    - Username and config class name is encoded into one argument in the following form:
        user<separator>configclass, where separator can be: . , / \ <space> 
    - username and config class are provided as separate arguments
    '''        
    separators = [' ',  '.',  ',',  '/',  '\\']
    config_class = ''
    user = ''
    if len(sys.argv) == 0:
        raise RuntimeError('No command line arguments')
    elif len(sys.argv) == 1:
        config_class = 'SafestartConfig'
        user = 'default'
    elif len(sys.argv) == 2:
        for separator in separators:
            if sys.argv[1].find(separator) != -1:
                parameters = sys.argv[1].split(separator)
                user = sys.argv[1].split(separator)[0]
                config_class = sys.argv[1].split(separator)[1]
                break
    elif len(sys.argv) == 3:
        config_class = sys.argv[2]
        user = sys.argv[1]
    else:
        raise RuntimeError('Unsupported command line arguments')
    if config_class =='' and user == '':
        raise RuntimeError('Invalid command line argument')
    return user, config_class

class testFindoutConfig(unittest.TestCase):
    #== Test cases of find_out_config() function ==
    def test_01_find_out_config_no_arguments(self):
        sys.argv = ['module.py']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('SafestartConfig', 'default'))

    def test_02_find_out_config_only_username(self):
        sys.argv = ['module.py', 'testuser']
        self.assertRaises(RuntimeError,  find_out_config)
        
    def test_03_find_out_config_arguments_with_separator(self):
        sys.argv = ['module.py', 'test_user.config']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))
        
    def test_04_find_out_config_arguments_with_separator(self):
        sys.argv = ['module.py', 'test_user/config']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))
        
    def test_05_find_out_config_arguments_with_invalid_separator(self):
        sys.argv = ['module.py', 'test_user@config']        
        self.assertRaises(RuntimeError,  find_out_config)

    def test_06_find_out_config_two_arguments(self):
        sys.argv = ['module.py', 'test_user', 'config'] 
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))

    def test_07_find_out_config_three_arguments(self):
        sys.argv = ['module.py', 'test_user', 'config',  'dummy'] 
        self.assertRaises(RuntimeError,  find_out_config)

    def test_08_find_out_config_no_arguments(self):
        sys.argv = [] 
        self.assertRaises(RuntimeError,  find_out_config)
        
class testVisexpRunner(unittest.TestCase):
    def setUp(self):
        global test_mode
        test_mode = True
    
    #== Test cases for VisexpRunner's constructor ==    
    def test_01_VisexpRunner_SafestartConfig(self):        
        self.v1 = VisExpRunner('default', 'SafestartConfig')
        self.assertEqual((self.v1.config.__class__, self.v1.config.user),  (visexpman.users.default.default_configs.SafestartConfig, 'default'))
        self.v1.close()

    def test_02_VisexpRunner_invalid_user(self):
        self.assertRaises(ImportError,  VisExpRunner, 'dummy', 'VerySimpleExperimentTestConfig')

    def test_03_VisexpRunner_invalid_config(self):
        #Here IndexError is expected, because the fetch_classes function returns an empty list which is indexed
        self.assertRaises(RuntimeError,  VisExpRunner, 'zoltan', 'dummy')
        
    def test_04_VisexpRunner_invalid_config_invalid_user(self):        
        self.assertRaises(ImportError,  VisExpRunner, 'dummy', 'dummy')        
        
    def test_05_VisexpRunner_valid_user_config(self):
        self.v1 = VisExpRunner('zoltan', 'VerySimpleExperimentTestConfig')
        self.assertEqual((self.v1.config.__class__, self.v1.config.user, self.v1.selected_experiment_config.__class__),  (visexpman.users.zoltan.automated_test_data.VerySimpleExperimentTestConfig, 'zoltan', visexpman.users.zoltan.automated_test_data.VerySimpleExperimentConfig))
        self.v1.close()
        
    def test_06_VisexpRunner_quit_command(self):
        v = VisExpRunner('zoltan', 'VerySimpleExperimentTestConfig')
        cs = command_handler.CommandSender(v.config, v, [[0.1,'SOCquitEOC']])
        cs.start()
        v.run_loop()
        cs.close()
        log = utils.read_text_file(v.logfile_path)
        self.assertEqual(self.check_application_log(log), True)
        
    def test_07_issue_multiple_commands(self):
        commands = [
                    [0.01,'SOCselect_experimentEOC0EOP'], 
                    [0.01,'SOCbullseyeEOC0EOP'], 
                    [0.01,'SOCquitEOC'], 
                    ]
        v = VisExpRunner('zoltan', 'VerySimpleExperimentTestConfig')        
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
        log = utils.read_text_file(v.logfile_path)
        self.assertEqual((self.check_application_log(log), log.find('Command handler: selected experiment: 0') != -1, log.find('Command handler: bullseye') != -1), (True, True, True))
        
    def test_08_run_short_experiment(self):
        '''
        The followings are tested:
        -application log
        -experiment log
        -content of zip archive
        -experiment_control class
        '''
        commands = [
                    [0.01,'SOCexecute_experimentEOC0EOP'], 
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'VerySimpleExperimentTestConfig'
        
        v = VisExpRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
        #Read logs
        log = utils.read_text_file(v.logfile_path)
        experiment_log = utils.read_text_file(v.experiment_control.logfile_path)
        #Check for certain string patterns in log and experiment log files, check if archiving zip file is created and if it contains the necessary files
        self.assertEqual((self.check_application_log(log), self.check_experiment_log(experiment_log), experiment_log.find('show_fullscreen(0.0, [1.0, 1.0, 1.0])') != -1, \
                log.find('init experiment visexpman.users.') != -1, log.find('Started experiment: visexpman.users.') != -1, log.find('Experiment complete') != -1, \
                log.find('Command handler: experiment executed') != -1, zipfile.is_zipfile(v.experiment_control.data_handler.zip_file_path), self.check_zip_file(v.experiment_control.data_handler.zip_file_path, config_name.replace('TestConfig', ''))), (True, True, True, True, True, True, True, True, True))
                
    def test_09_abort_experiment(self):
        commands = [
                    [0.01,'SOCexecute_experimentEOC0EOP'],                     
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'AbortableExperimentTestConfig'
        v = VisExpRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
        #Read logs
        log = utils.read_text_file(v.logfile_path)
        experiment_log = utils.read_text_file(v.experiment_control.logfile_path)
        #Check for certain string patterns in log and experiment log files, check if archiving zip file is created and if it contains the necessary files
        self.assertEqual((self.check_application_log(log), self.check_experiment_log(experiment_log), experiment_log.find('show_fullscreen(-1.0, [1.0, 1.0, 1.0])') != -1, \
                log.find('init experiment visexpman.users.') != -1, log.find('Started experiment: visexpman.users.') != -1, log.find('Experiment complete') != -1, \
                log.find('Command handler: experiment executed') != -1, zipfile.is_zipfile(v.experiment_control.data_handler.zip_file_path), \
                experiment_log.find('Abort pressed') != -1, self.check_zip_file(v.experiment_control.data_handler.zip_file_path, config_name.replace('TestConfig', ''))), (True, True, True, True, True, True, True, True, True, True))

    def test_10_user_command_in_experiment(self):
        '''
        Tests whether a user defined keyboard command is sensed. Additionally adding user info to experiment log is tested
        '''
        commands = [
                    [0.01,'SOCexecute_experimentEOC0EOP'],                     
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'UserCommandExperimentTestConfig'
        v = VisExpRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
        #Read logs
        log = utils.read_text_file(v.logfile_path)
        experiment_log = utils.read_text_file(v.experiment_control.logfile_path)
        #Check for certain string patterns in log and experiment log files, check if archiving zip file is created and if it contains the necessary files
        self.assertEqual((self.check_application_log(log), self.check_experiment_log(experiment_log), experiment_log.find('show_fullscreen(-1.0, [1.0, 1.0, 1.0])') != -1, \
                log.find('init experiment visexpman.users.') != -1, log.find('Started experiment: visexpman.users.') != -1, log.find('Experiment complete') != -1, \
                log.find('Command handler: experiment executed') != -1, log.find('user_command') != -1, zipfile.is_zipfile(v.experiment_control.data_handler.zip_file_path), \
                experiment_log.find('User note') != -1, self.check_zip_file(v.experiment_control.data_handler.zip_file_path, config_name.replace('TestConfig', ''))), (True, True, True, True, True, True, True, True, True, True, True))

    #TODO: play two experiments, various experiments, experiments with disabled hardware, test user logging during experiment, pre experiment


#== Test utilities ==
    def check_application_log(self, log):
        if log.find('Visexpman started') != -1 and\
        log.find('Visexpman initialized') != -1 and\
        log.find('Visexpman quit') != -1 and\
        log.find('Command handler: quit'):
            return True
        else:
            return False
            
    def check_experiment_log(self, log):
        if log.find('Experiment started at ') != -1 and\
        log.find('Parallel port data bits set to 1') != -1 and\
        log.find('Parallel port data bits set to 0') != -1 and\
        log.find('Experiment finished at '):
            return True
        else:
            return False
            
    def check_zip_file(self, zip_path, experiment_name):
        '''
        Check if some of the necessary files are included into the zipfile
        '''        
        archive = zipfile.ZipFile(zip_path, "r")
        namelist = archive.namelist()
        archive.close()
        if utils.is_in_list(namelist, 'module_versions.txt') and utils.is_in_list(namelist, 'engine/visexp_runner.py')\
        and utils.is_in_list(namelist, 'engine/__init__.py') and utils.is_in_list(namelist, '__init__.py') and str(namelist).find('log_' + experiment_name + '_'+ utils.date_string()) != -1:
            return True
        else:
            return False

if __name__ == "__main__":
    if test_mode:
        unittest.main()
    else:        
        v = VisExpRunner(*find_out_config())
#        cs = command_handler.CommandSender(v.config, v, [1.0,'SOCquitEOC'])
#        cs.start()
        v.run_loop()
#        cs.close()
    
#        a = VisExpRunner(*find_out_config())
#        a.run_loop()
#        time.sleep(1.0)
#        a = VisExpRunner(*find_out_config())    
#        a.run_loop()
#        time.sleep(1.0)
        
    
    
