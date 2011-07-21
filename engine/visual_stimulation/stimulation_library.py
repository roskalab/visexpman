import os.path
import os
import numpy
import math

import time
import Image

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# import psychopy.visual
# import psychopy.core
# import psychopy.log
import visexpman.engine.generic.parametric_control
import visexpman.users.zoltan.test.stimulus_library_test_data
from visexpman.engine.generic import utils

class Stimulations():
    """
    Contains all the externally callable stimulation patterns:
    1. show_image(self,  path,  duration = 0,  position = (0, 0),  formula = [])
    """
    def __init__(self,  config,  user_interface,  stimulation_control,  parallel):
        self.config = config
        self.screen = user_interface.screen
        self.stimulation_control = stimulation_control
        self.parallel = parallel
        start_time = time.time()         
        if not os.path.exists(self.config.DEFAULT_IMAGE_FILE) or os.stat(self.config.DEFAULT_IMAGE_FILE)[6]==0: # check for zeros sized file too
            Image.fromarray(numpy.ones((128, 128, 3), numpy.uint8)).save(self.config.DEFAULT_IMAGE_FILE, 'bmp')
        #self.image = psychopy.visual.SimpleImageStim(self.screen,  image = self.config.DEFAULT_IMAGE_FILE)         
        #self.shape = psychopy.visual.ShapeStim(self.screen)
        #self.inner_circle = psychopy.visual.ShapeStim(self.screen)
        
        default_texture = Image.new('RGBA',  (16, 16))
        #self.checkerboard = psychopy.visual.PatchStim(self.screen,  tex = default_texture)
        #self.gratings = psychopy.visual.PatchStim(self.screen,  tex = default_texture)
        #self.image_list = psychopy.visual.PatchStim(self.screen,  tex = default_texture)
        self.backgroundColor = utils.convert_color(self.config.BACKGROUND_COLOR)        
        
        self.flip_time = time.time()
        self.flip_times = []
        
        #self.test_message = psychopy.visual.TextStim(self.screen,  text = '',  pos = (0, 0),  color = self.config.TEXT_COLOR,  height = self.config.TEXT_SIZE)        
        
        if self.config.ENABLE_PARALLEL_PORT:
            import parallel
            self.bitmask = 0
        
    #Helper functions for showing stimulus
    def _show_stimulus(self,  duration, stimulus, flip = True):
        """
        This function shows the stimulus on the display for the required time. 
        TBD        
        
        """        
        if duration == 0.0:            
            if isinstance(stimulus, list):
                for stimulus_item in stimulus:                    
                    stimulus_item.draw()
            else:
                stimulus.draw()
            if flip == True:
                self._flip(trigger = True)
        else:
            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):
                if isinstance(stimulus, list):
                    for stimulus_item in stimulus:
                        stimulus_item.draw()
                else:
                    stimulus.draw()
                if i == 0:
                    self._flip(trigger = True)
                else:
                    self._flip(trigger = False)
                if self.stimulation_control.abort_stimulus():                    
                    break        
    
    def _flip(self,  trigger = False,  saveFrame = False):
        """
        Flips screen buffer. Additional operations are performed here: saving frame and generating trigger
        """
        
        now = time.time()
        wait = self.stimulation_control.wait_time - (now - self.flip_time)
        if self.stimulation_control.wait_time > 0.0:
            if wait > 0.0:
                time.sleep(wait)           
        self.screen.flip()        
            
        self.flip_time = time.time()
        
        if trigger:
            self._frame_trigger_pulse()
            
        if self.config.ENABLE_FRAME_CAPTURE:            
            pass
#             self.screen.getMovieFrame()            
        
        #periodic pause
        if self.config.ACTION_BETWEEN_STIMULUS != 'no':
            elapsed_time = int(now - self.stimulation_control.stimulation_start_time)
            if elapsed_time % self.config.SEGMENT_DURATION == 0 and elapsed_time >= self.config.SEGMENT_DURATION :                
#                 psychopy.log.data('Pause')
                if self.config.ACTION_BETWEEN_STIMULUS == 'keystroke':
                    while True:
                        if self.stimulation_control.is_next_pressed():
                            break
                elif self.config.ACTION_BETWEEN_STIMULUS.find('wait')  != -1:
                    time.sleep(float(self.config.ACTION_BETWEEN_STIMULUS.replace('wait_',  '')))
                    
                
        
    def _frame_trigger_pulse(self):
        '''
        Generates frame trigger pulses
        '''
        if self.config.ENABLE_PARALLEL_PORT:
            self.parallel.setData(self.config.FRAME_TRIGGER_ON | self.bitmask)
            time.sleep(self.config.FRAME_TRIGGER_PULSE_WIDTH)
            self.parallel.setData(self.config.FRAME_TRIGGER_OFF | self.bitmask)
        
    #Externally callable functions showing different visual patterns
    def set_background(self,  color):        
#        self.screen.setColor(utils.convert_color(color))
        self.backgroundColor = utils.convert_color(color)        
        
    def clear_screen(self, duration = 0.0,  color = None):
        
        if color == None:
            color_to_set = self.config.BACKGROUND_COLOR
        else:
            color_to_set = color
            
#         self.screen.logOnFlip('clear_screen(' + str(duration) + ', ' + str(color_to_set) + ')',  psychopy.log.DATA)
        self.screen.clear_screen(color = color_to_set)
        self.set_background(color_to_set)
