import os.path
import os
import numpy
import math

import time
import Image

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import visexpman.engine.generic.parametric_control
import visexpman.users.zoltan.test.stimulus_library_test_data
from visexpman.engine.generic import utils
import command_handler

class Stimulations(command_handler.CommandHandler):
    """
    Contains all the externally callable stimulation patterns:
    1. show_image(self,  path,  duration = 0,  position = (0, 0),  formula = [])
    """
    def __init__(self,  config,  caller,  experiment_control_dependent = True):
        self.config = config
        self.caller = caller
        self.experiment_control_dependent = experiment_control_dependent
        self.screen = caller.screen_and_keyboard
#        self.stimulation_control = stimulation_control
#        self.parallel = parallel        
        
        #self.image = psychopy.visual.SimpleImageStim(self.screen,  image = self.config.DEFAULT_IMAGE_PATH)         
        #self.shape = psychopy.visual.ShapeStim(self.screen)
        #self.inner_circle = psychopy.visual.ShapeStim(self.screen)
        
        #self.checkerboard = psychopy.visual.PatchStim(self.screen,  tex = default_texture)
        self.grating_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.grating_texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        #self.image_list = psychopy.visual.PatchStim(self.screen,  tex = default_texture)
#        self.backgroundColor = utils.convert_color(self.config.BACKGROUND_COLOR)        
        
        self.delayed_frame_counter = 0 #counts how many frames were delayed
        self.log_on_flip_message = ''
        self.elapsed_time = 0.0
        
        self.text_on_stimulus = []
        
        #Command buffer for keyboard commands during experiment
        self.command_buffer = ''
        #Abort command received signalling
        self.abort = False        
        
        #self.test_message = psychopy.visual.TextStim(self.screen,  text = '',  pos = (0, 0),  color = self.config.TEXT_COLOR,  height = self.config.TEXT_SIZE)        
        
#        if self.config.ENABLE_PARALLEL_PORT:
#            import parallel
#            self.bitmask = 0
        
    #Helper functions for showing stimulus
