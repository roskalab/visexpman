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
from visexpman.users.test import unittest_aggregator
from visexpman.users.common import stimuli
from visexpA.engine.datadisplay import videofile

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 0.0
        self.GRATING_STAND_TIME = 0.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 90)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5] 
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 0.0
        self.runnable = 'MovingGrating1'
        self._create_parameters_from_locals(locals())

class MovingGrating1(stimuli.MovingGrating):
    def run(self, fragment_id=0):
        shutil.rmtree(self.machine_config.CAPTURE_PATH)
        os.mkdir(self.machine_config.CAPTURE_PATH)
        self.machine_config.ENABLE_FRAME_CAPTURE = True
        grating.MovingGrating.run(self, fragment_id)
        #save captured frames to avi
        videofile.image_files2mpg(self.machine_config.CAPTURE_PATH, os.path.join(self.machine_config.VIDEO_PATH, '{0}.mpg'.format(self.experiment_name)), 
                                                                                                                                  fps = self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.machine_config.ENABLE_FRAME_CAPTURE = False

class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0
        self.PIXEL_SIZE = 50.0
        self.FLICKERING_FREQUENCY = 30.0
        self.N_WHITE_PIXELS = None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class WhiteNoiseExperiment(experiment.Experiment):
    def run(self):
        self.white_noise(duration = self.experiment_config.DURATION,
            pixel_size = self.experiment_config.PIXEL_SIZE, 
            flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
            colors = self.experiment_config.COLORS,
            n_on_pixels = self.experiment_config.N_WHITE_PIXELS)
        self.show_fullscreen()

class GUITestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0#Comment
        self.PAR2 = 2.0#Comment2
        self.PAR1 = 1.0#Comment1
        self.editable=True
        self._create_parameters_from_locals(locals())
        
class TestCommonExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeExperiment'
        SHAPE_SIZE = 100
        SPEEDS = [1000.0]
        DIRECTIONS = [90]
        self._create_parameters_from_locals(locals())
                                 
        
class DebugExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0#Comment
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())

class Debug(experiment.Experiment):
    def prepare(self):
        self.experiment_duration = self.experiment_config.DURATION
    
    def run(self):
        self.show_shape(duration=0,size=10, color=1.0, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,pos = utils.rc((10, 0)), size=30, color=0.7, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,size=100, color=0.4, part_of_drawing_sequence=True, flip=True)
        time.sleep(self.experiment_duration)
        return
            
if __name__ == "__main__":
    if True:
        v = visexp_runner.VisionExperimentRunner('peter', 'StimulusDevelopment')
#        v.run_experiment(user_experiment_config = 'MovingGratingTuning')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
    elif not True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'FullfieldSinewave')
    elif not True:
        v = visexp_runner.VisionExperimentRunner('antonia',  'MEASetup')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
    elif True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        if True:
            v.run_loop()
        else:
            v.run_experiment(user_experiment_config = 'IncreasingAnnulusParameters')
    else:
        v = visexp_runner.VisionExperimentRunner('zoltan',  'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
