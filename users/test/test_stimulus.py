import time
import numpy
import serial
import os.path
import os

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import visexpman
from visexpman.engine import visexp_runner
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.test import unittest_aggregator
from visexpman.users.common import stimuli
from visexpA.engine.datadisplay import videofile

class TestCurtainConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestCurtainExp'
        self._create_parameters_from_locals(locals())

class TestCurtainExp(experiment.Experiment):
    def run(self):
        self.moving_curtain(self.machine_config.SCREEN_SIZE_UM['col']*0.5, color = 1.0, direction=45.0, background_color = 0.0, pause = 0.0)
        
class TestNaturalStimConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestNaturalStimExp'
        self._create_parameters_from_locals(locals())
        
class TestNaturalStimExp(experiment.Experiment):
    def run(self):
        t0=time.time()
        self.show_fullscreen(duration=1.0, color=1.0)
        print 60/(time.time()-t0)
        speed = 100
        cut_off_ratio = 1.0
        profile_size = self.config.SCREEN_RESOLUTION['col']
        profile = numpy.linspace(0,1,profile_size)
        
#        profile[1::20] =0.0
#        profile[2::20] =0.0
        profile = numpy.repeat(profile, 10)
        profile[0::200] =0.0
        alltexture = numpy.repeat(profile,3).reshape(profile_size*10,1,3)
        texture = alltexture[:profile_size]
        diagonal = numpy.sqrt(self.config.SCREEN_RESOLUTION['row']**2+self.config.SCREEN_RESOLUTION['col']**2)
        alpha = numpy.arctan2(self.config.SCREEN_RESOLUTION['row'],self.config.SCREEN_RESOLUTION['col'])
        angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        orientation_rad = 0
        angles = angles + orientation_rad
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
                             [cut_off_ratio, 1.0],
                             [0.0, 1.0],
                             [0.0, 0.0],
                             [cut_off_ratio, 0.0],
                             ])

        glTexCoordPointerf(texture_coordinates)
        phase = 0.0
        dphase = (float(speed)/self.config.SCREEN_RESOLUTION['col'])/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        ds = int(float(speed)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        i = 0
        
#        self.machine_config.INSERT_FLIP_DELAY=True
        t0=time.time()
        while True:
            if i+profile_size>=alltexture.shape[0]:
                break
            phase -= dphase
#            glTexCoordPointerf(texture_coordinates + numpy.array([phase,0.0]))
            texture = alltexture[i:i+profile_size]
            i += ds
            glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
#            self._flip()
#            self.screen.flip()
#            time.sleep(5e-3)
            self._flip_and_block_trigger(1, 1, True, False)
#            self.frame_counter +=1
            if self.frame_counter  == 6000:
                break
            if self.abort:
                break
        dt=(time.time()-t0)
        print self.frame_counter/dt,dt
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        pass

class Pointing2NotExistingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'None'
        self._create_parameters_from_locals(locals())
        
class Pointing2NonExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'DummyClass'
        self._create_parameters_from_locals(locals())
        
class DummyClass(object):
    pass

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 0.0
        self.GRATING_STAND_TIME = 0.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 90)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5] 
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 0.0
        self.runnable = 'MovingGrating1'
        self._create_parameters_from_locals(locals())

class MovingGrating1(stimuli.MovingGrating):
    def run(self, fragment_id=0):
        shutil.rmtree(self.machine_config.CAPTURE_PATH)
        os.mkdir(self.machine_config.CAPTURE_PATH)
        self.machine_config.ENABLE_FRAME_CAPTURE = True
        grating.MovingGrating.run(self, fragment_id)
        #save captured frames to avi
        videofile.image_files2mpg(self.machine_config.CAPTURE_PATH, os.path.join(self.machine_config.VIDEO_PATH, '{0}.mpg'.format(self.experiment_name)), 
                                                                                                                                  fps = self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.machine_config.ENABLE_FRAME_CAPTURE = False

class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0
        self.PIXEL_SIZE = 50.0
        self.FLICKERING_FREQUENCY = 30.0
        self.N_WHITE_PIXELS = None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class WhiteNoiseExperiment(experiment.Experiment):
    def run(self):
        self.white_noise(duration = self.experiment_config.DURATION,
            pixel_size = self.experiment_config.PIXEL_SIZE, 
            flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
            colors = self.experiment_config.COLORS,
            n_on_pixels = self.experiment_config.N_WHITE_PIXELS)
        self.show_fullscreen()

class GUITestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0#Comment
        self.PAR2 = 2.0#Comment2
        self.PAR1 = 1.0#Comment1
        self.editable=True
        self._create_parameters_from_locals(locals())
        
class TestCommonExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeExperiment'
        SHAPE_SIZE = 100
        SPEEDS = [1000.0]
        DIRECTIONS = [90]
        self._create_parameters_from_locals(locals())
                                 
        
class DebugExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0#Comment
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())

class Debug(experiment.Experiment):
    def prepare(self):
        self.experiment_duration = self.experiment_config.DURATION
    
    def run(self):
        self.show_shape(duration=0,size=10, color=1.0, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,pos = utils.rc((10, 0)), size=30, color=0.7, part_of_drawing_sequence=True, flip=False)
        self.show_shape(duration=0,size=100, color=0.4, part_of_drawing_sequence=True, flip=True)
        time.sleep(self.experiment_duration)
        return
            
if __name__ == "__main__":
    if True:
        v = visexp_runner.VisionExperimentRunner('peter', 'StimulusDevelopment')
#        v.run_experiment(user_experiment_config = 'MovingGratingTuning')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
    elif not True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'FullfieldSinewave')
    elif not True:
        v = visexp_runner.VisionExperimentRunner('antonia',  'MEASetup')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
    elif True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        if True:
            v.run_loop()
        else:
            v.run_experiment(user_experiment_config = 'IncreasingAnnulusParameters')
    else:
        v = visexp_runner.VisionExperimentRunner('zoltan',  'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
