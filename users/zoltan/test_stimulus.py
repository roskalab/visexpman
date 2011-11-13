from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

class WDC(VisionExperimentConfig):
    '''
    Visexp runner windows test config
    '''
    def _set_user_parameters(self):        

        #paths
        EXPERIMENT_CONFIG = 'DebugExperimentConfig'
        LOG_PATH = unit_test_runner.TEST_working_folder      
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder        
        ARCHIVE_FORMAT = 'zip'
        
        #hardware
        ENABLE_PARALLEL_PORT = True        
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0             
        COORDINATE_SYSTEM='center'        
        
        self._create_parameters_from_locals(locals())
        
class DebugExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())          
        
class Debug(experiment.Experiment):
    def run(self):
#         self.show_shape('o', size = 100, duration = 0.3)
        self.show_grating(duration = 10.0, profile = 'sqr', orientation = 0, velocity = 500.0, white_bar_width = 100)
