import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.federico.stimuli import IntrinsicProtocol, IntrinsicProtConfig

class MyExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_THICKNESS=10.0
        self.runnable='MyExperiment'
        self._create_parameters_from_locals(locals())
        
class MyExperiment(experiment.Experiment):
    def run(self):
        self.moving_shape(utils.rc((1000,self.experiment_config.BAR_THICKNESS)), speeds=1000.0, directions=[0.0, 45.0,90.0], shape = 'rect', color = 255, background_color = 0.0, moving_range=utils.rc((0.0,0.0)), pause=0.0,block_trigger = False,shape_starts_from_edge = True)
        
##################################################################
class MyInstrConfig(IntrinsicProtConfig):
    def _create_parameters(self):
        IntrinsicProtConfig._create_parameters(self)
        self.DURATION = 10.0*0.05
        self.SPEEDS = 200
        self.ORIENTATIONS = range(0,360,90)
        self.FULLFIELD_ORIENTATIONS = range(0,360,45)
        self.runnable='MyIntrinsicProtocol'
        
class MyIntrinsicProtocol(IntrinsicProtocol):
    def prepare(self):
        
        self.positions = [
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *-2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *2/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *0, self.machine_config.SCREEN_SIZE_UM['col'] *2/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *2/ 6)),
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *-2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *0)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *0, self.machine_config.SCREEN_SIZE_UM['col'] *0)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *0)),
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *-2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *-2/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *0, self.machine_config.SCREEN_SIZE_UM['col'] *-2/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *2/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *-2/ 6))
            ]
        self.fragment_durations = [self.experiment_config.DURATION*len(self.positions)*2+self.experiment_config.PAUSE]
        print self.fragment_durations

    def run(self):
        IntrinsicProtocol.run(self)
                    
#################################################                  
cycles = 10
class Behavioral_10cm_4sec(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 1
        self.GRATING_SIZE = 10
        self.CYCLE_DURATION = 4
        self.NCYCLES = cycles
        
        self.DURATION = self.NCYCLES * self.CYCLE_DURATION
        self.SPEEDS = 2*self.GRATING_SIZE/self.CYCLE_DURATION
        self.DUTY_CYCLE = 1.0
        self.PAUSE = 0
        self.FULLFIELD_ORIENTATIONS = [0]
        self.runnable='MyFFGratingsExp'

class Behavioral_6cm_4sec(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 1
        self.GRATING_SIZE = 6
        self.CYCLE_DURATION = 4
        self.NCYCLES = cycles
        
        self.DURATION = self.NCYCLES * self.CYCLE_DURATION
        self.SPEEDS = 2*self.GRATING_SIZE/self.CYCLE_DURATION
        self.DUTY_CYCLE = 1.0
        self.PAUSE = 0
        self.FULLFIELD_ORIENTATIONS = [0]
        self.runnable='MyFFGratingsExp'

class Behavioral_10cm_3sec(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 1
        self.GRATING_SIZE = 10
        self.CYCLE_DURATION = 3
        self.NCYCLES = cycles
        
        self.DURATION = self.NCYCLES * self.CYCLE_DURATION
        self.SPEEDS = 2*self.GRATING_SIZE/self.CYCLE_DURATION
        self.DUTY_CYCLE = 1.0
        self.PAUSE = 0
        self.FULLFIELD_ORIENTATIONS = [0]
        self.runnable='MyFFGratingsExp'

class MyFFGratingsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = int(10.0*0.1)
        self.PAUSE = 0
        self.GRATING_SIZE = 10
        self.DUTY_CYCLE = 1.0
        self.DURATION = 10.0*3
        self.SPEEDS = 3.0*0
        self.FULLFIELD_ORIENTATIONS = range(0,360,90)
        self.runnable='MyFFGratingsExp'

class MyFFGratingsExp(experiment.Experiment):
    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            self.show_fullscreen(duration = self.experiment_config.PAUSE, color = 0)
            for ori in self.experiment_config.FULLFIELD_ORIENTATIONS:
#                self.show_grating_non_texture(self.experiment_config.DURATION,
#                    self.experiment_config.GRATING_SIZE,
#                    self.experiment_config.SPEEDS,
#                    ori,
#                    self.experiment_config.DUTY_CYCLE,
#                    contrast=1.0,background_color=0.0)
                self.show_grating(duration = self.experiment_config.DURATION,  
                        white_bar_width = self.experiment_config.GRATING_SIZE*0.5,  
                        orientation = ori,  
                        velocity =self.experiment_config.SPEEDS,
                        color_contrast = 1.0,  
                        color_offset = 0.5,
                        duty_cycle = self.experiment_config.DUTY_CYCLE)
