# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 16:05:56 2015

@author: rolandd
"""
import numpy
import copy
import time
import random

import inspect

from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

from visexpman.engine.generic import graphics,utils,colors,fileop, signal,geometry,videofile


from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from visexpman.users.common.stimuli import *

class ABatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = {}
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
        self.VARS['FingerPrinting']['FF_PAUSE_COLOR'] = 1.0
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0] #range(0,90, 45)
        self.VARS['FingerPrinting']['SPEEDS'] = [1600] #[500, 1600]      
        self.VARS['FingerPrinting']['DURATION'] = 1.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255        
        
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [25, 100]
        self.VARS['DashStimulus']['GAPSIZE'] = [5, 20]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 1.0
        self.VARS['DashStimulus']['SPEEDS'] = [1600]
        self.VARS['DashStimulus']['DIRECTIONS'] = [135] #range(0, 55, 5)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5
        
        self.runnable = 'PlayGround'
        self._create_parameters_from_locals(locals())


class PlayGround(experiment.Experiment):
    def prepare(self):
        
        self.experiments = {}
        for experiment_type in self.experiment_config.VARS:
            print experiment_type
            
            this_config = experiment.ExperimentConfig(machine_config=None, runnable=experiment_type)
            for var_name in self.experiment_config.VARS[experiment_type]:
                setattr(this_config, var_name, self.experiment_config.VARS[experiment_type][var_name])
            
            self.experiments[experiment_type] = eval(experiment_type)(machine_config = self.machine_config,
                                                                      digital_output = self.digital_output,
                                                                      experiment_config=this_config,
                                                                      queues = self.queues,
                                                                      parameters = self.parameters,
                                                                      log = self.log,
                                                                      )
            #machine_config, experiment_config=None, queues=None, parameters=None, log=None, digital_output=None):
            
            #self.experiments[experiment_type].experiment_config = experiment.ExperimentConfig(self.machine_config, runnable=experiment_type)
            #for var_name in self.experiment_config.VARS[experiment_type]:
                #eval('self.experiments[' + experiment_type + '].experiment_config.' + var_name + ' = self.experiment_config.VARS['+experiment_type+']['+var_name+']')
                #self.experiments[experiment_type].experiment_config.var_name = self.experiment_config.VARS[experiment_type][var_name]
            
            self.experiments[experiment_type].prepare()
        
    def run(self):
        
        for experiment_type in self.experiment_config.VARS:
            #self.stimulus_frame_info.append({'super_block':experiment_type, 'is_last':0, 'counter':self.frame_counter})
            
            # Before starting sub_experiment, update the frame_counter:
            self.experiments[experiment_type].frame_counter = self.frame_counter
            self.experiments[experiment_type].run()
            self.frame_counter = self.experiments[experiment_type].frame_counter

            for info in self.experiments[experiment_type].stimulus_frame_info:           
                self.stimulus_frame_info.append(info)
                print info
            
            #self.stimulus_frame_info.append({'super_block':experiment_type, 'is_last':1, 'counter':self.frame_counter})

            # After each sub_experiment, add one second of white fullscreen:
            self.stimulus_frame_info.append({'super_block':'FullScreen', 'is_last':0, 'counter':self.frame_counter})     
            self.show_fullscreen(duration=1.0, color=1.0, frame_trigger=True)
            self.stimulus_frame_info.append({'super_block':'FullScreen', 'is_last':1, 'counter':self.frame_counter})



