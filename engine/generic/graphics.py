import time
import os.path
import numpy
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
    import pygame
    default_text=GLUT_BITMAP_TIMES_ROMAN_24
except ImportError:
    print 'opengl or pygame not intalled'
    default_text=None

from PIL import Image
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import geometry

DISPLAY_FRAME_RATE = False
DISPLAY_FRAME_DELAY = False

def get_screen_size():
    import platform
    if platform.system() == 'Windows':
        import ctypes
        user32 = ctypes.windll.user32
        return utils.cr((user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)))
    elif platform.system() == 'Linux':
        import gtk
        window = gtk.Window()
        screen = window.get_screen()
        return utils.cr((screen.get_width(),screen.get_height()))
    

class Screen(object):
    """
    Use cases:
    - Standalone, interactive applications with animation
    - Visual stimulation with external control loop
    - Generating single frame (for development purposes)
    
    Functionalities:
    - Maintain and watch frame rate
    - Helper functions: display text, image
    - 
    """
    def __init__(self, configuration, screen_resolution = None, graphics_mode = 'single_frame', init_mode = 'create_screen'):
        """
        The following actions are performed:
        (- Calculates pixel scaling parameters based on coordinate system type)
        - Creates screen
        - Set background color
        - Scales screen
        
        graphics_mode:
        - standalone - interactive, standalone graphics applications
        - external - control loop is implemented externally. flip has to be called separately
        - single_frame - shows a single frame while key is pressed or for a certain time
        
        Expected configurations:
        - SCREEN_RESOLUTION
        - FULLSCREEN
        - SCREEN_EXPECTED_FRAME_RATE
        - BACKGROUND_COLOR
        - FRAME_WAIT_FACTOR
        - COORDINATE_SYSTEM
        or
        - ORIGO
        - HORIZONTAL_AXIS_POSITIVE_DIRECTION
        - VERTICAL_AXIS_POSITIVE_DIRECTION        
        
        
        Future: GAMMA, TEXT_COLOR
        """
        if screen_resolution is None:
            self.screen_resolution = configuration.SCREEN_RESOLUTION
        else:
            self.screen_resolution = screen_resolution
        self.init_mode = init_mode
        self.config = configuration
        self.mode = graphics_mode
        self.position = [0.0, 0.0, 0.0]
        self.heading = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.scale = 1.0
        self.position_step = 10.0
        self.angle_step = 10.0
        self.scale_step = 0.05
        self.init_flip_variables()
        if self.init_mode == 'create_screen':
            glutInit()
            #create screen using parameters in config
            self.create_screen()
            if self.config.SCREEN_MODE != 'psychopy':
                #setting background color to clear color
                glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
                glEnable(GL_DEPTH_TEST)
                self.scale_screen()
        self.image_texture_id = glGenTextures(1)
        self.initialization()
        
    def init_flip_variables(self):
        self.flip_time = time.time()
        self.flip_time_previous = self.flip_time
        self.frame_times=[]
        self.frame_rate = 0.0
        self.wait_time_left = 0.0
        self.elapsed_time = 0.0
        #frame wait time calculation
        self.frame_wait_time = self.config.FRAME_WAIT_FACTOR * 1.0 / self.config.SCREEN_EXPECTED_FRAME_RATE - self.config.FLIP_EXECUTION_TIME

        if self.config.OS == 'Linux':
            self.clock = pygame.time.Clock()
        
    def create_screen(self):
        '''
        Create pygame screen using SCREEN_RESOLUTION and FULLSCREEN parameters
        '''
        if self.config.SCREEN_MODE=='psychopy':
            self.create_psychopy_screen()
        elif self.config.SCREEN_MODE=='pygame':
            if not self.config.FULLSCREEN:
                import os
                os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self.config.SCREEN_POSITION['col'],self.config.SCREEN_POSITION['row'])
            flags = pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL
            if self.config.FULLSCREEN:            
                flags = flags | pygame.FULLSCREEN
            self.screen = pygame.display.set_mode((self.screen_resolution['col'], self.screen_resolution['row']), flags)
            pygame.display.set_caption(utils.get_window_title(self.config))
    #            glxext_arb.glXSwapIntervalSGI(0)
            #Hide mouse cursor
            pygame.mouse.set_visible(not self.config.FULLSCREEN)
            self.clock = pygame.time.Clock()
    #        elif self.window_type == 'pyglet':
    #            if self.config.FULLSCREEN:
    #                self.screen = pyglet.window.Window(fullscreen = self.config.FULLSCREEN, 
    #                                                vsync = True)
    #            else:
    #                self.screen = pyglet.window.Window(self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'], fullscreen = self.config.FULLSCREEN, 
    #                                                vsync = True)
    #            self.screen.set_mouse_visible(False)

    def create_psychopy_screen(self):
        from psychopy import visual
        kwargs={'size':(self.screen_resolution['col'],self.screen_resolution['row']), 'fullscr' :self.config.FULLSCREEN, 'screen':0, 'allowGUI':False, 'allowStencil':False,
             'color':[-1,-1,-1], 'colorSpace':'rgb','blendMode':'avg'}
        if self.config.PSYCHOPY_MONITOR_NAME!=None:
            kwargs['monitor']=self.config.PSYCHOPY_MONITOR_NAME
        self.screen = visual.Window(**kwargs)
        
    def close_screen(self):
        if self.config.SCREEN_MODE=='psychopy':
            self.screen.close()
        elif self.config.SCREEN_MODE=='pygame':
            pygame.quit()
        
    def __del__(self):
        if self.init_mode == 'create_screen':
            self.close_screen()
        
    def run(self):
        """
        Main loop for updating screen.
        """        
        if self.mode == 'single_frame':
            self.set_viewpoint(self.position,  self.heading,  self.roll, self.pitch)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_scene()
            self.flip()
            wait = True
            while wait:
                for event in pygame.event.get():
                    if event.type == 5 or event.type == 6:
                        wait = False
        elif self.mode == 'standalone':
            self.run_loop = True
            while self.run_loop:
                glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                #default view is set
                self.set_view((0, 0, 0), 0, 0, 0, 1.0)
                #glDisable(GL_LIGHTING) if light is enabled
                self.render_before_set_view()
                self.set_view(self.position,  self.heading,  self.roll, self.pitch, self.scale)
                self.draw_scene()
                self.flip()
                for event in pygame.event.get():
                    if event.type == 5 or event.type == 6:
                        self.run_loop = False
                    if event.type == pygame.KEYDOWN:
                        key_pressed = pygame.key.name(event.key)
                        if key_pressed == 'escape':
                            self.run_loop = False
                        self.keyboard_handler(key_pressed)
        elif self.mode == 'external':
            pass
    
    def flip(self):
        '''
        Flips screen buffers in a timed way to maintain expected frame rate. before_flip and after_flip are placeholders for user specific functions that should 
        be executed synchronized to flipping
        self.frame_rate is calculated here. Wait time before flip is calculated by considering elapsed time since last flip and frame_wait_time that describes the 
        required frame rate
        '''
        self.before_flip()
        #TODO: mac needs the delay
        if hasattr(self.config, 'INSERT_FLIP_DELAY') and self.config.INSERT_FLIP_DELAY:
           if self.config.ALTERNATIVE_TIMING:
               next_flip_time = self.flip_time_previous + 1.0 / self.config.SCREEN_EXPECTED_FRAME_RATE            
               while True:
                   if next_flip_time <= time.time():
                       break
           else:
               self.elapsed_time = time.time() - self.flip_time_previous
               self.wait_time_left = self.frame_wait_time - self.elapsed_time
               if self.wait_time_left > 0.0:
                   time.sleep(self.wait_time_left)
        if not self.config.STIMULUS2MEMORY:
            if self.config.OS == 'Linux':
                self.clock.tick(self.config.SCREEN_EXPECTED_FRAME_RATE)
