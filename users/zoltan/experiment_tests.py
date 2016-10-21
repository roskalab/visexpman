from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NaturalBarsExperiment1(experiment.Stimulus):
    def stimulus_configuration(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False

    def calculate_stimulus_duration(self):
        self.duration = self.DURATION*3*2
        
    def run(self):
        for i in range(3):
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)
            self.block_start()
            self.show_fullscreen(duration = self.DURATION, color =  1.0)
            self.block_end()
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)

class Flash(experiment.Stimulus):
    def stimulus_configuration(self):
        self.DURATION=0.5
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION*3
        
    def run(self):
        self.show_fullscreen(color=0.0,duration=self.DURATION)
        self.show_fullscreen(color=0.5,duration=self.DURATION)
        self.show_fullscreen(color=1.0,duration=self.DURATION)
        
class Gr(experiment.Stimulus):
    def stimulus_configuration(self):
        self.DURATION=3
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION*3
        
    def run(self):
#        texture=numpy.zeros((2,7,3))
#        texture[0,0,:]=1.0
#        texture[1,1,:]=1.0
#        cut_off_ratio=1
#        texture_coordinates = numpy.array(
#                             [
#                             [1.0, cut_off_ratio],
#                             [0.0, cut_off_ratio],
#                             [0.0, 0.0],
#                             [1.0, 0.0],
#                             ])
#        self._init_texture(utils.rc((100,400)),0,texture_coordinates)
#        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
#        phase=0
#        for i in range(120):
#            phase+=-0.01
#            glTexCoordPointerf(texture_coordinates + numpy.array([phase,0.0]))
#            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
#            glColor3fv((1.0,1.0,1.0))
#            glDrawArrays(GL_POLYGON,  0, 4)
#            self._flip(False)
#        self._deinit_texture()
        import time
        t0=time.time()
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION,display_area=utils.rc((400,600)),
                flicker={'frequency':5, 'modulation_size':50})
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION*3)
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION*2,
                flicker={'frequency':5, 'modulation_size':50})
        print t0-time.time()        
#        self.show_grating(white_bar_width=100, velocity=100.0,duration=self.DURATION,orientation=10)
#        self.show_grating(white_bar_width=100, velocity=100.0,duration=self.DURATION,orientation=90,display_area=utils.rc((400,800)))

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'Gr')
