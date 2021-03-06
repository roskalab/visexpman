import os.path
import os
import numpy
import math
import time
from PIL import Image
import inspect
import re

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


import command_handler
import experiment_control
from visexpman.engine.generic import graphics #Not used
from visexpman.engine.generic import utils,signal, geometry
from visexpman.engine.generic import colors
from visexpman.engine.vision_experiment import screen

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
        self.precalculate_duration_mode=False
        
    def _flip(self,  trigger = False,  saveFrame = False, count = True):
        """
        """
        if self.precalculate_duration_mode:
            self.frame_counter += 1
            return
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
            
    def block_start(self, block_name = ''):
        if hasattr(self, 'digital_output') and hasattr(self.digital_output,'set_data_bit'):
            self.digital_output.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1, log = False)
        self.stimulus_frame_info.append({'block_start':self.frame_counter, 'block_name': block_name})
        if self.machine_config.PLATFORM == 'elphys_retinal_ca':
            self.send({'plot': [time.time(), 1]})
        if hasattr(self.log, 'info'):
            self.log.info('{0} block started' .format(block_name))
                
    def block_end(self, block_name = ''):
        if hasattr(self, 'digital_output') and hasattr(self.digital_output,'set_data_bit'):
            self.digital_output.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0, log = False)
        self.stimulus_frame_info.append({'block_end':self.frame_counter, 'block_name': block_name})
        if self.machine_config.PLATFORM == 'elphys_retinal_ca':
            self.send({'plot': [time.time(), 0]})
        if hasattr(self.log, 'info'):
            self.log.info('{0} block ended' .format(block_name))
        
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


    #== Various visual patterns ==
    
    def show_fullscreen(self, duration = 0.0,  color = None, flip = True, count = True, frame_trigger = True):
        '''
        duration: 0.0: one frame time, -1.0: forever, any other value is interpreted in seconds        
        '''
        if count and not self.precalculate_duration_mode:
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
                    self._flip(trigger = frame_trigger, count = count)
                i += 1
        else:
            for i in range(int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)):
                if i == 0:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                elif i == 1:
                    self.screen.clear_screen(color = color_to_set)
                    self.log_on_flip_message = self.log_on_flip_message_continous
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous
                if flip:
                    self._flip(trigger = frame_trigger)
                if self.abort:
                    break
        #set background color to the original value
        glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
        if count and not self.precalculate_duration_mode:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
                
    def show_image(self,  path,  duration = 0,  position = utils.rc((0, 0)),  size = None, stretch=1.0, flip = True):
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
        #Generate log messages
        flips_per_frame = duration/(1.0/self.config.SCREEN_EXPECTED_FRAME_RATE)
        if flips_per_frame != numpy.round(flips_per_frame):
            raise RuntimeError('This duration is not possible, it should be the multiple of 1/SCREEN_EXPECTED_FRAME_RATE')                
        self.log_on_flip_message_initial = 'show_image(' + str(path)+ ', ' + str(duration) + ', ' + str(position) + ', ' + str(size)  + ', ' + ')'
        self.log_on_flip_message_continous = 'show_shape'
        self._save_stimulus_frame_info(inspect.currentframe())
        print self.frame_counter
        if os.path.isdir(path):
            for fn in os.listdir(path):
                self._show_image(os.path.join(path,fn),duration,position,stretch,flip)
            self.screen.clear_screen()
            self._flip(trigger = False)
        else:
            self._show_image(path,duration,position,flip)
        print self.frame_counter
        self._save_stimulus_frame_info(inspect.currentframe())
        
    def _show_image(self,path,duration,position,stretch,flip):
        if duration == 0.0:
            nframes=1
        else:
            nframes = int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)
        for i in range(nframes):
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.screen.render_imagefile(path, position = utils.rc_add(position,
                        utils.rc_multiply_with_constant(self.machine_config.SCREEN_CENTER, self.config.SCREEN_UM_TO_PIXEL_SCALE)),stretch=stretch)
            if flip:
                self._flip(trigger = True)
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

    def show_shape(self,  shape = '',  duration = 0.0,  pos = utils.rc((0,  0)),  color = [1.0,  1.0,  1.0],  background_color = None,  orientation = 0.0,  size = utils.rc((0,  0)),  ring_size = 1.0, flip = True, L_shape_config = None, X_shape_angle = None, ncorners = None,  inner_radius=None, save_sfi = True,angle=None):
        '''
        This function shows simple, individual shapes like rectangle, circle or ring. It is shown for one frame time when the duration is 0. 
        If pos is an array of rc values, duration parameter is not used for determining the whole duration of the stimulus
        '''
        #Generate log messages
        self.log_on_flip_message_initial = 'show_shape(' + str(shape)+ ', ' + str(duration) + ', ' + str(pos) + ', ' + str(color)  + ', ' + str(background_color)  + ', ' + str(orientation)  + ', ' + str(size)  + ', ' + str(ring_size) + ')'
        self.log_on_flip_message_continous = 'show_shape'
        if save_sfi:
            self._save_stimulus_frame_info(inspect.currentframe())
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
        size_pixel = utils.rc_multiply_with_constant(size_pixel, self.config.SCREEN_UM_TO_PIXEL_SCALE)        
        pos_pixel = utils.rc_multiply_with_constant(pos, self.config.SCREEN_UM_TO_PIXEL_SCALE)        
        #Calculate vertices
        points_per_round = 360
        if shape == 'circle' or shape == '' or shape == 'o' or shape == 'c' or shape =='spot':
            shape_type = 'circle'
            vertices = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
        elif shape == 'rect' or shape == 'rectangle' or shape == 'r' or shape == '||':
            vertices = utils.rectangle_vertices(size_pixel, orientation = orientation)
            vertices[:, 1]*=1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
            shape_type = 'rectangle'
        elif shape == 'annuli' or shape == 'annulus' or shape == 'a':
            vertices_outer_ring = utils.calculate_circle_vertices([size_pixel['col'],  size_pixel['row']],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices_inner_ring = utils.calculate_circle_vertices([size_pixel['col'] - ring_size,  size_pixel['row'] - ring_size],  resolution = points_per_round / 360.0)#resolution is vertex per degree
            vertices = numpy.zeros(shape = (vertices_outer_ring.shape[0] * 2, 2))
            vertices[:vertices_outer_ring.shape[0]] = vertices_outer_ring
            vertices[vertices_outer_ring.shape[0]:] = vertices_inner_ring
            shape_type = 'annulus'
        elif shape == 'triangle':
            vertices = geometry.triangle_vertices(size_pixel['row'], orientation)
            shape_type = shape
        elif shape == 'star':
            vertices_ = geometry.star_vertices(size_pixel['row'],ncorners,orientation,inner_radius)
            #make triangles of shape
            vertices = numpy.zeros((ncorners*3,2))
#            import pdb
#            pdb.set_trace()
            vertices[1::3] = vertices_[0::2]
            vertices[0::3] = numpy.roll(vertices_[1::2],1,axis=0)
            vertices[2::3] = vertices_[1::2]
            vertices = numpy.concatenate((vertices, vertices_[1::2]))
            shape_type = shape
        elif shape == 'X':
            shape_type = shape
            vertices = numpy.concatenate([geometry.rectangle_vertices(size_pixel, orientation = orientation),
                    geometry.rectangle_vertices(size_pixel, orientation = orientation+X_shape_angle)])
            vertices[:, 1]*=1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
        elif shape == 'L':
            shape_type = shape
            #create skeleton
            if L_shape_config['shorter_position'] == 'middle':
                p=geometry.point_coordinates(L_shape_config['shorter_side'], numpy.radians(L_shape_config['angle']), numpy.array([0,0]))
                v = numpy.array([[-0.5*L_shape_config['longer_side'], 0], [0,0], [0.5*L_shape_config['longer_side'],0],p])
            elif L_shape_config['shorter_position'] == 'start':
                start_point = numpy.array([-0.5*L_shape_config['longer_side'],0])
                p=geometry.point_coordinates(L_shape_config['shorter_side'], numpy.radians(L_shape_config['angle']), start_point)
                v=numpy.array([[0.5*L_shape_config['longer_side'],0], start_point, p])
            elif L_shape_config['shorter_position'] == 'end':
                start_point = numpy.array([0.5*L_shape_config['longer_side'],0])
                p=geometry.point_coordinates(L_shape_config['shorter_side'], numpy.radians(L_shape_config['angle']), start_point)
                v=numpy.array([[-0.5*L_shape_config['longer_side'],0], start_point, p])
            if L_shape_config['shorter_position'] == 'middle':
                wrist_distance = 0.5* L_shape_config['width']/numpy.sin(numpy.radians(45))
                base_shape = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(90), v[0]), 
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(-90), v[0]),
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(-90), v[2]),
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(90), v[2])])
                angle = numpy.radians(L_shape_config['angle'])
                endpoints = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']+90), v[3]),
                                                        geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']-90), v[3]),
                                                        ])
                wrist = numpy.array([
                                            geometry.point_coordinates(L_shape_config['shorter_side'], angle-numpy.pi, endpoints[1]),
                                            geometry.point_coordinates(L_shape_config['shorter_side'], angle-numpy.pi, endpoints[0])
                                            ])
                vertices = numpy.concatenate((base_shape, wrist, endpoints))
            elif L_shape_config['shorter_position'] == 'start':
                wrist_distance = 0.5* L_shape_config['width']/numpy.sin(numpy.radians(L_shape_config['angle']*0.5))
                endvertices1 = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(90), v[0]), 
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(-90), v[0])])
                endvertices2 = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']-90), v[2]), 
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']+90), v[2])])
                angle = numpy.radians((L_shape_config['angle']*0.5))
                wrist = numpy.array([geometry.point_coordinates(wrist_distance, angle - numpy.pi, v[1]),
                                                    geometry.point_coordinates(wrist_distance, angle, v[1])])
                vertices = numpy.concatenate((endvertices1, wrist, wrist, endvertices2))
            elif L_shape_config['shorter_position'] == 'end':
                wrist_distance = 0.5* L_shape_config['width']/numpy.sin(numpy.radians((180-L_shape_config['angle'])*0.5))
                endvertices1 = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(90), v[0]), 
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(-90), v[0])])
                endvertices2 = numpy.array([geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']-90), v[2]), 
                                                                geometry.point_coordinates(0.5*L_shape_config['width'], numpy.radians(L_shape_config['angle']+90), v[2])])
                angle = numpy.radians(((180-L_shape_config['angle'])*0.5)+L_shape_config['angle'])
                wrist = numpy.array([geometry.point_coordinates(wrist_distance, angle- numpy.pi, v[1]),
                                                    geometry.point_coordinates(wrist_distance, angle, v[1])])
                vertices = numpy.concatenate((endvertices1, wrist, wrist[::-1], endvertices2))
            vertices = geometry.rotate_point(vertices.T,orientation,numpy.array([0,0])).T
            vertices[:, 1]*=1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
            #Convert to pixels
            vertices *= self.config.SCREEN_UM_TO_PIXEL_SCALE
        n_vertices = vertices.shape[0]
        if len(pos_pixel.shape) == 0:
            number_of_positions = 1
            vertices = vertices + numpy.array([pos_pixel['col'], pos_pixel['row']])
        elif len(pos_pixel.shape) == 1:
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
        for frame_i in range(n_frames):            
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            if shape_type != 'annulus':
                if number_of_positions == 1:
                    if shape_type == 'star':#opengl cannot draw concave shapes
                        for i in range(ncorners):
                            glDrawArrays(GL_POLYGON,  i*3, 3)
                        glDrawArrays(GL_POLYGON,  ncorners*3, ncorners)
                    elif shape_type == 'L' or shape_type == 'X':
                        glDrawArrays(GL_POLYGON,  0, n_vertices/2)
                        glDrawArrays(GL_POLYGON,  n_vertices/2, n_vertices/2)
                    else:
                        glDrawArrays(GL_POLYGON,  0, n_vertices)
                else:
                    if shape_type == 'star':
                        raise NotImplementedError('moving star is not implemented')
                    elif shape_type == 'L' or shape_type == 'X':
                        glDrawArrays(GL_POLYGON,  frame_i * n_vertices, n_vertices/2)
                        glDrawArrays(GL_POLYGON,  int((frame_i+0.5) * n_vertices), n_vertices/2)
                    else:
                        glDrawArrays(GL_POLYGON,  frame_i * n_vertices, n_vertices)
            else:
                n = int(n_vertices/2)                
                glColor3fv(colors.convert_color(converted_background_color, self.config))
                glDrawArrays(GL_POLYGON,  n, n)
                glColor3fv(colors.convert_color(color, self.config))
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
            self._flip(trigger = True)
            if self.abort:
                break
            if stop_stimulus:                
                break
        glDisableClientState(GL_VERTEX_ARRAY)        
        #Restore original background color
        if background_color != None:            
            glClearColor(background_color_saved[0], background_color_saved[1], background_color_saved[2], background_color_saved[3])
        if save_sfi:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
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
#                texture.putpixel((column, row),  utils.convert_int_color(color.convert_color_from_pp(color.convert_color(color[row * n_checkers[0] + column]))))
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
                    
    def show_grating(self, duration = 0.0,  profile = 'sqr',  white_bar_width =-1,  display_area = utils.cr((0,  0)),  orientation = 0,  starting_phase = 0.0,  velocity = 0.0,  color_contrast = 1.0,  color_offset = 0.5,  background_color = None,  pos = utils.cr((0,  0)),  duty_cycle = 1.0,  noise_intensity = 0, part_of_drawing_sequence = False):
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
        stimulus_profile = numpy.array([[stimulus_profile_r],  [stimulus_profile_g],  [stimulus_profile_b]])
        stimulus_profile = stimulus_profile.transpose()
        if hasattr(self.config, 'GAMMA_CORRECTION'):
            stimulus_profile = self.config.GAMMA_CORRECTION(stimulus_profile)
        
        ######### Calculate texture phase shift per frame value ######
        pixel_velocity = -velocity * self.config.SCREEN_UM_TO_PIXEL_SCALE / float(self.config.SCREEN_EXPECTED_FRAME_RATE) / float(stimulus_profile.shape[0])
        
        if background_color != None:
            background_color_saved = glGetFloatv(GL_COLOR_CLEAR_VALUE)
            converted_background_color = colors.convert_color(background_color, self.config)
            glClearColor(converted_background_color[0], converted_background_color[1], converted_background_color[2], 0.0)
        else:
            converted_background_color = colors.convert_color(self.config.BACKGROUND_COLOR, self.config)
        
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
#         pixel_velocity= -1.5/stimulus_profile.shape[0]
#         number_of_frames = int(numpy.sqrt(800**2+600**2)/1.5)
        for i in range(number_of_frames):
            phase = pixel_velocity * i            
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
                self._flip(trigger = True)
            if self.abort:
                break
                    
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        if background_color != None:
            glClearColor(background_color_saved[0], background_color_saved[1], background_color_saved[2], background_color_saved[3])
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
                    
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
        self._save_stimulus_frame_info(inspect.currentframe())
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
                        glColor3fv(colors.convert_color(color[frame_i][dot_i], self.config))
                    elif isinstance(color[0], numpy.ndarray):
                        glColor3fv(colors.convert_color(color[frame_i][dot_i].tolist(), self.config))
                    else:
                        glColor3fv(colors.convert_color(color, self.config))
                    glDrawArrays(GL_POLYGON,  dot_i * n_vertices, n_vertices)
                    
                #Make sure that at the first flip the parameters of the function call are logged
                if not first_flip:
                    self.log_on_flip_message = self.log_on_flip_message_initial
                    first_flip = True
                else:
                    self.log_on_flip_message = self.log_on_flip_message_continous                
                self._flip(trigger = True)                
            if self.abort:
                break
                
        glDisableClientState(GL_VERTEX_ARRAY)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
            
    def show_natural_bars(self, speed = 300, repeats = 1, duration=20.0, minimal_spatial_period = None, spatial_resolution = None, intensity_levels = 255, direction = 0, background=None,offset=0.0, scale=1.0, fly_in=False, fly_out=False, circular=False,save_frame_info =True, is_block = False):
        if spatial_resolution is None:
            spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        if minimal_spatial_period is None:
            minimal_spatial_period = 10 * spatial_resolution
        self.log_on_flip_message_initial = 'show_natural_bars(' + str(speed)+ ', ' + str(repeats) +', ' + str(duration) +', ' + str(minimal_spatial_period)+', ' + str(spatial_resolution)+ ', ' + str(intensity_levels) +', ' + str(direction)+ ')'
        self.log_on_flip_message_continous = 'show_natural_bars'
        self.intensity_profile = offset+scale*signal.generate_natural_stimulus_intensity_profile(duration, speed, minimal_spatial_period, spatial_resolution, intensity_levels)
        if 0:#For testing only
            self.intensity_profile = numpy.linspace(0,1,self.intensity_profile.shape[0])
            self.intensity_profile[:0.1*self.intensity_profile.shape[0]]=0.0
            self.intensity_profile[-0.1*self.intensity_profile.shape[0]:]=1.0
        self.intensity_profile = numpy.tile(self.intensity_profile, repeats)
        if save_frame_info and not self.precalculate_duration_mode:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = False)
            self.stimulus_frame_info[-1]['parameters']['intensity_profile']=self.intensity_profile
        if hasattr(self.machine_config, 'GAMMA_CORRECTION'):
            self.intensity_profile = self.machine_config.GAMMA_CORRECTION(self.intensity_profile)
        intensity_profile_length = self.intensity_profile.shape[0]
        if self.intensity_profile.shape[0] < self.config.SCREEN_RESOLUTION['col']:
            self.intensity_profile = numpy.tile(self.intensity_profile, numpy.ceil(float(self.config.SCREEN_RESOLUTION['col'])/self.intensity_profile.shape[0]))
        alltexture = numpy.repeat(self.intensity_profile,3).reshape(self.intensity_profile.shape[0],1,3)
        bg=colors.convert_color(self.config.BACKGROUND_COLOR if background is None else background, self.config)
        fly_in_out = bg[0] * numpy.ones((self.config.SCREEN_RESOLUTION['col'],1,3))
        intensity_profile_length += (fly_in+fly_out)*fly_in_out.shape[0]
        if fly_in:
            alltexture=numpy.concatenate((fly_in_out,alltexture))
        if fly_out:
            alltexture=numpy.concatenate((alltexture,fly_in_out))
        texture = alltexture[:self.config.SCREEN_RESOLUTION['col']]
        diagonal = numpy.sqrt(2) * numpy.sqrt(self.config.SCREEN_RESOLUTION['row']**2 + self.config.SCREEN_RESOLUTION['col']**2)
        diagonal =  1*numpy.sqrt(2) * self.config.SCREEN_RESOLUTION['col']#Because of different orienations, the stimulus size corresponds to the screen width
        alpha =numpy.pi/4
        angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        angles = angles + direction*numpy.pi/180.0
        vertices = 0.5 * diagonal * numpy.array([numpy.cos(angles), numpy.sin(angles)])
        vertices = vertices.transpose()
        if self.config.COORDINATE_SYSTEM == 'ulcorner':
            vertices += self.config.SCREEN_UM_TO_PIXEL_SCALE*numpy.array([self.machine_config.SCREEN_CENTER['col'], self.machine_config.SCREEN_CENTER['col']])
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
        ds = float(speed*self.config.SCREEN_UM_TO_PIXEL_SCALE)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
