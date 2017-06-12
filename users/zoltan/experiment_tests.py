from OpenGL.GL import *
from OpenGL.GLUT import *
import numpy,time
from visexpman.engine.generic import utils,geometry,colors
from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.NROWS = 3#10
        self.NCOLUMNS = 6#18
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((50.0,90.0))
        self.DISPLAY_CENTER = utils.rc((25,45.0))
        self.ON_TIME = 2.0#0.8
        self.OFF_TIME = 0#0.8
        self.REPEATS = 1 
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  False
        self.runnable='ReceptiveFieldExploreZ'
        self._create_parameters_from_locals(locals())


class ReceptiveFieldExploreZ(experiment.Experiment):
    '''
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are presented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def prepare(self):
#	print self.machine_config.SCREEN_SIZE_UM
        shape_size, nrows, ncolumns, display_size, shape_colors, background_color = \
                self._parse_receptive_field_parameters(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None,
                                                    self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                                    self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                                    self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                                    self.experiment_config.COLORS,
                                                    self.experiment_config.BACKGROUND_COLOR)
        self.stimulus_duration, positions= self.receptive_field_explore_durations_and_positions(shape_size=shape_size, 
                                                                            nrows = nrows,
                                                                            ncolumns = ncolumns,
                                                                            shape_colors = shape_colors,
                                                                            flash_repeat = self.experiment_config.REPEATS,
                                                                            sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                                                            on_time = self.experiment_config.ON_TIME,
                                                                            off_time = self.experiment_config.OFF_TIME)
        self.fragment_durations=[self.stimulus_duration]
        
            
    def run(self):
        self.receptive_field_explore(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None, 
                                    self.experiment_config.ON_TIME,
                                    self.experiment_config.OFF_TIME,
                                    nrows = self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                    ncolumns = self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                    display_size = self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                    flash_repeat = self.experiment_config.REPEATS, 
                                    sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, 
                                    shape_colors = self.experiment_config.COLORS, 
                                    random_order = self.experiment_config.ENABLE_RANDOM_ORDER)
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR)
        #print self.shape_size,self.machine_config.SCREEN_SIZE_UM,self.ncolumns,self.nrows
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}

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
        if 0:
            ph=numpy.tile(numpy.sin(numpy.arange(100)/100.*2*3.14)*300,10)
            
            self.show_grating(white_bar_width =100,  phases=ph, duty_cycle=3)
            return
            
            initial_wait=2.0
            mask_size=400.
            bar_width=60.
            speed=80
            color=1.0
            motion=['expand','shrink','left','right']
            for m in motion:
                self.show_approach_stimulus(m, bar_width, speed)
            return
        from PIL import Image
        pixel_size=10.0/5#um/pixel
        shift=400.0#um
        speed=1200*1
        yrange=[1000,2000]
        fn='/tmp/Pebbleswithquarzite_grey.png'
        fn='/home/rz/1.jpg'
        self.show_rolling_image(fn,pixel_size,speed,shift,yrange,axis='vertical')
        return
        texture=numpy.flipud(numpy.asarray(Image.open(fn))/255.)
        if len(texture.shape)<3:
            texture=numpy.swapaxes(numpy.array(3*[texture]),0,2)
        texture=texture[yrange[0]:yrange[1],:,:]
        shift_pixel=shift/self.config.SCREEN_UM_TO_PIXEL_SCALE
        dpixel=speed*self.config.SCREEN_UM_TO_PIXEL_SCALE/self.config.SCREEN_EXPECTED_FRAME_RATE
        #Image size: texture.shape*pixel_size*screen um2 pixel ratio
        size=utils.rc(numpy.array(texture.shape[:2])*pixel_size/self.config.SCREEN_UM_TO_PIXEL_SCALE)
        texture_coordinates = numpy.array(
                             [
                             [1, 1],
                             [0.0, 1],
                             [0.0, 0.0],
                             [1, 0.0],
                             ])
        self._init_texture(size,0)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, texture.shape[1], texture.shape[0], 0, GL_RGB, GL_FLOAT, texture)
        #Calculate trajectory of image motion
        p0=(utils.nd(size)/2-utils.nd(self.config.SCREEN_RESOLUTION)/2)[::-1]
        p1=p0*numpy.array([-1,1])
        nshifts=int(size['row']/shift_pixel)-1
        vertical_offsets=numpy.arange(nshifts)*shift_pixel
        vertical_offsets=numpy.repeat(vertical_offsets,3)
        points=numpy.array([p0,p1,p0])
        points=numpy.array(points.tolist()*nshifts)
        points[:,1]-=vertical_offsets
        #Interpolate between points
        offset=numpy.empty((0,2))
        for i in range(points.shape[0]-1):
            start=points[i]
            end=points[i+1]
            nsteps=int(abs(((end-start)/dpixel)).max())
            increment_vector=(end-start)/abs((end-start)).max()*dpixel
            steps=numpy.repeat(numpy.arange(nsteps),2).reshape(nsteps,2)*increment_vector+start
            offset=numpy.concatenate((offset,steps))
        import time
        t0=time.time()
        for i in range(offset.shape[0]):
            now=time.time()
            index=int((now-t0)*self.config.SCREEN_EXPECTED_FRAME_RATE)
            vertices = geometry.rectangle_vertices(size, orientation = 0)-offset[index]
            glEnableClientState(GL_VERTEX_ARRAY)
            glVertexPointerf(vertices)
            glTexCoordPointerf(texture_coordinates)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor3fv((1.0,1.0,1.0))
            glDrawArrays(GL_POLYGON,  0, 4)
            self._flip(False)
            if self.abort:
                break
        print i/(time.time()-t0)
        self._deinit_texture()
        return
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
    stimulation_tester('zoltan', 'StimulusDevelopment', 'ReceptiveFieldTest')
