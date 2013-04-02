import time
import numpy
import serial
import os.path
import os

import visexpman
from visexpman.engine import visexp_runner
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.zoltan.test import unit_test_runner

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
        self.flash_shape(shape == 'ff', [1.0, 1.0, 1.0], 1.0)
        return
        self.show_shape(shape='r', color = numpy.array([[1.0, 0.5]]).T, duration = 2.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, size = utils.cr((100.0, 100.0)),pos = utils.cr(numpy.array([[0,100], [0, 100]])))
        self.show_grating(duration = 2.0,  
            white_bar_width = 100,  
            orientation = 90,  
            velocity = numpy.array([400,0]), 
            duty_cycle = 8.0)
        return
        self.show_grating(duration = 5.0,  
            white_bar_width = 100,  
            display_area = utils.rc((100,200)),
            orientation = 45,  
            pos = utils.rc((100,100)),
            velocity = 100,  
            duty_cycle = 1.0)
        self.show_grating(duration = 5.0,  
            white_bar_width = 100,  
            orientation = 90,  
            velocity = 100,  
            duty_cycle = 1.0)
            
if __name__ == "__main__":
    v = visexp_runner.VisionExperimentRunner('zoltan',  'SwDebugConfig')
    v.run_experiment(user_experiment_config = 'DebugExperimentConfig')