#        t0=time.time()
        texture_pointer = 0
        frame_counter = 0
        while True:
            start_index = int(texture_pointer)
            end_index = int(start_index + self.config.SCREEN_RESOLUTION['col'])
            if end_index > alltexture.shape[0]:
                end_index -= alltexture.shape[0]
            if start_index > alltexture.shape[0]:
                start_index -= alltexture.shape[0]
            if start_index < end_index:
                texture = alltexture[start_index:end_index]
            else:
                if circular:
                    texture = numpy.zeros_like(texture)
                    texture[:-end_index] = alltexture[start_index:]
                    texture[-end_index:] = alltexture[:end_index]
                    if start_index >= intensity_profile_length-1:
                        break
                else:
                    break
            texture_pointer += ds
            frame_counter += 1
            glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            self._flip(trigger = True)    
            if self.abort:
                break
#        dt=(time.time()-t0)
#        print self.frame_counter/dt,dt,self.frame_counter,texture_pointer
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        if save_frame_info and not self.precalculate_duration_mode:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
            self.stimulus_frame_info[-1]['parameters']['intensity_profile']=self.intensity_profile
            
    def white_noise(self, duration, square_size,save_frame_info=True):
        '''
        Generates white noise stimulus using numpy.random.random
        
        duration: duration of white noise stimulus in seconds
        square_size: size of squares. Number of squares is calculated from screen size but fractional squares are not displayed.
        The array of squares is centered
        '''
        if save_frame_info:
