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
import logging
import os
import shutil

class VisExpRunner():
    '''
    This class is responsible for running vision experiment.
    '''
    def __init__(self, user, config_class):
        self.state = 'init'
        #== Find and instantiate machine configuration ==
        if config_class == 'SafestartConfig':
            self.config = getattr(visexpman.engine.visual_stimulation.configuration, 'SafestartConfig')()
        else:
            self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.visual_stimulation.configuration.VisualStimulationConfig)[0][1]()
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
        self.tcpip_listener = network_interface.NetworkListener(self.config, self)
        self.tcpip_listener.start()
        #Set up command handler
        self.command_handler =  command_handler.CommandHandler(self.config, self)
        self.loop_state = 'running'
        #create list of imported python modules
        module_info = utils.imported_modules()
        self.visexpman_module_paths  = module_info[1]
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
        #All files in TMP_PATH are deleted
        shutil.rmtree(self.config.TMP_PATH)
        os.mkdir(self.config.TMP_PATH)
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
        user = ''
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

class testVisexpRunner(unittest.TestCase):
    #== Test cases of find_out_config() function ==
    def test_01_find_out_config_no_arguments(self):
        sys.argv = ['module.py']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('SafestartConfig', ''))

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
        
    #== Test cases for VisexpRunner's constructor ==    
    def test_09_VisexpRunner_SafestartConfig(self):
        v = VisExpRunner('', 'SafestartConfig')
        self.assertEqual((v.config.__class__, v.config.user),  (visexpman.engine.visual_stimulation.configuration.SafestartConfig, 'undefined'))
        
    def test_10_VisexpRunner_valid_user_config(self):
        v = VisExpRunner('zoltan', 'VisexpRunnerTestConfig')
        self.assertEqual((v.config.__class__, v.config.user, v.selected_experiment_config.__class__),  (visexpman.users.zoltan.test_data.VisexpRunnerTestConfig, 'zoltan', visexpman.users.zoltan.test_data.TestExperimentConfig))
        
    def test_11_VisexpRunner_invalid_user(self):
        self.assertRaises(ImportError,  VisExpRunner, 'dummy', 'VisexpRunnerTestConfig')
        
    def test_12_VisexpRunner_invalid_config(self):
        #Here IndexError is expected, because the fetch_classes function returns an empty list which is indexed
        self.assertRaises(IndexError,  VisExpRunner, 'zoltan', 'dummy')        
        
    def test_13_VisexpRunner_invalid_config_invalid_user(self):
        self.assertRaises(ImportError,  VisExpRunner, 'dummy', 'dummy')

if __name__ == "__main__":
#    unittest.main()
    VisExpRunner(*find_out_config()).run_loop()
    
