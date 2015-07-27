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
        self.runnable = 'PlayGround'
        self._create_parameters_from_locals(locals())


class PlayGround(experiment.Experiment):
    def prepare(self):
        pass
    
    def run(self):
        self.stimulus_frame_info.append({'super_block':'PlayGround', 'is_last':0, 'counter':self.frame_counter})
               
        #self.moving_comb(speed=500, orientation=0, bar_width=50, tooth_size=20, tooth_type='sawtooth', contrast=1.0, background=0,pos = utils.rc((0,0)) )
        self.fingerprinting()
        
        self.stimulus_frame_info.append({'super_block':'PlayGround', 'is_last': 1, 'counter':self.frame_counter})


    def fingerprinting(self, speed = 500, direction = 0.0, duration=2.0, intensity_levels = 255,
                       minimal_spatial_period = None, spatial_resolution = None, 
                       rewind = True,
                       save_frame_info =True,is_block = False):
        
        '''
            This stimulus repeats a texture object in lines that are then moving together.
            Required:
            - texture: 3D numpy.array with shape (nx,ny,3)
            - texture_size: width and length of each texture (in um)
            Optional:
            - texture_info: useful for data analysis, i.e. explain that the texture is
            - movingLines: every m-th rows move together while the others are static
            - duration: total time of stimulus in seconds
            - speed: in um/s
            - direction: in degrees
            - save_frame_info: default to True
        '''        
        if spatial_resolution is None:
            spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        if minimal_spatial_period is None:
            minimal_spatial_period = 10 * spatial_resolution
        
        screen = numpy.array([self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col']])
        
        # Create intensity profile:
        self.intensity_profile = signal.generate_natural_stimulus_intensity_profile(duration=duration,
                                                                                    speed=speed,
                                                                                    intensity_levels=255,
                                                                                    minimal_spatial_period=minimal_spatial_period,
                                                                                    spatial_resolution=spatial_resolution,
                                                                                    )
        
        self.intensity_profile = numpy.concatenate((numpy.zeros(1.5*screen[1]), self.intensity_profile, numpy.zeros(1.5*screen[1])) )
        
        
        if self.intensity_profile.shape[0] < self.config.SCREEN_RESOLUTION['col']:
            self.intensity_profile = numpy.tile(self.intensity_profile, numpy.ceil(float(self.config.SCREEN_RESOLUTION['col'])/self.intensity_profile.shape[0]))
        
        fly_in_out = self.config.BACKGROUND_COLOR[0] * numpy.ones((self.config.SCREEN_RESOLUTION['col'],1,3))        
        intensity_profile_length = self.intensity_profile.shape[0]        
        intensity_profile_length += 2*fly_in_out.shape[0]        
                
        texture = numpy.repeat(self.intensity_profile,3).reshape(self.intensity_profile.shape[0],1,3)
        #texture_size = numpy.array([self.intensity_profile.shape[0], screen[1]])

        #lPieces = screen[0]
        #nPieces = texture.shape[0]/100 + 1        
                
        
        # Size and number of repetiotions along the length of bar
        #wDist_px = (texture_size[0])/self.config.SCREEN_UM_TO_PIXEL_SCALE
        #wDist_px = (lPieces)/self.config.SCREEN_UM_TO_PIXEL_SCALE
        #nRepW = int(numpy.ceil(diagonal_px/wDist_px))
        
        # Size and number of repetiotions along the width of bar
        #lDist_px = (texture_size[1])/self.config.SCREEN_UM_TO_PIXEL_SCALE
        #lDist_px = (lPieces)/self.config.SCREEN_UM_TO_PIXEL_SCALE        
        #nRepL = int(numpy.ceil(diagonal_px/lDist_px))
        
        
        # Vertices that define the size of the texture (centered around (0,0) ), covers the whole screen:
        vertices = numpy.array([[-screen[0], -screen[1]],[-screen[0], screen[1]],[screen[0], screen[1]],[screen[0], -screen[1]]])*0.5
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        
        texture_piece = texture[:lPieces,:]
        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture_piece.shape[1], texture_piece.shape[0], 0, GL_RGB, GL_FLOAT, texture_piece)        
        
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        
        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        
        texture_coordinates = numpy.array([ [1.0, 1.0], [0.0, 1.0], [0.0, 0.0], [1.0, 0.0], ])
        glTexCoordPointerf(texture_coordinates)
        #glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
       
        def show_(texture_piece):
            glTexImage2D(GL_TEXTURE_2D, 0, 3, texture_piece.shape[1], texture_piece.shape[0], 0, GL_RGB, GL_FLOAT, texture_piece)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4) 
       
        # Enter stimulus loop:
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = False)
        
        dist = 0.0       
        ds = float(speed*self.config.SCREEN_UM_TO_PIXEL_SCALE)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        while True:
            dist += ds
            start_idx = int(dist)
            end_idx = numpy.min([start_idx + lPieces, texture.shape[0]])
            
            if self.abort or start_idx >= intensity_profile_length:
                break
            
            texture_piece = texture[start_idx:end_idx,:]
            show_(texture_piece)            
            self._flip(frame_trigger = True)
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
        # Enter rewind stimulus loop:
        if save_frame_info and rewind:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = False)
        
        while rewind:
            dist -= ds
            start_idx = int(dist)
            end_idx = numpy.min([start_idx + lPieces, texture.shape[0]])
            
            if self.abort or start_idx < 0:
                break
            
            texture_piece = texture[start_idx:end_idx,:]
            show_(texture_piece)
            self._flip(frame_trigger = True)
        
        # Finish up
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
       
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        # END OF show_dash