#             self.log.info('white_noise(' + str(duration)+ ', ' + str(square_size) + ')', source = 'stim')
            self._save_stimulus_frame_info(inspect.currentframe())
        square_size_pixel = square_size*self.machine_config.SCREEN_UM_TO_PIXEL_SCALE
        nframes = int(self.machine_config.SCREEN_EXPECTED_FRAME_RATE*duration)
        ncheckers = utils.rc_multiply_with_constant(self.machine_config.SCREEN_SIZE_UM, 1.0/square_size)
        ncheckers = utils.rc((numpy.floor(ncheckers['row']), numpy.floor(ncheckers['col'])))
        numpy.random.seed(0)
        checker_colors = numpy.zeros((0,ncheckers['row'],ncheckers['col']), dtype=numpy.bool)
        for i in range(int(nframes/self.machine_config.SCREEN_EXPECTED_FRAME_RATE/60)):
            checker_colors = numpy.concatenate((checker_colors, numpy.where(numpy.random.random((60*self.machine_config.SCREEN_EXPECTED_FRAME_RATE,ncheckers['row'],ncheckers['col']))<0.5, False,True)))
        params = {'ncheckers':ncheckers}
        if save_frame_info:
            self._append_to_stimulus_frame_info(params)
        size = utils.rc_multiply_with_constant(ncheckers, square_size_pixel)
        self._init_texture(size)
        for frame_i in range(nframes):
            texture = checker_colors[frame_i]
            texture = numpy.rollaxis(numpy.array(3*[numpy.cast['float'](texture)]), 0,3)
            glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            #self.draw()
            self._flip(trigger = True)
            if self.abort:
                break
        self._deinit_texture()
        if save_frame_info:
            self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
            self._append_to_stimulus_frame_info(params)
            numpy.save(self.filenames['fragments'][0].replace('.mat','.npy'), checker_colors)
        print checker_colors.sum()
        
    def _init_texture(self,size):
        from visexpman.engine.generic import geometry
        vertices = geometry.rectangle_vertices(size, orientation = 0)
        vertices[:,0]+=0.5*self.machine_config.SCREEN_RESOLUTION['col']
        vertices[:,1]+=0.5*self.machine_config.SCREEN_RESOLUTION['row']
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
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
        
    def _deinit_texture(self):
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
            
    def _append_to_stimulus_frame_info(self,values):
        self.stimulus_frame_info[-1]['parameters'].update(values)
    