#    def _show_stimulus(self,  duration, stimulus, flip = True):
#        """
#        This function shows the stimulus on the display for the required time. 
#        TBD        
#        
#        """        
#        if duration == 0.0:            
#            if isinstance(stimulus, list):
#                for stimulus_item in stimulus:                    
#                    stimulus_item.draw()
#            else:
#                stimulus.draw()
#            if flip == True:
#                self._flip(trigger = True)
#        else:
#            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):
#                if isinstance(stimulus, list):
#                    for stimulus_item in stimulus:
#                        stimulus_item.draw()
#                else:
#                    stimulus.draw()
#                if i == 0:
#                    self._flip(trigger = True)
#                else:
#                    self._flip(trigger = False)
##                if self.stimulation_control.abort_stimulus():                    
##                    break        
    
    def _flip(self,  trigger = False,  saveFrame = False):
        """
        Flips screen buffer. Additional operations are performed here: saving frame and generating trigger
        """        
        current_texture_state =glGetBooleanv(GL_TEXTURE_2D)
        if current_texture_state:
            glDisable(GL_TEXTURE_2D)
        self._show_text()
        if current_texture_state:
            glEnable(GL_TEXTURE_2D)
            
        self.screen.flip()
        self.flip_time = time.time()
        frame_rate_deviation = abs(self.screen.frame_rate - self.config.SCREEN_EXPECTED_FRAME_RATE)
        if frame_rate_deviation > self.config.FRAME_DELAY_TOLERANCE:
            self.delayed_frame_counter += 1
            frame_rate_warning = ' %2.2f' %(frame_rate_deviation)            
        else:
            frame_rate_warning = ''
        if self.experiment_control_dependent:
            # If this library is not called by an experiment class which is called form experiment control class, no logging shall take place            
            self.elapsed_time = self.flip_time -  self.caller.experiment_control.start_time
            self.log.info('%2.2f\t%s'%(self.screen.frame_rate,self.log_on_flip_message + frame_rate_warning))       
        if trigger:
            self._frame_trigger_pulse()
            
        #Keyboard commands
        command = self.screen.experiment_user_interface_handler() #Here only commands with running experiment domain are considered
        if command != None:
            self.command_buffer += self.parse(command)
            if self.command_buffer.find('abort_experiment') != -1:
                self.command_buffer = self.command_buffer.replace('abort_experiment', '')
                self.caller.experiment_control.log.info('Abort pressed')
                self.abort = True

    def _frame_trigger_pulse(self):
        '''
        Generates frame trigger pulses
        '''
        if self.experiment_control_dependent:
            self.parallel_port.set_data_bit(self.config.FRAME_TRIGGER_PIN, 1, log = False)
            time.sleep(self.config.FRAME_TRIGGER_PULSE_WIDTH)
            self.parallel_port.set_data_bit(self.config.FRAME_TRIGGER_PIN, 0, log = False)
        
    def _show_text(self):
        '''
        Overlays on stimulus all the added text configurations
        '''
        if self.config.ENABLE_TEXT:
            for text_config in self.text_on_stimulus:
                if text_config['enable']:
                    self.screen.render_text(text_config['text'], color = text_config['color'], position = text_config['position'],  text_style = text_config['text_style'])
    
    #== Public, helper functions ==
    def set_background(self,  color):
        '''
        Set background color. Call this when a visual pattern should have a different background color than config.BACKGROUND_COLOR
        '''
        color_to_set = utils.convert_color(color)
        glClearColor(color_to_set[0], color_to_set[1], color_to_set[2], 0.0)
        
    def add_text(self, text, color = (1.0,  1.0,  1.0), position = utils.rc((0.0, 0.0)),  text_style = GLUT_BITMAP_TIMES_ROMAN_24):
        '''
        Adds text to text list
        '''
        text_config = {'enable' : True, 'text' : text, 'color' : utils.convert_color(color), 'position' : position, 'text_style' : text_style}
        self.text_on_stimulus.append(text_config)
        
    def change_text(self, id, enable = None, text = None, color = None, position = None,  text_style = None):
        '''
        Changes the configuration of the text pointed by id. id is the index of the text_configuration in the text_on_stimulus stimulus list
        '''
        text_config = self.text_on_stimulus[id]
        if enable != None:
            text_config['enable'] = enable
        if text != None:
            text_config['text'] = text
        if color != None:
            text_config['color'] = utils.convert_color(color)
        if position != None:
            text_config['position'] = position
        if text_style != None:
            text_config['text_style'] = text_style        
        self.text_on_stimulus[id]
        
    def disable_text(self, id = None):
        '''
        Disables the configuration of the text pointed by id. id is the index of the text_configuration in the text_on_stimulus stimulus list
        '''
        if id == None:
            index = -1
        else:
            index = id
        self.text_on_stimulus[index]['enable'] = False


    #== Various visual patterns ==
    
    def show_fullscreen(self, duration = 0.0,  color = None, flip = True):
        '''
        duration: 0.0: one frame time, -1.0: forever, any other value is interpreted in seconds        
        '''
        
        if color == None:
            color_to_set = self.config.BACKGROUND_COLOR
        else:
            color_to_set = utils.convert_color(color)
        self.log_on_flip_message_initial = 'show_fullscreen(' + str(duration) + ', ' + str(color_to_set) + ')'
        self.log_on_flip_message_continous = 'show_fullscreen'
        self.screen.clear_screen(color = color_to_set)
        if duration == 0.0:
            self.log_on_flip_message = self.log_on_flip_message_initial
            if flip:
                self._flip(trigger = True)
        elif duration == -1.0:
            i = 0
            while not self.abort:
                if i == 0:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                elif i == 1:
                    self.screen.clear_screen(color = color_to_set)
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                if flip:
                    self._flip(trigger = True)
                i += 1
        else:
            for i in range(int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)):
                if i == 0:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                elif i == 1:
                    self.screen.clear_screen(color = color_to_set)
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                if flip:
                    self._flip(trigger = True)
                if self.abort:
                    self.abort = False
                    break
                    
        #set background color to the original value
        glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
                
    def show_image(self,  path,  duration = 0,  position = utils.rc((0, 0)),  size = None, flip = True):
        '''
        Two use cases are handled here:
            - showing individual image files
                duration: duration of showing individual image file
                path: path of image file
            - showing the content of a folder
                duration: duration of showing each image file in folder
                path: path of folder containing images
        position: position of image on screen in pixels. This can be controlled by parameters and a formula when images in a folder are shown
        
        If duration is 0, then each image will be shown for one display update time. 
        Otherwise duration shall be the multiple of 1/SCREEN_EXPECTED_FRAME_RATE to avoid dropped frames            
        
        Usage:
            Show a single image which path is image_path for 1 second in a centered position:
                show_image(image_path,  duration = 1.0,  position = (0, 0))
            Play the content of a directory (directory_path) which contains image files. Each imag is shown for one frame time :
                show_image(directory_path,  duration = 0,  position = (0, 0))
            Play the content of a directory (directory_path) which contains image files and the position of the image is  the function of time and some parameters:
                parameters = [100.0,  100.0]
                formula_pos_x = ['p[0] * cos(10.0 * t)',  parameters]
                formula_pos_y = ['p[1] * sin(10.0 * t)',  parameters]                
                formula = [formula_pos_x,  formula_pos_y]
                start_position = (10,10)
                show_image('directory_path',  0.0,  start_position,  formula)             
        '''
        self.screen.render_imagefile(path, position = position)
        if duration == 0.0:
            if flip:
                self._flip(trigger = True)        
        else:
            for i in range(int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)):
                if flip:
                    self._flip(trigger = True)
                if self.abort:
                    self.abort = False
                    break
        
