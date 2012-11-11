#TODO: ENABLE_UDP shall be replaced with udp config dictionary (similar to mes interface)
import os.path
import sys
import threading
import time
import unittest
import os.path
import Queue
import socket
import logging
import os
import traceback
import random
import zipfile
import numpy
import re

#Visexpman modules
import visexpman
try:
    import experiment
except:
    pass
from visexpman.engine.vision_experiment import command_handler
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import file
from visexpman.engine.generic import utils
from visexpman.engine.generic import log
from visexpman.engine.hardware_interface import network_interface
#Unit test
import unittest
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
class VisionExperimentRunner(command_handler.CommandHandler):
    '''
    This class is responsible for running vision experiment.
    '''
    def __init__(self, user, config_class, autostart = False):
        ########## Set up configurations ################
        try:
            self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        except IndexError:
            raise RuntimeError('Configuration class does not exist: ' + str(config_class))
        #Save user name
        if user == '':
            self.config.user = 'undefined'
        else:
            self.config.user = user
        #== Fetch experiment classes ==
        if self.config.user != 'undefined':
            self.experiment_config_list = utils.fetch_classes('visexpman.users.' + self.config.user,  required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig, direct = False)
        else:
            #In case of SafestartConfig, no experiment configs are loaded
            #TODO: Create some default experiments (mostly visual stimulation) linked to SafestartConfig
            self.experiment_config_list = []
        #Since 0-9 buttons can be used for experiment config (experiment) selection, maximum 10 experiment configs are allowed.
