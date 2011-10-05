#import os
#import time
#import numpy
#import visexpman
#import visexpman.engine.visual_stimulation.experiment as experiment
#from visexpman.engine.generic import utils
#from visexpman.engine.visual_stimulation import stimulation_library as stl
#from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
#
##TMP
#from OpenGL.GL import *
#
#class MultipleDotsTester(VisionExperimentConfig):
#    def _set_user_parameters(self):        
#        RUN_MODE = 'single experiment'
#        EXPERIMENT_CONFIG = 'GratingExperimentConfig'
#        LOG_PATH = 'C:\\_development\\virtual_reality\\software\\data'
#        BASE_PATH= 'C:\\_development\\virtual_reality\\software\\data'
#        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
#        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
#        ENABLE_PARALLEL_PORT = False
#        UDP_ENABLE = False
##        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
#        FULLSCREEN = False
#        SCREEN_RESOLUTION = utils.rc([500, 500])
#        ENABLE_FRAME_CAPTURE = False
#        SCREEN_EXPECTED_FRAME_RATE = 60.0
#        SCREEN_MAX_FRAME_RATE = 60.0
#        IMAGE_PROJECTED_ON_RETINA = False
#        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
#        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
#        FRAME_WAIT_FACTOR = 0 
#        GAMMA = 1.0
#        ENABLE_FILTERWHEEL = False
#        TEXT_ENABLE = False
#        
#        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
#        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
#        
#        SEGMENT_DURATION = 2
#        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
#        ACTION_BETWEEN_STIMULUS = 'off'
#
#        SCREEN_UM_TO_PIXEL_SCALE = 1.0
#        COORDINATE_SYSTEM='ulcorner'
#        COORDINATE_SYSTEM='center'
#            
#        ACQUISITION_TRIGGER_PIN = 2
#        FRAME_TRIGGER_PIN = 0
#        self._create_parameters_from_locals(locals())
#        
#class MultipleDotsTesterLinux(VisionExperimentConfig):
#    def _set_user_parameters(self):        
#        RUN_MODE = 'single experiment'
#        EXPERIMENT_CONFIG = 'GratingExperimentConfig'
##        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
#        LOG_PATH = '/media/Common/visexpman_data'
#        BASE_PATH= '/media/Common/visexpman_data'
#        ARCHIVE_PATH = '/media/Common/visexpman_data'
#        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'        
#        ENABLE_PARALLEL_PORT = False
#        UDP_ENABLE = False
##        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
#        FULLSCREEN = True
#        SCREEN_RESOLUTION = utils.rc([500, 500])
#        SCREEN_RESOLUTION = utils.cr([800, 600])
#        SCREEN_RESOLUTION = utils.cr([1680, 1050])
##        SCREEN_RESOLUTION = utils.cr([1024, 768])
#
#        ENABLE_FRAME_CAPTURE = False
#        SCREEN_EXPECTED_FRAME_RATE = 60.0
#        SCREEN_MAX_FRAME_RATE = 60.0
#        IMAGE_PROJECTED_ON_RETINA = False
#        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
#        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
#        FRAME_WAIT_FACTOR = 0
#        GAMMA = 1.0
#        ENABLE_FILTERWHEEL = False
#        TEXT_ENABLE = True
#        
#        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
#        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
#        
#        SEGMENT_DURATION = 2
#        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
#        ACTION_BETWEEN_STIMULUS = 'off'
#
#        SCREEN_UM_TO_PIXEL_SCALE = 1.0
#        COORDINATE_SYSTEM='ulcorner'
#        COORDINATE_SYSTEM='center'
#            
#        ACQUISITION_TRIGGER_PIN = 2
#        FRAME_TRIGGER_PIN = 0
#        self._create_parameters_from_locals(locals())        
#
#class MultipleDotsTesterMac(VisionExperimentConfig):
#    def _set_user_parameters(self):
#        RUN_MODE = 'single experiment'
#        EXPERIMENT_CONFIG = 'GratingExperimentConfig'
#        LOG_PATH = '/Users/rz/visexpman/data'
#        BASE_PATH= '/Users/rz/visexpman/data'
#        ARCHIVE_PATH = '/Users/rz/visexpman/data'
#        CAPTURE_PATH = '/Users/rz/visexpman/data/Capture'
#        ENABLE_PARALLEL_PORT = False
#        UDP_ENABLE = False
##        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
#        FULLSCREEN = False
#        SCREEN_RESOLUTION = utils.rc([500, 500])        
#        ENABLE_FRAME_CAPTURE = True
#        SCREEN_EXPECTED_FRAME_RATE = 15.0
#        SCREEN_MAX_FRAME_RATE = 60.0
#        IMAGE_PROJECTED_ON_RETINA = False
#        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
#        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
#        FRAME_WAIT_FACTOR = 0
#        GAMMA = 1.0
#        ENABLE_FILTERWHEEL = False
#        TEXT_ENABLE = False
#        
#        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
#        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
#        
#        SEGMENT_DURATION = 2
#        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
#        ACTION_BETWEEN_STIMULUS = 'off'
#
#        SCREEN_UM_TO_PIXEL_SCALE = 1.0
#        COORDINATE_SYSTEM='ulcorner'
#        COORDINATE_SYSTEM='center'
#            
#        ACQUISITION_TRIGGER_PIN = 2
#        FRAME_TRIGGER_PIN = 0
#        self._create_parameters_from_locals(locals())        
#        
#class GratingExperimentConfig(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.runnable = 'GratingTest'
#        self.pre_runnable = 'MultipleDotTestPre'        
#        self._create_parameters_from_locals(locals())
#
#class GratingTest(experiment.Experiment):
#    def run(self, stl):
#        time.sleep(0.3)        
#        stl.add_text('tex\nt', color = self.experiment_config.machine_config.TEXT_COLOR, position = utils.cr((100.0, 100.0)))
#        stl.change_text(0, text = 'aa')
#        stl.add_text('tex\nt', color = (1.0,  1.0,  0.0), position = utils.cr((200.0, 200.0)))
#        stl.clear_screen(duration = 0.5)
#        stl.show_grating(duration = 60.0, profile = 'sqr', orientation = 0, velocity = 0.0, white_bar_width = 50, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
#        
#class DotsExperimentConfig(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.NDOTS = 50
#        self.NFRAMES = 10
#        self.PATTERN_DURATION = 0.3
#        self.RANDOM_DOTS = True
#        self.runnable = 'MultipleDotTest'
#        self.pre_runnable = 'MultipleDotTestPre'
#        self._create_parameters_from_locals(locals())
#        
#class MultipleDotTestPre(experiment.PreExperiment):
#    def run(self):
#        pass
#                
#class MultipleDotTest(experiment.Experiment):
#    def run(self, stl):
##        self.st.show_gratings(duration = 2.0, orientation = 45, velocity = 300, spatial_frequency = 100, display_area =  generic.utils.cr((200,  200)), pos = generic.utils.cr((100, 100)))        
#        stl.add_text('tex\nt', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 100.0)))
#        stl.change_text(0, text = 'aa')
#        stl.add_text('tex\nt', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 200.0)))
#        stl.disable_text(1)
#        import random
#        self.config = self.experiment_config.machine_config
#        random.seed(0)
#        dot_sizes = []
#        dot_positions = []
#        for j in range(self.experiment_config.NFRAMES):
#            dot_sizes_per_frame = []
#            dot_positions_per_frame = []
#            if isinstance(self.experiment_config.NDOTS,  list):
#                dots = ndots[j]
#            else:
#                dots = self.experiment_config.NDOTS
#            for i in range(dots):
#                coords = (random.random(),  random.random())
#                coords = utils.rc(coords)
#                dot_positions.append([coords['col'] * self.config.SCREEN_RESOLUTION['col'] - self.config.SCREEN_RESOLUTION['col'] * 0.0, coords['row'] * self.config.SCREEN_RESOLUTION['row'] - 0.0 * self.config.SCREEN_RESOLUTION['row']])
#                dot_sizes.append(10 + 100 * random.random())                
#        
#        dot_positions = utils.cr(numpy.array(dot_positions).transpose())
#        dot_sizes = numpy.array(dot_sizes)
#        if isinstance(self.experiment_config.NDOTS, list):
#            colors = utils.random_colors(max(self.experiment_config.NDOTS), self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
#        else:
#            colors = utils.random_colors(self.experiment_config.NDOTS, self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
#        if self.experiment_config.NFRAMES == 1:
#            colors = [colors]
#        
#        if self.experiment_config.RANDOM_DOTS:
#            stl.show_dots(dot_sizes, dot_positions, self.experiment_config.NDOTS, duration = self.experiment_config.PATTERN_DURATION,  color = numpy.array(colors))
#        else:
#            side = 240.0
#            dot_sizes = numpy.array([50, 30, 30, 30, 30, 20])
#            colors = numpy.array([[[1.0,0.0,0.0],[1.0,1.0,1.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0,1.0,1.0],[0.8,0.0,0.0]]])
#            dot_positions = utils.cr(numpy.array([[0, side, side, -side, -side, 1.5 * side], [0, side, -side, -side, side, 1.5 * side]]))
#            ndots = 6
#            stl.show_dots(dot_sizes, dot_positions, ndots, duration = 4.0,  color = colors)            
#        
#def send_tcpip_sequence(vs_runner, messages, parameters,  pause_before):
#    '''This method is intended to be run as a thread and sends multiple message-parameter pairs. 
#    Between sending individual message-parameter pairs, we wait pause_before amount of time. This can be used to allow remote side do its processing.'''
#    import socket
#    import struct
#    # Send data
#    for i in range(len(messages)):
#        while vs_runner.state !='idle':
#            time.sleep(0.2)
#        time.sleep(pause_before[i])
#        print 'slept ' + str(pause_before[i])
#        try:
#            sock = socket.create_connection(('localhost', 10000))
#            sock.sendall('SOC'+messages[i]+'EOC'+parameters[i]+'EOP')
#        except Exception as e:
#            print e
#        finally:  
#            sock.close()        
#    return
#
#if __name__ == '__main__':
#    import visexpman
#    import threading
#    from visexpman.engine.run_visual_stimulation import VisualStimulation
#    vs_runner = VisualStimulation('zoltan','MultipleDotsTesterLinux')
#    messages = ['start_stimulation']
#    parameters = ['']
#    pause_before = [1, 2]
#    sender = threading.Thread(target=send_tcpip_sequence, args=(vs_runner, messages, parameters, pause_before))
#    sender.setDaemon(True)
#    sender.start()
#    vs_runner.run()
#    pass
