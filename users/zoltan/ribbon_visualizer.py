import time
import os
import numpy
import shutil
from OpenGL.GL import *

import visexpman.engine.generic.graphics
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpA.engine.datahandlers import hdf5io
import visexpman.engine.generic.configuration

class RibbonScanVisualizeConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        FPS_RANGE = (1.0, 200.0)
        COLOR_RANGE = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
        SCREEN_RESOLUTION = utils.rc([600, 800])
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0, FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0, FPS_RANGE]
        BACKGROUND_COLOR = [[0.0, 0.0, 0.0], COLOR_RANGE]
        FRAME_WAIT_FACTOR = [1.0, [0.0, 1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
        ORIGO = utils.rc((0, 0))
        CAPTURE_PATH = '/home/rz/Downloads/output'
        ENABLE_FRAME_CAPTURE = False
        self._create_parameters_from_locals(locals())
        
class RibbonScanScene(visexpman.engine.generic.graphics.Screen):
    '''
    1 unit = 1mm
    '''
    def __init__(self, config, graphics_mode, filename):
        self.filename = filename
        visexpman.engine.generic.graphics.Screen.__init__(self, config, graphics_mode)

    def initialization(self):
        h = hdf5io.Hdf5io(self.filename, filelocking=False)
        h.close()
        #enable blending to display transparent objects
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA) 
        
    def user_keyboard_handler(self, key_pressed):
        pass
    
    def draw_scene(self):
        #draw x,y and z axis 
        glEnableClientState(GL_VERTEX_ARRAY)
#        glVertexPointerf(self.vertices)
#        glLineWidth(1)
#        glColor4fv((1.0, 0.0, 0.0, 1.0))
#        glDrawArrays(GL_LINES, 0 , 2)
#        glColor4fv((0.0, 1.0, 0.0, 1.0))
#        glDrawArrays(GL_LINES, 2, 2)
#        glColor4fv((0.0, 0.0, 1.0, 1.0))
#        glDrawArrays(GL_LINES, 4, 2)
#        vertex_array_offset = self.vertex_pointers[0]
#        
#        #draw plane mirror
#        if self.enable_plane_mirror:
#            glColor4fv((0.5, 0.5, 0.5, 0.7))
#            glDrawArrays(GL_POLYGON, vertex_array_offset, self.vertex_pointers[2])
#        vertex_array_offset = vertex_array_offset + self.vertex_pointers[2]
#        #draw aam mirror
#        if self.enable_aam_mirror:
#            for i in range(int(self.vertex_pointers[3] / self.number_of_shape_vertices)):
#                r = float(i) / (self.vertex_pointers[3] / self.number_of_shape_vertices)
#                g = 1.0 - r
#                b = 1.0
#                alpha = 0.5
#                glColor4fv((r, g, b,  alpha))
#                glDrawArrays(GL_POLYGON, vertex_array_offset + i*self.number_of_shape_vertices ,  self.number_of_shape_vertices)
#        vertex_array_offset = vertex_array_offset + self.vertex_pointers[3]
#        #draw toroid screen
#        #== End of drawing objects ==
        glDisableClientState(GL_VERTEX_ARRAY)

    def render_before_set_view(self):
        return
        msg = str(self.position) + "%2.0f, %2.0f, %2.0f, %2.1f,%2.2f, %f"%(self.heading,  self.roll, self.pitch, self.scale, self.frame_rate, self.wait_time_left)
        self.render_text(msg, color = (0.8, 0.8, 0.8), position = utils.cr((-400, -250)))

def visualize_xz_scan(filename):
    config = RibbonScanVisualizeConfig()
    g = RibbonScanScene(config, graphics_mode = 'standalone', filename = filename)
    g.run()
    g.close_screen()

if __name__=='__main__':
    f = '/home/rz/Downloads/fragment_xz_north_170812_31_-138_-140.0_MovingGratingNoMarching_1345193761_0.hdf5'
    visualize_xz_scan(f)
