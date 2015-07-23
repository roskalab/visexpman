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

from stimuli import *

# ------------------------------------------------------------------------------
class ExampleDashStimulus(experiment.ExperimentConfig):
    def _create_parameters(self):
    #     self.SHAPE = 'rect'
    #     self.COLORS = [1.0, 0.0] # black, white
    #     self.BACKGROUND_COLOR = 0.5 # grey
    #     self.SHAPE_SIZE = 150.0 # um
    #     self.ON_TIME = 1.0 
    #     self.OFF_TIME = 1.0
    #     self.PAUSE_BEFORE_AFTER = 1.0
    #     self.REPEATS = 6
    #     self.REPEAT_SEQUENCE = 1
    #     self.ENABLE_RANDOM_ORDER = True
        self.runnable='DashStimulus'
        self._create_parameters_from_locals(locals())


class DashStimulus2(experiment.Experiment):
    def run(self):
        print 'Start DashStimulus2.run()'
        
        self.block_start()        
        #self.white_noise(duration = self.experiment_config.DURATION*60,
        #        pixel_size = self.experiment_config.PIXEL_SIZE, 
        #        flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
        #        colors = self.experiment_config.COLORS,
        #        n_on_pixels = _n_white_pixels, set_seed = False)
        self.block_end()
        self.show_fullscreen(color=0.5)
        


