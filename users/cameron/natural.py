from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

# class NaturalMovie(experiment.ExperimentConfig):
#     def _create_parameters(self):
# #        self.FILENAME = 'c:\\Data\\nn.3707-sv1_frames'
# #        self.FILENAME = 'c:\\Data\\nn.3707-sv2_frames'
#         self.FILENAME = 'c:\\Data\\spont_falco_moving_frames'
# #        self.FILENAME = 'c:\\Data\\stimulated_falco_sound_frames'
#         self.FRAME_RATE=60.0
#         self.STRETCH = 1.0
#         self.runnable = 'NaturalMovieExperiment'
#         self._create_parameters_from_locals(locals())
        
        
class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.READ_ELECTRODE_COORDINATE =  False
        self.JUMPING = False
        self.FILENAME = 'c:\\Data\\movies\\catmovie1'
        self.FRAME_RATE= 30.0
        self.STRETCH = 4.573
        self.runnable = 'NaturalMovieExperiment'
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0
        self.REPETITIONS = 2
        self._create_parameters_from_locals(locals())
#         
# class NaturalMovieSv2(experiment.ExperimentConfig):
#     def _create_parameters(self):
#         self.FILENAME = 'c:\\Data\\movies\\catmovie2'
#         self.FRAME_RATE= 30.0
#         self.STRETCH = 4.573
#         self.runnable = 'NaturalMovieExperiment'
#         self.BACKGROUND_TIME = 0.5
#         self.BACKGROUND_COLOR = 0.5
#         self.REPETITIONS = 3
#         self._create_parameters_from_locals(locals())
#        
# class NaturalMovieSv3(experiment.ExperimentConfig):
#     def _create_parameters(self):
#         self.FILENAME = 'c:\\Data\\movies\\catmovie3'
#         self.FRAME_RATE= 30.0
#         self.STRETCH = 4.573
#         self.runnable = 'NaturalMovieExperiment'
#         self.BACKGROUND_TIME = 0.5
#         self.BACKGROUND_COLOR = 0.5
#         self.REPETITIONS = 3
#         self._create_parameters_from_locals(locals())
#         
class NaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
#         self.SPEED = [800,400,1200.0]#um/s
#         self.REPEATS = 6 #5
#         self.DIRECTIONS = [0,180] #range(0,360,90)
#         self.DURATION = 12

        self.SPEED = [800,400,1200]#um/s
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0,180] #range(0,360,90)
        self.DURATION = 12
        
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.ENABLE_FLYINOUT= True #True # False
        self.ALWAYS_FLY_IN_OUT = True #True # False
        
        #Advanced/Tuning
        self.MINIMAL_SPATIAL_PERIOD= 120 #None
        self.SCALE= 1.0
        self.OFFSET=0.0
        self.runnable = 'NaturalBarsExperimentC'
        self._create_parameters_from_locals(locals())

class NaturalBarsTest(NaturalBarsConfig):
    def _create_parameters(self):
        NaturalBarsConfig._create_parameters(self)
        self.SPEED = [800]#um/s
        self.REPEATS = 1
        self.DIRECTIONS = [0]
        self.DURATION = 3

        
      
class NaturalBarsExperimentC(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)*len(self.experiment_config.SPEED)]
        self.duration=self.fragment_durations[0]
        print self.duration
        
    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            print rep
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR, flip=True)
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                for speeds in self.experiment_config.SPEED:
                    if self.abort:
                        break
                    if self.experiment_config.ALWAYS_FLY_IN_OUT:
                        fly_in = True
                        fly_out = True
                    else:
                        if self.experiment_config.SPEED.index(speeds) == 0:
                            fly_in = True
                            fly_out = False
                        elif self.experiment_config.SPEED.index(speeds) == len(self.experiment_config.SPEED)-1:
                            fly_in = False
                            fly_out = True
                        else:
                            fly_in = False
                            fly_out = False
                    if not self.experiment_config.ENABLE_FLYINOUT:
                        fly_in = False
                        fly_out = False
                    self.block_start('natural_bars')
                    self.show_natural_bars(speed = speeds, duration=self.experiment_config.DURATION, minimal_spatial_period = self.experiment_config.MINIMAL_SPATIAL_PERIOD, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, 
                            scale=self.experiment_config.SCALE,
                            offset=self.experiment_config.OFFSET,
                            intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out)
                    self.block_end('natural_end')
           
        
class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
        from visexpman.users.antonia.electrode_id_reader import read_single_electrode_coordinate,read_receptive_field_centers
        if self.experiment_config.READ_ELECTRODE_COORDINATE:
            coordinates = read_single_electrode_coordinate()
        else:
            if self.experiment_config.JUMPING:
                coordinates,contrasts = read_receptive_field_centers()
        
        self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
           duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
            
        if self.experiment_config.JUMPING:    
            for coordinate in coordinates:
                for repetitions in range(self.experiment_config.REPETITIONS):
                    self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                    self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH,position=utils.cr(tuple(coordinate)))
                    self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                    if self.abort:
                        break
                if self.abort or not self.experiment_config.JUMPING:#when not jumping, one iteration is enough
                    break
        else:
            for repetitions in range(self.experiment_config.REPETITIONS):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                if self.abort:
                   break