class StimulationSequences(Stimulations):

    def moving_comb(self, speed, orientation, bar_width, tooth_size, tooth_type, contrast, background,pos):
        '''
        tooth_type: square, sawtooth
        '''
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = False)
        bar_width_pix = self.config.SCREEN_UM_TO_PIXEL_SCALE*bar_width
        tooth_size_pix = self.config.SCREEN_UM_TO_PIXEL_SCALE*tooth_size
        pos_pix = utils.rc_multiply_with_constant(pos, self.config.SCREEN_UM_TO_PIXEL_SCALE)
        converted_background_color = colors.convert_color(self.config.BACKGROUND_COLOR, self.config)
        combv,nshapes=self._draw_comb(orientation, bar_width_pix, tooth_size_pix, tooth_type)
        combv = geometry.rotate_point(utils.cr((combv[:,0],combv[:,1])),orientation,utils.cr((0,0)))
        combv = numpy.array([combv['col'], -combv['row']]).T
        trajectories, trajectory_directions, duration = self.moving_shape_trajectory(bar_width, [speed], [orientation],1,0,shape_starts_from_edge=True)
        glEnableClientState(GL_VERTEX_ARRAY)
        nvertice = (combv.shape[0]-4)/(nshapes-1)
        for frame_i in range(trajectories[0].shape[0]):
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv(colors.convert_color(contrast, self.config))
            v=combv + numpy.array([trajectories[0][frame_i]['col']*self.config.SCREEN_UM_TO_PIXEL_SCALE+pos_pix['col'],trajectories[0][frame_i]['row']*self.config.SCREEN_UM_TO_PIXEL_SCALE+pos_pix['row']])
            glVertexPointerf(v)
            for shi in range(nshapes):
                if shi == 0:
                    glDrawArrays(GL_POLYGON,  0, 4)
                else:
                    glDrawArrays(GL_POLYGON,  4+(shi-1)*nvertice, nvertice)
            self._flip(trigger = True)
            if self.abort:
                break
        glDisableClientState(GL_VERTEX_ARRAY)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
    
    def _draw_comb(self, orientation, bar_width, tooth_size, tooth_type):
        bar_height = numpy.sqrt(self.machine_config.SCREEN_RESOLUTION['row']**2+self.machine_config.SCREEN_RESOLUTION['col']**2)
        vertices = geometry.rectangle_vertices(utils.cr((bar_width,bar_height)))
        if tooth_type == 'sawtooth':
            tooth_v = geometry.triangle_vertices(tooth_size)
            offset = numpy.array([0,0])
            tooth_spacing = tooth_size
            ntooth = int(bar_height/tooth_size)
        elif tooth_type == 'square':
            tooth_v = geometry.rectangle_vertices(utils.rc((tooth_size,tooth_size)))
            offset = numpy.array([0.5*tooth_size,0])
            tooth_spacing = 2*tooth_size
            ntooth = int(bar_height/tooth_size/2)
        for toothi in range(ntooth):
            rel_position = numpy.array([0.5*(bar_width-0*tooth_size), (toothi+0.5)*tooth_spacing-0.5*bar_height])
            vertices = numpy.concatenate((vertices, tooth_v+offset+rel_position))
        nshapes = ntooth + 1
        return vertices,nshapes
        
    def moving_cross(self, speeds, sizes, position, movement_directions):
        self._save_stimulus_frame_info(inspect.currentframe())
        bar_height = 3*numpy.sqrt(self.machine_config.SCREEN_SIZE_UM['row']**2+self.machine_config.SCREEN_SIZE_UM['col']**2)
        ds = numpy.array(speeds)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        movement = float(max(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']))+max(sizes)
        trajectories = []
        for i in range(len(movement_directions)):
            startp = geometry.point_coordinates(0.5*movement, numpy.radians(movement_directions[i]-180), self.config.SCREEN_CENTER)
            if i>0:
                startp = utils.rc_add(startp, position)
            endp = geometry.point_coordinates(0.5*movement, numpy.radians(movement_directions[i]), self.config.SCREEN_CENTER)
            if ds[i] == 0:
                startp = position
                trajectories.append(numpy.repeat(startp,trajectories[0].shape[0]))
            else:
                trajectories.append(numpy.tile(utils.calculate_trajectory(startp, endp, ds[i]),int(numpy.ceil(ds[i]/ds[0]))))
            if i>0:
                if trajectories[0].shape[0]<trajectories[i].shape[0]:
                    trajectories[i] = trajectories[i][:trajectories[0].shape[0]]
        nframes = trajectories[0].shape[0]
        trajectories = numpy.array([numpy.array([t['col'], t['row']]) for t in trajectories])
        trajectories = numpy.concatenate([trajectories[:,:,i] for i in range(trajectories.shape[2])])
        base_vertices = numpy.concatenate([geometry.rectangle_vertices(utils.rc((bar_height, sizes[i])), movement_directions[i]) for i in range(len(sizes))]).T
        vertices = numpy.tile(base_vertices,trajectories.shape[0]/2).T
        vertices += numpy.repeat(trajectories,4,axis=0)
        vertices *= self.config.SCREEN_UM_TO_PIXEL_SCALE
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        for frame_i in range(nframes):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv(colors.convert_color(1.0, self.config))
            glDrawArrays(GL_POLYGON, frame_i*8, 4)
            glDrawArrays(GL_POLYGON, frame_i*8+4, 4)
            self._flip(trigger = True)
            if self.abort:
                break
        glDisableClientState(GL_VERTEX_ARRAY)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
    def flash_stimulus(self, timing, flash_color = 1.0, background_color = 0.0, repeats = 1):
        '''
        timing: a series of durations have to be provided in seconds to define a flashing pattern. The first item is always displayed with background color
        '''
        for repeat in range(repeats):
            state = False
            for duration in timing:
                if state:
                    self.show_fullscreen(color = flash_color, duration = duration)
                else:
                    self.show_fullscreen(color = background_color, duration = duration)
                state = not state
            
    def angle2screen_pos(self,angle,axis=None):
        distance_from_center = self.machine_config.SCREEN_DISTANCE_FROM_MOUSE_EYE*numpy.tan(numpy.radians(angle))
        if axis!=None:
            distance_from_center+=self.machine_config.SCREEN_CENTER[axis]
        self.machine_config.SCREEN_PIXEL_WIDTH#mm
        return (distance_from_center/self.machine_config.SCREEN_PIXEL_WIDTH)/self.machine_config.SCREEN_UM_TO_PIXEL_SCALE#um coordinate
        
    def angle2size(self,size_deg, pos_deg):
        minangle=utils.rc_add(pos_deg,utils.rc_multiply_with_constant(size_deg,0.5),'-')
        maxangle=utils.rc_add(pos_deg,utils.rc_multiply_with_constant(size_deg,0.5),'+')
        size_row=self.angle2screen_pos(maxangle['row'],'row')-self.angle2screen_pos(minangle['row'],'row')
        size_col=self.angle2screen_pos(maxangle['col'],'col')-self.angle2screen_pos(minangle['col'],'col')
        return utils.rc((size_row,size_col))

    def receptive_field_explore(self,shape_size, on_time, off_time, nrows = None, ncolumns=None, display_size = None, flash_repeat = 1, sequence_repeat = 1, background_color = None, shape_colors = [1.0], random_order = False):
        '''        
        Aka Marching Squares
    
        Input parameters/use cases
        1) nrows, ncolumns -> if None, automatically calculate for the whole screen surface
        2) shape size -> if none, nrows and ncolumns and screen size will be used for determining the shape size
        3) optional: display area
        4) Random order
        5) Colors
        6) On time, off time
        7) flash repeat
        8) Sequence repeat
        9) Background color
    
        '''
        shape_size, nrows, ncolumns, display_size, shape_colors, background_color = \
                self._parse_receptive_field_parameters(shape_size, nrows, ncolumns, display_size, shape_colors, background_color)
        duration, positions = self.receptive_field_explore_durations_and_positions(shape_size=shape_size, 
                                                                            nrows = nrows,
                                                                            ncolumns = ncolumns,
                                                                            shape_colors = shape_colors,
                                                                            flash_repeat = flash_repeat,
                                                                            sequence_repeat = sequence_repeat,
                                                                            on_time = on_time,
                                                                            off_time = off_time)
        import random,itertools
        positions_and_colors=[[c,p] for c,p in itertools.product(shape_colors,positions)]
        import pdb
#        pdb.set_trace()
        if random_order:
            ct=0
            while True:
                positions_and_colors,success = utils.shuffle_positions_avoid_adjacent(positions_and_colors,shape_size)
                if success:
                    break
                else:
                    ct+=1
                if ct>=10:
                    raise RuntimeError('Could not generate non adjacent random order of squares')
                    
            #random.shuffle(positions_and_colors)
        if hasattr(self.experiment_config, 'SIZE_DIMENSION') and self.experiment_config.SIZE_DIMENSION=='angle':
            positions_and_colors_angle=positions_and_colors
            #Consider positions in degree units and convert them to real screen positions
            #correct for screen center
            screen_center_um=self.machine_config.SCREEN_CENTER
            positions_and_colors = [[c,utils.rc((p['row']-screen_center_um['row'], p['col']-screen_center_um['col']))] for c,p in positions_and_colors]
            #Correct for display center
            center_angle_correction=utils.rc_add(utils.rc_multiply_with_constant(display_size,0.5),self.experiment_config.DISPLAY_CENTER,'-')
            positions_and_colors = [[c,utils.rc((p['row']-center_angle_correction['row'], p['col']-center_angle_correction['col']))] for c,p in positions_and_colors]
            #Convert angles to positions
            positions_and_colors = [[p,self.angle2size(shape_size, p),c,utils.rc((self.angle2screen_pos(p['row'],'row'),self.angle2screen_pos(p['col'],'col')))] for c, p in positions_and_colors]
            pos=numpy.array([p for a,d,c,p in positions_and_colors])
            offset=utils.cr(((pos['col'].max()+pos['col'].min())/2,(pos['row'].max()+pos['row'].min())/2))
            #offset=utils.rc_add(offset,screen_center_um,'+')
            positions_and_colors = [[a,d,c,utils.rc_add(p,offset,'-')] for a,d,c, p in positions_and_colors]
            #Convert to ulcorner
            if self.machine_config.COORDINATE_SYSTEM=='ulcorner':
                positions_and_colors = [[a,d,c,utils.rc((-p['row']+0.5*self.machine_config.SCREEN_SIZE_UM['row'],p['col']+0.5*self.machine_config.SCREEN_SIZE_UM['col']))] for a,d,c, p in positions_and_colors]
        else:
            positions_and_colors= [[0,shape_size,c,p] for c,p in positions_and_colors]
        self.nrows=nrows
        self.ncolumns=ncolumns
        self.shape_size=shape_size
        self.show_fullscreen(color = background_color, duration = off_time)
        for r1 in range(sequence_repeat):
            for angle,shape_size_i, color,p in positions_and_colors:
                    print angle
                    #print shape_size_i['row']
            #for p in positions:
             #   for color in shape_colors:
                    for r2 in range(flash_repeat):
                        if self.abort:
                            break
                        if hasattr(self, 'block_start'):
                            self.block_start(block_name = 'position')
                        self.show_fullscreen(color = background_color, duration = off_time*0.5)
                        self.show_shape(shape = 'rect',
                                    size = shape_size_i,
                                    color = color,
                                    background_color = background_color,
                                    duration = on_time,
                                    pos = p,
                                    angle=angle)
                        self.show_fullscreen(color = background_color, duration = off_time*0.5)
                        if hasattr(self, 'block_end'):
                            self.block_end(block_name = 'position')
        
    def _parse_receptive_field_parameters(self, shape_size, nrows, ncolumns, display_size, shape_colors, background_color):
        if background_color is None:
            background_color = self.experiment_config.BACKGROUND_COLOR
        if not isinstance(shape_colors, list):
            shape_colors = [shape_colors]
        if display_size is None:
            display_size = self.machine_config.SCREEN_SIZE_UM
        if shape_size is None:
            shape_size = utils.rc((display_size['row']/float(nrows), display_size['col']/float(ncolumns)))
        elif not hasattr(shape_size, 'dtype'):
            shape_size = utils.rc((shape_size, shape_size))
        if nrows is None and ncolumns is None:
            nrows = int(numpy.floor(display_size['row']/float(shape_size['row'])))
            ncolumns = int(numpy.floor(display_size['col']/float(shape_size['row'])))
        return shape_size, nrows, ncolumns, display_size, shape_colors, background_color
        
    def _receptive_field_explore_positions(self,shape_size, nrows, ncolumns):
        if shape_size.shape == (1, ):
            shape_size = shape_size[0]
        y_dir = 1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
        first_position = utils.rc_add(self.machine_config.SCREEN_CENTER, utils.rc((shape_size['row']*(0.5*nrows-0.5)*y_dir, shape_size['col']*(0.5*ncolumns-0.5))), '-')
        positions = []
        for r in range(nrows):
            for c in range(ncolumns):
                p=utils.rc_add(first_position, utils.rc((y_dir*r*shape_size['row'], c*shape_size['col'])))
                positions.append(p)
        return positions
        
    def receptive_field_explore_durations_and_positions(self, **kwargs):
        positions = self._receptive_field_explore_positions(kwargs['shape_size'], kwargs['nrows'], kwargs['ncolumns'])
        offtime=kwargs['off_time'] if kwargs['off_time']>0 else 2.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        return len(positions)*len(kwargs['shape_colors'])*kwargs['flash_repeat']*kwargs['sequence_repeat']*(kwargs['on_time']+offtime)+offtime, positions
        
    def moving_grating_stimulus(self):
        pass

    def moving_shape_trajectory(self, size, speeds, directions,repetition,pause=0.0,shape_starts_from_edge=False):
        '''
        Calculates moving shape trajectory and total duration of stimulus
        '''
        if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
            self.vaf = 1
        else:
            self.vaf = -1
        if self.machine_config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
            self.haf = 1
        else:
            self.has = -1
        if not (isinstance(speeds, list) or hasattr(speeds,'dtype')):
            speeds = [speeds]
        if hasattr(size, 'dtype'):
            shape_size = max(size['row'], size['col'])
        else:
            shape_size = size
        if shape_starts_from_edge:
            self.movement = max(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) + shape_size
        else:
            self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) - shape_size # ref to machine conf which was started
        trajectory_directions = []
        trajectories = []
        nframes = 0
        for spd in speeds:
            for direction in directions:
                for rep in range(repetition):
                    end_point = utils.rc_add(utils.cr((0.5 * self.movement *  numpy.cos(numpy.radians(self.vaf*direction)), 0.5 * self.movement * numpy.sin(numpy.radians(self.vaf*direction)))), self.machine_config.SCREEN_CENTER, operation = '+')
                    start_point = utils.rc_add(utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(self.vaf*direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(self.vaf*direction - 180.0)))), self.machine_config.SCREEN_CENTER, operation = '+')
                    if spd == 0:
                        raise RuntimeError('Zero speed is not supported')
                    spatial_resolution = spd/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                    trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))
                    nframes += trajectories[-1].shape[0]
                    trajectory_directions.append(direction)
        duration = float(nframes)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE  + (len(speeds)*len(directions)*repetition+1)*pause
        return trajectories, trajectory_directions, duration
        
        
    def moving_curtain(self,speed, color = 1.0, direction=0.0, background_color = 0.0, pause = 0.0, noshow=False):
        if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
            self.vaf = 1
        else:
            self.vaf = -1
        if self.machine_config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
            self.haf = 1
        else:
            self.has = -1
        self.log_on_flip_message_initial = 'moving_curtain(' + str(color)+ ', ' + str(background_color) +', ' + str(speed) +', ' + str(direction) +', ' + str(pause) + ' )'
        self._save_stimulus_frame_info(inspect.currentframe())
        movement = numpy.sqrt(self.machine_config.SCREEN_SIZE_UM['col']**2+self.machine_config.SCREEN_SIZE_UM['row']**2)
        size = utils.rc((movement, movement))
        end_point = self.machine_config.SCREEN_CENTER
        start_point = utils.rc_add(utils.cr((0.5 * 2 * movement * numpy.cos(numpy.radians(self.vaf*direction - 180.0)), 0.5 * 2 * movement * numpy.sin(numpy.radians(self.vaf*direction - 180.0)))), self.machine_config.SCREEN_CENTER, operation = '+')
        pos = utils.calculate_trajectory(start_point, end_point, speed/self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        if noshow:
            return pos
        if pause > 0:
            self.show_fullscreen(duration = pause, color = background_color, save_frame_info = False)
        for p in pos:
            self.show_shape(shape = 'rect',  pos = p,  
                            color = color,  background_color = background_color,  orientation =self.vaf*direction , size = size)
            if self.abort:
                break
        if pause > 0:
            self.show_fullscreen(duration = pause, color = color, save_frame_info = False)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
#class FlashConfig(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        #Timing        
#        self.WAIT_BEFORE_FLASH = 5.0
#        self.FLASH_TIME = 10.0
#        self.PERIOD_TIME = 60.0
#        self.REPEATS = 3.0
#        self.BLACK = 0.0
#        self.WHITE = 1.0
#        self.runnable = 'Flash'
#        
#        self._create_parameters_from_locals(locals())
#        
#class Flash(experiment.Experiment):
#    
#    def prepare(self):
#        pass
#
#    def run(self, fragment_id=0):
#        for repeat in range(self.experiment_config.REPEATS):
#            self.show_fullscreen(color = self.experiment_config.BLACK, duration = self.experiment_config.WAIT_BEFORE_FLASH)
#            self.show_fullscreen(color = self.experiment_config.WHITE, duration = self.experiment_config.FLASH_TIME)
#            self.show_fullscreen(color = self.experiment_config.BLACK, duration = self.experiment_config.PERIOD_TIME - self.experiment_config.WAIT_BEFORE_FLASH - self.experiment_config.FLASH_TIME)

if __name__ == "__main__":
    pass
