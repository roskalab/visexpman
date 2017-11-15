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
        self.FILENAME = 'c:\\Data\\Movies\\catcam17'
        self.FRAME_RATE=30.0 # Frame rate should be 24 fps, but forced to set to 30 fps because it must be a multiple of 16.6 ms (i.e. 60 fps).
        self.STRETCH = 3 # Vertical pixel range of 720 pixels. 
        self.runnable = 'NaturalMovieOnlyE'
        
        self._create_parameters_from_locals(locals())
        
        
    
class NaturalMovieOnly1x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie1_1'
        self.STRETCH = 2.75 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly1x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie1_2'
        self.STRETCH = 2.75 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly1x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie1_3'
        self.STRETCH = 2.75 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly2x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie2_1'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly2x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie2_2'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly2x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie2_3'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly2x4(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie2_4'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly2x5(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie2_5'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_1'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 

class NaturalMovieOnly3x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_2'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_3'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x4(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_4'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x5(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_5'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x6(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_6'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x7(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_7'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x8(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_8'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnly3x9(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie3_9'
        self.STRETCH = 1.8 # Vertical pixel range of 720 pixels. 

class NaturalMovieOnlyDepixel1x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small1_1'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel1x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small1_2'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel1x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small1_3'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel2x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small2_1'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels.  
        
class NaturalMovieOnlyDepixel2x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small2_2'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel2x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small2_3'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel2x4(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small2_4'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel2x5(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small2_5'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x1(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_1'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 

class NaturalMovieOnlyDepixel3x2(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_2'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x3(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_3'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x4(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_4'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x5(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_5'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x6(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_6'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x7(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_7'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x8(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_8'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 
        
class NaturalMovieOnlyDepixel3x9(NaturalMovieOnly):
    def _create_parameters(self):
        NaturalMovieOnly._create_parameters(self)
        self.FILENAME = 'c:\\Data\\Movies\\movie_small3_9'
        self.STRETCH = 103 # Vertical pixel range of 720 pixels. 

        

        
class NaturalMovieOnlyE(experiment.Experiment):
    def prepare(self):
        self.movie_fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
        self.fragment_durations = [self.movie_fragment_durations[0]]
        self.durations = [self.fragment_durations[0]]
        self.duration=self.durations[0]
        
    def my_movie(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        for rep in range(self.experiment_config.MOVIE_REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            #self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)    
        
    def run(self):
        # Effectively, this is run when the code is called (and is required), but you don't have to run the code until 
        self.my_movie()
        # You can also have control signals here. 
