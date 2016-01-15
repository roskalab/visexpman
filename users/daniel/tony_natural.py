from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class TonyNaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800,400,1200]#um/s
        self.SPEED = [800]#um/s
        self.REPEATS = 1#6 #5
        self.DIRECTIONS = [0,90,180,270] #range(0,360,90)
        self.DURATION = 12
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.0
        self.ENABLE_FLYINOUT= True #True # False
        self.ALWAYS_FLY_IN_OUT = True #True # False
        #Advanced/Tuning
        self.MINIMAL_SPATIAL_PERIOD= 120 #None
        self.SCALE= 1.0
        self.OFFSET=0.0
        self.runnable = 'TonyNaturalBarsExperiment'
        self._create_parameters_from_locals(locals())
        
class TonyNaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        if len(self.experiment_config.SPEED)>1:
            raise RuntimeError('Not supported')
        fitime=self.machine_config.SCREEN_SIZE_UM['col']/self.experiment_config.SPEED[0]
        self.fragment_durations = [(2*fitime+self.experiment_config.DURATION)*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)*len(self.experiment_config.SPEED)+self.experiment_config.BACKGROUND_TIME*self.experiment_config.REPEATS]
        
    def run(self):
        #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
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
                    #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                    self.show_natural_bars(speed = speeds, duration=self.experiment_config.DURATION, minimal_spatial_period = self.experiment_config.MINIMAL_SPATIAL_PERIOD, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, 
                            #background_color=self.experiment_config.BACKGROUND_COLOR,
                            scale=self.experiment_config.SCALE,
                            offset=self.experiment_config.OFFSET,
                            intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out)
                    #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
