import time
import os
import os.path
import numpy
import shutil
from OpenGL.GL import *
try:
    import Image
except ImportError:
    from PIL import Image

import visexpman.engine.generic.graphics
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
import hdf5io
import visexpman.engine.generic.configuration
from visexpman.engine import generic
if 0:
    from visexpA.engine.datadisplay import imaged

class RibbonScanVisualizeConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        FPS_RANGE = (1.0, 200.0)
        COLOR_RANGE = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
        SCREEN_RESOLUTION = utils.rc([768, 1024])
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0, FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0, FPS_RANGE]
        BACKGROUND_COLOR = [[0.0, 0.0, 0.0], COLOR_RANGE]
        FRAME_WAIT_FACTOR = [1.0, [0.0, 1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
        ORIGO = utils.rc((0, 0))
        CAPTURE_PATH = '/mnt/databig/xzfigures'
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
        self.position = [-60.0, 30.0, 0.0]
        self.heading = -10.0
        self.roll = -20.0
        self.pitch = -50.0
        self.scale = 1.4
        h = hdf5io.Hdf5io(self.filename, filelocking= False)
        scanner_trajectory = h.findvar('scanner_trajectory')
        g = h.findvar('pre_scan')
        g = generic.horizontal_flip_array_image(generic.vertical_flip_array_image(g))/255.0
        self.meanimage = numpy.zeros((g.shape[0], g.shape[1], 3))
        self.meanimage[:, :, 1] = g
        xy_scan_info = h.findvar('xy_scan_info')
        xy_scan_info = xy_scan_info[xy_scan_info.keys()[0]]
        scale = xy_scan_info['scale']
        origin = xy_scan_info['origin']
        h.close()
        #Draw 2d image
        n = scanner_trajectory.shape[0]
        resample_rate = 0.1
        resampled_scanner_trajectory_r = numpy.interp(numpy.arange(n*resample_rate)/(n*resample_rate), numpy.arange(n)/float(n), scanner_trajectory['row'])
        resampled_scanner_trajectory_c = numpy.interp(numpy.arange(n*resample_rate)/(n*resample_rate), numpy.arange(n)/float(n), scanner_trajectory['col'])
        resampled_scanner_trajectory = utils.cr(numpy.array([resampled_scanner_trajectory_c, resampled_scanner_trajectory_r]))
        self.trajectory_on_meanimage = imaged.draw_on_meanimage(generic.horizontal_flip_array_image(generic.vertical_flip_array_image(self.meanimage*255)),  origin, scale, scanner_trajectory = resampled_scanner_trajectory)
        self.trajectory_on_meanimage = generic.vertical_flip_array_image(self.trajectory_on_meanimage)
        #enable blending to display transparent objects
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.image_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        height = 100.0
        vertices = []
        xy_scan_vertices = [
                            origin['col'][0], origin['row'][0], 
                            origin['col'][0] + scale['col'][0] * self.meanimage.shape[1], origin['row'][0]+ scale['row'][0] * self.meanimage.shape[0], 
                            ]
        self.meanimage_size = [xy_scan_vertices[2], xy_scan_vertices[3]]
        vertices.extend([
                         [xy_scan_vertices[0], xy_scan_vertices[1], 0], 
                         [xy_scan_vertices[0], xy_scan_vertices[3], 0], 
                         [xy_scan_vertices[2], xy_scan_vertices[3], 0], 
                         [xy_scan_vertices[2], xy_scan_vertices[1], 0], 
                         ])
        for i in range(scanner_trajectory.shape[0]):
            if i != scanner_trajectory.shape[0] - 1:
                vector = [scanner_trajectory[i]['col'], scanner_trajectory[i]['row'], scanner_trajectory[i+1]['col'], scanner_trajectory[i+1]['row']]
            else:
                vector = [scanner_trajectory[i]['col'], scanner_trajectory[i]['row'], scanner_trajectory[0]['col'], scanner_trajectory[0]['row']]
            vertices.extend([
                                     [vector[0], vector[1], -0.5*height], 
                                     [vector[2], vector[3], -0.5*height], 
                                     [vector[2], vector[3], 0.5*height], 
                                     [vector[0], vector[1], 0.5*height],
                                     ])
        self.vertices = numpy.round(numpy.array(vertices), 0)
                                
    def user_keyboard_handler(self, key_pressed):
        pass
    
    def draw_scene(self):
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(self.vertices)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, self.meanimage.shape[1], self.meanimage.shape[0], 0, GL_RGB, GL_FLOAT, self.meanimage)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        texture_coordinates = numpy.array(
                             [
                             [1.0, 1.0],
                             [1.0, 0.0],
                             [0.0, 0.0],
                             [0.0, 1.0],
                             ])
                                     
        glTexCoordPointerf(texture_coordinates)
        
        glColor4fv((1.0, 1.0, 1.0,  1.0))
        glDrawArrays(GL_POLYGON, 0, 4)
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        
        number_of_faces = self.vertices.shape[0]/4-1
        for i in range(0, number_of_faces):
            r = 1.0
            g = 1.0
            b = 0.0
            alpha = 0.4
            glColor4fv((r, g, b,  alpha))
            glDrawArrays(GL_POLYGON, i*4+4, 4)
        glDisableClientState(GL_VERTEX_ARRAY)
        path_2d = os.path.join(self.config.CAPTURE_PATH, os.path.split(self.filename)[1].replace('.hdf5', '{0:0.0f}_{1:1.0f}_2d.png'.format(self.meanimage_size[0], self.meanimage_size[1])))
        path_3d = os.path.join(self.config.CAPTURE_PATH, os.path.split(self.filename)[1].replace('.hdf5', '{0:0.0f}_{1:1.0f}_3d.png'.format(self.meanimage_size[0], self.meanimage_size[1])))
        for p in [path_2d, path_3d]:
            if os.path.exists(p):
                os.remove(p)
        self.run_loop = False
        self.save_frame(path_3d)
        Image.fromarray(numpy.cast['uint8'](self.trajectory_on_meanimage)).save(path_2d)

def visualize_xz_scan(filename):
    config = RibbonScanVisualizeConfig()
    g = RibbonScanScene(config, graphics_mode = 'standalone', filename = filename)
    g.run()
    g.close_screen()

if __name__=='__main__':
    files = ['/mnt/databu0/20121031/fragment_xz_maste_middle_310112_-9_0_-130.0_MovingGratingNoMarching_1351702018_0.hdf5']
    #basepath = "/mnt/databig/data/"
    #dirs,  files = fileop.find_files_and_folders(basepath,  extension = 'hdf5', filter = 'fragmeent_xz')
    for f in files:
        if "fragment_xz" in f:
            try:
                print f
                visualize_xz_scan(f)
                break
            except Exception as e:
                print  f
                print e
                pass
#            break