class DashStimulus(experiment.Experiment):
    #def prepare(self):
    #    pass
        # parameter_default_values = {
        # 'REPETITIONS': 1,
        # }
        # self.set_default_experiment_parameter_values(parameter_default_values)
        # #Calculate duration
        # trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
        #                             size = self.experiment_config.SHAPE_SIZE,
        #                             speeds = self.experiment_config.SPEEDS,
        #                             directions = self.experiment_config.DIRECTIONS,
        #                             pause = self.pause_between_directions,
        #                             repetition = self.experiment_config.REPETITIONS,
        #                             shape_starts_from_edge = True)
        # if hasattr(self.log, 'info'):
        #      self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration), source = 'stim')
    
    def run2(self):
        self_SHAPE_POSITIONS = {0:{'row':5,'col':2}}#,1:{'row':300,'col':400}}
        print 'DashStimulus.run()'
        
        self.block_start()
        self.show_shapes(shape='rect', 
                        shape_size=[[50, 200]],
                        shape_positions=self_SHAPE_POSITIONS,
                        nshapes=1,
                        duration = 10.0,
                        color = (1.0,  1.0,  1.0),
                        background_color = None,
                        block_trigger = False,
                        are_same_shapes_over_frames = False,
                        colors_per_shape = True,
                        save_frame_info = True)
        self.block_end()
        self.show_fullscreen(color=0.5)
        '''
        Shows a huge number (up to several hunders) of shapes.
        Parameters:
            shape_size: one dimensional list of shape sizes in um or the size of rectangle, in this case a two dimensional array is also supported
            shape_positions: one dimensional list of shape positions (row, col) in um.
            nshapes: number of shapes per frame
            color: can be a single tuple of the rgb values that apply to each shapes over the whole stimulation. Both list and numpy formats are supported
                    Optionally a two dimensional list can be provided where the dimensions are organized as above controlling the color of each shape individually
            duration: duration of each frame in s. When 0, frame is shown for one frame time.
            are_same_shapes_over_frames: if True, all frames show the same shapes with different colors

        The shape_sizes and shape_positions are expected to be in a linear list. Based on the nshapes, these will be segmented to frames assuming
        that on each frame the number of shapes are equal.
        '''
        
    def run(self):
        self_SHAPE_POSITIONS = {0:{'row':5,'col':2}}#,1:{'row':300,'col':400}}
        print 'DashStimulus.run()'
        
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':0, 'counter':self.frame_counter})
        #self.block_start()
        self.show_dash()
        # self.show_grating(  duration = 0.0,
        #                     profile = 'sqr',
        #                     white_bar[0] =-1,
        #                     display_area = utils.cr((0,  0)),
        #                     orientation = 0,
        #                     starting_phase = 0.0,
        #                     velocity = 10.0,
        #                     color_contrast = 1.0,
        #                     color_offset = 0.5,
        #                     pos = utils.cr((0,  0)),
        #                     duty_cycle = 1.0,
        #                     noise_intensity = 0,
        #                     part_of_drawing_sequence = False,
        #                     is_block = False,
        #                     save_frame_info = True,
        #                     block_trigger = False)
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':1, 'counter':self.frame_counter})
        #self.block_end()
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
            - white_bar[0]: length of one bar in um (pixel)
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
            show_grating(duration = 3.0, orientation = 45, velocity = 100, white_bar[0] = 100)
        2) Show grating with sine profile on a 500x500 area with 10 degree starting phase
            show_grating(duration = 3.0, profile = 'sin', display_area = (500, 500), starting_phase = 10, velocity = 100, white_bar[0] = 200)
        3) Show grating with sawtooth profile on a 500x500 area where the color contrast is light red and the color offset is light blue
            show_grating(duration = 3.0, profile = 'saw', velocity = 100, white_bar[0] = 200, color_contrast = [1.0,0.0,0.0], color_offset = [0.0,0.0,1.0]) 
        """
        
    def create_bar(self, size=[128,128], bar=[10,10], gap=[10,10]):# width_ratio = 1.0, length_ratio = 1.0):
        # Create BAR texture:
        #bar[0] = 100
        #gap[0] = round(bar[0]/width_ratio)
        #bar[1] = 100
        #gap[1] = round(bar[1]/length_ratio)
        texture_W = size[0]
        texture_L = size[1]
        
        bar_in = copy.copy(bar)
        gap_in = copy.copy(gap)
        
        fw = texture_W / float(bar_in[0]+gap_in[0])
        gap[0] = int(gap_in[0]*fw*0.5)*2
        bar[0] = texture_W - gap[0] #int(bar[0]*fw)
        
        fl = texture_L / float(bar_in[1]+gap_in[1])
        gap[1] = int(gap_in[1]*fl*0.5)*2
        bar[1] = texture_L-gap[1] #int(bar[0]*fl)
        
        # gap[0] = round(size[0]/(2*(width_ratio+1.0)))
        # bar[0] = (texture_W/2 - gap[0])#(gap[0]*width_ratio;
        # gap[1] = round(size[1]/(2*(length_ratio+1.0)))
        # bar[1] = (texture_L/2 - gap[1]) #gap[1]*length_ratio;
        # 
        bg_color  = numpy.array([[0,0,0]])
        bar_color = numpy.array([[1,0,0]])
        
        #texture_H = 2*(bar[0]+gap[0])
        #texture_W = 2*(bar[1]+gap[1])
        
        # Upper and lower gap between dashes
        gap_w = numpy.repeat([numpy.repeat(bg_color, texture_W, axis=0)], 0.5*gap[0], axis=0)
        
        # Left and right gap between dashes
        gap_l = numpy.repeat(bg_color, 0.5*gap[1], axis=0)
        # Dash itself (one dimensional)
        dash_l = numpy.repeat(bar_color, bar[1], axis=0)
        
        # Dash and left-right gaps in 2D
        dash = numpy.repeat([numpy.concatenate((gap_l, dash_l, gap_l))], bar[0], axis=0)
        return numpy.concatenate((gap_w, dash, gap_w)) 
        
    def show_dash(self):
        
        bar = [100, 100] # W, L um
        gap = [100, 100]
        
        movingLines = 2
        time = 5 #
        speed = 160 # um/s
        
              
        #speed = 300
        #y_repeat = 1# 3
        #x_repeat = 1#0
        #
        
        #maxLength = 2*speed*time/(self.config.SCREEN_UM_TO_PIXEL_SCALE*self.config.SCREEN_RESOLUTION['row'])
        
        diagonal_px = numpy.sqrt(2) * numpy.sqrt(self.config.SCREEN_RESOLUTION['row']**2 + self.config.SCREEN_RESOLUTION['col']**2)
        diagonal_px =  1*numpy.sqrt(2) * self.config.SCREEN_RESOLUTION['col']
        
        
        #alpha =numpy.pi/4
        #angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        #angles = numpy.array([  45.,  135.,  225.,  -45.]) * numpy.pi/180
        
        #vertices_x = 0.5 * diagonal_px * numpy.array([numpy.cos(angles), numpy.sin(angles)])
        #vertices_x = vertices_x.transpose()
        
        screen = numpy.array([self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col']])
        # vertices0 = numpy.array([[screen[0], screen[1]],[-screen[0], screen[1]],[-screen[0], -screen[1]],[screen[0], -screen[1]]])
        vertices = []
        
        wDist_px = (bar[0]+gap[0])/self.config.SCREEN_UM_TO_PIXEL_SCALE #float(screen[1])/float(nRepW)*numpy.sqrt(2)
        nRepW   = int(numpy.ceil(diagonal_px/wDist_px)) #int(numpy.ceil( diagonal_px*self.config.SCREEN_UM_TO_PIXEL_SCALE/(bar[0]+gap[0])  ))#diagonal_px maximum
        
        lDist_px = (bar[1]+gap[1])/self.config.SCREEN_UM_TO_PIXEL_SCALE
        nRepL = int(numpy.ceil(diagonal_px/lDist_px))
        
        # for l in numpy.arange(-(nRepW*0.5),nRepW*0.5,1.0):
        #     d0 = wDist_px*l
        #     d1 = wDist_px*(l+1.0)
        #     v = numpy.concatenate(([vertices0[:,0]*2*maxLength], [[d0,d0,d1,d1]]), axis=0 ).T
        #     vertices.append(v)
        
        nPixTexture = 128
        #nPixH = nPixTexture/2
        vertices2 = numpy.array([[-lDist_px, -wDist_px],[-lDist_px, wDist_px],[lDist_px, wDist_px],[lDist_px, -wDist_px]])*0.5
        
        texture = self.create_bar(size = [nPixTexture,nPixTexture], bar=bar, gap=gap)
        # x_repeat = 2*maxLength*screen[0]/128
        # 
        # print x_repeat
        # texture_coordinates = numpy.array(
        #                     [
        #                     [ x_repeat, 1.0],# y_repeat],
        #                     [-x_repeat, 1.0],# y_repeat],
        #                     [-x_repeat, 0.0],#-y_repeat],
        #                     [ x_repeat, 0.0],#-y_repeat],
        #                     ])
        texture_coordinates = numpy.array(
                            [
                            [1.0, 1.0],# y_repeat],
                            [0.0, 1.0],# y_repeat],
                            [0.0, 0.0],#-y_repeat],
                            [1.0, 0.0],#-y_repeat],
                            ])
        
        #print texture
        
        glEnableClientState(GL_VERTEX_ARRAY)
        #glVertexPointerf(vertices1)
        #glVertexPointerf(vertices2)
        
        #GLuint texture_handles()
        texture_handles = glGenTextures(1)
        
        glBindTexture(GL_TEXTURE_2D, texture_handles)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        #glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        glTexCoordPointerf(texture_coordinates)
        
        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
        #glBindTexture(GL_TEXTURE_2D, texture_handles+1)
        #glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
        #glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        
        # glEnable(GL_TEXTURE_2D)
        # glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        # 
        # texture_coordinates = numpy.array(
        #                     [
        #                     [x_repeat, y_repeat],
        #                     [0.0, y_repeat],
        #                     [0.0, 0.0],
        #                     [x_repeat, 0.0],
        #                     ])
        # glTexCoordPointerf(texture_coordinates)
        # glDisable(GL_TEXTURE_2D)
        # Texture coordinates: choose each corner of the texture, i.e. the entire texture
        # If the values extend 1, the texture is being repeated:
        
        
        def show_dash():
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_handles)
            glVertexPointerf(vertices2)#[i])
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glDrawArrays(GL_POLYGON,  0, 4)
            glDisable(GL_TEXTURE_2D)
            
        dist = 0
        t = 0
        #speed*time/(self.config.SCREEN_UM_TO_PIXEL_SCALE*self.config.SCREEN_RESOLUTION['row'])
        dx = speed/(self.config.SCREEN_EXPECTED_FRAME_RATE*self.config.SCREEN_UM_TO_PIXEL_SCALE)
        #for t in range(200):
        while True:
            
            dist += dx
            t += 1
            if self.abort:
                break
            if t > (time*self.config.SCREEN_EXPECTED_FRAME_RATE):
                break
            
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
             
            for w_i in range(-1, nRepW+1):
                
                for l_i in range(-1, nRepL+1):
                
                    glPushMatrix()
            # # FIRST TEXTURE:
            # glEnable(GL_TEXTURE_2D)
            # glBindTexture(GL_TEXTURE_2D, texture_handles)
            # glVertexPointerf(vertices1)
            # glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            # glTexCoordPointerf(texture_coordinates)
            # 
            # glColor3fv((1.0,1.0,1.0))
            # glDrawArrays(GL_POLYGON,  0, 4)
            # glDisable(GL_TEXTURE_2D)
            
                    glRotatef(t*0.0, 0,0,1)
                    if w_i%movingLines == 0:
                        glTranslate((dist+l_i*lDist_px)%((nRepL+1)*lDist_px)-screen[1],0,0)
                    else:
                        glTranslate((l_i*lDist_px)%((nRepL+1)*lDist_px)-screen[1],0,0)
                    
                    glTranslate(0,(w_i*wDist_px)%((nRepW+1)*wDist_px)-screen[0], 0)
                    
                    show_dash()
                    glPopMatrix()

            
            
            # SECOND TEXTURE:
            #glPushMatrix()
            
            #glRotatef(0, 0,0,1)
            #glTranslate(t, 0, 0)
            # glEnable(GL_TEXTURE_2D)
            # glBindTexture(GL_TEXTURE_2D, texture_handles)
            # #glBegin(GL_QUADS)
            # glVertexPointerf(vertices2)
            # glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            # glTexCoordPointerf(texture_coordinates)
            # 
            # glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
            # #glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            # glColor3fv((1.0,1.0,1.0))
            # glDrawArrays(GL_POLYGON,  0, 4)
            #glEnd()
            #show_dashes(0)
            
            #glPopMatrix()
            
            #glDisable(GL_TEXTURE_2D)
            
            self._flip(frame_trigger = True)
            
            if self.abort:
                break
        
        
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        
        glDeleteTextures(texture_handles)
    
    def show_dash2(self, speed = 300, repeats = 5, duration=20.0, dash_color=numpy.array([1, 0, 0]), minimal_spatial_period = None, spatial_resolution = None, intensity_levels = 255, direction = 0, save_frame_info =True, is_block = False):
        if spatial_resolution is None:
            spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
            
        if minimal_spatial_period is None:
            minimal_spatial_period = 10 * spatial_resolution
            
        #self.log.info('show_natural_bars(' + str(speed)+ ', ' + str(repeats) +', ' + str(duration) +', ' + str(minimal_spatial_period)+', ' + str(spatial_resolution)+ ', ' + str(intensity_levels) +', ' + str(direction)+ ')',source='stim')
        #if save_frame_info:
        #    self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
        
        #self.intensity_profile = signal.generate_natural_stimulus_intensity_profile(duration, speed, minimal_spatial_period, spatial_resolution, intensity_levels)
        # self.intensity_profile = [1,2,3]
        # self.intensity_profile = numpy.tile(self.intensity_profile, repeats)
        # if hasattr(self.machine_config, 'GAMMA_CORRECTION'):
        #     self.intensity_profile = self.machine_config.GAMMA_CORRECTION(self.intensity_profile)
        # intensity_profile_length = self.intensity_profile.shape[0]
        # if self.intensity_profile.shape[0] < self.config.SCREEN_RESOLUTION['col']:
        #     self.intensity_profile = numpy.tile(self.intensity_profile, numpy.ceil(float(self.config.SCREEN_RESOLUTION['col'])/self.intensity_profile.shape[0]))
        # 
        #alltexture = numpy.repeat(self.intensity_profile,3).reshape(self.intensity_profile.shape[0],1,3)
        #fly_in_out = self.config.BACKGROUND_COLOR[0] * numpy.ones((self.config.SCREEN_RESOLUTION['col'],1,3))
        #intensity_profile_length += 2*fly_in_out.shape[0]
        #alltexture=numpy.concatenate((fly_in_out,alltexture,fly_in_out))
        #texture = alltexture[:self.config.SCREEN_RESOLUTION['col']]
        # alltexture: Array of color-triplets:
        background_color = numpy.array([0,0,0])
        dash    = numpy.array([numpy.concatenate((numpy.tile(dash_color,       (2,1) ), numpy.tile(background_color, (20,1)) ) )])
        spacing = numpy.array([numpy.concatenate((numpy.tile(background_color, (2,1) ), numpy.tile(background_color, (20,1)) ) )])
        
        # axis 0 -> time dimension
        alltexture = numpy.concatenate((dash, spacing), axis=0)
        #alltexture.shape
        alltexture = numpy.repeat(alltexture,500, axis=0)
        #alltexture = numpy.repeat(alltexture,10, axis=1)
        texture = alltexture[:self.config.SCREEN_RESOLUTION['col']]
        intensity_profile_length = texture.shape[0]
        
        diagonal_px = numpy.sqrt(2) * numpy.sqrt(self.config.SCREEN_RESOLUTION['row']**2 + self.config.SCREEN_RESOLUTION['col']**2)
        diagonal_px =  1*numpy.sqrt(2) * self.config.SCREEN_RESOLUTION['col']
        
        alpha =numpy.pi/4
        angles = numpy.array([alpha, numpy.pi - alpha, alpha + numpy.pi, -alpha])
        angles = angles + direction*numpy.pi/180.0
        vertices = 0.5 * diagonal_px * numpy.array([numpy.cos(angles), numpy.sin(angles)])
        vertices = vertices.transpose()

        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        # Say something about this:
        texture_coordinates = numpy.array(
                            [
                            [0.0, 0.0],
                            # [1.0, 1.0],
                            # [0.0, 1.0],
                            # [0.0, 0.0],
                            # [1.0, 0.0],
                            ])
        glTexCoordPointerf(texture_coordinates)
        ds = float(speed*self.config.SCREEN_UM_TO_PIXEL_SCALE)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
#        t0=time.time()
        texture_pointer = 0
        frame_counter = 0
        self._add_block_start(is_block, 0, 0)
        while True:
            
            start_index = int(texture_pointer)
            end_index = int(start_index + self.config.SCREEN_RESOLUTION['col'])
            if end_index > alltexture.shape[0]:
                end_index -= alltexture.shape[0]
            if start_index < end_index:
                texture = alltexture[start_index:end_index]
            else:
                # Loop alltexture:
                texture = numpy.zeros_like(texture)
                texture[:-end_index] = alltexture[start_index:]
                texture[-end_index:] = alltexture[:end_index]
            print str(start_index) + '  ' + str(intensity_profile_length)
            if start_index >= intensity_profile_length:
                break
            texture_pointer += ds
            frame_counter += 1
            glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[0], texture.shape[1], 0, GL_RGB, GL_FLOAT, texture)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            self._flip(frame_trigger = True)
            if self.abort:
                break
        self._add_block_end(is_block, 0, 1)
#        dt=(time.time()-t0)
#        print self.frame_counter/dt,dt,self.frame_counter,texture_pointer
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        
        #if save_frame_info:
        #    self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)
 