#            count = ctypes.c_uint()
#            glxext_arb.glXGetVideoSyncSGI(ctypes.byref(count))
#            glxext_arb.glXWaitVideoSyncSGI(0, 0, ctypes.byref(count))
            
#            if hasattr(self,  'prev'):
#                self.diff.append(count.value-self.prev)
#            else:
#                self.diff = []
#            self.prev = count.value
            
#            glxext_arb.glXWaitVideoSyncSGI(2, (count.value+1)%2, ctypes.byref(count))
            if self.config.SCREEN_MODE=='psychopy':
                self.screen.flip()
            elif self.config.SCREEN_MODE=='pygame':
                pygame.display.flip()

#        elif window_type == 'pyglet':
#            self.screen.flip()
        self.flip_time = time.time()
        if self.flip_time - self.flip_time_previous != 0.0:
            self.frame_rate = 1.0 / (self.flip_time - self.flip_time_previous)
        else:
            self.frame_rate = self.config.SCREEN_EXPECTED_FRAME_RATE
        self.after_flip()
        self.flip_time_previous = self.flip_time
        self.frame_times.append(self.flip_time)
        
        if DISPLAY_FRAME_RATE:
            print self.frame_rate
        if DISPLAY_FRAME_DELAY:
            if abs(self.frame_rate - self.config.SCREEN_EXPECTED_FRAME_RATE) > 1.0:
                print abs(self.frame_rate - self.config.SCREEN_EXPECTED_FRAME_RATE)
        if self.config.ENABLE_FRAME_CAPTURE and self.start_frame_capture:
            if hasattr(self.config, 'CAPTURE_FORMAT'):
                fileformat = self.config.CAPTURE_FORMAT
            else:
                fileformat = 'png'
            self.save_frame(os.path.join(self.config.CAPTURE_PATH,  'captured_{1:0=10}.{0}'.format(fileformat, self.captured_frame_counter)))
            self.captured_frame_counter+=1
        if self.config.STIMULUS2MEMORY:
            if not hasattr(self, 'stimulus_bitmaps'):
                self.stimulus_bitmaps = []
            self.stimulus_bitmaps.append(self.get_frame())
        
    def scale_screen(self):
        '''
        Set projection matrix according to HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION parameters.
        Set viewport according to screen resolution and origo.
        
        !!! Only orthographic projection is supported this time !!!
        '''
        glMatrixMode (GL_PROJECTION)
        glLoadIdentity()
        left = -0.5 * self.screen_resolution['col']
        right = 0.5 * self.screen_resolution['col']
        bottom = 0.5 * self.screen_resolution['row']
        top = -0.5 * self.screen_resolution['row']
        
        if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'left':
            left = left * -1.0 + self.config.ORIGO['col']
            right = right * -1.0 + self.config.ORIGO['col']
        elif self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
            left = left - self.config.ORIGO['col']
            right = right - self.config.ORIGO['col']
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
            top = top * -1.0 - self.config.ORIGO['row']
            bottom = bottom * -1.0 - self.config.ORIGO['row']
        elif self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
            top = top + self.config.ORIGO['row']
            bottom = bottom + self.config.ORIGO['row']
        
        z_range = max(self.screen_resolution['row'], self.screen_resolution['col'])
        glOrtho(left, right, bottom, top,  -z_range, z_range)
                
        #set viewport according to ORIGO parameter
