import visexpman.engine.visual_stimulation.configuration
import os
import visexpman.engine.generic.parameter
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.configuration

GEOMETRY_PRECISION = 3

class GraphicsTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        FPS_RANGE = (1.0,  200.0) 
        COLOR_RANGE = [[0.0, 0.0,  0.0],  [1.0, 1.0,  1.0]]
        
        SCREEN_RESOLUTION = utils.rc([768, 1024])        
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0,  FPS_RANGE]        
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
        FRAME_WAIT_FACTOR = [1.0,  [0.0,  1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        COORDINATE_SYSTEM = 'center' #ulcorner
#        COORDINATE_SYSTEM = 'ulcorner'
        CAPTURE_PATH = '/media/Common/visexpman_data'
        SIMULATION_DATA_PATH = '/media/Common/visexpman_data'
        self.N_CORES = 4
        ENABLE_FRAME_CAPTURE = False

     
        
        self._create_parameters_from_locals(locals())
        
    def _calculate_parameters(self):
        self.ORIGO, self.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.VERTICAL_AXIS_POSITIVE_DIRECTION= utils.coordinate_system(self.COORDINATE_SYSTEM, self.SCREEN_RESOLUTION)
        
class VRConfig(visexpman.engine.visual_stimulation.configuration.VisualStimulationConfig):
    def _set_user_specific_parameters(self):
        FULLSCREEN = True
        BACKGROUND_COLOR = [0.0,  0.0, 0.0]
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_RESOLUTION = utils.cr([1600, 900])
#        SCREEN_RESOLUTION = utils.cr([1680, 1050])
#        SCREEN_RESOLUTION = utils.cr([3280, 1050])
        self._set_parameters_from_locals(locals())
        
class UbuntuDeveloperConfig(visexpman.engine.visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):
        RUN_MODE = 'single experiment'
#        RUN_MODE = 'user interface'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'gratings_stimulus.py'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'increasing_spot_stimulus.py'
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        PRE_EXPERIMENT = 'Pre'
        ENABLE_PRE_EXPERIMENT = True
#        EXPERIMENT = 'ShapeTest'
#        SINGLE_EXPERIMENT = 'GratingMaskTest'
#        SINGLE_EXPERIMENT = 'DrumStimTest'
        LOG_PATH = '../../../presentinator/data/log/'
        ARCHIVE_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = True
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = True
        FULLSCREEN = False
#        SCREEN_RESOLUTION = [1024,  768]
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        corner = False
        if corner:
            ORIGO = utils.cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
        else:
            ORIGO = utils.cr((0, 0))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class WindowsDeveloperConfig(visexpman.engine.visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        PRE_EXPERIMENT = 'Pre'
        ENABLE_PRE_EXPERIMENT = True
#        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'checkerboard_stimulus.py'
#         RUN_MODE = 'user interface'        
#         EXPERIMENT = 'MultipleStimulus'
#        EXPERIMENT = 'OpenGLTest'
        FILTERWHEEL_ENABLE = False
        LOG_PATH = '..' + os.sep + 'data'
#         TEXT_ENABLE = True
        ARCHIVE_PATH = '..' + os.sep + 'data'
        CAPTURE_PATH = '..' + os.sep + 'data'
        ENABLE_PARALLEL_PORT = False
        #STIMULATION_FOLDER_PATH = self.BASE_PATH + os.sep + 'stimulus_examples'
        FULLSCREEN = False
        SCREEN_RESOLUTION = [800, 600]
        GAMMA = 1.0
        TEXT_COLOR = [1.0, 0.0, 0.0]
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'no'
        
        self._set_parameters_from_locals(locals())


class ScreenTestConfig(visexpman.engine.generic.configuration.Config):
    
    def _set_user_specific_parameters(self):
        RUN_MODE = 'user interface'
        LOG_PATH = 'data'
        ARCHIVE_PATH = 'data'
        CAPTURE_PATH = 'data'
        ENABLE_PARALLEL_PORT = False
        FULLSCR = False
        SCREEN_RESOLUTION = [1680, 1050]
#        SCREEN_RESOLUTION = [800, 600]
        SCREEN_RESOLUTION = [1024, 768]
        ENABLE_FRAME_CAPTURE = False
        
        EXPECTED_FRAME_RATE = 60.0
        MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.Parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'
        
        self._set_parameters_from_locals(locals())
        
if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    
