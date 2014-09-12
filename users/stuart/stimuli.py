import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.federico.stimulations import IntrinsicProtocol, IntrinsicProtConfig

class MyExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_THICKNESS=10.0
        self.runnable='MyExperiment'
        self._create_parameters_from_locals(locals())
        
class MyExperiment(experiment.Experiment):
    def run(self):
        self.moving_shape(utils.rc((1000,self.experiment_config.BAR_THICKNESS)), speeds=10.0, directions=[0.0, 45.0,90.0], shape = 'rect', color = 255, background_color = 0.0, moving_range=utils.rc((0.0,0.0)), pause=0.0,block_trigger = False,shape_starts_from_edge = True)
        
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
class MyFFGratingsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = int(10.0*0.1)
        self.PAUSE = 0
        self.GRATING_SIZE = 100
        self.DUTY_CYCLE = 1.0
        self.DURATION = 10.0*.2
        self.SPEEDS = 102*2
        self.FULLFIELD_ORIENTATIONS = range(0,360,90)
        self.runnable='MyFFGratingsExp'

class MyFFGratingsExp(experiment.Experiment):
    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            self.show_fullscreen(duration = self.experiment_config.PAUSE, color = 0)
            for ori in self.experiment_config.FULLFIELD_ORIENTATIONS:
                self.show_grating(duration = self.experiment_config.DURATION,  
                        white_bar_width = self.experiment_config.GRATING_SIZE,  
                        orientation = ori,  
                        velocity =self.experiment_config.SPEEDS,
                        color_contrast = 1.0,  
                        color_offset = 0.5,
                        duty_cycle = self.experiment_config.DUTY_CYCLE)
