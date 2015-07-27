#%%
import os
os.chdir('/home/rolandd/Software/')

import sys
import unittest
import time
import os.path
import numpy
import warnings
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.vision_experiment.screen import StimulationScreen
from visexpman.engine.vision_experiment import experiment_control
from visexpman.engine.generic.graphics import check_keyboard
from visexpman.engine.generic import utils,fileop,introspect
import hdf5io

import visexpman.engine.visexp_app as app

context = visexpman.engine.application_init(user='roland', config='MEAConfig', user_interface_name='stim', single_file='pilot02_cell_classification')

#
#context = visexpman.engine.application_init(user='antonia',
#                                  config='MEASetup',
#                                  user_interface_name='stim')


#
app.run_stim(context)
visexpman.engine.stop_application(context)


#%%

import visexpman.engine.generic.signal as s
x = s.generate_natural_stimulus_intensity_profile(speed = 500,
                                                  duration=20.0,
                                                  intensity_levels=255,
                                                  minimal_spatial_period=17.5,
                                                  spatial_resolution=1.75)


#%% This works:
import parallel
p = parallel.Parallel()
##
for N in range(1,32):
    print N
    p.setData(N)
    time.sleep(0.5)

## Look at the log file:
c = context['machine_config']
folder = c.LOG_PATH

import scipy.io
M = scipy.io.loadmat(folder + '/' + 'log_MEAConfig_roland_stim_2015-05-20_16-13-48_MarchingSquares_143213124125.mat')

##
for k,v in self.datafile.items() :
     #v
     for j in v:
        i         
        if j is None:
            print 'n'
        else:
            print 'i'

##
cmd = "start"

import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://bs-hpws19:75000")
socket.send(cmd)
socket.recv()


##

import visexpman.engine.hardware_interface.queued_socket as qs

class Test(qs.QueuedSocketHelpers):
    #def __init__(self,socket_queues):
    pass

#socket_queues['fromsocket'] = ...
socket_queues = []
t = Test(socket_queues)



##
import matplotlib.pyplot as p

with p.xkcd(scale=1, randomness=10, length=300):
    font = {'family':'Ubuntu'}
    p.rc('font', **font)
    p.plot([1,2,3,1,2])
p.show()


##
import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

from visexpman.engine.generic import graphics,utils,colors,fileop, signal,geometry,videofile


from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from visexpman.users.roland.stimuli import *


alltexture = numpy.array([[[ 6,  8, 11]],[[ 7,  5, 32]],[[ 7,  0, -4]]])
alltexture = numpy.repeat(alltexture,200, axis=0)
alltexture = numpy.repeat(alltexture,2, axis=1)
texture = alltexture

direction = 0
#diagonal = numpy.sqrt(2) * numpy.sqrt(self.config.SCREEN_RESOLUTION['row']**2 + self.config.SCREEN_RESOLUTION['col']**2)
#diagonal =  1*numpy.sqrt(2) * self.config.SCREEN_RESOLUTION['col']
diagonal = 100
alpha =numpy.pi/4
angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
angles = angles + direction*numpy.pi/180.0
vertices = 0.5 * diagonal * numpy.array([numpy.cos(angles), numpy.sin(angles)])
vertices = vertices.transpose()
        
glEnableClientState(GL_VERTEX_ARRAY)
glVertexPointerf(vertices)
glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
glEnable(GL_TEXTURE_2D)
glEnableClientState(GL_TEXTURE_COORD_ARRAY)
texture_coordinates = numpy.array(
                        [
                        [1.0, 1.0],
                        [0.0, 1.0],
                        [0.0, 0.0],
                        [1.0, 0.0],
                        ])
glTexCoordPointerf(texture_coordinates)
#ds = float(speed*self.config.SCREEN_UM_TO_PIXEL_SCALE)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
#        t0=time.time()
#texture_pointer = 0
#frame_counter = 0
#self._add_block_start(is_block, 0, 0)
# while True:
#     start_index = int(texture_pointer)
#     end_index = int(start_index + self.config.SCREEN_RESOLUTION['col'])
#     if end_index > alltexture.shape[0]:
#         end_index -= alltexture.shape[0]
#     if start_index < end_index:
#         texture = alltexture[start_index:end_index]
#     else:
#         texture = numpy.zeros_like(texture)
#         texture[:-end_index] = alltexture[start_index:]
#         texture[-end_index:] = alltexture[:end_index]
#     if start_index >= intensity_profile_length:
#         break
#     texture_pointer += ds
#     frame_counter += 1
#     glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
#     glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
#     glColor3fv((1.0,1.0,1.0))
#     glDrawArrays(GL_POLYGON,  0, 4)
#     self._flip(frame_trigger = True)
#     if self.abort:
#         break


