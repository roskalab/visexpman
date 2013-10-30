import os.path
import os
import numpy
import math
import time
import Image
import inspect
import re

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import command_handler
import experiment_control
from visexpman.engine.generic import graphics #Not used
from visexpman.engine.generic import utils
from visexpman.engine.generic import colors
from visexpman.engine.vision_experiment import screen
from visexpA.engine.datadisplay import videofile

import unittest
command_extract = re.compile('SOC(.+)EOC')

class Stimulations(experiment_control.ExperimentControl):#, screen.ScreenAndKeyboardHandler):
    """
    Contains all the externally callable stimulation patterns:
    1. show_image(self,  path,  duration = 0,  position = (0, 0),  formula = [])
    """
    def __init__(self,  config,  application_log, experiment_control_dependent = True):
        self.config = config
        #graphics.Screen constructor intentionally not called, only the very necessary variables for flip control are created.
        self.screen = graphics.Screen(config, init_mode = 'no_screen')
#        self.init_flip_variables()
#        self.load_keyboard_commands(self) #this is necessary for accepting keyboard commands during experiment
        self.abort = False
        
        experiment_control.ExperimentControl.__init__(self, config, application_log)
        
        self.experiment_control_dependent = experiment_control_dependent
        self.grating_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.grating_texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        
        self.delayed_frame_counter = 0 #counts how many frames were delayed
        self.log_on_flip_message = ''
        self.elapsed_time = 0
        
        self.text_on_stimulus = []
        
        #Command buffer for keyboard commands during experiment
        self.command_buffer = ''
        
    def _flip(self,  trigger = False, count = True):
        """
        Flips screen buffer. Additional operations are performed here: saving frame and generating trigger
        """
        current_texture_state = glGetBooleanv(GL_TEXTURE_2D)
        if current_texture_state:
            glDisable(GL_TEXTURE_2D)
        self._show_text()
        if current_texture_state:
            glEnable(GL_TEXTURE_2D)
        self.screen.flip()
        self.flip_time = time.time()
        if count and hasattr(self, 'frame_counter'):
            self.frame_counter += 1
        frame_rate_deviation = abs(self.screen.frame_rate - self.config.SCREEN_EXPECTED_FRAME_RATE)
        if frame_rate_deviation > self.config.FRAME_DELAY_TOLERANCE:
            self.delayed_frame_counter += 1
            frame_rate_warning = ' %2.2f' %(frame_rate_deviation)            
        else:
            frame_rate_warning = ''
        if self.experiment_control_dependent and not self.config.STIMULUS2MEMORY:
            # If this library is not called by an experiment class which is called form experiment control class, no logging shall take place
            if hasattr(self, 'start_time'):
                self.elapsed_time = self.flip_time -  self.start_time
                self.log.info('%2.2f\t%s'%(self.screen.frame_rate,self.log_on_flip_message + frame_rate_warning))       
        if trigger and not self.config.STIMULUS2MEMORY:
            self._frame_trigger_pulse()
        self.check_abort_pressed()
        
    def _flip_and_block_trigger(self, frame_i, n_frames, frame_trigger, block_trigger):
        if block_trigger and frame_i==0:
            self._flip(trigger = frame_trigger)
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1, log = False)
        elif block_trigger and frame_i == n_frames -1:
            self._flip(trigger = frame_trigger)
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0, log = False)
        elif block_trigger:
            self._flip(trigger = frame_trigger)
        else:
            self._flip(trigger = frame_trigger)
            
    def check_abort_pressed(self):
        command = screen.check_keyboard() #Here only commands with running experiment domain are considered
        if command != None:
            for k, v in self.config.COMMANDS.items():
                if v['key'] == command and 'running experiment' in v['domain']:
                    self.command_buffer += k
                    break
        if 'abort_experiment' in self.command_buffer or utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
            self.command_buffer = self.command_buffer.replace('abort_experiment', '')
            self.printl('Abort pressed', application_log = True)
            self.abort = True
            return True
        else:
            return False
        
    def _save_stimulus_frame_info(self, caller_function_info, is_last = False):
        '''
        Saves:
        -frame counter
        -elapsed time
        -stimulus function's name
        -parameters of stimulus
        '''
        if hasattr(self, 'elapsed_time') and hasattr(self, 'frame_counter') and\
                hasattr(self, 'stimulus_frame_info'):
            args, _, _, values = inspect.getargvalues(caller_function_info)
            caller_name =inspect.getframeinfo(caller_function_info)[2]
            frame_info = {}
            frame_info['counter'] = self.frame_counter
            if is_last:
                frame_info['counter']  -= 1
            frame_info['elapsed_time'] = self.elapsed_time
            frame_info['stimulus_type'] = caller_name
            frame_info['is_last'] = is_last
            frame_info['parameters'] = {}
            for arg in args:
                if arg != 'self':
                    if values[arg] is None:
                        frame_info['parameters'][arg] = ''
                    else:
                        frame_info['parameters'][arg] = values[arg]
            self.stimulus_frame_info.append(frame_info)

    def _frame_trigger_pulse(self):
        '''
        Generates frame trigger pulses
        '''
        if self.experiment_control_dependent and hasattr(self, 'parallel_port'):
            self.parallel_port.set_data_bit(self.config.FRAME_TRIGGER_PIN, 1, log = False)
            time.sleep(self.config.FRAME_TRIGGER_PULSE_WIDTH)
            self.parallel_port.set_data_bit(self.config.FRAME_TRIGGER_PIN, 0, log = False)
            
    def block_trigger_pulse(self, pulse_width=None):
        if self.experiment_control_dependent and hasattr(self, 'parallel_port'):
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1, log = False)
            if pulse_width is None:
                time.sleep(self.config.BLOCK_TRIGGER_PULSE_WIDTH)
            else:
                time.sleep(pulse_width)
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0, log = False)
        
    def _show_text(self):
        '''
        Overlays on stimulus all the added text configurations
        '''
        if self.config.ENABLE_TEXT:
            for text_config in self.text_on_stimulus:
                if text_config['enable']:
                    self.screen.render_text(text_config['text'], color = text_config['color'], position = text_config['position'],  text_style = text_config['text_style'])
                    
    def _get_shape_string(self, shape):
        if shape == 'circle' or shape == '' or shape == 'o' or shape == 'c' or shape =='spot':
            shape_type = 'circle'
        elif shape == 'rect' or shape == 'rectangle' or shape == 'r' or shape == '||':
            shape_type = 'rectangle'
        elif shape == 'annuli' or shape == 'annulus' or shape == 'a':
            shape_type = 'annulus'
        return shape_type
    
    #== Public, helper functions ==
    def set_background(self,  color):
        '''
        Set background color. Call this when a visual pattern should have a different background color than config.BACKGROUND_COLOR
        '''
        color_to_set = colors.convert_color(color, self.config)
        glClearColor(color_to_set[0], color_to_set[1], color_to_set[2], 0.0)
        
    def add_text(self, text, color = (1.0,  1.0,  1.0), position = utils.rc((0.0, 0.0)),  text_style = GLUT_BITMAP_TIMES_ROMAN_24):
        '''
        Adds text to text list
        '''
        text_config = {'enable' : True, 'text' : text, 'color' : colors.convert_color(color, self.config), 'position' : position, 'text_style' : text_style}
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
            text_config['color'] = colors.convert_color(color, self.config)
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

    def trigger_pulse(self, pin, width = None):
        '''
        Generates trigger pulses
        '''
        if width is None:
            width = self.config.FRAME_TRIGGER_PULSE_WIDTH
        if self.experiment_control_dependent and hasattr(self, 'parallel_port'):
            self.parallel_port.set_data_bit(pin, 1, log = False)
            time.sleep(width)
            self.parallel_port.set_data_bit(pin, 0, log = False)

    #== Various visual patterns ==
    
    def show_fullscreen(self, duration = 0.0,  color = None, flip = True, count = True, block_trigger = False, save_frame_info = True, frame_trigger = True):
        '''
        duration: 0.0: one frame time, -1.0: forever, any other value is interpreted in seconds        
        '''
        if count and save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe())
        if color == None:
            color_to_set = self.config.BACKGROUND_COLOR
        else:
            color_to_set = colors.convert_color(color, self.config)
        self.log_on_flip_message_initial = 'show_fullscreen(' + str(duration) + ', ' + str(color_to_set) + ')'
        self.log_on_flip_message_continous = 'show_fullscreen'
        self.screen.clear_screen(color = color_to_set)
        if duration == 0.0:
            self.log_on_flip_message = self.log_on_flip_message_initial
            if flip:
                self._flip(trigger = frame_trigger, count = count)
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
                    self._flip(trigger = True, count = count)
                i += 1
        else:
            n_frames = int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)
            for i in range(n_frames):
                if i == 0:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                elif i == 1:
                    self.screen.clear_screen(color = color_to_set)
                    self.log_on_flip_message = self.log_on_flip_message_continous
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                if flip:
                    self._flip_and_block_trigger(i, n_frames, frame_trigger, block_trigger)
                if self.abort:
                    break
                    
        #set background color to the original value
        glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
        if count and save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
                
    def show_image(self,  path,  duration = 0,  position = utils.rc((0, 0)),  size = None, flip = True, block_trigger = False):
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
            n_frames = int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)
            for i in range(n_frames):
                if flip:
                    self._flip_and_block_trigger(i, n_frames, True, block_trigger)
                if self.abort:
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

    def show_shape(self, shape = '',  duration = 0.0,  pos = utils.rc((0,  0)),  color = [1.0,  1.0,  1.0],  background_color = None,  orientation = 0.0,  size = utils.rc((0,  0)),  ring_size = None, flip = True, block_trigger = False, save_frame_info = True, enable_centering = True, part_of_drawing_sequence = False):
        '''
        This function shows simple, individual shapes like rectangle, circle or ring. It is shown for one frame time when the duration is 0. 
        If pos is an array of rc values, duration parameter is not used for determining the whole duration of the stimulus
        color: 2d numpy array: duration is ignored and the first dimension will be the number of intensities displayed
        '''
        #Generate log messages
        self.log_on_flip_message_initial = 'show_shape(' + str(shape)+ ', ' + str(duration) + ', ' + str(pos) + ', ' + str(color)  + ', ' + str(background_color)  + ', ' + str(orientation)  + ', ' + str(size)  + ', ' + str(ring_size) + ')'
        self.log_on_flip_message_continous = 'show_shape'
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe())
        #Calculate number of frames
        n_frames = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        if n_frames == 0:
            n_frames = 1
        if hasattr(color,  'shape') and len(color.shape) ==2:
            n_frames = color.shape[0]
        #convert um dimension parameters to pixel
        if isinstance(size, float) or isinstance(size, int):        
            size_pixel = utils.rc((size, size))        
        elif isinstance(size, numpy.ndarray):   
            size_pixel = size                
        else:
            raise RuntimeError('Parameter size is provided in an unsupported format')
        size_pixel = utils.rc_multiply_with_constant(size_pixel, self.config.SCREEN_UM_TO_PIXEL_SCALE)        
        if hasattr(self, 'screen_center') and enable_centering:
            pos_with_offset = utils.rc_add(pos, self.screen_center)
        else:
            pos_with_offset = pos
        pos_pixel = utils.rc_multiply_with_constant(pos_with_offset, self.config.SCREEN_UM_TO_PIXEL_SCALE)
        if ring_size is not None:
            ring_size_pixel = ring_size * self.config.SCREEN_UM_TO_PIXEL_SCALE
        #Calculate vertices
        points_per_round = 360
        if shape == 'circle' or shape == '' or shape == 'o' or shape == 'c' or shape =='spot':
            shape_type = 'circle'
            vertices = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
        elif shape == 'rect' or shape == 'rectangle' or shape == 'r' or shape == '||':
            vertices = utils.rectangle_vertices(size_pixel, orientation = orientation)
            shape_type = 'rectangle'
        elif shape == 'annuli' or shape == 'annulus' or shape == 'a':
            vertices_outer_ring = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices_inner_ring = utils.calculate_circle_vertices([size_pixel['col'] - 2*ring_size_pixel,  size_pixel['row'] - 2*ring_size_pixel],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices = numpy.zeros(shape = (vertices_outer_ring.shape[0] * 2, 2))
            vertices[:vertices_outer_ring.shape[0]] = vertices_outer_ring
            vertices[vertices_outer_ring.shape[0]:] = vertices_inner_ring
            shape_type = 'annulus'
        n_vertices = vertices.shape[0]
        if len(pos_pixel.shape) == 0:#When does it happen?????????????
            number_of_positions = 1
            vertices = vertices + numpy.array([pos_pixel['col'], pos_pixel['row']])
        elif len(pos_pixel.shape) == 1 and pos_pixel.shape[0] == 1:
            number_of_positions = 1
            vertices = vertices + numpy.array([pos_pixel['col'], pos_pixel['row']]).T
        elif len(pos_pixel.shape) == 1 and pos_pixel.shape[0] > 1:
            if shape_type == 'annulus':
                raise RuntimeError('Moving annulus stimulus is not supported')
            else:
                n_frames = pos_pixel.shape[0]
                number_of_positions = pos_pixel.shape[0]
                packed_vertices = numpy.zeros((number_of_positions * n_vertices, 2), dtype = numpy.float64)
                for i in range(number_of_positions):
                    packed_vertices[i * n_vertices: (i+1) * n_vertices, :] = vertices + numpy.array([pos_pixel['col'][i], pos_pixel['row'][i]])
                vertices = packed_vertices
        #Set color
        if hasattr(color,  'shape') and len(color.shape) ==2:
            glColor3fv(colors.convert_color(color[0], self.config))
        else:
            glColor3fv(colors.convert_color(color, self.config))
        if background_color != None:
            background_color_saved = glGetFloatv(GL_COLOR_CLEAR_VALUE)
            converted_background_color = colors.convert_color(background_color, self.config)
            glClearColor(converted_background_color[0], converted_background_color[1], converted_background_color[2], 0.0)
        else:
            converted_background_color = colors.convert_color(self.config.BACKGROUND_COLOR, self.config)        
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        first_flip = False
        stop_stimulus = False
        start_time = time.time()
        frame_i = 0
        while True:
            if not part_of_drawing_sequence:
                glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            if shape_type != 'annulus':
                if hasattr(color,  'shape') and len(color.shape) == 2:
                    glColor3fv(colors.convert_color(color[frame_i], self.config))
                if number_of_positions == 1:
                    glDrawArrays(GL_POLYGON,  0, n_vertices)
                else:
                    glDrawArrays(GL_POLYGON,  frame_i * n_vertices, n_vertices)
            else:
                n = int(n_vertices/2)                
                glColor3fv(converted_background_color)
                glDrawArrays(GL_POLYGON,  n, n)
                if hasattr(color,  'shape') and len(color.shape) ==2:
                    glColor3fv(colors.convert_color(color[frame_i], self.config))
                else:
                    glColor3fv(colors.convert_color(color, self.config))
                glDrawArrays(GL_POLYGON,  0, n)
            #Make sure that at the first flip the parameters of the function call are logged
            if not first_flip:
                self.log_on_flip_message = self.log_on_flip_message_initial
                first_flip = True
            else:
                if time.time() - start_time > duration and duration >=1.0 and not self.config.ENABLE_FRAME_CAPTURE:
                    stop_stimulus = True
                    self.log_on_flip_message = self.log_on_flip_message_continous + ' Less frames shown.'
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
            if flip:
                self._flip_and_block_trigger(frame_i, n_frames, True, block_trigger)
            if self.abort:
                break
            if stop_stimulus:                
                break
            frame_i += 1
            if duration != -1 and frame_i == n_frames:
                break
        glDisableClientState(GL_VERTEX_ARRAY)        
        #Restore original background color
        if background_color != None:            
            glClearColor(background_color_saved[0], background_color_saved[1], background_color_saved[2], background_color_saved[3])
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
           
                    
    def show_checkerboard(self, n_checkers, duration = 0.0, pos = utils.cr((0,  0)), color = [], box_size = utils.cr((0,  0)), background_color = None, flip = True, save_frame_info = True,block_trigger=False):
        '''
        Shows checkerboard:
            n_checkers = (x dir (column), y dir (rows))
            pos - position of display area
            box_size - size of a box in um
            duration - duration of stimulus in seconds            
            color - array of color values. Dimensions:
                            1. Frame
                            2. row
                            3. col
                            4. color channel
        '''
        self.log_on_flip_message_initial = 'show_checkerboard(' + str(n_checkers)+ ', ' + str(duration) +', ' + str(box_size) +')'
        self.log_on_flip_message_continous = 'show_checkerboard'
        first_flip = False
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe())
        nframes = color.shape[0]
        nshapes = n_checkers['row']*n_checkers['col']
        if not hasattr(box_size, 'dtype'):
            box_size = utils.rc((box_size, box_size))
        shape_size = numpy.array([numpy.ones(nshapes*nframes)*box_size['row'], numpy.ones(nshapes*nframes)*box_size['col']]).T
        grid_positions = numpy.array(numpy.meshgrid(numpy.linspace(-(n_checkers['row']-1)/2.0, (n_checkers['row']-1)/2.0, n_checkers['row'])*box_size['row'], numpy.linspace(-(n_checkers['col']-1)/2.0, (n_checkers['col']-1)/2.0, n_checkers['col'])*box_size['col']),dtype=numpy.float).T
        shape_positions = utils.rc(numpy.array([numpy.array(grid_positions[:,:,0].flatten().tolist()*nframes), numpy.array(grid_positions[:,:,1].flatten().tolist()*nframes)]))
        color_adjusted = color[:,::-1,:,:]
        self.show_shapes('rectangle', shape_size, shape_positions, nshapes, 
                    duration = duration, 
                    color = numpy.reshape(color_adjusted.flatten(), (color_adjusted.shape[0], color_adjusted.shape[1]*color_adjusted.shape[2],color_adjusted.shape[3])), 
                    background_color = background_color,
                    block_trigger = block_trigger, colors_per_shape = False, save_frame_info = False)
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)

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
#                    color = color.convert_color(colors[(n_rings -1 - ring) * n_slices + slice])
#                except IndexError:
#                    color = (-1.0,  -1.0,  -1.0)
#                
#                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = color,  fillColor = color,  vertices =  vertices,  pos = pos_p))
#            if inner_circles:
#                vertices  = utils.calculate_circle_vertices(inner_r)
#                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = (-1.0,  -1.0,  -1.0),  fillColor = (-1.0,  -1.0,  -1.0),  vertices =  vertices,  pos = pos_p))
#                
#        self._show_stimulus(duration,  self.ring,  flip)
                    
    def show_grating(self, duration = 0.0,  profile = 'sqr',  white_bar_width =-1,  display_area = utils.cr((0,  0)),  orientation = 0,  starting_phase = 0.0,  velocity = 0.0,  color_contrast = 1.0,  color_offset = 0.5,  pos = utils.cr((0,  0)),  duty_cycle = 1.0,  noise_intensity = 0, part_of_drawing_sequence = False, block_trigger = False, save_frame_info = True):
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
            bar_width = self.config.SCREEN_RESOLUTION['col'] * self.config.SCREEN_UM_TO_PIXEL_SCALE
        else:
            bar_width = white_bar_width * self.config.SCREEN_UM_TO_PIXEL_SCALE
        #== Logging ==
        self.log_on_flip_message_initial = 'show_grating(' + str(duration)+ ', ' + str(profile) + ', ' + str(white_bar_width) + ', ' + str(display_area)  + ', ' + str(orientation)  + ', ' + str(starting_phase)  + ', ' + str(velocity)  + ', ' + str(color_contrast)  + ', ' + str(color_offset) + ', ' + str(pos)  + ')'
        self.log_on_flip_message_continous = 'show_grating'
        first_flip = False
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe())
        
        #== Prepare ==
        orientation_rad = orientation * math.pi / 180.0
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
            orientation_rad *= -1
        if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'down':
            pass
            
        pos_transformed = utils.rc_multiply_with_constant(pos, self.config.SCREEN_UM_TO_PIXEL_SCALE)
        
        pos_adjusted = []
        pos_adjusted.append(pos_transformed['col'])
        pos_adjusted.append(pos_transformed['row'])
        if display_area['col'] == 0 and display_area['row'] == 0 and self.config.COORDINATE_SYSTEM == 'ulcorner':
            pos_adjusted[0] += 0.5 * self.config.SCREEN_RESOLUTION['col']
            pos_adjusted[1] += 0.5 * self.config.SCREEN_RESOLUTION['row']            
        
        if display_area['col'] == 0:
            screen_width = self.config.SCREEN_RESOLUTION['col']
        else:
            screen_width = display_area['col']
        display_area_adjusted = []
        display_area_adjusted.append(display_area['col'] * self.config.SCREEN_UM_TO_PIXEL_SCALE)
        display_area_adjusted.append(display_area['row'] * self.config.SCREEN_UM_TO_PIXEL_SCALE)
        display_area_adjusted = numpy.array(display_area_adjusted)        
        
        #If grating are to be shown on fullscreen, modify display area so that no ungrated parts are on the screen considering rotation
        if display_area_adjusted[0] == 0:            
            display_area_adjusted[0] = self.config.SCREEN_RESOLUTION['col'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['row'] * abs(math.sin(orientation_rad))
            screen_width = self.config.SCREEN_RESOLUTION['col']
        if display_area_adjusted[1] == 0:
            display_area_adjusted[1] = self.config.SCREEN_RESOLUTION['row'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['col'] * abs(math.sin(orientation_rad))        
        #calculate vertices of display area
        #angles between diagonals
        alpha = numpy.arctan(display_area_adjusted[1]/display_area_adjusted[0])
        angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        angles = angles + orientation_rad
        diagonal = numpy.sqrt((display_area_adjusted **2).sum())
        vertices = 0.5 * diagonal * numpy.array([numpy.cos(angles), numpy.sin(angles)])
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
        period = int(bar_width * (1.0 + duty_cycle))
        #modify profile length so that the profile will contain integer number of repetitions
        repetitions = numpy.ceil(display_area_adjusted[0]/period)
        profile_length = period * repetitions
        cut_off_ratio = display_area_adjusted[0]/profile_length
        profile_length = int(profile_length)
        waveform_duty_cycle = 1.0 / (1.0 + duty_cycle)
        stimulus_profile_r = utils.generate_waveform(profile_adjusted[0], profile_length, period, color_contrast_adjusted[0], color_offset_adjusted[0], starting_phase, waveform_duty_cycle)
        stimulus_profile_g = utils.generate_waveform(profile_adjusted[1], profile_length, period, color_contrast_adjusted[1], color_offset_adjusted[1], starting_phase, waveform_duty_cycle)
        stimulus_profile_b = utils.generate_waveform(profile_adjusted[2], profile_length, period, color_contrast_adjusted[2], color_offset_adjusted[2], starting_phase, waveform_duty_cycle)
        stimulus_profile = numpy.array([[stimulus_profile_r], [stimulus_profile_g], [stimulus_profile_b]])
        stimulus_profile = stimulus_profile.transpose()
        if hasattr(self.config, 'GAMMA_CORRECTION'):
            stimulus_profile = self.config.GAMMA_CORRECTION(stimulus_profile)
        if hasattr(self.config, 'COLOR_MASK'):
            stimulus_profile *= self.config.COLOR_MASK
        if duration == 0.0:
            n_frames = 1
        else:
            n_frames = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        ######### Calculate texture phase shift per frame value ######
        if hasattr(velocity, 'dtype') and len(velocity.shape)>0:
            pixel_velocities = -velocity * self.config.SCREEN_UM_TO_PIXEL_SCALE / float(self.config.SCREEN_EXPECTED_FRAME_RATE) / float(stimulus_profile.shape[0])
        else:
            pixel_velocity = -velocity * self.config.SCREEN_UM_TO_PIXEL_SCALE / float(self.config.SCREEN_EXPECTED_FRAME_RATE) / float(stimulus_profile.shape[0])
            pixel_velocities = numpy.ones(n_frames)*pixel_velocity
        pixel_velocities = numpy.interp(
                                        numpy.arange(n_frames)/float(n_frames), numpy.arange(pixel_velocities.shape[0])/float(pixel_velocities.shape[0]), pixel_velocities)
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
                             [0.0, 1.0],
                             [0.0, 0.0],
                             [cut_off_ratio, 0.0],
                             ])

        glTexCoordPointerf(texture_coordinates)
        start_time = time.time()
