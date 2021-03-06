import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument

class MyExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_THICKNESS=10.0
        self.runnable='MyExperiment'
        self._create_parameters_from_locals(locals())
        
class MyExperiment(experiment.Experiment):
    def run(self):
        self.moving_shape(utils.rc((1000,self.experiment_config.BAR_THICKNESS)), speeds=10.0, directions=[0.0, 45.0,90.0], shape = 'rect', color = 255, background_color = 0.0, moving_range=utils.rc((0.0,0.0)), pause=0.0,block_trigger = False,shape_starts_from_edge = True)
        
##################################################################
class Retinotopy(experiment.ExperimentConfig):#was MyInstrConfig
    def _create_parameters(self):
        self.SCREEN_PER_MASK_RATIO = 1
        self.MASK_PER_GRATING_RATIO = 4
        self.MASK_SIZE = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO, self.machine_config.SCREEN_SIZE_UM['col'] / self.SCREEN_PER_MASK_RATIO))
        self.GRATING_SIZE = self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO/self.MASK_PER_GRATING_RATIO
        self.DUTY_CYCLE = 1.0
        self.BACKGROUND_COLOR = 0.005
        #Speeds
        #5/6 of screen is 60 degree of mouse visual field
        angular_factor = self.machine_config.SCREEN_SIZE_UM['col']*(5.0/6.0)/60.0
        if 0:
            self.STARTING_ANGULAR_SPEED = 10.0#degree/sec
            self.FINAL_ANGULAR_SPEED = 50.0#degree/sec
            self.SPEEDS = numpy.array([self.STARTING_ANGULAR_SPEED, self.FINAL_ANGULAR_SPEED]) * angular_factor

        
        self.ENABLE_TRIGGER_WAIT = True
        self.DURATION = 10.0*0.1
        self.SPEEDS = 200
        self.ORIENTATIONS = range(0,360,90)
        self.FULLFIELD_ORIENTATIONS = range(0,360,90)
        self.PAUSE = 10.0
        self.BLANK_DELAY = 14.0
        self.runnable='MyIntrinsicProtocol'
        self.pre_runnable='IntrinsicPre'
        
class MyIntrinsicProtocol(experiment.Experiment):
    def prepare(self):
        self.positions = [
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *1/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *5/6)), 
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *3/6, self.machine_config.SCREEN_SIZE_UM['col'] *5/6)), 
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *5/6, self.machine_config.SCREEN_SIZE_UM['col'] *5/6)),
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *1/6, self.machine_config.SCREEN_SIZE_UM['col'] *3/6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *3/6, self.machine_config.SCREEN_SIZE_UM['col'] *3/6)), 
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *5/6, self.machine_config.SCREEN_SIZE_UM['col'] *3/6)),
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *1/6, self.machine_config.SCREEN_SIZE_UM['col'] *1/ 6)), 
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *3/6, self.machine_config.SCREEN_SIZE_UM['col'] *1/ 6)), 
#            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *5/6, self.machine_config.SCREEN_SIZE_UM['col'] *1/ 6))
            ]
        self.fragment_durations = [self.experiment_config.DURATION*len(self.positions)*2+self.experiment_config.BLANK_DELAY]
        print self.fragment_durations

    def run(self):
        #Initial delay and flash
    
#        self.show_fullscreen(color = 0.5, duration=6.0)
#        self.show_fullscreen(color = 0.5, duration=self.experiment_config.PAUSE)
        
        for i in range(15):
            spd = self.experiment_config.SPEEDS
            self.show_fullscreen(color = 0.005, duration=self.experiment_config.BLANK_DELAY)
    
            if i ==1 and isinstance(spd, list):
                spd = spd[::-1]
            if self.experiment_config.ENABLE_TRIGGER_WAIT:
                while True:
                    if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                        self.abort=True
                        break
                    elif daq_instrument.read_digital_line('Dev1/port0/line0')[0] == 1:
                        break
            if self.abort:
                return
            for position in self.positions:
                for ori in self.experiment_config.ORIENTATIONS:
                    mask_size = copy.deepcopy(self.experiment_config.MASK_SIZE)
                    if ori == 90 or ori == 270:
                        mask_size['col'] = self.experiment_config.MASK_SIZE['row']
                        mask_size['row'] = self.experiment_config.MASK_SIZE['col']
                    self.show_grating(duration = self.experiment_config.DURATION,  
                                    white_bar_width = self.experiment_config.GRATING_SIZE,  
                                    display_area = mask_size,
                                    orientation = ori,  
                                    velocity =spd,
                                    color_contrast = 1.0,  
                                    color_offset = 0.5,  
                                    pos = position,
                                    duty_cycle = self.experiment_config.DUTY_CYCLE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR)
                self.show_fullscreen(color = 0.005, duration=self.experiment_config.PAUSE)
                self.printl('Waiting for next MES trigger')
                if self.experiment_config.ENABLE_TRIGGER_WAIT:
                    while True:
                        if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                            self.abort=True
                            break
                        elif daq_instrument.read_digital_line('Dev1/port0/line0')[0] == 1:
                            break
                if self.abort:
                    return
                    
#################################################                  
class MyFFGratingsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = int(10.0*0.1)
        self.PAUSE = 6
        self.GRATING_SIZE = 100
        self.DUTY_CYCLE = 1.0
        self.DURATION = 10.0*.3
        self.SPEEDS = 102*2
        self.FULLFIELD_ORIENTATIONS = range(0,360,360)
        self.runnable='MyFFGratingsExp'

class MyFFGratingsExp(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.REPEATS* len(self.experiment_config.FULLFIELD_ORIENTATIONS)*self.experiment_config.DURATION]
    
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

class IntrinsicPre(experiment.PreExperiment):    
    def run(self):
       self.show_fullscreen(duration = 0, color = 0.005,  flip=False)