#         self.screen.clearBuffer()
        if duration == 0.0:
            self._flip()
        else:
            for i in range(int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)):
                self._flip()
                
    def show_image(self,  path,  duration = 0,  position = (0, 0),  formula = [],  size = None):
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
        position_p = (self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1])
        if os.path.isdir(path) == True:
            #when content of directory is to be shown
            image_file_paths = os.listdir(path)
            image_file_paths.sort()
            #initialize parametric control
            start_time = time.time()            
            posx_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[0],  start_time)
            posy_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[1],  start_time) 
            
            for image_file_path in image_file_paths:
                if len(formula) > 0:
                    #parametric control
                    parametric_data_x = formula[0]
                    parametric_data_y = formula[1]
                    actual_time_tick = time.time()
                    posx_parametric_control.update(value = None,  parameters = parametric_data_x[1],  formula = parametric_data_x[0],  time_tick = actual_time_tick)
                    posy_parametric_control.update(value = None,  parameters = parametric_data_y[1],  formula = parametric_data_y[0],  time_tick = actual_time_tick)
                    parametric_position =  (posx_parametric_control.value,  posy_parametric_control.value)
                    self._show_image_file(path + os.sep + image_file_path,  duration,  parametric_position)
                else:
                    self._show_image_file(path + os.sep + image_file_path,  duration,  position)                    
                    
                if self.stimulation_control.abort_stimulus():
                    break
            
        elif os.path.isfile(path) == True:
            path_adjusted = path
            #resize file
            if size != None and size != (0,  0):                
                stimulus_image = Image.open(path)
                stimulus_image = stimulus_image.resize((int(size[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE), int(size[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)))
                stimulus_image.save(self.config.TEMP_IMAGE_PTH)
                path_adjusted = self.config.TEMP_IMAGE_PTH
            
            #initialize parametric control
            start_time = time.time()            
            posx_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[0],  start_time)
            posy_parametric_control = visexpman.engine.generic.parametric_control.ParametricControl(position[1],  start_time)             
            if len(formula) > 0:
                #parametric control
                for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):
                    parametric_data_x = formula[0]
                    parametric_data_y = formula[1] 
                    actual_time_tick = time.time()
                    posx_parametric_control.update(value = None,  parameters = parametric_data_x[1],  formula = parametric_data_x[0],  time_tick = actual_time_tick)
                    posy_parametric_control.update(value = None,  parameters = parametric_data_y[1],  formula = parametric_data_y[0],  time_tick = actual_time_tick)
                    parametric_position =  (posx_parametric_control.value,  posy_parametric_control.value)                
                    self._show_image_file(path_adjusted, 0,  parametric_position)
            else:            
                #when a single image file is to be shown
                self._show_image_file(path_adjusted, duration,  position)
        else:
            pass
            #invalid path
        

    def _show_image_file(self,  path,  duration,  position, flip = True):
        self.image.setPos((self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1]))        
        self.screen.logOnFlip('_show_image_file(' + path + ', ' + str(duration) + ', ' + str(position) + ')',  psychopy.log.DATA)
        if duration == 0:                                        
                    self.image.setImage(path)
                    self.image.draw()
                    if flip:
                    	self._flip(trigger = True)
        else:
            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):                    
                    self.image.setImage(path)            
                    self.image.draw()
                    if i == 0:
                        if flip:
                            self._flip(trigger = True)
                    else:
                        if flip:
                        	self._flip(trigger = False)
                        
                    
    def show_movie(self,  video_file_path,  position = (0, 0)):
        '''
        Plays a movie file. Pressing 'a' aborts the playback. The video is positioned according to the value of position parameter
        Parametric control of position is no possible. Some frames are always dropped.
        '''        
        position_p = (self.config.SCREEN_PIXEL_TO_UM_SCALE * position[0],  self.config.SCREEN_PIXEL_TO_UM_SCALE * position[1])
        self.movie = psychopy.visual.MovieStim(self.screen,  filename = video_file_path,  pos = position_p) 
        msg = 'video size: ' + str(self.movie.format.height) + ', ' + str(self.movie.format.width)
        psychopy.log.data(msg)
        globalClock = psychopy.core.Clock()
        frame_counter = 0
        while globalClock.getTime() < self.movie.duration: 
            self._flip() 
            self._frame_trigger_pulse()
            self.movie.draw()
            frame_counter = frame_counter + 1
            self.screen.logOnFlip(str(frame_counter) + ' show_movie(' + video_file_path +  ', ' + str(position) + ')', psychopy.log.DATA)            
            if self.stimulation_control.abort_stimulus():
                break
            
    def show_shape(self,  shape = '',  duration = 0.0,  pos = (0,  0),  color = [1.0,  1.0,  1.0],  orientation = 0.0,  size = [0,  0],  formula = [],  ring_size = 1.0, flip = True):
        '''
        This function shows simple, individual shapes like rectangle, circle or ring. It is shown for one frame time when the duration is 0. Otherwise parametric control is available while the time defined by duration.
        
        The following parameters can be controlled: position, color, orientation
        
        Usage:
        1.  Show a single rectangle for one frame time, the default color is white, and the default position is in the center of the screen:
            show_shape(shape = 'rect',  duration = 0.0,  size = [10,  100])
        2. Show an annuli stimulus for 1 second
            show_shape(shape = 'annuli',  duration = 1.0,  color = [1.0, 0.0, 0.0], size = [210,  100],  ring_size = [50,  10])
        3. Show a rectangle with where position, orientation and color are parametrically controlled:
            #first set formula and parameters for parametric control
            parameters = []
            posx = ['100*sin(t)',  parameters]
            posy = ['100*cos(t)',  parameters]
            ori = ['',  []]  #unconfigured parametric control
            color_r = ['sin(t)',  parameters]
            color_g = ['cos(t)',  parameters]
            color_b = ['cos(t+pi*0.25)',  parameters]
            #the order of parametric control configurations matter
            formula = [posx,  posy,  ori, color_r,  color_g,  color_b]
            show_shape(shape = 'rect',  duration = 5.0,  size = [100,  200],  formula = formula)        
        '''
        
        position = pos
        converted_color = utils.convert_color(color)
        if  formula != []:
            parametric_control_enable = True
        else:
            parametric_control_enable = False
        
        if isinstance(size, int) or isinstance(size, float):
            size_adjusted = [size * self.config.SCREEN_PIXEL_TO_UM_SCALE,  size * self.config.SCREEN_PIXEL_TO_UM_SCALE]
        else:
            size_adjusted = []
            for item in size:
                size_adjusted.append(item * self.config.SCREEN_PIXEL_TO_UM_SCALE)        
        
        #calculate the coordinates of the shape's vertices
        if shape == 'rect' or shape == 'rectangle':
            vertices = [[-0.5 * size_adjusted[0], -0.5 * size_adjusted[1]],  [-0.5 * size_adjusted[0], 0.5 * size_adjusted[1]],  [0.5 * size_adjusted[0], 0.5 * size_adjusted[1]],  [0.5 * size_adjusted[0], -0.5 * size_adjusted[1]]]
        elif shape == 'circle' or shape == 'annulus' or shape == 'annuli':
            vertices = utils.calculate_circle_vertices(size_adjusted,  1.0)
        
        if shape == 'annulus' or shape == 'annuli':
            if isinstance(ring_size, list):
                _ring_size = [size_adjusted[0] - ring_size[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  size_adjusted[1] - ring_size[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE]
            else:
                _ring_size = [size_adjusted[0] - ring_size * self.config.SCREEN_PIXEL_TO_UM_SCALE,  size_adjusted[1] - ring_size * self.config.SCREEN_PIXEL_TO_UM_SCALE]
            inner_circle_vertices = utils.calculate_circle_vertices(_ring_size,  1.0) 
        
        if duration == 0.0:            
            #show shape for a single frame
            self.screen.logOnFlip('show_shape(' + shape+ ', ' + str(duration) + ', ' + str(position) + ', ' + str(converted_color)  + ', ' + str(orientation)  + ', ' + str(size) + ')',  psychopy.log.DATA)            
            self.shape.setVertices(vertices)
            self.shape.setFillColor(converted_color)            
            self.shape.setLineColor(converted_color)
            self.shape.setPos((position[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  position[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE))
            self.shape.setOri(orientation)            
            
            if shape == 'annulus' or shape == 'annuli':
                    self.inner_circle.setVertices(inner_circle_vertices) 
                    self.inner_circle.setFillColor(self.backgroundColor)                
                    self.inner_circle.setLineColor(self.backgroundColor)
                    self.inner_circle.setPos((position[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  position[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE))
                    self.inner_circle.setOri(orientation)
                    
            self.shape.draw()
            if flip:
            	self._flip(trigger = True)
        else:            
            #initialize parametric control
            if parametric_control_enable:
                #convert color to Presentinator color format so that parametric control could handle this format
                color_presentinator_format = utils.convert_color_from_pp(converted_color)                
                start_time = time.time()
                posx_pc = visexpman.engine.generic.parametric_control.ParametricControl(position[0],  start_time)
                posy_pc = visexpman.engine.generic.parametric_control.ParametricControl(position[1],  start_time) 
                ori_pc = visexpman.engine.generic.parametric_control.ParametricControl(orientation,  start_time)                 
                color_r_pc = visexpman.engine.generic.parametric_control.ParametricControl(color_presentinator_format[0],  start_time) 
                color_g_pc = visexpman.engine.generic.parametric_control.ParametricControl(color_presentinator_format[1],  start_time) 
                color_b_pc = visexpman.engine.generic.parametric_control.ParametricControl(color_presentinator_format[2],  start_time)          
                
                posx_pars = formula[0]
                posy_pars = formula[1]
                ori_pars = formula[2]
                color_r_pars = formula[3]
                color_g_pars = formula[4]
                color_b_pars = formula[5]
            
            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):                                               
                #parametric control                
                if parametric_control_enable: 
                    actual_time_tick = time.time()                    
                    posx_pc.update(value = None,  parameters = posx_pars[1],  formula = posx_pars[0],  time_tick = actual_time_tick)                    
                    posy_pc.update(value = None,  parameters = posy_pars[1],  formula = posy_pars[0],  time_tick = actual_time_tick)                    
                    ori_pc.update(value = None,  parameters = ori_pars[1],  formula = ori_pars[0],  time_tick = actual_time_tick)                    
                    color_r_pc.update(value = None,  parameters = color_r_pars[1],  formula = color_r_pars[0],  time_tick = actual_time_tick)                    
                    color_g_pc.update(value = None,  parameters = color_g_pars[1],  formula = color_g_pars[0],  time_tick = actual_time_tick)                    
                    color_b_pc.update(value = None,  parameters = color_b_pars[1],  formula = color_b_pars[0],  time_tick = actual_time_tick)
                    position_to_set = (posx_pc.value,  posy_pc.value)
                    orientation_to_set = ori_pc.value
                    color_to_set = utils.convert_color((color_r_pc.value,  color_g_pc.value,  color_b_pc.value))
                else:
                    position_to_set = position                    
                    orientation_to_set = orientation                    
                    color_to_set = converted_color

                self.screen.logOnFlip('show_shape(' + shape+ ', ' + str(duration) + ', ' + str(position_to_set) + ', ' + str(color_to_set)  + ', ' + str(orientation_to_set)  + ', ' + str(size) + ')',  psychopy.log.DATA)
                self.shape.setVertices(vertices)                 
                self.shape.setFillColor(color_to_set)                
                self.shape.setLineColor(color_to_set)  
                self.shape.setPos((position_to_set[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  position_to_set[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE))
                self.shape.setOri(orientation_to_set)                
                
                if shape == 'annulus' or shape == 'annuli':
                    self.inner_circle.setVertices(inner_circle_vertices) 
                    self.inner_circle.setFillColor(self.backgroundColor)                
                    self.inner_circle.setLineColor(self.backgroundColor)
                    self.inner_circle.setPos((position_to_set[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  position_to_set[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE))
                    self.inner_circle.setOri(orientation_to_set)
                
                self.shape.draw() 
                if shape == 'annulus' or shape == 'annuli':
                    self.inner_circle.draw() 
                    
                if formula == []:
                    if i == 0:
                        self._flip(trigger = True)
                    else:
                        self._flip(trigger = False)
                else:
                    self._flip(trigger = True)
                    
                if self.stimulation_control.abort_stimulus():
                    break
                    
    def show_checkerboard(self,   n_checkers,  duration = 0.0,  pos = (0,  0),  color = [],  box_size = (0, 0), flip = True):
        '''
        Shows checkerboard:
            n_checkers = (x dir (column), y dir (rows)), above 32x32 config, frame drop may occur
            pos - position of display area
            color - array of color values. Each item corresponds to one box
            box_size - size of a box in pixel   
            duration - duration of stimulus in seconds            
            color - array of color values. Each item corresponds to one box. 0 position is the top left box, the last one is the bottom right
        Usage example:
            n_checkers = (21, 21)
            box_size = [80, 50]    
            n_frames = 100    
            cols = random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames) 
            for i in range(n_frames):
                self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols[i], box_size = box_size)
        '''
        
        box_size_p = (box_size[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  box_size[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        pos_p = (pos[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  pos[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        
        #check if number of boxes are the power of two
        max_checker_number = max(n_checkers)
        checker_number_two_log = math.log(max_checker_number,  2)
        if checker_number_two_log != math.floor(checker_number_two_log) or  n_checkers[0] != n_checkers[1]:
            new_size = int(2 ** math.ceil(checker_number_two_log))
            n_checkers_fixed = (new_size,  new_size)
        else:
            n_checkers_fixed = n_checkers            
        
        #centerpoint is shifted, so an offset shall be calculated to move it back
        x_offset = int((n_checkers_fixed[0] - n_checkers[0]) * box_size_p[0] * 0.5)
        y_offset = int((n_checkers_fixed[1] - n_checkers[1]) * box_size_p[1] * 0.5)
        pos_offset = (pos_p[0]  + x_offset,  pos_p[1]  - y_offset)
            
        self.screen.logOnFlip('show_checkerboard(' + str(n_checkers)+ ', ' + str(duration) + ', ' + str(pos) + ', ' + str(color[:self.config.MAX_LOG_COLORS])  + ', ' + str(box_size)  + ')',  psychopy.log.DATA) 
        texture = Image.new('RGBA',  n_checkers_fixed) 
        for row in range(n_checkers[1]):
            for column in range(n_checkers[0]):            
                texture.putpixel((column, row),  utils.convert_int_color(utils.convert_color_from_pp(utils.convert_color(color[row * n_checkers[0] + column]))))
        
        self.checkerboard.setPos(pos_offset)
        self.checkerboard.setTex(texture) 
        self.checkerboard.setSize((box_size_p[0] * n_checkers_fixed[0],  box_size_p[1] * n_checkers_fixed[1]))        
        
        self._show_stimulus(duration,  self.checkerboard, flip)

    def show_ring(self,  n_rings, diameter,  inner_diameter = [],  duration = 0.0,  n_slices = 1,  colors = [],  pos = (0,  0), flip = True):
        """
        This stimulation shows concentric rings or circles. The rings/circles can be divided into pie slices.
        n_rings: number of rings to be drawn
        diameter: diameter' of outer rings. The followings are accepted:
                    - list of integers: outer diameter of each rings
                    - list of list of two integers: the two values determine the diameter in the x and y direction
                    - single integer: diameter of first (innermost) ring. The diameter of additional rings will be the multiple of this value
        inner_diameter: The following data types are accepted:
                    - list of integers: inner diameter of each rings, assuming that diameter is a list
                    - list of list of two integers: the two values determine the inner diameter in the x and y direction, assuming that diameter is a list
                    - integer: width of rings regardless of the type of diameter
        duration; duration of stimulus in second. If zero, stimulus is shown for one frame time
        n_slices: number of slices displayed for each ring
        colors: list of colors. The 0 place is the slice in the innermost circle, which angle range is between 0 and a positive number, for example in case of n_slices = 4, the angle range is 0, 90 for the 0. slice.
        pos: center position of stimulus
        
        Use cases:
        1) Show three concentrical circles for 1 second:
            n_rings = 3
            outer_diameter = [100, 120, 140]
            show_ring(n_rings, outer_diameter,  duration = 1.0,  colors = colors)
        2) Show rings 5 rings:
            n_rings = 5
            outer_diameter = 100
            inner_diameter = 5 #width of ring
            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  colors = colors)
        3) Show sliced rings with arbitrary thickness and diameter
            n_rings = 4
            n_slices = 2
            outer_diameter = [100, 200, 300]
            inner_diameter = [90, 180, 250]
            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  n_slices = 2, colors = colors)
        4) Show oval rings
            n_rings = 2
            outer_diameter = [[100, 200], [200, 300]]
            inner_diameter = [[90, 190], [190, 290]]
            show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  colors = colors)        
        """        
        self.screen.logOnFlip('show_rings(' + str(n_rings)+ ', ' + str(diameter) + ', ' + str(inner_diameter) + ', ' + str(duration)  + ', ' + str(n_slices)  + ', ' + str(colors[:self.config.MAX_LOG_COLORS])  + ', ' + str(pos)  + ')',  psychopy.log.DATA)
        
        pos_p = (pos[0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  pos[1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)        
        outer_diameter = diameter       
        
        #sort diameter lists to avoid putting a bigger circle on a smaller one
        if isinstance(outer_diameter, list):
            outer_diameter.sort()
            outer_diameter.reverse()
        
        if isinstance(inner_diameter, list):
            inner_diameter.sort()
            inner_diameter.reverse()        
        
        #if number of rings is not consistent with the number of provided list of diameter values
        if isinstance(outer_diameter, list):
            if n_rings != len(outer_diameter):
                n_rings = len(outer_diameter)                    
        
        if isinstance(outer_diameter, list) and isinstance(inner_diameter, list):            
            if len(inner_diameter) == 0 or (len(inner_diameter) != len(outer_diameter)):
                inner_circles = False
            else:
                inner_circles = True
                
        elif isinstance(outer_diameter, list) and not isinstance(inner_diameter, list):            
            new_inner_diameter = []
            for diameter in outer_diameter:
                if isinstance(diameter,  list):
                    new_inner_diameter.append([diameter[0] - inner_diameter,  diameter[1] - inner_diameter])
                else:
                    new_inner_diameter.append(diameter - inner_diameter)
            inner_diameter = new_inner_diameter
            inner_circles = True
        elif not isinstance(outer_diameter, list):
            outer_diameter = numpy.linspace(outer_diameter,  n_rings * outer_diameter,  n_rings).tolist()
            outer_diameter.reverse()
            if isinstance(inner_diameter, list):
                inner_circles = False
            elif not isinstance(inner_diameter, list):
                new_inner_diameter = []
                for diameter in outer_diameter:
                    new_inner_diameter.append(diameter - inner_diameter)
                inner_diameter = new_inner_diameter                
                inner_circles = True            
        
        slice_angle = 360.0 / n_slices        
        self.ring = []
        for ring in range(n_rings):
            #diameter can be a list (ellipse) or a single integer (circle)            
            if isinstance(outer_diameter[ring],  list):                
                outer_r = [outer_diameter[ring][0]  * self.config.SCREEN_PIXEL_TO_UM_SCALE, outer_diameter[ring][1]  * self.config.SCREEN_PIXEL_TO_UM_SCALE]
            else:
                outer_r = (outer_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  outer_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE)                
            
            if inner_circles:
                if isinstance(inner_diameter[ring],  list):
                    inner_r = (inner_diameter[ring][0] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  inner_diameter[ring][1] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
                else:                    
                    inner_r = (inner_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE,  inner_diameter[ring] * self.config.SCREEN_PIXEL_TO_UM_SCALE)            
            
            for slice in range(n_slices):
                start_angle = slice_angle * slice
                end_angle = slice_angle * (slice + 1)
                vertices = utils.calculate_circle_vertices(outer_r,  start_angle = start_angle,  end_angle = end_angle+1)               
                
                try:
                    color = utils.convert_color(colors[(n_rings -1 - ring) * n_slices + slice])
                except IndexError:
                    color = (-1.0,  -1.0,  -1.0)
                
                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = color,  fillColor = color,  vertices =  vertices,  pos = pos_p))                
            if inner_circles:
                vertices  = utils.calculate_circle_vertices(inner_r)
                self.ring.append(psychopy.visual.ShapeStim(self.screen, lineColor = (-1.0,  -1.0,  -1.0),  fillColor = (-1.0,  -1.0,  -1.0),  vertices =  vertices,  pos = pos_p))
                
        self._show_stimulus(duration,  self.ring,  flip)  
                    
    def show_gratings(self,  duration = 0.0,  profile = 'sqr',  spatial_frequency =-1,  display_area = (0,  0),  orientation = 0,  starting_phase = 0.0,  velocity = 0.0,  color_contrast = 1,  color_offset = 0,  pos = (0,  0),  duty_cycle = 0.5,  noise_intensity = 0):
        """
        This stimulation shows gratings with different color (intensity) profiles.
            - duration: duration of stimulus in seconds
            - profile: shape of gratings color (intensity) profile, the followings are possible:
                - 'sqr': square shape, most common grating profile
                - 'tri': triangle profile
                - 'saw': sawtooth profile
                - 'sin': sine
                - 'cos': cosine
                profile parameter can be a list of these keywords. Then different profiles are applied to each color channel
            - spatial_frequency: length of one period in um (pixel)
            - display area
            - orientation: orientation of gratings in degrees
            - starting_phase: starting phase of stimulus in degrees
            - velocity: velocity of the movement of gratings in pixel/s
            - color_contrast: color contrast of grating stimuli. Can be a single intensity value of an rgb value. Accepted range: 0...1
            - color_offset: color (intensity) offset of stimulus. Can be a single intensity value of an rgb value. Accepted range: 0...1
            - pos: position of stimuli
            - duty_cycle: duty cycle of grating stimulus with sqr profile
            - noise_intensity: Maximum contrast of random noise mixed to the stimulus.
        
        Usage examples:
        1) Show a simple, fullscreen, gratings stimuli for 3 seconds with 45 degree orientation
            show_gratings(duration = 3.0, orientation = 45, velocity = 100, spatial_frequency = 100)
        2) Show gratings with sine profile on a 500x500 area with 10 degree starting phase
            show_gratings(duration = 3.0, profile = 'sin', display_area = (500, 500), starting_phase = 10, velocity = 100, spatial_frequency = 200)
        3) Show gratings with sawtooth profile on a 500x500 area where the color contrast is light red and the color offset is light blue
            show_gratings(duration = 3.0, profile = 'saw', velocity = 100, spatial_frequency = 200, color_contrast = [1.0,0.0,0.0], color_offset = [0.0,0.0,1.0]) 
        """        
        
        if spatial_frequency == -1:
            spatial_frequency_to_set = self.config.SCREEN_RESOLUTION['col']
        else:
            spatial_frequency_to_set = spatial_frequency
            
        self.screen.logOnFlip('show_gratings(' + str(duration)+ ', ' + str(profile) + ', ' + str(spatial_frequency_to_set) + ', ' + str(display_area)  + ', ' + str(orientation)  + ', ' + str(starting_phase)  + ', ' + str(velocity)  + ', ' + str(color_contrast)  + ', ' + str(color_offset) + ', ' + str(pos)  + ')',  psychopy.log.DATA)       
   
        if isinstance(pos, numpy.ndarray):
            column_index = 'col'
            row_index = 'row'
            pos_rc = pos            
        else:
            column_index = 0
            row_index = 1
            pos_rc = utils.rc(pos)
            
        pos_transformed = utils.coordinate_transform(utils.rc_multiply_with_constant(pos_rc, self.config.SCREEN_PIXEL_TO_UM_SCALE), self.config.ORIGO, self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.config.VERTICAL_AXIS_POSITIVE_DIRECTION)
            
        pos_adjusted = []
        pos_adjusted.append(pos_transformed['col'])
        pos_adjusted.append(pos_transformed['row'])

        
        orientation_rad = orientation * math.pi / 180.0
        
        if isinstance(display_area, numpy.ndarray):
            column_index = 'col'
            row_index = 'row'
        else:
            column_index = 0
            row_index = 1
        
        screen_width = display_area[column_index] * self.config.SCREEN_PIXEL_TO_UM_SCALE
        display_area_adjusted = []
        display_area_adjusted.append(display_area[column_index] * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        display_area_adjusted.append(display_area[row_index] * self.config.SCREEN_PIXEL_TO_UM_SCALE) 
        
        #If gratings are to be shown on fullscreen, modify display area so that no ungrated parts are on the screen considering rotation
        if display_area_adjusted[0] == 0:            
            display_area_adjusted[0] = int(self.config.SCREEN_RESOLUTION['col'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['row'] * abs(math.sin(orientation_rad)))
            screen_width = self.config.SCREEN_RESOLUTION['col']
        if display_area_adjusted[1] == 0:            
            display_area_adjusted[1] = int(self.config.SCREEN_RESOLUTION['row'] * abs(math.cos(orientation_rad)) + self.config.SCREEN_RESOLUTION['col'] * abs(math.sin(orientation_rad)))    
        
        #generate texture        
        period_scale = float(display_area_adjusted[0]) / float(spatial_frequency_to_set * self.config.SCREEN_PIXEL_TO_UM_SCALE)
        period = float(self.config.GRATING_TEXTURE_RESOLUTION) / period_scale
        period_original = period
        
        n_periods = float(self.config.GRATING_TEXTURE_RESOLUTION) / float(period)
        n_periods = 2 ** math.ceil(math.log(n_periods,  2))
        if n_periods < 1.0:
            n_periods = 1.0
        period = float(self.config.GRATING_TEXTURE_RESOLUTION) / n_periods
        display_width_correction = period_original / period        
        
        #generate stimulus profile        
        if isinstance(profile, str):
            profile_adjusted = [profile,  profile,  profile]            
        else:
            profile_adjusted = []
            for profile_i in profile:
                profile_adjusted.append(profile_i)        
        
        #contrast and offset can be provided in rgb or intensity. For both the accepted range is 0...1.0
        if not isinstance(color_contrast, list):
            color_contrast_adjusted = [color_contrast,  color_contrast,  color_contrast]
        else:
            color_contrast_adjusted = []
            for color_contrast_i in color_contrast:
                color_contrast_adjusted.append(color_contrast_i)
            
        if not isinstance(color_offset, list):
            color_offset_adjusted = [color_offset,  color_offset,  color_offset]
        else:
            color_offset_adjusted = []
            for color_offset_i in color_offset:
                color_offset_adjusted.append(color_offset_i)            
        
        #modify contrast and offset so that the range of the stimulus profile would fit to the color range of Psychopy
        for i in range(len(color_contrast_adjusted)):
            color_contrast_adjusted[i] = color_contrast_adjusted[i] * 2.0
            color_offset_adjusted[i] = 2.0 * color_offset_adjusted[i]  - 1.0 + 0.5 * color_contrast_adjusted[i]         

        #generate stimulus profiles
        stimulus_profile_r = utils.generate_waveform(profile_adjusted[0], self.config.GRATING_TEXTURE_RESOLUTION, period, color_contrast_adjusted[0], color_offset_adjusted[0], starting_phase, duty_cycle)
        stimulus_profile_g = utils.generate_waveform(profile_adjusted[1], self.config.GRATING_TEXTURE_RESOLUTION, period, color_contrast_adjusted[1], color_offset_adjusted[1], starting_phase, duty_cycle)
        stimulus_profile_b = utils.generate_waveform(profile_adjusted[2], self.config.GRATING_TEXTURE_RESOLUTION, period, color_contrast_adjusted[2], color_offset_adjusted[2], starting_phase, duty_cycle)
        stimulus_profile = numpy.array([stimulus_profile_r,  stimulus_profile_g,  stimulus_profile_b])
        stimulus_profile = stimulus_profile.transpose()
    
        if float(noise_intensity) == 0.0 and self.config.OS_TYPE != 'win':
            texture = numpy.array(stimulus_profile,  ndmin = 3)        
        else:
            texture = numpy.zeros((self.config.GRATING_TEXTURE_RESOLUTION,  self.config.GRATING_TEXTURE_RESOLUTION,  3))
            for i in range(self.config.GRATING_TEXTURE_RESOLUTION):            
                texture[i,  :] = stimulus_profile
            #generate noise            
            noise = numpy.random.rand((texture.shape)[0],  (texture.shape)[1],  (texture.shape)[2]) * noise_intensity
            texture = texture + noise       
        
        #make sure that texture values are in the -1.0...1.0 range
        texture = numpy.where(texture > 1.0,  1.0,  texture)
        texture = numpy.where(texture < -1.0,  -1.0,  texture)       
      
        self.gratings.setTex(texture)
        
        #Spatial frequency is distorted by rounding the number of profile repeats on screen. Consequently the display area has to be stretched to restore required spatial frequency
        display_area_adjusted = (display_area_adjusted[0] * display_width_correction,  display_area_adjusted[1])
        
        self.gratings.setSize(display_area_adjusted) 
        self.gratings.setPhase(0.0)
        self.gratings.setOri(orientation)
        
        #For a phase correct graing stimulus, the stretched texture has to be offset along the x axis and from the right side some columns have to be masked out
        
        #the stretched display area has to be masked to show the stimulus with the right size
        mask = numpy.ones((self.config.GRATING_TEXTURE_RESOLUTION,  self.config.GRATING_TEXTURE_RESOLUTION))
        if display_width_correction < 1.0:
            n_maskable_columns = 0
        else:
            n_maskable_columns = int(round((self.config.GRATING_TEXTURE_RESOLUTION * (1 - 1.0/ display_width_correction))))         
        
        mask[:,  self.config.GRATING_TEXTURE_RESOLUTION - n_maskable_columns : self.config.GRATING_TEXTURE_RESOLUTION] = -1 * mask[:,  self.config.GRATING_TEXTURE_RESOLUTION - n_maskable_columns  : self.config.GRATING_TEXTURE_RESOLUTION]         
        self.gratings.setMask(mask)
        
        #corrigate effect of masking and rotation
        offset = int(float(0.5 * n_maskable_columns) * float(display_area_adjusted[0]) / self.config.GRATING_TEXTURE_RESOLUTION)
        pos_adjusted[0] = pos_adjusted[0] + offset * math.cos(orientation_rad)
        pos_adjusted[1] = pos_adjusted[1] - offset * math.sin(orientation_rad)        
        
        self.gratings.setPos(pos_adjusted)       
        
        # calculate phase step considering stimulus size, frame rate and velocity
        movement_per_frame = float(velocity * self.config.SCREEN_PIXEL_TO_UM_SCALE) / self.config.SCREEN_EXPECTED_FRAME_RATE
        phase_step = movement_per_frame / screen_width / display_width_correction       
        
        if duration == 0.0:            
            self.gratings.draw()
            self._flip(trigger = True)
        else:
            for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):                                                 
                self.gratings.setPhase(phase_step,  '+')
                self.gratings.draw()
                self._flip(trigger = True)
                if self.stimulation_control.abort_stimulus():
                    break
                    
                    
    def show_dots(self,  dot_sizes, dot_positions, ndots, duration = 0.0,  color = (1.0,  1.0,  1.0)):        
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
        #self.screen.logOnFlip('show_dots(' + str(duration)+ ', ' + str(dot_sizes) +', ' + str(dot_positions) +')',  psychopy.log.DATA)
        
        st = time.time()
        
        radius = 1.0
        vertices = utils.calculate_circle_vertices([radius,  radius],  1.0/1.0)
        n_frames = len(dot_positions) / ndots        
        n_vertices = len(vertices)
        #convert dot positions from user coordinate system                    
#         transformed_dot_positions = utils.coordinate_transform(dot_positions, self.config.ORIGO, self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.config.VERTICAL_AXIS_POSITIVE_DIRECTION)
        transformed_dot_positions = dot_positions
        frames_vertices = numpy.zeros((n_frames * ndots * n_vertices,  2)) 
        pixel_scale = numpy.array(self.config.SCREEN_UM_TO_NORM_SCALE)
        index = 0
        for frame_i in range(n_frames):
            for dot_i in range(ndots):
                dot_index = frame_i * ndots + dot_i
                dot_size = dot_sizes[dot_index]
                dot_position = numpy.array((transformed_dot_positions[dot_index]['col'], transformed_dot_positions[dot_index]['row']))
                dot_to_screen =  self.config.SCREEN_UM_TO_PIXEL_SCALE * (vertices * dot_size + dot_position)
                frames_vertices[index: index + n_vertices] = dot_to_screen
                index = index + n_vertices

        if duration == 0:
            n_frames_per_pattern = 1
        else:
            n_frames_per_pattern = int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))
        
#        print time.time() - st        
        glEnableClientState(GL_VERTEX_ARRAY)
        dot_pointer = 0
        for frame_i in range(n_frames):            
            start_i = dot_pointer * n_vertices
            end_i = (dot_pointer + ndots) * n_vertices
            dot_pointer = dot_pointer + ndots
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
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
                if i == 0:
                    self._flip(trigger = True)
                else:
                    self._flip(trigger = False)
                if self.stimulation_control.visual_stimulation_runner.abort:
                    break
                
        glDisableClientState(GL_VERTEX_ARRAY)
        
    def show_drum(self,  duration,  rpm,  n_stripes,  drum_base_size ,  drum_height, contraction,  pos = (0, 0),  color = 1.0,  background_color = 0.0,  duty_cycle = 0.5):
        '''
        THIS IS OBSOLETE
        Parameters:
            duration: duration of stimulus in s
            rpm: rotaional speed in rpm
            n_stripes: number of stripes
            drum_base_size: size of drum base in pixel
            drum_height: height of drum in pixels
            contraction: ratio of contraction in respect of stripe_width_at_base           
            
        '''
        #NOTE: antialiasing would be nice
        n_vertices_per_stripe = 20 #number of vertices per arc
        delta_angle = rpm / 60.0 * 360.0 / self.config.SCREEN_EXPECTED_FRAME_RATE        
        
        n_frames = int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)
        outer_arc_diameter = drum_base_size + 2 * drum_height
        angle_range_per_stripe = 360.0 / float(n_stripes)
        angle_range_inner = angle_range_per_stripe * duty_cycle
        angle_range_outer = angle_range_per_stripe * duty_cycle * contraction * (drum_base_size * 0.5) / (0.5 * drum_base_size + drum_height)       
        vertices = numpy.zeros((n_frames * n_vertices_per_stripe * n_stripes * 2,  2))
        for frame_i in range(n_frames):
            for stripe in range(n_stripes):
                angle = stripe * angle_range_per_stripe + delta_angle * frame_i
                inner_arc_vertices = visexpman.engine.generic.utilities.arc_vertices(1.0, n_vertices_per_stripe,  angle, angle_range_inner)
                inner_arc_vertices = (inner_arc_vertices * numpy.array(drum_base_size) + pos) * self.config.SCREEN_UM_TO_NORM_SCALE            
                outer_arc_vertices = visexpman.engine.generic.utilities.arc_vertices(1.0, n_vertices_per_stripe,  angle, angle_range_outer)
                outer_arc_vertices = (outer_arc_vertices * outer_arc_diameter + pos) * self.config.SCREEN_UM_TO_NORM_SCALE            
                vertices[n_stripes * frame_i * 2 * n_vertices_per_stripe + stripe * 2 * n_vertices_per_stripe: n_stripes * frame_i * 2 * n_vertices_per_stripe + (stripe + 1) * 2 * n_vertices_per_stripe] = numpy.concatenate((outer_arc_vertices,  inner_arc_vertices[::-1]))
            
        background_color_converted = utils.convert_to_rgb(background_color)
        glClearColor(background_color_converted[0],  background_color_converted[1],  background_color_converted[2],  0.0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        for frame_i in range(n_frames):            
            glClear(GL_COLOR_BUFFER_BIT)            
            glColor3fv(utils.convert_to_rgb(color))
            for stripe in range(n_stripes):
                glDrawArrays(GL_POLYGON,  frame_i * n_stripes * 2 * n_vertices_per_stripe + stripe * 2 * n_vertices_per_stripe, 2 * n_vertices_per_stripe)
            self._flip()
            if self.stimulation_control.abort_stimulus():                    
                break
                
        glDisableClientState(GL_VERTEX_ARRAY)
        
        
    def show_shape_new(self):
        size = 40
        n_frames = 100
        spd = 0.003
        vertices = numpy.array([[0.5 * size,  0.5 * size], 
                                [0.5 * size,  -0.5 * size], 
                                [-0.5 * size,  -0.5 * size], 
                                [-0.5 * size,  0.5 * size], 
                                ])

        vertices = vertices  * self.config.SCREEN_UM_TO_NORM_SCALE
        
        vert = numpy.zeros((n_frames,  4,  2))
        for i in range(n_frames):
            vert[i] = vertices + 0*numpy.array([-5 + i*6, 0])
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        
#        glMatrixMode(GL_PROJECTION)
#        glLoadIdentity()
#        gluOrtho2D(-0.5 * self.config.SCREEN_RESOLUTION[0], 0.5 * self.config.SCREEN_RESOLUTION[0],  -0.5 * self.config.SCREEN_RESOLUTION[1], 0.5 * self.config.SCREEN_RESOLUTION[1])
#        glMatrixMode(GL_MODELVIEW)
#        glLoadIdentity()

        for i in range(n_frames):          
            
            glVertexPointerf(vertices)
            glColor3fv(numpy.array([1.0,  1.0,  1.0]))
            glTranslatef(-0.5+i*spd, 0.0, 0.0)
            glDrawArrays(GL_POLYGON,  0, 4)
            
            self._flip()
            if self.stimulation_control.abort_stimulus():                    
                break
        
        glDisableClientState(GL_VERTEX_ARRAY)
        
        
                    
    def show_image_list(self,  image_list,  duration = 0.0, pos = (0,  0),  display_size = (0,  0),  orientation = 0):
        '''
        TBD        
        '''
       
        for imi in image_list:
            self.image_list.setTex(imi)
            if duration == 0.0:
                self._flip(trigger = True)                                     
                self.image_list.draw()
            else:
                for i in range(int(float(duration) * float(self.config.SCREEN_EXPECTED_FRAME_RATE))):                 
                    if i == 0:
                        self._flip(trigger = True)
                    else:
                        self._flip(trigger = False)                
#                     self.image_list.setPhase(phase_step,  '+')
                    self.image_list.draw()
                    if self.stimulation_control.abort_stimulus():
                        break

    def set_parallel(self,  bitmask):
        if self.config.ENABLE_PARALLEL_PORT:
            self.bitmask = bitmask
            self.parallel.setData(self.config.ACQUISITION_TRIGGER_ON | bitmask)
                        
    def _display_test_message(self,  message,  duration = 1.5):
    	if self.config.TEXT_ENABLE:
            self.test_message.setText(message)
            for i in range(int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)):
                self.test_message.draw()
                self._flip()
        
    def stimulation_library_test(self):   
        stimulus_library_test_data = visexpman.users.zoltan.test.stimulus_library_test_data.StimulusLibraryTestData(self.config)
        if stimulus_library_test_data.run_test['show_image() tests']:           
            test_datas =  stimulus_library_test_data.test_data_set[0]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n' + 'Expected result: ' + test_data['expected result'])
                self.show_image(test_data['path'],  duration = test_data['duration'],  position = test_data['position'],  formula = test_data['formula'],  size = test_data['size'])            
                self.clear_screen(duration = 0.5)
                
        if stimulus_library_test_data.run_test['show_movie() tests']:
            test_datas =  stimulus_library_test_data.test_data_set[1]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n' + 'Expected result: ' + test_data['expected result'])    
                self.show_movie(test_data['video_file_path'],  position = test_data['position'])
                self.clear_screen(duration = 0.5)
                
        if stimulus_library_test_data.run_test['show_shape() test']:
            test_datas =  stimulus_library_test_data.test_data_set[2]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n' + 'Expected result: ' + test_data['expected result'])    
                self.show_shape(test_data['shape'],  duration = test_data['duration'],  pos =  test_data['position'],  color =  test_data['color'],  orientation =  test_data['orientation'],  size =  test_data['size'],  formula =  test_data['formula'],  ring_size =  test_data['ring_size'])
                self.clear_screen(duration = 0.5)
        
        if stimulus_library_test_data.run_test['show_checkerboard() test']:
            test_datas =  stimulus_library_test_data.test_data_set[3]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n' + 'Expected result: ' + test_data['expected result'])    
                self.show_checkerboard( test_data['n_checkers'],  duration =  test_data['duration'],  pos = test_data['position'],  color = test_data['color'],  box_size = test_data['box_size'])
                self.clear_screen(duration = 0.5)
                
        if stimulus_library_test_data.run_test['show_ring() test']:
            test_datas =  stimulus_library_test_data.test_data_set[4]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n\r\n' + 'Expected result: ' + test_data['expected result'])    
                self.show_ring( test_data['n_rings'],  test_data['diameter'],  inner_diameter = test_data['inner_diameter'],  duration =  test_data['duration'],  n_slices = test_data['n_slices'],  colors = test_data['color'], pos = test_data['pos'])
                self.clear_screen(duration = 0.5)
        
        if stimulus_library_test_data.run_test['show_gratings() test']:
            test_datas =  stimulus_library_test_data.test_data_set[5]
            for test_data in test_datas:
                self._display_test_message('Test name: ' + test_data['test name'] + '\r\n\r\n' + 'Expected result: ' + test_data['expected result'])    
                self.show_gratings(duration =  test_data['duration'],   profile =  test_data['profile'],  spatial_frequency = test_data['spatial_frequency'],  display_area = test_data['display_area'], orientation = test_data['orientation'],  starting_phase = test_data['starting_phase'],  velocity = test_data['velocity'],  color_contrast = test_data['color_contrast'],  color_offset = test_data['color_offset'],  pos = test_data['pos'],  duty_cycle = test_data['duty_cycle'],  noise_intensity = test_data['noise_intensity'])
                self.clear_screen(duration = 0.5)

if __name__ == "__main__":
    print '------------------------------start------------------------------'
    ui = UserInterface() 
    st = Stimulations(ui)
    while 1:
        cmd = ui.user_interface_handler()
        if cmd != '':
            ui.user_interface_handler(cmd)
        if cmd == 'q':
            break            
        if cmd == 'i':
            parameters = [100.0,  100.0]
            formula_pos_x = ['p[0] * cos(10.0 * t)',  parameters]
            formula_pos_y = ['p[1] * sin(10.0 * t)',  parameters]            
            formula = [formula_pos_x,  formula_pos_y]
            ui.enable_frame_interval_watch()
            st.show_image('../Imaging/pictures',  1.0/7.5,  (0, 0),  formula)             
            st.show_image('../Imaging/pictures',  0,  (0, 0))             
            st.show_image(DEFAULT_IMAGE_PATH,  1.0,  (0, 0),  formula) 
            st.show_image(DEFAULT_IMAGE_PATH,  1.0,  (0, 100) )                        
        if cmd == 'm':
            ui.enable_frame_interval_watch()
            st.show_movie('../data/movie/test.avi',  (19, 100))
            ui.disable_frame_interval_watch()
            cmd = ui.user_interface_handler()
        if cmd == 's':
            parameters = []
            posx = ['100*sin(t)',  parameters]
            posy = ['100*cos(t)',  parameters]
            ori = ['',  []] 
            color_r = ['sin(t)',  parameters]
            color_g = ['cos(t)',  parameters]
            color_b = ['cos(t+pi*0.25)',  parameters]
            formula = [posx,  posy,  ori, color_r,  color_g,  color_b ]
            ui.enable_frame_interval_watch()            
            st.set_background(0.3)        
            
            for i in range(10):
                st.show_shape(shape = 'rect',  size = [100,  70],  orientation = i)
            st.show_shape(shape = 'rect',  duration = 0.5,  size = [10,  10],  orientation = 0)
            st.show_shape(shape = 'rect',  duration = 0.0,  size = [10,  100],  orientation = 0)
            st.show_shape(shape = 'annulus',  duration = 5.0,  size = [100,  200],  formula = formula,  ring_size = [50,  100])
            
            ui.disable_frame_interval_watch()
            cmd = ui.user_interface_handler()            
        
    print '------------------------------end------------------------------'