#         lower_left_corner_x = self.config.ORIGO['col']
#         lower_left_corner_y = self.config.ORIGO['row']
#         glViewport(lower_left_corner_x, lower_left_corner_y, self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'])
  
        
    def clear_screen(self, color = None):
        #clears screen to color
        if color is not None:
            glClearColor(color[0], color[1], color[2], 0.0)
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
    def set_view(self, position,  heading,  roll, pitch, scale):
        '''
        Sets viewing by translating and rotating model.
        '''        
        glMatrixMode (GL_MODELVIEW)
        glLoadIdentity()
        glScalef(scale,  scale, scale)
        glRotatef(roll,  0.0, 0.0, 1.0)
        glRotatef(pitch, 1.0, 0.0, 0.0)
        glRotatef(heading, 0.0, 1.0, 0.0)
        glTranslatef(position[0],  position[1],  position[2])
        
    def initialization(self):
        self.start_frame_capture=False
        self.captured_frame_counter=0
        
    def render_text(self, text, color = (1.0,  1.0,  1.0), position = utils.rc((0.0, 0.0)),  text_style = default_text):
        '''
        Renders text on screen using times new roman characters. Spacing is a constant 12 pixels, so shorter characters like 'l' is diplayed with a little gap
        '''
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        if len(color) == 3:
            glColor3fv(color)
        elif len(color) == 4:
            glColor4fv(color)
        line_index = 0
        row_index = 0
        for i in range(len(text)):
            if text_style == GLUT_BITMAP_TIMES_ROMAN_24:
                spacing = 14
            elif text_style == GLUT_BITMAP_TIMES_ROMAN_10:
                spacing = 8
            elif text_style == GLUT_BITMAP_9_BY_15:
                spacing = 15
            elif text_style == GLUT_BITMAP_8_BY_13:
                spacing = 13
            if text[i] == '\n':
                if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
                    line_index += 1
                elif self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
                    line_index -= 1
                row_index = 0
            else:                
                glRasterPos2f(position['col'] + spacing * row_index, position['row'] - line_index * spacing)
                glutBitmapCharacter(text_style, ord(text[i]))
                row_index += 1
                
        #Restore original color
        glColor4fv(current_color)
        
    def render_imagefile(self, path, position = utils.rc((0, 0)), stretch=1.0):
        '''
        Renders an image file on screen with its original size.
        '''
        im = Image.open(path)
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION=='down':
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
        image = (numpy.cast['float'](numpy.asarray(im))/255.0)
        if image.shape[2]>3:
            mask=numpy.where(image[:,:,3]>0, True, False)[:,:,numpy.newaxis]
            image=image[:,:,:3]* mask
        self.render_image(image, position = position, stretch=stretch,position_in_pixel=False)
        return image
        
    def render_image(self,image, position = utils.rc((0, 0)), stretch=1.0,position_in_pixel=False):
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        scale = 1.0 if position_in_pixel else self.config.SCREEN_UM_TO_PIXEL_SCALE
        vertices = numpy.array([
                                [position['col']*scale + 0.5 * image.shape[1]*stretch, position['row']*scale - 0.5 * image.shape[0]*stretch],
                                [position['col']*scale + 0.5 * image.shape[1]*stretch, position['row']*scale + 0.5 * image.shape[0]*stretch],
                                [position['col']*scale - 0.5 * image.shape[1]*stretch, position['row']*scale + 0.5 * image.shape[0]*stretch],
                                [position['col']*scale - 0.5 * image.shape[1]*stretch, position['row']*scale - 0.5 * image.shape[0]*stretch],
                                ])
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        dt = GL_FLOAT
#        dt = GL_UNSIGNED_BYTE
        glTexImage2D(GL_TEXTURE_2D, 0, 3, image.shape[1], image.shape[0], 0, GL_RGB, dt, image)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
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
        glColor3fv((1.0,1.0,1.0))
        glDrawArrays(GL_POLYGON,  0, 4)
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)        
        
    def create_texture(self):
        pass
        
    def save_frame(self, path):
        '''
        Saves actual frame in frame buffer to an image file
        '''
        pixels = glReadPixels(0, 0, self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'],  GL_RGB, GL_UNSIGNED_BYTE)        
        try:
            frame = Image.fromstring('RGB', (self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']), pixels)
        except:
            frame = Image.frombytes('RGB', (self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']), pixels)
            
        frame = frame.transpose(Image.FLIP_TOP_BOTTOM)
        frame.save(path)
        
    def get_frame(self):
        pixels = glReadPixels(0, 0, self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'],  GL_RGB, GL_UNSIGNED_BYTE)        
        frame = Image.fromstring('RGB', (self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']), pixels)
        frame = frame.transpose(Image.FLIP_TOP_BOTTOM)
        return numpy.asarray(frame)
        
    def cuboid_vertices(self, sizes):
        vertices = numpy.array([
                                [sizes[0], sizes[1], sizes[2]],
                                [-sizes[0], sizes[1], sizes[2]],
                                [-sizes[0], sizes[1], -sizes[2]],
                                [sizes[0], sizes[1], -sizes[2]],
                                [sizes[0], -sizes[1], sizes[2]],
                                [-sizes[0], -sizes[1], sizes[2]],
                                [-sizes[0], -sizes[1], -sizes[2]],
                                [sizes[0], -sizes[1], -sizes[2]],                                
                               ])
        vertices = 0.5 * vertices
        vertices = numpy.array([
                                vertices[0], vertices[1], vertices[2], vertices[3], 
                                vertices[0], vertices[1], vertices[5], vertices[4], 
                                vertices[1], vertices[2], vertices[6], vertices[5],
                                vertices[4], vertices[5], vertices[6], vertices[7], 
                                vertices[0], vertices[3], vertices[7], vertices[4], 
                                vertices[2], vertices[3], vertices[7], vertices[6]
                                ])
        
        return vertices
    #Placeholder functions that user can overdefine
    def render_before_set_view(self):        
        #placeholder for graphics items that shall not be translated or rotated by user when viewport is adjusted
        pass
        
    def before_flip(self):
        pass
        
    def after_flip(self):
        pass
    
    def draw_scene(self):
        pass
        
    #Additional helper functions
    def print_viewing_parameters(self):
        print self.position,  self.heading,  self.roll, self.pitch
        
    def keyboard_handler(self, key_pressed):
        '''
        Watches keyboard and modifies position, heading, roll and pitch of model
        '''        
        if key_pressed == 'up':
            self.position[1] = self.position[1] + self.position_step
        elif key_pressed == 'down':
            self.position[1] = self.position[1] - self.position_step
        if key_pressed == 'right':
            self.position[0] = self.position[0] + self.position_step
        elif key_pressed == 'left':
            self.position[0] = self.position[0] - self.position_step
        elif key_pressed == 'page up':
            self.position[2] = self.position[2] + self.position_step
        elif key_pressed == 'page down':
            self.position[2] = self.position[2] - self.position_step
        elif key_pressed == 'q':
            self.heading = self.heading + self.angle_step
        elif key_pressed == 'w':
            self.heading = self.heading - self.angle_step
        elif key_pressed == 'a':
            self.roll = self.roll + self.angle_step
        elif key_pressed == 's':
            self.roll = self.roll - self.angle_step
        elif key_pressed == 'z':
            self.pitch = self.pitch + self.angle_step
        elif key_pressed == 'x':
            self.pitch = self.pitch - self.angle_step
        elif key_pressed == '1':
            if self.scale > 0.0:
                self.scale = self.scale - self.scale_step            
        elif key_pressed == '2':
            self.scale = self.scale + self.scale_step
        elif key_pressed == '3':
            self.save_frame(fileop.generate_filename(self.config.CAPTURE_PATH + os.sep + 'capture.bmp'))
            print 'frame saved'
        self.user_keyboard_handler(key_pressed)
        
    def user_keyboard_handler(self, key_pressed):
        pass

    def draw_L(self, size,position):
        '''
        size: the longer side of the L
        '''
        width = 0.25*size
        lenght1=size
        lenght2=0.5 * size
        vertices = numpy.array([
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + lenght1 - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + lenght1 - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + lenght2 - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + lenght2 - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width],
                                
                                
                                ])
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glDrawArrays(GL_POLYGON,  0, 6)
        glDisableClientState(GL_VERTEX_ARRAY)
        
    def draw_circle(self, size, position):
        vertices=geometry.circle_vertices(size,  resolution = 1.0, pos = (position['row'],position['col']))
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glDrawArrays(GL_POLYGON,  0, vertices.shape[0])
        glDisableClientState(GL_VERTEX_ARRAY) 
        
    def draw_square(self, size,position):
        width = size
        vertices = numpy.array([
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width],
                                [position['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE - 0.5 * width, 
                                    position['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE + 0.5 * width],
                                
                                
                                
                                ])
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glDrawArrays(GL_POLYGON,  0, 6)
        glDisableClientState(GL_VERTEX_ARRAY) 
        
def check_keyboard():
    '''
    Get pressed key
    '''        
    keys_pressed = []
    try:
        events=pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                key_pressed = pygame.key.name(event.key)
                keys_pressed.append(key_pressed)
    except:
        from psychopy import event
        keys_pressed = event.getKeys()
    return keys_pressed
    
def is_key_pressed(key):
    return key in check_keyboard()
    
def is_valid_frame_rate(fps_requested, fps_machine,threshold=0.1):
    trequested=1.0/fps_requested
    tmachine=1.0/fps_machine
    frac=numpy.modf(trequested/tmachine)[0]
    if frac>0.5:
        frac=1-frac
    return frac<threshold

if __name__ == "__main__": 
    pass
    
