import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
import visexpman.engine.visual_stimulation.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import os
import serial
import numpy

class PPRLConfig(VisionExperimentConfig):
    
    def _set_user_parameters(self):
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
        LOG_PATH = '/var/log/'
        ARCHIVE_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0

        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        
        ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION = utils.coordinate_system('corner')
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class K247AWindowsConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = 'c:\\temp\\'
        BASE_PATH='c:\\Data\\stimuli\\'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())

class RC3DWindowsConfig(VisionExperimentConfig):
    #NOT TESTED
    def _set_user_parameters(self):        
        ENABLE_PARALLEL_PORT = True        
        FULLSCREEN = True
        SCREEN_RESOLUTION = [1600,  1200]
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        SERVER_UDP_IP = '172.27.26.10'
        ARCHIVE_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        #test steps:
        # 1. frame rate 60
        # 2. parallel port OK
        # 3 network control
        # 4 stimulus types
        
        self._set_parameters_from_locals(locals())

class MBP(VisionExperimentConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = '/Users/hd/Documents/DataBase'
        EXPERIMENT_LOG_PATH = LOG_PATH
        BASE_PATH='/Users/hd/Documents/DataBase'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [90, [0, 10000]] #seconds
        ARCHIVE_FORMAT = 'hdf5'
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())

# class ZoliTester(VisionExperimentConfig):
# 
#     def _set_user_parameters(self):     
#         MES = {'ENABLE' : True, 'ip': '',  'port' : 10001,  'receive buffer' : 256}   
#         RUN_MODE = 'single experiment'
#         EXPERIMENT_CONFIG = 'MovingDotTestConfig'
#         path = '/Users/rz/visexpman/data'
#         path = 'c:\\temp\\test'
# #         path = '/media/Common/visexpman_data/test'
#         LOG_PATH = path        
#         EXPERIMENT_LOG_PATH = path
#         ARCHIVE_PATH = path
#         CAPTURE_PATH = path
#         ENABLE_PARALLEL_PORT = False
#         UDP_ENABLE = False        
#         FULLSCREEN = False
#         SCREEN_RESOLUTION = utils.rc([768, 1024])
#         ENABLE_FRAME_CAPTURE = False
#         SCREEN_EXPECTED_FRAME_RATE = 60.0
#         SCREEN_MAX_FRAME_RATE = 60.0
#         IMAGE_PROJECTED_ON_RETINA = False
#         SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
#         SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
#         FRAME_WAIT_FACTOR = 0 
#         GAMMA = 1.0
#         ENABLE_FILTERWHEEL = False
#         ENABLE_TEXT = False
#         
#         MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
# 
#         SCREEN_UM_TO_PIXEL_SCALE = 1.0
#         COORDINATE_SYSTEM='ulcorner'
#         ARCHIVE_FORMAT = 'hdf5'
#         ACQUISITION_TRIGGER_PIN = 2
#         FRAME_TRIGGER_PIN = 0
#         self._create_parameters_from_locals(locals())
        
class VS3DUS(VisionExperimentConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        
        #=== paths/data handling ===
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
#         SCREEN_RESOLUTION = utils.rc([768, 1024])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        MAXIMUM_RECORDING_DURATION = [13, [0, 10000]]
        
        #=== Network ===
        ENABLE_UDP = False
        MES = {'ENABLE' : True, 'ip': '',  'port' : 10002,  'receive buffer' : 256}
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 10e-3
        
        #=== stage ===
        motor_serial_port = {
                                    'port' :  unit_test_runner.TEST_stage_com_port,
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        STAGE = [[{'serial_port' : motor_serial_port,
                 'enable': not True,
                 'speed': 1000000,
                 'acceleration' : 1000000,
                 'move_timeout' : 45.0,
                 'um_per_ustep' : numpy.ones(3, dtype = numpy.float)
                 }]]
                 
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]]        
                                    
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
                                                
        #=== LED controller ===
        DAQ_CONFIG = [[
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'SAMPLE_RATE' : 1000,                    
                    'AI_CHANNEL' : 'Dev1/ai0:1',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : -5.0,
                    'DURATION_OF_AI_READ' : 10.0,
                    'ENABLE' : not False
                    }
                    ]]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        
        
        self._create_parameters_from_locals(locals())
        
class GratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GratingExperiment'
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())       

class GratingExperiment(experiment.Experiment):
    def run(self):
        orientation = [0,45,90]
        ai = daq_instrument.AnalogIO(self.machine_config, self.caller)
        ai.start_daq_activity() 
        for i in range(len(orientation)):
            self.mes_command.put('SOCacquire_line_scanEOCc:\\temp\\test\\line_scan_data{0}.matEOP'.format(i))
            self.show_grating(duration =9.0, profile = 'sqr', orientation = orientation[i], velocity = 500.0, white_bar_width = 100)
            
        ai.finish_daq_activity()
        ai.release_instrument()
            
        #Save 
        if not hasattr(ai, 'ai_data'):
            ai.ai_data = numpy.zeros(2)
        path = utils.generate_filename(os.path.join(self.machine_config.ARCHIVE_PATH, 'ai_data.txt'))
        numpy.savetxt(path, ai.ai_data)            
        data_to_hdf5 = {'sync_data' : ai.ai_data}
        setattr(self.hdf5, mes_fragment_name, data_to_hdf5)
        self.hdf5.save(mes_fragment_name)
        

if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    