#         pixel_velocity= -1.5/stimulus_profile.shape[0]
#         n_frames = int(numpy.sqrt(800**2+600**2)/1.5)
        phase = 0
        for i in range(n_frames):
            phase += pixel_velocities[i]
            glTexCoordPointerf(texture_coordinates + numpy.array([phase,0.0]))
            if not part_of_drawing_sequence:
                glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            #Make sure that at the first flip the parameters of the function call are logged
            if not first_flip:
                self.log_on_flip_message = self.log_on_flip_message_initial
                first_flip = True
            else:
                self.log_on_flip_message = self.log_on_flip_message_continous
            if not part_of_drawing_sequence:
                self._flip_and_block_trigger(i, n_frames, True, block_trigger)
            if self.abort:
                break
                    
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
    def show_dots(self,  dot_diameters, dot_positions, ndots, duration = 0.0,  color = (1.0,  1.0,  1.0), block_trigger = False):
        '''
        Maintains backward compatibility with old stimulations using show_dots
        '''
        self.show_shapes('o', dot_diameters, dot_positions, ndots, duration = duration,  color = color, block_trigger = block_trigger, colors_per_shape = False)
                    
    def show_shapes(self, shape, shape_size, shape_positions, nshapes, duration = 0.0,  color = (1.0,  1.0,  1.0), background_color = None, block_trigger = False, colors_per_shape = True, save_frame_info = True):
        '''
        Shows a huge number (up to several hunders) of shapes.
        Parameters:
            shape_size: one dimensional list of shape sizes in um or the size of rectangle, in this case a two dimensional array is also supported
            shape_positions: one dimensional list of shape positions (row, col) in um.
            nshapes: number of shapes per frame
            color: can be a single tuple of the rgb values that apply to each shapes over the whole stimulation. Both list and numpy formats are supported
                    Optionally a two dimensional list can be provided where the dimensions are organized as above controlling the color of each shape individually
            duration: duration of each frame in s. When 0, frame is shown for one frame time.

        The shape_sizes and shape_positions are expected to be in a linear list. Based on the nshapes, these will be segmented to frames assuming
        that on each frame the number of shapes are equal.
        '''
        self.log_on_flip_message_initial = 'show_shapes(' + str(duration)+ ', ' + str(shape_size) +', ' + str(shape_positions) +')'
        self.log_on_flip_message_continous = 'show_shapes'
        first_flip = False
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe())
        shape = self._get_shape_string(shape)
        if shape == 'circle':
            radius = 1.0
            vertices = utils.calculate_circle_vertices([radius,  radius],  1.0/1.0)
        elif shape == 'rectangle':
            vertices = numpy.array([[0.5, 0.5], [0.5, -0.5], [-0.5, -0.5], [-0.5, 0.5]])
        else:
            raise RuntimeError('Unknown shape: {0}'.format(shape))
        n_frames = len(shape_positions) / nshapes
        self.log_on_flip_message_initial += ' n_frames = ' + str(n_frames)
        n_vertices = len(vertices)        
        frames_vertices = numpy.zeros((n_frames * nshapes * n_vertices,  2))         
        index = 0
        for frame_i in range(n_frames):
            for shape_i in range(nshapes):
                shape_index = frame_i * nshapes + shape_i
                shape_size_i = shape_size[shape_index]
                shape_position = numpy.array((shape_positions[shape_index]['col'], shape_positions[shape_index]['row']))
                shape_to_screen =  self.config.SCREEN_UM_TO_PIXEL_SCALE * (vertices * shape_size_i + shape_position)
                frames_vertices[index: index + n_vertices] = shape_to_screen
                index = index + n_vertices
        if duration == 0:
            n_frames_per_pattern = 1
        else:
            n_frames_per_pattern = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        if hasattr(color, 'dtype') and hasattr(self.config, 'GAMMA_CORRECTION'):
            color_corrected = self.config.GAMMA_CORRECTION(color)
        else:
            color_corrected = color
        if background_color != None:
            background_color_saved = glGetFloatv(GL_COLOR_CLEAR_VALUE)
            converted_background_color = colors.convert_color(background_color, self.config)
            glClearColor(converted_background_color[0], converted_background_color[1], converted_background_color[2], 0.0)
        else:
            converted_background_color = colors.convert_color(self.config.BACKGROUND_COLOR, self.config)        
        glEnableClientState(GL_VERTEX_ARRAY)
        shape_pointer = 0
        for frame_i in range(n_frames):
            start_i = shape_pointer * n_vertices
            end_i = (shape_pointer + nshapes) * n_vertices
            shape_pointer = shape_pointer + nshapes
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)            
#            self._show_text()
            glVertexPointerf(frames_vertices[start_i:end_i])
            for i in range(n_frames_per_pattern):
                for shape_i in range(nshapes):
                    if colors_per_shape:
                        glColor3fv(colors.convert_color(color_corrected[shape_i], self.config))
                    elif isinstance(color_corrected[0], list):
                        glColor3fv(colors.convert_color(color_corrected[frame_i][shape_i], self.config))
                    elif isinstance(color_corrected[0], numpy.ndarray):
                        glColor3fv(colors.convert_color(color_corrected[frame_i][shape_i].tolist()))
                    else:
                        glColor3fv(colors.convert_color(color_corrected, self.config))
                    glDrawArrays(GL_POLYGON, shape_i * n_vertices, n_vertices)
                    if self.abort:
                        break
                #Make sure that at the first flip the parameters of the function call are logged
                if not first_flip:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                    first_flip = True
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                self._flip_and_block_trigger(i, n_frames_per_pattern, True, block_trigger)
                if self.abort:
                    break
            if self.abort:
                break
                
        glDisableClientState(GL_VERTEX_ARRAY)
        #Restore original background color
        if background_color != None:            
            glClearColor(background_color_saved[0], background_color_saved[1], background_color_saved[2], background_color_saved[3])
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
class StimulationSequences(Stimulations):
    '''
    Stimulation sequences, helpers
    '''
    def _merge_identical_frames(self):
        self.merged_bitmaps = [[self.screen.stimulus_bitmaps[0], 1]]
        for frame_i in range(1, len(self.screen.stimulus_bitmaps)):
            if abs(self.merged_bitmaps[-1][0] - self.screen.stimulus_bitmaps[frame_i]).sum()==0:
                self.merged_bitmaps[-1][1] += 1
            else:
                self.merged_bitmaps.append([self.screen.stimulus_bitmaps[frame_i], 1])
        
    def stimulusbitmap2uled(self):
        expected_configs = ['ULED_SERIAL_PORT', 'STIMULUS2MEMORY']
        if all([hasattr(self.machine_config, expected_config) for expected_config in expected_configs]) and self.machine_config.STIMULUS2MEMORY:
            self.config.STIMULUS2MEMORY = False
            from visexpman.engine.hardware_interface import microled
            self.microledarray = microled.MicroLEDArray(self.machine_config)
            self._merge_identical_frames()
            for frame_i in range(len(self.merged_bitmaps)):
                t0=time.time()
                self.microledarray.reset()
                self._frame_trigger_pulse()
                if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False) or self.check_abort_pressed():
                    self.abort=True
                    break
                pixels = numpy.where(self.merged_bitmaps[frame_i][0].mean(axis=2) == 0, False, True)
                self.microledarray.display_pixels(pixels, self.merged_bitmaps[frame_i][1]/self.machine_config.SCREEN_EXPECTED_FRAME_RATE-(time.time()-t0), clear=False)
                
            self.microledarray.release_instrument()
        else:
            raise RuntimeError('Micro LED array stimulation is not configured properly, make sure that {0} parameters have correct values'.format(expected_configs))
        
    def export2video(self, filename, img_format='png'):
        videofile.images2mpeg4(os.path.join(self.machine_config.CAPTURE_PATH,  'captured_%5d.{0}'.format(img_format)), filename, int(self.machine_config.SCREEN_EXPECTED_FRAME_RATE))
        
    def flash_stimulus(self, shape, timing, colors, sizes = utils.rc((0, 0)), position = utils.rc((0, 0)), background_color = 0.0, repeats = 1, block_trigger = True, save_frame_info = True,  ring_sizes = None):
        '''
        Use cases:
        shape: like show_shape, ff = fullfield
        timing: 1. [ON TIME, OFF_TIME] for each size and/or each color
                    2. OFF TIME 1, ON_TIME flash1, OFF_TIME 2, ON_TIME flash2
        colors: formats:
                1. single color in intensity or rgb format
                2. 2d numpy array: duration is ignored and the first dimension will be the number of intensities displayed
        sizes: 1. single size
                  2. 2d numpy array: series of different sizes
        '''
        if save_frame_info:
            self.log.info('flash_stimulus(' + str(shape)+ ', ' + str(timing) +', ' + str(colors) +', ' + str(sizes)  +', ' + str(position)  + ', ' + str(background_color) + ', ' + str(repeats) + ', ' + str(block_trigger) + ')')
            self._save_stimulus_frame_info(inspect.currentframe())
        if isinstance(timing, list) and len(timing) == 2 or hasattr(timing, 'dtype') and timing.shape[0] == 2:
            #find out number of flashes
            if isinstance(sizes, list):
                n_flashes = len(sizes)
            elif hasattr(sizes, 'dtype'):
                if len(sizes.shape) == 0:
                    n_flashes = 0
                else:
                    n_flashes = sizes.shape[0]
            elif isinstance(ring_sizes, list):
                n_flashes = len(ring_sizes)
            elif hasattr(ring_sizes, 'dtype'):
                if len(ring_sizes.shape) == 0:
                    n_flashes = 0
                else:
                    n_flashes = ring_sizes.shape[0]
            else:
                raise RuntimeError('sizes or ring_sizes parameter shall be list or numpy.array.')
            if n_flashes == 0:
                if isinstance(colors, list):
                    n_flashes = len(colors)
                elif hasattr(colors, 'dtype'):
                    n_flashes = colors.shape[0]
            timing = [timing[0], timing[1]] * n_flashes
            timing.insert(0, timing[1])
        for r in range(repeats):
            state = False
            for i in range(len(timing)):
                if state:
                    if hasattr(colors, '__iter__'):
                        color = colors[(i-1)/2]
                    else:
                        color = colors
                    if shape == 'ff':
                        self.show_fullscreen(color = color, duration = timing[i], save_frame_info = False, block_trigger = block_trigger)
                    else:
                        if hasattr(sizes, '__iter__') and len(sizes.shape) > 0:
                            if len(sizes.dtype) == 2 : #row, col format
                                size = utils.rc((sizes[(i-1)/2]['row'], sizes[(i-1)/2]['col']))
                            else:
                                size = utils.rc((sizes[(i-1)/2],sizes[(i-1)/2]))
                        else:
                            size = sizes
                        if hasattr(ring_sizes, '__iter__') and len(ring_sizes.shape) > 0:
                            ring_size = ring_sizes[(i-1)/2]
                        else:
                            ring_size = ring_sizes
                        self.show_shape(shape = shape,  duration = timing[i],  pos = position,  color = color,  background_color = background_color,  size = size,  block_trigger = block_trigger, save_frame_info = False, ring_size = ring_size)
                else:
                    self.show_fullscreen(color = background_color, duration = timing[i], save_frame_info = False, block_trigger = False)
                state = not state
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)

    def increasing_spot(self, spot_sizes, on_time, off_time, color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)), block_trigger = True):
        self.log.info('increasing_spot(' + str(spot_sizes)+ ', ' + str(on_time) +', ' + str(off_time) +', ' + str(color) +', ' + str(background_color) +', ' + str(pos) + ', ' + str(block_trigger) + ')')
        self._save_stimulus_frame_info(inspect.currentframe())
        self.flash_stimulus('o', [on_time, off_time], color, sizes = numpy.array(spot_sizes), position = pos, background_color = background_color, repeats = 1, block_trigger = block_trigger, save_frame_info = False)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)

    def moving_grating_stimulus(self):
        pass
        
    def moving_shape(self, size, speeds, directions, shape = 'rect', color = 1.0, background_color = 0.0, moving_range=utils.rc((0.0,0.0)), pause=0.0,block_trigger = False):
        #TODO:
