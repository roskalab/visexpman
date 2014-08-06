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
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.REPETITIONS = 8
        self._create_parameters_from_locals(locals())
        
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
        self.SPEED = 300.0#um/s
        self.REPEATS = 3#5
        self.DIRECTIONS = range(0,360,90)
        self.DURATION = 15.0
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())
        

class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self.show_natural_bars(speed = self.experiment_config.SPEED, duration=self.experiment_config.DURATION, minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = directions)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        
class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
        from visexpman.users.antonia.electrode_id_reader import read_single_electrode_coordinate,read_receptive_field_centers
        if self.experiment_config.READ_ELECTRODE_COORDINATE:
            coordinates = read_single_electrode_coordinate()
        else:
            coordinates = read_receptive_field_centers()
        for repetitions in range(self.experiment_config.REPETITIONS):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
            if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
                duration = 0
            elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
                raise RuntimeError('This frame rate is not possible')
            else:
                duration = 1.0/self.experiment_config.FRAME_RATE
            for coordinate in coordinates:
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                if self.experiment_config.JUMPING:
                    self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH,position=utils.cr(tuple(coordinate)))
                else:
                    self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                if self.abort or not self.experiment_config.JUMPING:#when not jumping, one iteration is enough
                    break
            if self.abort:
                break
