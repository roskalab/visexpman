from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import copy
import time

class NaturalMovieOnly(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.MOVIE_REPEATS=1
        self.FILENAME = 'c:\\Data\\catcam17'
        self.FRAME_RATE=30.0 # Change frame rate back to 25 fps when possible (by adding images). 
        self.STRETCH = 2.75 # Covers 661 pixels vertical / 51 angular degrees. 
        self.runnable = 'NaturalMovieOnly'
        
        self._create_parameters_from_locals(locals())
        
        
    def _create_parameters_from_locals(self, locals,  check_path = True):
        if len(locals['self'].DUTY_CYCLES)==1 and len(locals['self'].ORIENTATIONS)>1:
            locals['self'].DUTY_CYCLES=locals['self'].DUTY_CYCLES*len(locals['self'].ORIENTATIONS)
        experiment.ExperimentConfig._create_parameters_from_locals(self, locals)

        
        
class NaturalMovieOnly(experiment.Experiment):
    def prepare(self):
        self.movie_fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
        self.fragment_durations = [self.movie_fragment_durations[0]]
        
    def my_movie(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        for rep in range(self.experiment_config.MOVIE_REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)    
        
    def run(self):
        # Effectively, this is run when the code is called (and is required), but you don't have to run the code until 
        self.my_movie()
        # You can also have control signals here. 