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

from stimuli import *

# ------------------------------------------------------------------------------
class ExampleDashStimulus(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BARSIZE = [25, 100]
        self.GAPSIZE = [5, 20]
        self.MOVINGLINES = 3
        self.DURATION = 1
        self.SPEEDS = [1600]
        self.DIRECTIONS = range(0, 55, 5)
        self.BAR_COLOR = 0.5
        
        self.runnable='DashStimulus'
        self._create_parameters_from_locals(locals())



class DashStimulus(experiment.Experiment):
    def prepare(self):
        
        self.bgcolor = self.config.BACKGROUND_COLOR
        if hasattr(self.experiment_config, 'BACKGROUND_COLOR'):
            self.bgcolor = colors.convert_color(self.experiment_config.BACKGROUND_COLOR, self.config)
        
        self.barcolor = self.experiment_config.BAR_COLOR
        if type(self.barcolor) is float or type(self.barcolor) is int:
            self.barcolor = colors.convert_color(self.experiment_config.BAR_COLOR, self.config)
        
        self.texture = self.create_bar(size=[128,128],
                                       bar=self.experiment_config.BARSIZE,
                                       gap=self.experiment_config.GAPSIZE,
                                       bgcolor = self.bgcolor, 
                                       barcolor=self.barcolor)
        
        self.texture_size = numpy.array(self.experiment_config.BARSIZE) + numpy.array(self.experiment_config.GAPSIZE)
        self.texture_info = {'bar_size':self.experiment_config.BARSIZE,
                             'gap_size':self.experiment_config.GAPSIZE,
                             'bar_color':self.barcolor,
                             'bgcolor':self.bgcolor,
                            }
                            
        self.stimulus_duration = len(self.experiment_config.DIRECTIONS)*\
                                 len(self.experiment_config.SPEEDS)*\
                                 self.experiment_config.DURATION*\
                                 self.experiment_config.MOVINGLINES
    
    def run(self):
        
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':0, 'counter':self.frame_counter})
        
        for speed in self.experiment_config.SPEEDS:
            for direction in self.experiment_config.DIRECTIONS:
            
                self.show_dashes(texture = self.texture,
                                texture_size = self.texture_size,
                                texture_info = self.texture_info,
                                movingLines = self.experiment_config.MOVINGLINES,
                                duration = self.experiment_config.DURATION,
                                speed = speed,
                                direction = direction,
                                )
        
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':1, 'counter':self.frame_counter})
    
    
    def create_bar(self, size, bar, gap, bgcolor = [0,0,0], barcolor = [1,1,1]):# width_ratio = 1.0, length_ratio = 1.0):
        # Create BAR texture:
        texture_W = size[0]
        texture_L = size[1]
        
        bar_ = copy.copy(bar)
        gap_ = copy.copy(gap)
        
        fw = texture_W / float(bar[0]+gap[0])
        gap_[0] = int(gap[0]*fw*0.5)*2
        bar_[0] = texture_W - gap_[0]
        
        fl = texture_L / float(bar[1]+gap[1])
        gap_[1] = int(gap[1]*fl*0.5)*2
        bar_[1] = texture_L-gap_[1]
        
        bg_color  = numpy.array([bgcolor])
        bar_color = numpy.array([barcolor])
        
        # Upper and lower gap_ between dashes
        gap_w = numpy.repeat([numpy.repeat(bg_color, texture_W, axis=0)], 0.5*gap_[0], axis=0)
        
        # Left and right gap between dashes
        gap_l = numpy.repeat(bg_color, 0.5*gap_[1], axis=0)
        # Dash itself (one dimensional)
        dash_l = numpy.repeat(bar_color, bar_[1], axis=0)
        
        # Dash and left-right gaps in 2D
        dash = numpy.repeat([numpy.concatenate((gap_l, dash_l, gap_l))], bar_[0], axis=0)
        return numpy.concatenate((gap_w, dash, gap_w)) 
    
    