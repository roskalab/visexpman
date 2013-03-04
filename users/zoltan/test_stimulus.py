from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
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
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder        
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
        self.moving_shape(utils.rc((10.0,100.0)), 800, range(0,360,45), shape = 'rect', moving_range=utils.rc((0,0)), pause=1.0)
