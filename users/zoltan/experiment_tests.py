import numpy
import visual_stimulation.experiment
import generic.configuration
import generic.utils

class Pre(visual_stimulation.experiment.PreExperiment):    
    def run(self):
        self.st.show_shape(shape = 'circle',  duration = 0.0,  pos = (0,  0),  color = [1.0,  1.0,  1.0],  orientation = 0.0,  size = [10,  10])
       
class DotsExperimentConfig(visual_stimulation.experiment.ExperimentConfig):
    def _create_application_parameters(self):        
        NDOTS = [200, [1, 1000]]
        NFRAMES = [1*75, [1, 3000]]
        PATTERN_DURATION = [0.0, [0.0, 2.0]]
        self._create_parameters_from_locals(locals())

class MultipleDotTest(visual_stimulation.experiment.Experiment):
    def run(self):
        import random
#        print generic.utils.rc([random.random(),  random.random()])['row']
        random.seed(0)
        dot_sizes = []
        dot_positions = []
        for j in range(self.experiment_config.NFRAMES):
            dot_sizes_per_frame = []
            dot_positions_per_frame = []
            if isinstance(self.experiment_config.NDOTS,  list):
                dots = ndots[j]
            else:
                dots = self.experiment_config.NDOTS
            for i in range(dots):
                coords = (random.random(),  random.random())
                coords = generic.utils.rc(coords)
                dot_positions_per_frame.append([coords['col'] * self.config.SCREEN_RESOLUTION['col'] - self.config.SCREEN_RESOLUTION['col'] * 0.5, coords['row'] * self.config.SCREEN_RESOLUTION['row'] - 0.5 * self.config.SCREEN_RESOLUTION['row']])
                dot_sizes_per_frame.append(10 + 19 * random.random())
            dot_sizes.append(dot_sizes_per_frame)
            dot_positions.append(dot_positions_per_frame)
           
        if isinstance(self.experiment_config.NDOTS, list):
            colors = generic.utils.random_colors(max(self.experiment_config.NDOTS), self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
        else:
            colors = generic.utils.random_colors(self.experiment_config.NDOTS, self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
        if self.experiment_config.NFRAMES == 1:
            colors = [colors]
        
        self.st.show_dots(numpy.array(dot_sizes), numpy.array(dot_positions), duration = self.experiment_config.PATTERN_DURATION,  color = numpy.array(colors))        
        
class MyExperimentConfig(visual_stimulation.experiment.ExperimentConfig):
    def _create_application_parameters(self):
        PAR = 'dummy'
        self._create_parameters_from_locals(locals())

class MyStimulus1(visual_stimulation.experiment.Experiment):
    
    def run(self):
        off_time1 = 1.0
        off_time2 = 1.0
        on_time = 1.0
        color = 128
        self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
        self.st.clear_screen(duration = on_time,  color = color)
        self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)


class MyStimulus2(visual_stimulation.experiment.Experiment):
    
    def run(self):
        off_time1 = 1.0
        off_time2 = 1.0
        on_time = 1.0
        color = [1.0,  0.0,  0.0]
        self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
        self.st.clear_screen(duration = on_time,  color = color)
        self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)

class OpenGLTest(visual_stimulation.experiment.Experiment):
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
        

class ShapeTest(visual_stimulation.experiment.Experiment):
    def run(self):        

        self.st.show_shape_new()
#        for i in range(100):
#            pos = (-500+130*i,  0)
#            self.st.show_image(self.config.DEFAULT_IMAGE_PATH,  position = pos)

class GratingMaskTest(visual_stimulation.experiment.Experiment):
    def run(self):
        self.st.show_gratings(duration = 10.0, orientation = 45, velocity = 600, spatial_frequency = 300)

#        test_time = 1.0
#        preset_time  =1.0
#        posttest_delay = 1.0
#
#        self.st.clear_screen(duration = preset_time,  color = 0.0)
#        
#        for i in range(int(self.config.SCREEN_EXPECTED_FRAME_RATE * test_time * 0.5)):
#            self.st.clear_screen(duration = 0.0,  color = 1.0)
#            self.st.clear_screen(duration = 0.0,  color = 0.0)
#        
#            
#        self.st.clear_screen(duration = posttest_delay,  color = 0.0)
        
class DrumStimTest(visual_stimulation.experiment.Experiment):
    def run(self):
        duration  = 10.0
        rpm = 10
        n_stripes =8
        drum_base_size = 50
        drum_height = 500
        contraction = 10
        self.st.show_drum(duration,  rpm,  n_stripes,  drum_base_size ,  drum_height, contraction,  color = [0.5,  0.5,  0.5],  pos = (100,  100))