#        position_p = (self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1])
#        if os.path.isdir(path) == True:
#            #when content of directory is to be shown
#            image_file_paths = os.listdir(path)
#            image_file_paths.sort()
#            #initialize parametric control
#            start_time = time.time()            
#            posx_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[0],  start_time)
#            posy_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[1],  start_time) 
#            
#            for image_file_path in image_file_paths:
#                if len(formula) > 0:
#                    #parametric control
#                    parametric_data_x = formula[0]
#                    parametric_data_y = formula[1]
#                    actual_time_tick = time.time()
#                    posx_parametric_control.update(value = None,  parameters = parametric_data_x[1],  formula = parametric_data_x[0],  time_tick = actual_time_tick)
#                    posy_parametric_control.update(value = None,  parameters = parametric_data_y[1],  formula = parametric_data_y[0],  time_tick = actual_time_tick)
#                    parametric_position =  (posx_parametric_control.value,  posy_parametric_control.value)
#                    self._show_image_file(path + os.sep + image_file_path,  duration,  parametric_position)
#                else:
#                    self._show_image_file(path + os.sep + image_file_path,  duration,  position)                    
#                    
#                if self.stimulation_control.abort_stimulus():
#                    break
#            
#        elif os.path.isfile(path) == True:
#            path_adjusted = path
#            #resize file
#            if size != None and size != (0,  0):                
#                stimulus_image = Image.open(path)
#                stimulus_image = stimulus_image.resize((int(size[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE), int(size[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)))
#                stimulus_image.save(self.config.TEMP_IMAGE_PTH)
#                path_adjusted = self.config.TEMP_IMAGE_PTH
#            
#            #initialize parametric control
#            start_time = time.time()            
#            posx_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[0],  start_time)
#            posy_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[1],  start_time)             
#            if len(formula) > 0:
#                #parametric control
#                for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):
#                    parametric_data_x = formula[0]
#                    parametric_data_y = formula[1] 
#                    actual_time_tick = time.time()
#                    posx_parametric_control.update(value = None,  parameters = parametric_data_x[1],  formula = parametric_data_x[0],  time_tick = actual_time_tick)
#                    posy_parametric_control.update(value = None,  parameters = parametric_data_y[1],  formula = parametric_data_y[0],  time_tick = actual_time_tick)
#                    parametric_position =  (posx_parametric_control.value,  posy_parametric_control.value)                
#                    self._show_image_file(path_adjusted, 0,  parametric_position)
#            else:            
#                #when a single image file is to be shown
#                self._show_image_file(path_adjusted, duration,  position)
#        else:
#            pass
#            #invalid path
#        
#
#    def _show_image_file(self,  path,  duration,  position, flip = True):
#        self.image.setPos((self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1]))        
#        self.screen.logOnFlip('_show_image_file(' + path + ', ' + str(duration) + ', ' + str(position) + ')',  psychopy.log.DATA)
#        if duration == 0:                                        
#                    self.image.setImage(path)
#                    self.image.draw()
#                    if flip:
#                    	self._flip(trigger = True)
#        else:
#            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):                    
#                    self.image.setImage(path)            
#                    self.image.draw()
#                    if i == 0:
#                        if flip:
#                            self._flip(trigger = True)
#                    else:
#                        if flip:
#                        	self._flip(trigger = False)
#                        
#                    
#    def show_movie(self,  video_file_path,  position = (0, 0)):
#        '''
#        Plays a movie file. Pressing 'a' aborts the playback. The video is positioned according to the value of position parameter
#        Parametric control of position is no possible. Some frames are always dropped.
#        '''        
#        position_p = (self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1])
#        self.movie = psychopy.visual.MovieStim(self.screen,  filename = video_file_path,  pos = position_p) 
#        msg = 'video size: ' + str(self.movie.format.height) + ', ' + str(self.movie.format.width)
#        psychopy.log.data(msg)
#        globalClock = psychopy.core.Clock()
#        frame_counter = 0
#        while globalClock.getTime() < self.movie.duration: 
#            self._flip() 
#            self._frame_trigger_pulse()
#            self.movie.draw()
#            frame_counter = frame_counter + 1
#            self.screen.logOnFlip(str(frame_counter) + ' show_movie(' + video_file_path +  ', ' + str(position) + ')', psychopy.log.DATA)            
#            if self.stimulation_control.abort_stimulus():
#                break

    def show_shape(self,  shape = '',  duration = 0.0,  pos = utils.rc((0,  0)),  color = [1.0,  1.0,  1.0],  background_color = None,  orientation = 0.0,  size = utils.rc((0,  0)),  ring_size = 1.0):
        '''
        This function shows simple, individual shapes like rectangle, circle or ring. It is shown for one frame time when the duration is 0. 
    
        '''        
        #Generate log messages
        self.log_on_flip_message_initial = 'show_shape(' + str(shape)+ ', ' + str(duration) + ', ' + str(pos) + ', ' + str(color)  + ', ' + str(background_color)  + ', ' + str(orientation)  + ', ' + str(size)  + ', ' + str(ring_size) + ')'
        self.log_on_flip_message_continous = 'show_shape'        
        #Calculate number of frames
        n_frames = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        if n_frames == 0:
            n_frames = 1
        #convert um dimension parameters to pixel
        if isinstance(size, float) or isinstance(size, int):        
            size_pixel = utils.rc((size, size))        
        elif isinstance(size, numpy.ndarray):   
            size_pixel = size                
        else:
            raise RuntimeError('Parameter size is provided in an unsupported format')
        size_pixel = utils.rc_multiply_with_constant(size_pixel, self.config.SCREEN_PIXEL_TO_UM_SCALE)        
        pos_pixel = utils.rc_multiply_with_constant(pos, self.config.SCREEN_PIXEL_TO_UM_SCALE)        
        #Calculate vertices
        points_per_round = 360
        if shape == 'circle' or shape == '' or shape == 'o' or shape == 'c':
            shape_type = 'circle'
            vertices = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
        elif shape == 'rect' or shape == 'rectangle' or shape == 'r' or shape == '||':
            vertices = utils.rectangle_vertices(size_pixel, orientation = orientation)
            shape_type = 'rectangle'
        elif shape == 'annuli' or shape == 'annulus' or shape == 'a':
            vertices_outer_ring = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices_inner_ring = utils.calculate_circle_vertices([size_pixel['col'] - ring_size,  size_pixel['row'] - ring_size],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices = numpy.zeros(shape = (vertices_outer_ring.shape[0] * 2, 2))
            vertices[:vertices_outer_ring.shape[0]] = vertices_outer_ring
            vertices[vertices_outer_ring.shape[0]:] = vertices_inner_ring
            shape_type = 'annulus'            
        vertices = vertices + numpy.array([pos_pixel['col'], pos_pixel['row']])
        n_vertices = vertices.shape[0]

        #Set color
        glColor3fv(utils.convert_color(color))
        if background_color != None:
            background_color_saved = glGetFloatv(GL_COLOR_CLEAR_VALUE)
            converted_background_color = utils.convert_color(background_color)
            glClearColor(converted_background_color[0], converted_background_color[1], converted_background_color[2], 0.0)
        else:
            converted_background_color = utils.convert_color(self.config.BACKGROUND_COLOR)        
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        first_flip = False
        stop_stimulus = False
        start_time = time.time()
        for frame_i in range(n_frames):
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            if shape_type != 'annulus':
                glDrawArrays(GL_POLYGON,  0, n_vertices)
            else:
                n = int(n_vertices/2)                
                glColor3fv(utils.convert_color(converted_background_color))
                glDrawArrays(GL_POLYGON,  n, n)
                glColor3fv(utils.convert_color(color))
                glDrawArrays(GL_POLYGON,  0, n)
            #Make sure that at the first flip the parameters of the function call are logged
            if not first_flip:
                self.log_on_flip_message = self.log_on_flip_message_initial
                first_flip = True
            else:
                if time.time() - start_time > duration and duration >=1.0:
                    stop_stimulus = True
                    self.log_on_flip_message = self.log_on_flip_message_continous + ' Less frames shown.'
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
            if frame_i == 0:
                self._flip(trigger = True)
            else:
                self._flip(trigger = False)
            if self.abort:
                self.abort = False
                break
            if stop_stimulus:                
                break
                
        glDisableClientState(GL_VERTEX_ARRAY)        
        #Restore original background color
        if background_color != None:            
            glClearColor(background_color_saved[0], background_color_saved[1], background_color_saved[2], background_color_saved[3])
        
#                    
#    def show_checkerboard(self,   n_checkers,  duration = 0.0,  pos = (0,  0),  color = [],  box_size = (0, 0), flip = True):
#        '''
#        Shows checkerboard:
#            n_checkers = (x dir (column), y dir (rows)), above 32x32 config, frame drop may occur
#            pos - position of display area
#            color - array of color values. Each item corresponds to one box
#            box_size - size of a box in pixel   
#            duration - duration of stimulus in seconds            
#            color - array of color values. Each item corresponds to one box. 0 position is the top left box, the last one is the bottom right
#        Usage example:
#            n_checkers = (21, 21)
#            box_size = [80, 50]    
#            n_frames = 100    
#            cols = random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames) 
#            for i in range(n_frames):
#                self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols[i], box_size = box_size)
#        '''
#        
#        box_size_p = (box_size[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  box_size[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
#        pos_p = (pos[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  pos[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
#        
#        #check if number of boxes are the power of two
#        max_checker_number = max(n_checkers)
#        checker_number_two_log = math.log(max_checker_number,  2)
#        if checker_number_two_log != math.floor(checker_number_two_log) or  n_checkers[0] != n_checkers[1]:
#            new_size = int(2 ** math.ceil(checker_number_two_log))
#            n_checkers_fixed = (new_size,  new_size)
#        else:
#            n_checkers_fixed = n_checkers            
#        
#        #centerpoint is shifted, so an offset shall be calculated to move it back
#        x_offset = int((n_checkers_fixed[0] - n_checkers[0]) * box_size_p[0] * 0.5)
#        y_offset = int((n_checkers_fixed[1] - n_checkers[1]) * box_size_p[1] * 0.5)
#        pos_offset = (pos_p[0]  + x_offset,  pos_p[1]  - y_offset)
#            
#        self.screen.logOnFlip('show_checkerboard(' + str(n_checkers)+ ', ' + str(duration) + ', ' + str(pos) + ', ' + str(color[:self.config.MAX_LOG_COLORS])  + ', ' + str(box_size)  + ')',  psychopy.log.DATA) 
#        texture = Image.new('RGBA',  n_checkers_fixed) 
#        for row in range(n_checkers[1]):
#            for column in range(n_checkers[0]):            
#                texture.putpixel((column, row),  utils.convert_int_color(utils.convert_color_from_pp(utils.convert_color(color[row * n_checkers[0] + column]))))
#        
#        self.checkerboard.setPos(pos_offset)
#        self.checkerboard.setTex(texture) 
#        self.checkerboard.setSize((box_size_p[0] * n_checkers_fixed[0],  box_size_p[1] * n_checkers_fixed[1]))        
#        
#        self._show_stimulus(duration,  self.checkerboard, flip)
#
#    def show_ring(self,  n_rings, diameter,  inner_diameter = [],  duration = 0.0,  n_slices = 1,  colors = [],  pos = (0,  0), flip = True):
#        """
#        This stimulation shows concentric rings or circles. The rings/circles can be divided into pie slices.
#        n_rings: number of rings to be drawn
#        diameter: diameter' of outer rings. The followings are accepted:
#                    - list of integers: outer diameter of each rings
#                    - list of list of two integers: the two values determine the diameter in the x and y direction
#                    - single integer: diameter of first (innermost) ring. The diameter of additional rings will be the multiple of this value
#        inner_diameter: The following data types are accepted:
#                    - list of integers: inner diameter of each rings, assuming that diameter is a list
#                    - list of list of two integers: the two values determine the inner diameter in the x and y direction, assuming that diameter is a list
#                    - integer: width of rings regardless of the type of diameter
#        duration; duration of stimulus in second. If zero, stimulus is shown for one frame time
#        n_slices: number of slices displayed for each ring
#        colors: list of colors. The 0 place is the slice in the innermost circle, which angle range is between 0 and a positive number, for example in case of n_slices = 4, the angle range is 0, 90 for the 0. slice.
#        pos: center position of stimulus
#        
#        Use cases:
#        1) Show three concentrical circles for 1 second:
#            n_rings = 3
#            outer_diameter = [100, 120, 140]
#            show_ring(n_rings, outer_diameter,  duration = 1.0,  colors = colors)
#        2) Show rings 5 rings:
#            n_rings = 5
#            outer_diameter = 100
#            inner_diameter = 5 #width of ring
#            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  colors = colors)
#        3) Show sliced rings with arbitrary thickness and diameter
#            n_rings = 4
#            n_slices = 2
#            outer_diameter = [100, 200, 300]
#            inner_diameter = [90, 180, 250]
#            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  n_slices = 2, colors = colors)
#        4) Show oval rings
#            n_rings = 2
#            outer_diameter = [[100, 200], [200, 300]]
#            inner_diameter = [[90, 190], [190, 290]]
#            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  colors = colors)        
#        """        
#        self.screen.logOnFlip('show_rings(' + str(n_rings)+ ', ' + str(diameter) + ', ' + str(inner_diameter) + ', ' + str(duration)  + ', ' + str(n_slices)  + ', ' + str(colors[:self.config.MAX_LOG_COLORS])  + ', ' + str(pos)  + ')',  psychopy.log.DATA)
#        
#        pos_p = (pos[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  pos[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)        
#        outer_diameter = diameter       
#        
#        #sort diameter lists to avoid putting a bigger circle on a smaller one
#        if isinstance(outer_diameter, list):
#            outer_diameter.sort()
#            outer_diameter.reverse()
#        
#        if isinstance(inner_diameter, list):
#            inner_diameter.sort()
#            inner_diameter.reverse()        
#        
#        #if number of rings is not consistent with the number of provided list of diameter values
#        if isinstance(outer_diameter, list):
#            if n_rings != len(outer_diameter):
#                n_rings = len(outer_diameter)                    
#        
#        if isinstance(outer_diameter, list) and isinstance(inner_diameter, list):            
#            if len(inner_diameter) == 0 or (len(inner_diameter) != len(outer_diameter)):
#                inner_circles = False
#            else:
#                inner_circles = True
#                
#        elif isinstance(outer_diameter, list) and not isinstance(inner_diameter, list):            
#            new_inner_diameter = []
#            for diameter in outer_diameter:
#                if isinstance(diameter,  list):
#                    new_inner_diameter.append([diameter[0] - inner_diameter,  diameter[1] - inner_diameter])
#                else:
#                    new_inner_diameter.append(diameter - inner_diameter)
#            inner_diameter = new_inner_diameter
#            inner_circles = True
#        elif not isinstance(outer_diameter, list):
#            outer_diameter = numpy.linspace(outer_diameter,  n_rings * outer_diameter,  n_rings).tolist()
#            outer_diameter.reverse()
#            if isinstance(inner_diameter, list):
#                inner_circles = False
#            elif not isinstance(inner_diameter, list):
#                new_inner_diameter = []
#                for diameter in outer_diameter:
#                    new_inner_diameter.append(diameter - inner_diameter)
#                inner_diameter = new_inner_diameter                
#                inner_circles = True            
#        
#        slice_angle = 360.0 / n_slices        
#        self.ring = []
#        for ring in range(n_rings):
#            #diameter can be a list (ellipse) or a single integer (circle)            
#            if isinstance(outer_diameter[ring],  list):                
#                outer_r = [outer_diameter[ring][0]  * self.config.SCREEN_PIXEL_TO_UM_SCALE, outer_diameter[ring][1]  * self.config.SCREEN_PIXEL_TO_UM_SCALE]
#            else:
#                outer_r = (outer_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  outer_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE)                
#            
#            if inner_circles:
#                if isinstance(inner_diameter[ring],  list):
#                    inner_r = (inner_diameter[ring][0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  inner_diameter[ring][1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
#                else:                    
#                    inner_r = (inner_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  inner_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE)            
#            
#            for slice in range(n_slices):
#                start_angle = slice_angle * slice
#                end_angle = slice_angle * (slice + 1)
#                vertices = utils.calculate_circle_vertices(outer_r,  start_angle = start_angle,  end_angle = end_angle+1)               
#                
#                try:
#                    color = utils.convert_color(colors[(n_rings -1 - ring) * n_slices + slice])
#                except IndexError:
#                    color = (-1.0,  -1.0,  -1.0)
#                
#                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = color,  fillColor = color,  vertices =  vertices,  pos = pos_p))
#            if inner_circles:
#                vertices  = utils.calculate_circle_vertices(inner_r)
#                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = (-1.0,  -1.0,  -1.0),  fillColor = (-1.0,  -1.0,  -1.0),  vertices =  vertices,  pos = pos_p))
#                
#        self._show_stimulus(duration,  self.ring,  flip)
                    
    def show_grating(self, duration = 0.0,  profile = 'sqr',  white_bar_width =-1,  display_area = utils.cr((0,  0)),  orientation = 0,  starting_phase = 0.0,  velocity = 0.0,  color_contrast = 1.0,  color_offset = 0.5,  pos = utils.cr((0,  0)),  duty_cycle = 1.0,  noise_intensity = 0):
        """
        This stimulation shows grating with different color (intensity) profiles.
            - duration: duration of stimulus in seconds
            - profile: shape of grating color (intensity) profile, the followings are possible:
                - 'sqr': square shape, most common grating profile
                - 'tri': triangle profile
                - 'saw': sawtooth profile
                - 'sin': sine
                - 'cos': cosine
                profile parameter can be a list of these keywords. Then different profiles are applied to each color channel
            - white_bar_width: length of one bar in um (pixel)
            - display area
            - orientation: orientation of grating in degrees
            - starting_phase: starting phase of stimulus in degrees
            - velocity: velocity of the movement of grating in um/s
            - color_contrast: color contrast of grating stimuli. Can be a single intensity value of an rgb value. Accepted range: 0...1
            - color_offset: color (intensity) offset of stimulus. Can be a single intensity value of an rgb value. Accepted range: 0...1
            - pos: position of stimuli
            - duty_cycle: duty cycle of grating stimulus with sqr profile. Its interpretation is different from the usual: duty cycle tells how many times the spatial frequency is the width of the black stripe
            - noise_intensity: Maximum contrast of random noise mixed to the stimulus.
        
        Usage examples:
        1) Show a simple, fullscreen, grating stimuli for 3 seconds with 45 degree orientation
            show_grating(duration = 3.0, orientation = 45, velocity = 100, white_bar_width = 100)
        2) Show grating with sine profile on a 500x500 area with 10 degree starting phase
            show_grating(duration = 3.0, profile = 'sin', display_area = (500, 500), starting_phase = 10, velocity = 100, white_bar_width = 200)
        3) Show grating with sawtooth profile on a 500x500 area where the color contrast is light red and the color offset is light blue
            show_grating(duration = 3.0, profile = 'saw', velocity = 100, white_bar_width = 200, color_contrast = [1.0,0.0,0.0], color_offset = [0.0,0.0,1.0]) 
        """        
        if white_bar_width == -1:
            bar_width = self.config.SCREEN_RESOLUTION['col'] * self.config.SCREEN_PIXEL_TO_UM_SCALE
        else:
            bar_width = white_bar_width * self.config.SCREEN_PIXEL_TO_UM_SCALE
        #== Logging ==
        self.log_on_flip_message_initial = 'show_grating(' + str(duration)+ ', ' + str(profile) + ', ' + str(white_bar_width) + ', ' + str(display_area)  + ', ' + str(orientation)  + ', ' + str(starting_phase)  + ', ' + str(velocity)  + ', ' + str(color_contrast)  + ', ' + str(color_offset) + ', ' + str(pos)  + ')'
        self.log_on_flip_message_continous = 'show_grating'
        first_flip = False        
        
        #== Prepare ==
        orientation_rad = orientation * math.pi / 180.0
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
            orientation_rad *= -1
        if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'down':
            pass
            #TODO:
                
        pos_transformed = utils.rc_multiply_with_constant(pos, self.config.SCREEN_PIXEL_TO_UM_SCALE)        
            
        pos_adjusted = []
        pos_adjusted.append(pos_transformed['col'])
        pos_adjusted.append(pos_transformed['row'])
        
        if display_area['col'] == 0:
            screen_width = self.config.SCREEN_RESOLUTION['col'] * self.config.SCREEN_PIXEL_TO_UM_SCALE
        else:
            screen_width = display_area['col'] * self.config.SCREEN_PIXEL_TO_UM_SCALE
        display_area_adjusted = []
        display_area_adjusted.append(display_area['col'] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        display_area_adjusted.append(display_area['row'] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        display_area_adjusted = numpy.array(display_area_adjusted)
        
        pixel_velocity = -velocity * self.config.SCREEN_PIXEL_TO_UM_SCALE / float(self.config.SCREEN_EXPECTED_FRAME_RATE) / screen_width        
        
        #If grating are to be shown on fullscreen, modify display area so that no ungrated parts are on the screen considering rotation
        if display_area_adjusted[0] == 0:            
            display_area_adjusted[0] = self.config.SCREEN_RESOLUTION['col'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['row'] * abs(math.sin(orientation_rad))
            screen_width = self.config.SCREEN_RESOLUTION['col']
        if display_area_adjusted[1] == 0:            
            display_area_adjusted[1] = self.config.SCREEN_RESOLUTION['row'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['col'] * abs(math.sin(orientation_rad))
            
        #calculate vertices of display area
        #angles between diagonals
        alpha = numpy.arctan(display_area_adjusted[0]/display_area_adjusted[1])
        angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        angles = angles - orientation_rad
        diagonal = numpy.sqrt((display_area_adjusted **2).sum())
        vertices = 0.5 * diagonal * numpy.array([numpy.sin(angles), numpy.cos(angles)])
        vertices = vertices.transpose()
        vertices = vertices + numpy.array([pos_adjusted])
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        #== Generate grating profile        
        if isinstance(profile, str):
            profile_adjusted = [profile,  profile,  profile]            
        else:
            profile_adjusted = []
            for profile_i in profile:
                profile_adjusted.append(profile_i)
        
        #contrast and offset can be provided in rgb or intensity. For both the accepted range is 0...1.0
        if not isinstance(color_contrast, list) and not isinstance(color_contrast, tuple):
            color_contrast_adjusted = [color_contrast,  color_contrast,  color_contrast]
        else:
            color_contrast_adjusted = []
            for color_contrast_i in color_contrast:
                color_contrast_adjusted.append(color_contrast_i)
            
        if not isinstance(color_offset, list) and not isinstance(color_offset, tuple):
            color_offset_adjusted = [color_offset,  color_offset,  color_offset]
        else:
            color_offset_adjusted = []
            for color_offset_i in color_offset:
                color_offset_adjusted.append(color_offset_i)

        #calculate grating profile period from spatial frequency
        period = bar_width * (1.0 + duty_cycle)
        #modify profile length so that the profile will contain integer number of repetitions
        repetitions = numpy.ceil(display_area_adjusted[0]/period)
        profile_length = period * repetitions
        cut_off_ratio = display_area_adjusted[0]/profile_length
        profile_length = int(profile_length)

        waveform_duty_cycle = 1.0 - 1.0 / (1.0 + duty_cycle)
        stimulus_profile_r = utils.generate_waveform(profile_adjusted[0], profile_length, period, color_contrast_adjusted[0], color_offset_adjusted[0], starting_phase, waveform_duty_cycle)
        stimulus_profile_g = utils.generate_waveform(profile_adjusted[1], profile_length, period, color_contrast_adjusted[1], color_offset_adjusted[1], starting_phase, waveform_duty_cycle)
        stimulus_profile_b = utils.generate_waveform(profile_adjusted[2], profile_length, period, color_contrast_adjusted[2], color_offset_adjusted[2], starting_phase, waveform_duty_cycle)
        stimulus_profile = numpy.array([[stimulus_profile_r],  [stimulus_profile_g],  [stimulus_profile_b]])
        stimulus_profile = stimulus_profile.transpose()        
        
        #== Generate texture  
        texture = stimulus_profile
        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        texture_coordinates = numpy.array(
                             [
                             [cut_off_ratio, 1.0],
                             [cut_off_ratio, 0.0],
                             [0.0, 0.0],
                             [0.0, 1.0],
                             ])
                                     
        glTexCoordPointerf(texture_coordinates)
        
        #== Send opengl commands ==
        if duration == 0.0:
            number_of_frames = 1
        else:
            number_of_frames = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        start_time = time.time()
        stop_stimulus = False
        for i in range(number_of_frames):
            phase = pixel_velocity * i
            glTexCoordPointerf(texture_coordinates + numpy.array([phase,0.0]))
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            #Make sure that at the first flip the parameters of the function call are logged
            if not first_flip:
                self.log_on_flip_message = self.log_on_flip_message_initial
                first_flip = True
            else:
                #If running of stimulus lasts longer than duration, abort it, unless duration is less than 1 sec. In this case
                #it is assumed that the number of displayable  frames are more important than the duration
                if time.time() - start_time > duration and duration >=1.0:
#                    stop_stimulus = True#TODO This functionality shall be completely removed
                    self.log_on_flip_message = self.log_on_flip_message_continous + ' Less frames shown.'
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
            self._flip(trigger = True)
            if self.abort:
                self.abort = False
                break
            if stop_stimulus:                
                break
                    
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
                    
    def show_dots(self,  dot_diameters, dot_positions, ndots, duration = 0.0,  color = (1.0,  1.0,  1.0)):
        '''
        Shows a huge number (up to several hunders) of dots.
        Parameters:
            dot_sizes: one dimensional list of dot sizes in um. 
            dot_positions: one dimensional list of dot positions (row, col) in um.
            ndots: number of dots per frame
            color: can be a single tuple of the rgb values that apply to each dots over the whole stimulation. Both list and numpy formats are supported
                    Optionally a two dimensional list can be provided where the dimensions are organized as above controlling the color of each dot individually
            duration: duration of each frame in s. When 0, frame is shown for one frame time.

        The dot_sizes and dot_positions are expected to be in a linear list. Based on the ndots, these will be segmented to frames assuming
        that on each frame the number of dots are equal.
        '''
        #TODO/idea: add support for showing rectangles and annuli
        self.log_on_flip_message_initial = 'show_dots(' + str(duration)+ ', ' + str(dot_diameters) +', ' + str(dot_positions) +')'
        self.log_on_flip_message_continous = 'show_dots'
        first_flip = False
        radius = 1.0
        vertices = utils.calculate_circle_vertices([radius,  radius],  1.0/1.0)
        n_frames = len(dot_positions) / ndots
        self.log_on_flip_message_initial += ' n_frames = ' + str(n_frames)
        n_vertices = len(vertices)        
        frames_vertices = numpy.zeros((n_frames * ndots * n_vertices,  2))         
        index = 0
        for frame_i in range(n_frames):
            for dot_i in range(ndots):
                dot_index = frame_i * ndots + dot_i
                dot_size = dot_diameters[dot_index]
                dot_position = numpy.array((dot_positions[dot_index]['col'], dot_positions[dot_index]['row']))
                dot_to_screen =  self.config.SCREEN_UM_TO_PIXEL_SCALE * (vertices * dot_size + dot_position)
                frames_vertices[index: index + n_vertices] = dot_to_screen
                index = index + n_vertices

        if duration == 0:
            n_frames_per_pattern = 1
        else:
            n_frames_per_pattern = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))

        glEnableClientState(GL_VERTEX_ARRAY)
        dot_pointer = 0
        for frame_i in range(n_frames):
            start_i = dot_pointer * n_vertices
            end_i = (dot_pointer + ndots) * n_vertices
            dot_pointer = dot_pointer + ndots
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)            
#            self._show_text()
            glVertexPointerf(frames_vertices[start_i:end_i])
            for i in range(n_frames_per_pattern):
                for dot_i in range(ndots):
                    if isinstance(color[0],  list):
                        glColor3fv(color[frame_i][dot_i])
                    elif isinstance(color[0], numpy.ndarray):
                        glColor3fv(color[frame_i][dot_i].tolist())
                    else:
                        glColor3fv(color)
                    glDrawArrays(GL_POLYGON,  dot_i * n_vertices, n_vertices)
                    
                #Make sure that at the first flip the parameters of the function call are logged
                if not first_flip:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                    first_flip = True
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                if i == 0:
                    self._flip(trigger = True)
                else:
                    self._flip(trigger = False)
            if self.abort:
                self.abort = False
                break
                
        glDisableClientState(GL_VERTEX_ARRAY)
        

if __name__ == "__main__":
    pass