#        if len(self.experiment_config_list) > 10: 
#            raise RuntimeError('Maximum 10 different experiment types are allowed')
            
        self._init_logging()
        self.log.info('Visexpman started')
        #Start up queued clients
        self._init_network()
        #Set up command handler
        command_handler.CommandHandler.__init__(self)
        if autostart:
            self.keyboard_command_queue.put('SOCexecute_experimentEOCEOP')
            self.keyboard_command_queue.put('SOCquitEOCEOP')
        #Select and instantiate stimulus as specified in machine config, This is necessary to ensure that pre-experiment will run immediately after startup
        if len(self.experiment_config_list) > 0:
            try:
                self.experiment_config = [ex1[1] for ex1 in self.experiment_config_list if ex1[1].__name__ == self.config.EXPERIMENT_CONFIG][0](self.config, self.queues, self.connections, self.log)
            except IndexError:
                raise RuntimeError('Experiment config does not exists: {0}'.format(self.config.EXPERIMENT_CONFIG))
        else:
            self.experiment_config = None
        #Determine default experiment config index from machine config
        for i in range(len(self.experiment_config_list)):
            if self.experiment_config_list[i][1].__name__ == self.config.EXPERIMENT_CONFIG:
                self.selected_experiment_config_index = i
        #If udp enabled (= presentinator interface enabled), check for *presentinator*.py files in current user folder and delete them
        if self.config.ENABLE_UDP:
            user_folder = os.path.join(self.config.PACKAGE_PATH, 'users', self.config.user)
            for filename in file.filtered_file_list(user_folder,  'presentinator_experiment', fullpath = True):
                os.remove(filename)
        self.loop_state = 'running' #This state variable is necessary to end the main loop of the program from the command handler
        self.log.info('Visexpman initialized')

    def run_loop(self):
        last_log_time = time.time()
        try:
            while self.loop_state == 'running':
                self.clear_screen_to_background()
                self.refresh_non_experiment_screen(flip = False)
                if hasattr(self.experiment_config, 'pre_runnable') and self.experiment_config.pre_runnable is not None:
                    self.experiment_config.pre_runnable.run()
                self.user_interface_handler()
                result = self.parse()
                if len(str(result)) > 0:
                    self.message_to_screen.extend(result)
                #Log 'loop alive' in every 10 sec
                now = time.time()
                if now - last_log_time > 10.0:
                    last_log_time = now
                    self.log.info('main loop alive')
                #To avoid race condition
                time.sleep(0.1)
        except:
            traceback_info = traceback.format_exc()
            self.log.info(traceback_info)
            print traceback_info
        self.close()

    def close(self):
        self._stop_network()
        #Finish log
        self.log.info('Visexpman quit')
        self.log.flush()
        
    def run_experiment(self, user_experiment_config):
        utils.is_keyword_in_queue(self.queues['gui']['in'], 'abort', keep_in_queue = False)
        context = {}
        context['stage_origin'] = numpy.zeros(3)
        for experiment_config in self.experiment_config_list:
            if experiment_config[1].__name__ == user_experiment_config.__class__.__name__:
                self.experiment_config = experiment_config[1](self.config, self.queues, self.connections, self.log)
                #Copy experiment config values
                for attr in dir(user_experiment_config):
                    if attr == attr.upper():
                        setattr(self.experiment_config, attr, getattr(user_experiment_config, attr))
                        if hasattr(user_experiment_config, attr +'_p'):
                            setattr(self.experiment_config, attr+'_p', getattr(user_experiment_config, attr +'_p'))
                result = self.experiment_config.runnable.run_experiment(context)
                return result
        
    def __del__(self): #To avoid unit test warning
        pass
        
    def _stop_network(self):
        if unit_test_runner.TEST_enable_network:
            self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
            self.queues['gui']['out'].put('SOCclose_connectionEOCstop_clientEOP')
            time.sleep(3.0)
            self.log.queue(self.connections['mes'].log_queue, 'mes connection')
            self.log.queue(self.connections['gui'].log_queue, 'gui connection')
            self.log.info('Network connections terminated')
        
    def _init_network(self):
        self.connections = {}
        self.queues = {}
        self.queues['gui'] = {}
        self.queues['gui']['out'] = Queue.Queue()
        self.queues['gui']['in'] = Queue.Queue()
        self.queues['mes'] = {}
        self.queues['mes']['out'] = Queue.Queue()
        self.queues['mes']['in'] = Queue.Queue()
        self.queues['udp'] = {'in' : Queue.Queue() }
        self.connections['gui'] = network_interface.start_client(self.config, 'STIM', 'GUI_STIM', self.queues['gui']['in'], self.queues['gui']['out'])
        self.connections['mes'] = network_interface.start_client(self.config, 'STIM', 'STIM_MES', self.queues['mes']['in'], self.queues['mes']['out'])
        if self.config.ENABLE_UDP:
            server_address = ''
            self.udp_listener = network_interface.NetworkListener(server_address, self.queues['udp']['in'], socket.SOCK_DGRAM, self.config.UDP_PORT)
            self.udp_listener.start()
        self.log.info('Network clients started')

    def _init_logging(self):
        #set up logging
        self.logfile_path = file.generate_filename(self.config.LOG_PATH + os.sep + 'log_' + self.config.__class__.__name__ + '_'+  utils.date_string() + '.txt')
        self.log = log.Log('visexpman log ' +  str(time.time()), self.logfile_path, write_mode = 'user control')

def find_out_config():
    '''
    Finds out configuration from the calling arguments. The following options are supported:
    - No argument: SafestartConfig is loaded
    - Username and config class name is encoded into one argument in the following form:
        user<separator>configclass, where separator can be: . , / \ <space> 
    - username and config class are provided as separate arguments
    '''        
    #TODO: optparser shall be used
    separators = [' ',  '.',  ',',  '/',  '\\']
    config_class = ''
    user = ''
    autostart = False
    if len(sys.argv) == 0:
        raise RuntimeError('No command line arguments')
    elif len(sys.argv) == 1:
        config_class = 'SafestartConfig'
        user = 'default'
    elif len(sys.argv) == 2:
        for separator in separators:
            if separator in sys.argv[1]:
                parameters = sys.argv[1].split(separator)
                user = sys.argv[1].split(separator)[0]
                config_class = sys.argv[1].split(separator)[1]
                break
    elif len(sys.argv) == 3:
        config_class = sys.argv[2]
        user = sys.argv[1]
    elif len(sys.argv) == 4:
        config_class = sys.argv[2]
        user = sys.argv[1]
        if sys.argv[3] == 'autostart':
            autostart = True
    else:
        raise RuntimeError('Unsupported command line arguments')
    if config_class =='' and user == '':
        raise RuntimeError('Invalid command line argument')
    return user, config_class, autostart

