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
from visexpman.users.common import stimulations
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
        
class MovingGrating1(stimulations.MovingGrating):
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

        
class DebugExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())          
        
class Debug(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION]
    
    def run(self):
        self.show_shape(duration=0,size=10, color=1.0, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,pos = utils.rc((10, 0)), size=30, color=0.7, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,size=100, color=0.4, part_of_drawing_sequence=True, flip=True)
        time.sleep(5.0)
        return
        from visexpman.engine.generic.introspect import Timer
        self.config.STIMULUS2MEMORY = True
        with Timer(''):
            for i in range(10):
                self.show_shape(duration=self.experiment_config.DURATION,size=10, color=i*0.1)
        self.config.STIMULUS2MEMORY = False
        return
        ncheckers = utils.rc((3, 3))
        colors = numpy.zeros((1, ncheckers['row'], ncheckers['col'], 3))
        colors[0,0,0,:]=numpy.array([1.0, 1.0, 0.0])
        colors[0,1,1,:]=numpy.array([0.0, 1.0, 0.0])
        colors[0,2,2,:]=numpy.array([1.0, 0.0, 0.0])
        self.show_checkerboard(ncheckers, duration = 0.5, color = colors, box_size = utils.rc((10, 10)))
        return
        self.increasing_spot([100,200], 1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, 1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)))
        t0 = self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        self.flash_stimulus('ff', [1/t0, 2/t0]*3, 1.0)
        self.flash_stimulus('ff', [1/t0, 2/t0], colors = numpy.array([[0.4, 0.6, 1.0]]).T)
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = utils.rc((100, 100)))
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = utils.rc(numpy.array([[100, 100], [200, 200]])))
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = numpy.array([[100, 200]]).T)
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
