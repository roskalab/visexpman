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

from stimuli import *

class APlayGroundConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FF_PAUSE_DURATION = 1.0
        self.FF_PAUSE_COLOR = 1.0
        self.DIRECTIONS = range(0,90, 45)
        self.SPEEDS = [500, 1600]      
        self.DURATION = 2.0        
        
        self.runnable = 'PlayGround'
        self._create_parameters_from_locals(locals())


class PlayGround(experiment.Experiment):
    def prepare(self):
        
        #self.speed = 500
        #self.direction = 0.0
        duration = self.experiment_config.DURATION
        
        self.intensity_levels = 255
        minimal_spatial_period = None
        spatial_resolution = None
        
        if spatial_resolution is None:
            spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        if minimal_spatial_period is None:
            minimal_spatial_period = 10 * spatial_resolution
        
        screen_size = numpy.array([self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col']])
        
        # Create intensity profile(s):
        self.intensity_profiles = {}
        for speed in self.experiment_config.SPEEDS:
            intensity_profile = signal.generate_natural_stimulus_intensity_profile(duration=duration,
                                                                                        speed=speed,
                                                                                        intensity_levels=self.intensity_levels,
                                                                                        minimal_spatial_period=minimal_spatial_period,
                                                                                        spatial_resolution=spatial_resolution,
                                                                                        )
            
            intensity_profile = numpy.concatenate((numpy.zeros(1.5*screen_size[1]), intensity_profile, numpy.zeros(1.5*screen_size[1])) )
            if intensity_profile.shape[0] < self.config.SCREEN_RESOLUTION['col']:
                intensity_profile = numpy.tile(intensity_profile, numpy.ceil(float(self.config.SCREEN_RESOLUTION['col'])/intensity_profile.shape[0]))
            
            self.intensity_profiles[speed] = intensity_profile
        
    def run(self):
        self.stimulus_frame_info.append({'super_block':'PlayGround', 'is_last':0, 'counter':self.frame_counter})
        
        for speed in self.experiment_config.SPEEDS:
            for direction in self.experiment_config.DIRECTIONS:
                #self.moving_comb(speed=500, orientation=0, bar_width=50, tooth_size=20, tooth_type='sawtooth', contrast=1.0, background=0,pos = utils.rc((0,0)) )
                self.fingerprinting(self.intensity_profiles[speed], speed, direction = direction, forward=True)
                self.show_fullscreen(duration=self.experiment_config.FF_PAUSE_DURATION, color=self.experiment_config.FF_PAUSE_COLOR,frame_trigger=True)
                self.fingerprinting(self.intensity_profiles[speed], speed, direction = direction, forward=False)
            
        self.stimulus_frame_info.append({'super_block':'PlayGround', 'is_last': 1, 'counter':self.frame_counter})