class TestFindoutConfig(unittest.TestCase):
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
        
class TestVisionExperimentRunner(unittest.TestCase):

    def setUp(self):
        if '_09_' in self._testMethodName and unit_test_runner.TEST_mes:
            from visexpman.users.zoltan.automated_test_data import TestMesPlatformConfig
            self.server_config = TestMesPlatformConfig()
            self.server = network_interface.CommandRelayServer(self.server_config)

    def tearDown(self):
        if '_09_' in self._testMethodName and unit_test_runner.TEST_mes:
            raw_input('1. In MES software close connections\n\
                 2. Press ENTER')
            if hasattr(self, 'server'):
                self.server.shutdown_servers()
            if '_01_'in self._testMethodName:
                self.v1.close()
                
    #== Test cases for VisexpRunner's constructor ==    
    def test_01_VisexpRunner_SafestartConfig(self):        
        self.v1 = VisionExperimentRunner('default', 'SafestartConfig')
        self.assertEqual((self.v1.config.__class__, self.v1.config.user),  (visexpman.users.default.default_configs.SafestartConfig, 'default'))
        self.v1.close()

    def test_02_VisexpRunner_invalid_user(self):
        self.assertRaises(ImportError,  VisionExperimentRunner, 'dummy', 'StandaloneConfig')

    def test_03_VisexpRunner_invalid_config(self):
        #Here IndexError is expected, because the fetch_classes function returns an empty list which is indexed
        self.assertRaises(RuntimeError,  VisionExperimentRunner, 'zoltan', 'dummy')
        
    def test_04_VisexpRunner_invalid_config_invalid_user(self):
        self.assertRaises(ImportError,  VisionExperimentRunner, 'dummy', 'dummy')

    def test_05_standalone_experiment(self):
        '''
        Tests whether abort keyboard command and  a user defined keyboard command is sensed. Additionally adding user info to experiment log is tested
        Additional tests:
        - calls to hardware when disabled
        - pre experiment
        - bullseye command -> command handler
        - the expected machine and experiment configs are instantiated
        -test frame rate
        '''
        commands = [
                     [0.01,'SOCbullseyeEOCEOP'], 
                    [0.02,'SOCexecute_experimentEOC'],                     
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'StandaloneConfig'
        v = VisionExperimentRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
       #Read logs
        log = file.read_text_file(v.logfile_path)
        experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])
        frame_rate = v.experiment_config.runnable.frame_rate
        expected_frame_rate = v.experiment_config.runnable.machine_config.SCREEN_EXPECTED_FRAME_RATE
        if unit_test_runner.TEST_os == 'posix':
            frame_rate_tolerance = 30.0
        else:
            frame_rate_tolerance = 0.2
        #Check for certain string patterns in log and experiment log files, check if archiving zip file is created and if it contains the necessary files
        self.assertEqual(
                        (self.check_application_log(v), 
                        'Abort pressed' in log, 
                        '{\'keyword_arguments\': {}, \'method\': \'bullseye\', \'arguments\': ()}' in log, 
                        self.check_experiment_log(v), 
                        'show_fullscreen(-1.0, [1.0, 1.0, 1.0])' in experiment_log,
                        'Abort pressed' in experiment_log,
                        'User note' in experiment_log, 
                        'Pulse train configuration: [[[[0, 0.2, 0.5], [0.1, 0.1, 0.1], [2.0, 2.0, 2.0]], [[0, 0.2, 0.5], [0.1, 0.1, 0.1], [2.0, 2.0, 2.0]]], 1.0]' in experiment_log, 
                        'Start pulse train' in experiment_log, 
                        'Daq instrument released' in experiment_log, 
                        v.config.__class__, 
                        v.config.user,
                        v.experiment_config.__class__, 
                        frame_rate < expected_frame_rate + frame_rate_tolerance and frame_rate > expected_frame_rate - frame_rate_tolerance
                        ),
                        (True, True, True, True, True, True, True, True, True, True, 
                        visexpman.users.zoltan.automated_test_data.StandaloneConfig,
                       'zoltan',
                       visexpman.users.zoltan.automated_test_data.StandaloneExperimentConfig, 
                       True
                        ))
                        
    def test_06_visual_stimulations_centered(self):
        if not unit_test_runner.TEST_nostim:
            config_name = 'VisualStimulationsTestConfig'
            v = VisionExperimentRunner('zoltan', config_name)        
            commands = [
                        [0.0,'SOCexecute_experimentEOC'],                    
                        [0.0,'SOCquitEOC'],
                        ]
            cs = command_handler.CommandSender(v.config, v, commands)
            cs.start()
            v.run_loop()
            cs.close()
            #Read logs
            log = file.read_text_file(v.logfile_path)
            experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])        
            self.assertEqual(
                            (self.check_application_log(v), 
                            self.check_experiment_log(v),
                            v.config.__class__, 
                            v.config.user,
                            v.experiment_config.__class__, 
                            self.check_captured_frames(v.config.CAPTURE_PATH, os.path.join(unit_test_runner.TEST_reference_frames_folder, 'test_06')), 
                            self.check_experiment_log_for_visual_stimuli(experiment_log), 
                            ),
                            (True, True,
                            visexpman.users.zoltan.automated_test_data.VisualStimulationsTestConfig,
                           'zoltan',
                           visexpman.users.zoltan.automated_test_data.VisualStimulationsExperimentConfig, 
                           True, 
                           True, 
                            ))
                        
    def test_07_visual_stimulations_ul_corner(self):
        if not unit_test_runner.TEST_nostim:
            config_name = 'VisualStimulationsUlCornerTestConfig'
            v = VisionExperimentRunner('zoltan', config_name)        
            commands = [
                        [0.0,'SOCexecute_experimentEOC'],                    
                        [0.0,'SOCquitEOC'],
                        ]
            cs = command_handler.CommandSender(v.config, v, commands)
            cs.start()
            v.run_loop()
            cs.close()
            #Read logs
            log = file.read_text_file(v.logfile_path)
            experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])        
            self.assertEqual(
                            (self.check_application_log(v), 
                            self.check_experiment_log(v),
                            v.config.__class__, 
                            v.config.user,
                            v.experiment_config.__class__, 
                            self.check_captured_frames(v.config.CAPTURE_PATH, os.path.join(unit_test_runner.TEST_reference_frames_folder, 'test_07')), 
                            self.check_experiment_log_for_visual_stimuli(experiment_log), 
                            ),
                            (True, True,
                            visexpman.users.zoltan.automated_test_data.VisualStimulationsUlCornerTestConfig,
                           'zoltan',
                           visexpman.users.zoltan.automated_test_data.VisualStimulationsExperimentConfig, 
                           True, 
                           True, 
                            ))
                        
    def test_08_visual_stimulations_scaled(self):
        if not unit_test_runner.TEST_nostim:
            config_name = 'VisualStimulationsScaledTestConfig'
            v = VisionExperimentRunner('zoltan', config_name)        
            commands = [
                        [0.0,'SOCexecute_experimentEOC'],                    
                        [0.0,'SOCquitEOC'],
                        ]
            cs = command_handler.CommandSender(v.config, v, commands)
            cs.start()
            v.run_loop()
            cs.close()
            #Read logs
            log = file.read_text_file(v.logfile_path)
            experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])        
            self.assertEqual(
                            (self.check_application_log(v), 
                            self.check_experiment_log(v),
                            v.config.__class__, 
                            v.config.user,
                            v.experiment_config.__class__, 
                            self.check_captured_frames(v.config.CAPTURE_PATH, os.path.join(unit_test_runner.TEST_reference_frames_folder, 'test_08')), 
                            self.check_experiment_log_for_visual_stimuli(experiment_log), 
                            ),
                            (True, True,
                            visexpman.users.zoltan.automated_test_data.VisualStimulationsScaledTestConfig,
                           'zoltan',
                           visexpman.users.zoltan.automated_test_data.VisualStimulationsExperimentConfig, 
                           True, 
                           True, 
                            ))
                            
    @unittest.skipIf(not unit_test_runner.TEST_mes,  'MES tests disabled')
    def test_09_mes_platform(self):
        '''
        Tested features:
        -fragmented experiment
        -communication with mes
        -acquisition of analog input
        -led stimulation
        -stage move/read
        -parallel port (generates sync signal)
        
        unit test runner command line switches: pp, mes (real/emulated mes), daq, stage
        '''
        raw_input('1. In MES software, server address shall be set to this machine\'s ip\n\
                2. Connect MES to stim\n\
                3. Press ENTER')
        
        commands = [
                    [0.02,'SOCexecute_experimentEOC'],
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'TestMesPlatformConfig'
        v = VisionExperimentRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
       #Read logs
        log = file.read_text_file(v.logfile_path)
        experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])
        self.assertEqual(
                        (self.check_application_log(v), 
                        self.check_experiment_log(v), 
                        'show_fullscreen(' in experiment_log,
                        v.config.__class__, 
                        v.config.user,
                        v.experiment_config.__class__, 
                        ),
                        (True, True, True,
                        visexpman.users.zoltan.automated_test_data.TestMesPlatformConfig,
                       'zoltan',
                       visexpman.users.zoltan.automated_test_data.MesPlatformExperimentC, 
                        ))

    def test_10_elphys_platform(self):
        '''
        Tested features:
        -fragmented experiment
        -experiment dynamic loading
        -acquisition of analog input
        -filterwheel
        -parallel port (generates sync signal)
        
        unit test runner command line switches: pp, daq
        '''
        experiment_source = file.read_text_file(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'zoltan', 'test', 'elphys_test_experiment.py'))
        experiment_source = experiment_source.replace('\n', '<newline>')
        experiment_source = experiment_source.replace(',', '<comma>')
        experiment_source = experiment_source.replace('=', '<equal>')
        
        commands = [
                    [0.02,'SOCexecute_experimentEOCsource_code={0}EOP'.format(experiment_source)],
                    [0.01,'SOCquitEOC'], 
                    ]
        config_name = 'TestElphysPlatformConfig'
        v = VisionExperimentRunner('zoltan', config_name)
        cs = command_handler.CommandSender(v.config, v, commands)
        cs.start()
        v.run_loop()
        cs.close()
       #Read logs
        log = file.read_text_file(v.logfile_path)
        experiment_log = file.read_text_file(v.experiment_config.runnable.filenames['experiment_log'])
        self.assertEqual(
                        (self.check_application_log(v), 
                        self.check_experiment_log(v), 
                        'show_fullscreen(' in experiment_log,
                        v.config.__class__, 
                        v.config.user,
                        'ElphysPlatformExpConfig' in v.experiment_config.__class__.__name__, 
                        v.experiment_config.runnable.frame_counter, 
                        ),
                        (True, True, True,
                        visexpman.users.zoltan.automated_test_data.TestElphysPlatformConfig,
                       'zoltan',
                       True, 
                       int(v.experiment_config.runnable.fragment_durations[0] * v.config.SCREEN_EXPECTED_FRAME_RATE), 
                        ))
        
    
    ############## Helpers #################
    def check_application_log(self, vision_experiment_runner, experiment_run = True):
        log = file.read_text_file(vision_experiment_runner.logfile_path)
        if 'Visexpman started' in log and 'Visexpman initialized' in log and 'Visexpman quit' in log and \
        '{\'keyword_arguments\': {}, \'method\': \'quit\', \'arguments\': ()}' in log:
            result = True
        else:
            result = False
        if experiment_run:
            if not (vision_experiment_runner.experiment_config.runnable.experiment_name in log and 'started at' in log and 'Experiment finished at ' in log):
                result = False
        return result
            
    def check_experiment_log(self, vision_experiment_runner):
        log = file.read_text_file(vision_experiment_runner.experiment_config.runnable.filenames['experiment_log'])
        if vision_experiment_runner.experiment_config.runnable.experiment_name in log and 'started at' in log and 'Experiment finished at ' in log:
            result = True
        else:
            result = False
        for filename in vision_experiment_runner.experiment_config.runnable.filenames['fragments']:
            if not 'Measurement data saved to: ' + filename in log:
                result = False
        return result
        
    def check_captured_frames(self, capture_folder, reference_folder):
        result = True
        frame_files = file.listdir_fullpath(reference_folder)
        frame_files.sort()
        for reference_file_path in frame_files:
            reference_file = open(reference_file_path, 'rb')
            reference_data = reference_file.read(os.path.getsize(reference_file_path))
            reference_file.close()
            captured_frame_path = reference_file_path.replace(reference_folder, capture_folder)
            captured_file = open(captured_frame_path, 'rb')
            captured_data = captured_file.read(os.path.getsize(captured_frame_path))
            captured_file.close()
            number_of_differing_pixels = (utils.string_to_array(reference_data) != utils.string_to_array(captured_data)).sum()/3.0                        
            if reference_data != captured_data:                                                            
                if number_of_differing_pixels >= unit_test_runner.TEST_pixel_difference_threshold:
                    print reference_file_path, number_of_differing_pixels
                    result = False
        return result
        
    def check_experiment_log_for_visual_stimuli(self, experiment_log):        
        if '2.7.' in sys.version:
            reference_strings = [
                'show_fullscreen(0.0, [1.0, 1.0, 1.0])', 
                'show_fullscreen(0.0, [0.0, 0.0, 0.0])', 
                'show_grating(0.0, sqr, -1, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 200, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 45, 0.0, 50.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, (1.0, 0.3, 0.0), (0.5, 0.85, 0.0), (0, 0))', 
                'show_grating(0.0, sqr, 10, (100, 100), 90, 0.0, 0.0, [1.0, 1.0, 1.0], 0.5, (0, 0))', 
                'show_grating(0.0, sin, 20, (600, 600), 10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sin, 20, (600, 0), 10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sin, 20, (0, 600), -10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, tri, 20, (100, 100), 350, 0.0, 0.0, 0.5, 0.25, (0, 100))', 
                'show_grating(0.0, tri, 20, (100, 100), 350, 90.0, 0.0, 0.5, 0.25, (0, 100))', 
                'show_grating(0.0, saw, 50, (100, 200), 0, 0.0, 0.0, 1.0, 0.5, (250, 300))', 
                'show_grating(0.0333333333333, sqr, 40, (0, 0), 0, 0.0, 2400.0, 1.0, 0.5, (0, 0))',
                'show_dots(0.0, [100, 100], [(0, 0)',  
                'show_dots(0.0, [100, 100, 10], [(0, 0)', 
                'show_dots(0.0, [100, 100, 10], [(0, 0) ', 
                'show_dots(0.0333333333333, [200 200 200  20  20  20], [(0, 0) (0, 200) (200, 200) (0, 0) (0, 200) (100, 100)])', 
                'show_shape(, 0.0, (100, -50), [1.0, 1.0, 1.0], None, 0.0, 200.0, 1.0)', 
                'show_shape(circle, 0.0333333333333, (0, 0), 200, None, 0.0, (200.0, 100.0), 1.0)', 
                'show_shape(r, 0.0, (0, 0), [1.0, 1.0, 1.0], (1.0, 0.0, 0.0), 0.0, 100.0, 1.0)', 
                'show_shape(a, 0.0, (0, 0), [1.0, 1.0, 1.0], 120, 0.0, 100.0, 10.0)', 
                'show_shape(r, 0.0, (0, 0), [1.0, 0.0, 0.0], None, 10, (100.0, 200.0), 1.0)',
                'show_shape(a, 0.0, (0, 0), [1.0, 1.0, 1.0], None, 0.0, (100.0, 200.0), 10.0)'                
                             ]        
        elif '2.6.' in sys.version:
            reference_strings = [
                'show_fullscreen(0.0, [1.0, 1.0, 1.0])', 
                'show_fullscreen(0.0, [0.0, 0.0, 0.0])', 
                'show_grating(0.0, sqr, -1, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 200, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 0, 0.0, 0.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 45, 0.0, 50.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, 1.0, 0.5, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sqr, 100, (0, 0), 90, 0.0, 50.0, (1.0, 0.29999999999999999, 0.0), (0.5, 0.84999999999999998, 0.0), (0, 0))', 
                'show_grating(0.0, sqr, 10, (100, 100), 90, 0.0, 0.0, [1.0, 1.0, 1.0], 0.5, (0, 0))', 
                'show_grating(0.0, sin, 20, (600, 600), 10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sin, 20, (600, 0), 10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, sin, 20, (0, 600), -10, 0.0, 0.0, 0.5, 0.25, (0, 0))', 
                'show_grating(0.0, tri, 20, (100, 100), 350, 0.0, 0.0, 0.5, 0.25, (100, 0))', 
                'show_grating(0.0, tri, 20, (100, 100), 350, 90.0, 0.0, 0.5, 0.25, (100, 0))', 
                'show_grating(0.0, saw, 50, (100, 200), 0, 0.0, 0.0, 1.0, 0.5, (300, 250))', 
                'show_grating(0.0333333333333, sqr, 40, (0, 0), 0, 0.0, 2400.0, 1.0, 0.5, (0, 0))', 
                'show_dots(0.0, [100, 100], [array((0, 0),',  
                'show_dots(0.0, [100, 100, 10], [array((0, 0),', 
                'show_dots(0.0, [100, 100, 10], [array((0, 0), ', 
                'show_dots(0.0333333333333, [200 200 200  20  20  20], [(0, 0) (200, 0) (200, 200) (0, 0) (200, 0) (100, 100)])', 
                'show_shape(, 0.0, (-50, 100), [1.0, 1.0, 1.0], None, 0.0, 200.0, 1.0)', 
                'show_shape(circle, 0.0333333333333, (0, 0), 200, None, 0.0, (100.0, 200.0), 1.0)', 
                'show_shape(r, 0.0, (0, 0), [1.0, 1.0, 1.0], (1.0, 0.0, 0.0), 0.0, 100.0, 1.0)', 
                'show_shape(a, 0.0, (0, 0), [1.0, 1.0, 1.0], 120, 0.0, 100.0, 10.0)', 
                'show_shape(r, 0.0, (0, 0), [1.0, 0.0, 0.0], None, 10, (100.0, 200.0), 1.0)', 
                'show_shape(a, 0.0, (0, 0), [1.0, 1.0, 1.0], None, 0.0, (100.0, 200.0), 10.0)'
                             ]
        for reference_string in reference_strings:
            if reference_string not in experiment_log:
                print reference_string
                return False
        return True


if __name__ == "__main__":
    commands = []
    for i in range(0):
        if i == 0:
            commands.append([0.0, 'SOCexecute_experimentEOCEOP'])
        else:
            commands.append([40.0, 'SOCexecute_experimentEOCEOP'])
#    commands.append([0.0, 'SOCquitEOCEOP'])
    v = VisionExperimentRunner(*find_out_config())
    cs = command_handler.CommandSender(v.config, v, commands)
    cs.start()
    v.run_loop()
    cs.close()
    #TODO: test case for showshape(dur = 1.0), showfullscreen(dur = 1.0) sequence
    #TODO: test case for um_to_pixel_scale parameter
    #TODO full screeen grating test with ulcorner coord system