#        if hasattr(self, 'screen_center'):
#            pos_with_offset = utils.rc_add(pos, self.screen_center)
#        else:
#            pos_with_offset = pos
        self.log.info('moving_shape(' + str(size)+ ', ' + str(speeds) +', ' + str(directions) +', ' + str(shape) +', ' + str(color) +', ' + str(background_color) +', ' + str(moving_range) + ', '+ str(pause) + ', ' + str(block_trigger) + ')')
        if hasattr(size, 'dtype'):
            shape_size = max(size['row'], size['col'])
        else:
            shape_size = size
        if not (isinstance(speeds, list) or hasattr(speeds,'dtype')):
            speeds = [speeds]
        self.movement = min(self.config.SCREEN_SIZE_UM['row'], self.config.SCREEN_SIZE_UM['col']) - shape_size # ref to machine conf which was started
        self._save_stimulus_frame_info(inspect.currentframe())
        #Calculate axis factors
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
            vaf = 1
        else:
            vaf = -1
        if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
            haf = 1
        else:
            has = -1
        self.show_fullscreen(duration = 0, color = background_color, save_frame_info = False, frame_trigger = False)
        for spd in speeds:
            for direction in directions:
                end_point = utils.rc_add(utils.cr((0.5 * self.movement *  numpy.cos(numpy.radians(vaf*direction)), 0.5 * self.movement * numpy.sin(numpy.radians(vaf*direction)))), self.config.SCREEN_CENTER, operation = '+')
                start_point = utils.rc_add(utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(vaf*direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(vaf*direction - 180.0)))), self.config.SCREEN_CENTER, operation = '+')
                spatial_resolution = spd/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                self.show_shape(shape = shape,  pos = utils.calculate_trajectory(start_point,  end_point,  spatial_resolution),  color = color,  background_color = background_color,  orientation =vaf*direction , size = size,  block_trigger = block_trigger, save_frame_info = False, enable_centering = False)
                if pause > 0:
                    self.show_fullscreen(duration = pause, color = background_color, save_frame_info = False, frame_trigger = False)
                if self.abort:
                    break
        self.show_fullscreen(duration = 0, color = background_color, save_frame_info = False, frame_trigger = False)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
    def white_noise(self, duration, pixel_size = utils.rc((1,1)), flickering_frequency = 0, colors = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], n_on_pixels = None):
        '''
        pixel_size : in um
        flickering_frequency: pattern change frequency, 0: max frame rate
        colors: set of colors or intensities to be used
        n_on_pixels: if provided the number of white pixels shown. colors shall be a list of two.
        '''
        self.log.info('white_noise(' + str(duration)+ ', ' + str(pixel_size) +', ' + str(flickering_frequency) +', ' + str(colors) +', ' + str(n_on_pixels) + ')')
        self._save_stimulus_frame_info(inspect.currentframe())
        if flickering_frequency == 0:
            npatterns = duration * self.config.SCREEN_EXPECTED_FRAME_RATE
            pattern_duration = 1
        else:
            npatterns = duration * flickering_frequency
            pattern_duration = self.config.SCREEN_EXPECTED_FRAME_RATE/flickering_frequency
        if not hasattr(pixel_size, 'dtype'):
            pixel_size = utils.rc((pixel_size, pixel_size))
        npixels = utils.rc((int(self.config.SCREEN_SIZE_UM['row']/pixel_size['row']), int(self.config.SCREEN_SIZE_UM['col']/pixel_size['col'])))
        if isinstance(colors[0],list):
            n_channels = len(colors[0])
        else:
            n_channels = 1
        color = numpy.zeros((npatterns, npixels['row'], npixels['col'], n_channels))
        numpy.random.seed(0)
        randmask = numpy.random.random(color.shape[:-1])
        if n_on_pixels is None:
            ranges =  numpy.linspace(0, 1, len(colors)+1)
            for r_i in range(ranges.shape[0]-1):
                indexes = numpy.nonzero(numpy.where(randmask > ranges[r_i], 1, 0) * numpy.where(randmask <= ranges[r_i + 1], 1, 0))
                color[indexes] = colors[r_i]
        elif len(colors) == 2:
            indexes = numpy.nonzero(randmask[0])
            import random
            random.seed(0)
            for pattern_i in range(int(npatterns)):
                rows = [random.choice(indexes[0]) for i in range(n_on_pixels)]
                cols = [random.choice(indexes[1]) for i in range(n_on_pixels)]
                color[pattern_i][rows, cols] = colors[-1]
                pass
        color = numpy.repeat(color, pattern_duration, 0)
        self.show_checkerboard(npixels, duration = 0, color = color, box_size = pixel_size, save_frame_info = True)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)

    def sine_wave_shape(self):
        pass
        
    def projector_calibration(self, intensity_range = [0.0, 1.0], npoints = 128, time_per_point = 1.0, repeats = 3, sync_flash = False):
        self._save_stimulus_frame_info(inspect.currentframe())
        step = (intensity_range[1]-intensity_range[0])/(npoints)
        intensities = numpy.concatenate((numpy.arange(intensity_range[0], intensity_range[1]+step, step), numpy.arange(intensity_range[1], intensity_range[0]-step, -step)))
        if sync_flash:
            self.show_fullscreen(duration = 1.0, color = intensity_range[1])
            self.show_fullscreen(duration = 3.0, color = intensity_range[0])
        else:
            self.show_fullscreen(duration = 4.0, color = intensity_range[0])
        for r in range(repeats):
            for c in intensities:
                self.show_fullscreen(duration = time_per_point, color = c)
                self.measure_light_power(c)
                if self.check_abort_pressed():
                    break
                    
    def measure_light_power(self, reference_intensity):
        pass
        
class testStimulationPatterns(unittest.TestCase):

    def test_01_stimulation_development(self):
        from visexpman.engine.visexp_runner import VisionExperimentRunner
        v = VisionExperimentRunner('zoltan', 'StimulusDevelopmentMachineConfig')
        v.run_experiment('StimulusPatternDevelopmentConfig')

if __name__ == "__main__":
    unittest.main()
