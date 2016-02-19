from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class TonyNaturalBarsCircularConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800,400,1200]#um/s
        self.SPEED = [800]#um/s
        self.REPEATS = 1#5
        self.DIRECTIONS = [0,90,180,270] #range(0,360,90)
        self.DURATION = 12
        self.BACKGROUND_TIME = 2.5
        self.BACKGROUND_COLOR = 0.5
        self.CIRCULAR=True
        self.ENABLE_FLYINOUT= True #True # False
        self.ALWAYS_FLY_IN_OUT = True #True # False
        if self.CIRCULAR:
            self.ENABLE_FLYINOUT=False
        #Advanced/Tuning
        self.MINIMAL_SPATIAL_PERIOD= 120 #None
        self.SCALE= 1.0
        self.OFFSET=0.0
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())

class TonyNaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800,400,1200]#um/s
        self.SPEED = [800]#um/s
        self.REPEATS = 1#5
        self.DIRECTIONS = [0,90,180,270] #range(0,360,90)
        self.DURATION = 12
        self.BACKGROUND_TIME = 2.5
        self.BACKGROUND_COLOR = 0.5
        self.CIRCULAR=False
        self.ENABLE_FLYINOUT= True #True # False
        self.ALWAYS_FLY_IN_OUT = True #True # False
        if self.CIRCULAR:
            self.ENABLE_FLYINOUT=False
        #Advanced/Tuning
        self.MINIMAL_SPATIAL_PERIOD= 120 #None
        self.SCALE= 1.0
        self.OFFSET=0.0
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())
        
class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        if len(self.experiment_config.SPEED)>1:
            raise RuntimeError('Not supported')
        fitime=self.machine_config.SCREEN_SIZE_UM['col']/self.experiment_config.SPEED[0]
        if not self.experiment_config.CIRCULAR:
            fitime*=2
        self.fragment_durations = [(fitime+self.experiment_config.DURATION)*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)*len(self.experiment_config.SPEED)+self.experiment_config.BACKGROUND_TIME*self.experiment_config.REPEATS]
#        self.precalculate_duration_mode=True
#        self.abort=False
#        self.run()
#        self.fragment_durations = [self.frame_counter/self.machine_config.SCREEN_EXPECTED_FRAME_RATE]
#        self.frame_counter = 0
#        self.precalculate_duration_mode=False
        
    def run(self):
        #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        for directions in self.experiment_config.DIRECTIONS:
            if self.abort:
                break
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR, flip=True)
            for speeds in self.experiment_config.SPEED:
                if self.abort:
                    break
                for rep in range(self.experiment_config.REPEATS):
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
                    self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                    self.show_natural_bars(speed = speeds, duration=self.experiment_config.DURATION, minimal_spatial_period = self.experiment_config.MINIMAL_SPATIAL_PERIOD, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, 
                            background=self.experiment_config.BACKGROUND_COLOR,
                            circular=self.experiment_config.CIRCULAR,
                            scale=self.experiment_config.SCALE,
                            offset=self.experiment_config.OFFSET,
                            intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out)
                    self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        self.show_fullscreen(duration = 0, color =  self.experiment_config.BACKGROUND_COLOR, flip=True)
