

class ExperimentConfig(generic.Config):
    def _create_application_parameters(self):
        PAR = 'assa'
        
        self._create_parameters_from_locals(locals())    
    
    

    

class Experiment():
    
    def __init__(self,  stimulus_library):
        self.st = stimulus_library
        self.config = stimulus_library.config        
        self.experimentconfig = getattr(self.__name__+'Config')()
        
    def run(self):
        pass
        
    def cleanup(self):
        pass

class MultipleStimulus(Experiment):
    
    def run(self):
        self.stimulus_set = []
        i = 0
        for stim in self.config.STIMULUS_LIST:
            self.st._display_test_message(stim)            
            self.stimulus_set.append(getattr(sys.modules[__name__],  stim)(self.st))
            self.stimulus_set[i].run()            
            
            i = i + 1
            
    def cleanup(self):
        for single_stimulus in self.stimulus_set:
            single_stimulus.cleanup()
        print 'DONE'

class MyStimulus1(Experiment):
    
    def run(self):
        off_time1 = 1.0
        off_time2 = 1.0
        on_time = 1.0
        color = 128
        self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
        self.st.clear_screen(duration = on_time,  color = color)
        self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)


class MyStimulus2(Experiment):
    
    def run(self):
        off_time1 = 1.0
        off_time2 = 1.0
        on_time = 1.0
        color = [1.0,  0.0,  0.0]
        self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
        self.st.clear_screen(duration = on_time,  color = color)
        self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)

class OpenGLTest(Experiment):
    def run(self):
        size = 100.0
        vertices = numpy.array([[0.5 * size,  0.5 * size, 0],
                                [0.5 * size,  -0.5 * size, 0.0], 
                                [-0.5 * size,  -0.5 * size, 0.0],
                                [-0.5 * size,  0.5 * size, 0.0],
                                ])
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)       
        glClear (GL_COLOR_BUFFER_BIT)
        
        spd = 0.001
        i = 0
        glTranslatef(100.0,10.0, 0.0)
        self.st.set_background((1.0, 1.0, 0.0))
        while True:            
            glClear (GL_COLOR_BUFFER_BIT)
            glColor3f (1.0, 0.3, 1.0)            
            glRotate(i*spd, 0.0, 0.0, 1.0)            
            glDrawArrays(GL_POLYGON,  0, 4)
            self.st._flip()
            key_pressed = ''
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    key_pressed = key_pressed + pygame.key.name(event.key)
            if key_pressed == 'a':
                break
            i += 1
            
            
            
        glDisableClientState(GL_VERTEX_ARRAY)
        self.st.clear_screen(duration = 0.1,  color = (1.0, 0.0, 0.0))
        

class ShapeTest(Experiment):
    def run(self):        

        self.st.show_shape_new()
#        for i in range(100):
#            pos = (-500+130*i,  0)
#            self.st.show_image(self.config.DEFAULT_IMAGE_PATH,  position = pos)

class GratingMaskTest(Experiment):
    def run(self):
        self.st.show_gratings(duration = 10.0, orientation = 45, velocity = 600, spatial_frequency = 300)

#        test_time = 1.0
#        preset_time  =1.0
#        posttest_delay = 1.0
#
#        self.st.clear_screen(duration = preset_time,  color = 0.0)
#        
#        for i in range(int(self.config.EXPECTED_FRAME_RATE * test_time * 0.5)):
#            self.st.clear_screen(duration = 0.0,  color = 1.0)
#            self.st.clear_screen(duration = 0.0,  color = 0.0)
#        
#            
#        self.st.clear_screen(duration = posttest_delay,  color = 0.0)
        
class DrumStimTest(Experiment):
    def run(self):
        duration  = 10.0
        rpm = 10
        n_stripes =8
        drum_base_size = 50
        drum_height = 500
        contraction = 10
        self.st.show_drum(duration,  rpm,  n_stripes,  drum_base_size ,  drum_height, contraction,  color = [0.5,  0.5,  0.5],  pos = (100,  100))

class MultipleDotTest(Experiment):
    def run(self):
        import random
        ndots = 200
        nframes = 30 * 1
#        ndots = [2,  3]
#        nframes = 2
        fd = 0.0
        random.seed(0)
        dot_sizes = []
        dot_positions = []
        for j in range(nframes):
            dot_sizes_per_frame = []
            dot_positions_per_frame = []
            if isinstance(ndots,  list):
                dots = ndots[j]
            else:
                dots = ndots
            for i in range(dots):
                coords = [random.random(),  random.random()]
                dot_positions_per_frame.append([coords[0]*self.config.SCREEN_RESOLUTION[0]-self.config.SCREEN_RESOLUTION[0] * 0.5, coords[1]*self.config.SCREEN_RESOLUTION[1]-0.5 * self.config.SCREEN_RESOLUTION[1]])
                dot_sizes_per_frame.append(10 + 19 * random.random())
            dot_sizes.append(dot_sizes_per_frame)
            dot_positions.append(dot_positions_per_frame)
           
        if isinstance(ndots,  list):
            colors = utils.random_colors(max(ndots), nframes,  greyscale = True,  inital_seed = 0)
        else:
            colors = utils.random_colors(ndots, nframes,  greyscale = True,  inital_seed = 0)
        if nframes == 1:
            colors = [colors]
        
        self.st.show_dots(dot_sizes, dot_positions, duration = fd,  color = colors)
#        cols = [1.0,  0.5, 0.25,  0.0]
#        self.st.show_checkerboard((2, 2), duration = 1.0, pos = (0, 0), color = cols, box_size = (10,  10))
        
#        self.st.show_shape(shape = 'circle',  duration = 1.0,  pos = (0,  0),  color = [1.0,  1.0,  1.0],  orientation = 0.0,  size = [10,  10])
