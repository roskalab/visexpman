import time
import numpy
import serial
import visexpman
import os.path
import os
import tempfile
if os.name == 'nt':
    import PyDAQmx.DAQmxConstants as DAQmxConstants

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import configuration as config
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.zoltan.test import unit_test_runner
from visexpman.users.daniel import grating
from visexpman.users.peter import mea_configurations as peter_configurations

GEOMETRY_PRECISION = 3

class GraphicsTestConfig(config.Config):
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

class Stimulus2video(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingGratingConfig'
        PLATFORM = 'standalone'
        #=== paths/data handling ===
        use_drive = 'tmp'
        if use_drive =='v':
            root_folder = 'V:\\'
        elif use_drive =='c':
            root_folder = 'c:\\visexp'
        elif use_drive == 'tmp':
            root_folder = tempfile.gettempdir()
        else:
            root_folder = '/home/zoltan/visexp/' 
        drive_data_folder = os.path.join(root_folder, 'experiment_data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        VIDEO_PATH = drive_data_folder
        if use_drive == 'g':
            MES_DATA_FOLDER = 'g:\\User\\Zoltan\\data'
        elif use_drive =='v':
            MES_DATA_FOLDER = 'V:\\debug\\data'
        elif use_drive =='c':
            MES_DATA_FOLDER = 'c:\\visexp\\debug\\data'
        elif use_drive == 'tmp':
            MES_DATA_FOLDER = drive_data_folder
            VIDEO_PATH = 'c:\\visexp'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #Create folders that does not exists
        for folder in [drive_data_folder, LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, MES_DATA_FOLDER, CONTEXT_PATH, CAPTURE_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE =  False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen        
        MAXIMUM_RECORDING_DURATION = [1000, [0, 10000]] #100
        MES_TIMEOUT = 10.0
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        self._create_parameters_from_locals(locals())

class SwDebugConfig(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'IncreasingAnnulusParameters'
        PLATFORM = 'standalone'
        ENABLE_UDP=False
        BACKGROUND_COLOR = [0.5,0.5,0.5]
        SCREEN_UM_TO_PIXEL_SCALE = 0.5
        COLOR_MASK = numpy.array([0.0, 1.0, 1.0])
        import copy
        TEXT_COLOR = copy.deepcopy(BACKGROUND_COLOR)
        TEXT_COLOR[1] += 0.15
        self.GAMMA_CORRECTION = numpy.array([
                                             [0, 15.6], 
                                             [20, 54],
                                             [40, 175], 
                                             [60, 500],
                                             [70, 725], 
                                             [80, 996],
                                             [90, 1300], 
                                             [100, 1630],
                                             [110, 2000],
                                             [120, 2400], 
                                             [130, 2850], 
                                             [140, 3250], 
                                             [150, 3810], 
                                             [160, 4460],
                                             [165, 4820], 
                                             [170, 5130],  
                                             [180, 5890], 
                                             [190, 6630], 
                                             [200, 7430],
                                             [210, 8300], 
                                             [220, 9000], 
                                             [230, 9500],
                                             [255, 9500], 
                                             ])
        root_folder = '/mnt/datafast/debug'
        if not os.path.exists(root_folder):
            root_folder = '/mnt/rznb'
            if not os.path.exists(root_folder):
                root_folder = 'V:\\debug'
                if not os.path.exists(root_folder):
                    root_folder = '/home/zoltan/Downloads'
        drive_data_folder = os.path.join(root_folder, 'experiment_data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        STIM_RECORDS_ANALOG_SIGNALS = True
        #Create folders that does not exists
        for folder in [drive_data_folder, LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, CONTEXT_PATH, CAPTURE_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
#        SCREEN_UM_TO_PIXEL_SCALE = 0.5
        INSERT_FLIP_DELAY = True
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE =  not True
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        gamma_corr_filename = 'c:\\visexp\\data\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction',filelocking=False))
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        GUI_SIZE =  utils.cr((1280,1024))
        
        self._create_parameters_from_locals(locals())

class CaImagingTestConfig(configuration.RetinalCaImagingConfig):
    
    def _set_user_parameters(self):
        #### paths/data handling ####
        self.root_folder = '/mnt/datafast/debug/data'
#        self.root_folder = '/mnt/rznb/data'
        if not os.path.exists(self.root_folder) and os.name == 'nt':
            self.root_folder = 'v:\\debug\\data'
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = self.root_folder
        CONTEXT_PATH = self.root_folder
        self.CONTEXT_NAME = '2pdev1.hdf5'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
#        EXPERIMENT_FILE_FORMAT = 'mat'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        
        #### Network ####
        ENABLE_UDP_TRIGGER= False
        UDP_PORT = 446
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.26.32'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        self.BASE_PORT = 30000
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
            'GUI_STIM'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANALYSIS'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+6}, 'ANALYSIS' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 7}}, 
            'GUI_IMAGING'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+8}, 'IMAGING' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 9}},
            'STIM_IMAGING'  : {'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT+10}, 'IMAGING' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 11}},
            }
        COORDINATE_SYSTEM='center'
        ######################### Ca imaging specific ################################ 
        self.CA_IMAGING_START_DELAY = 5.0#NEW
        self.CA_IMAGING_START_TIMEOUT = 15.0
        MAX_PMT_VOLTAGE = 8.0
        SCANNER_START_STOP_TIME = 0.02
        SCANNER_MAX_POSITION = 350.0
        POSITION_TO_SCANNER_VOLTAGE = 2.0/128.0*(10.0/9.0)#10 um bead is 9 um
        XMIRROR_OFFSET = 0*-64.0#um
        YMIRROR_OFFSET = 0.0#um
        SCANNER_SETTING_TIME = [3e-4, 1e-3]#This time constraint sets the speed of scanner (lenght of transient)
        SCANNER_TRIGGER_CONFIG = {'offset': 0.0, 'pulse_width': 20.0e-6, 'amplitude':5.0, 'enable':False}
        SINUS_CALIBRATION_MAX_LINEARITY_ERROR = 10e-2
        CA_FRAME_TRIGGER_AMPLITUDE = 5.0
        PMTS = {'TOP': {'AI': 1,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'AI' : 0,'COLOR': 'RED', 'ENABLE': False}}
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'aio',
        'DAQ_TIMEOUT' : 5.0, 
        'AO_SAMPLE_RATE' : 400000,
        'AI_SAMPLE_RATE' : 400000,
        'AO_CHANNEL' : 'Dev1/ao0:3',
        'AI_CHANNEL' : 'Dev1/ai0:1',
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : -5.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        {
        'DAQ_TIMEOUT' : 1.0, 
        'DO_CHANNEL' : unit_test_runner.TEST_daq_device + '/port0/line0',
        'ENABLE' : True
        }, 
        {#Ca sync, stim sync, elphys
        'ANALOG_CONFIG' : 'ai',
        'DAQ_TIMEOUT' : 3.0,
        'SAMPLE_RATE' : 5000,
        'AI_CHANNEL' : 'Dev1/ai0:2',
        'MAX_VOLTAGE' : 10.0,
        'MIN_VOLTAGE' : -10.0,
        'DURATION_OF_AI_READ' : 2*self.MAXIMUM_RECORDING_DURATION,
        'ENABLE' : True
        },
        ]
        self.CAIMAGE_DISPLAY = {}
        self.CAIMAGE_DISPLAY['VERTICAL_FLIP'] = False
        self.CAIMAGE_DISPLAY['HORIZONTAL_FLIP'] = True
        MAIN_IMAGE_SIZE = utils.rc((500,500))
        GUI_SIZE =  utils.cr((1280,1024))
#        if os.name == 'nt':
#            DAQ_CONFIG[0]['AI_TERMINAL'] = DAQmxConstants.DAQmx_Val_PseudoDiff
        self._create_parameters_from_locals(locals())

class JobhandlerTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        #### paths/data handling ####
        self.root_folder = '/mnt/datafast/'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        CONTEXT_PATH = os.path.join(self.root_folder, 'context')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        #### experiment specific ####
        PARSE_PERIOD = 0.1
        
        #### Network ####
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        self.COMMAND_RELAY_SERVER['ENABLE'] = False
        self.BASE_PORT = 20000
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {#TODO: probably IP addresses are not necessary here
            'GUI_MES'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}}, 
            'STIM_MES'  : {'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT+2}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 3}}, 
            'GUI_STIM'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANALYSIS'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+6}, 'ANALYSIS' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 7}}, 
            }
        #### hardware ####
        self.ROI = {}
        self.ROI['process'] = 'all'
        self.ROI['overwrite'] = True
        self.ROI['rawdata_filter']= {'width':13, 
            'spatial_width':1,
            'ncpus':16, 
            'thr':2.5,
            'separation_width':1, 
            'spatial_connectivity':1, 
            'transfermode': 'file'
                                     }
        ###Screen ###
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        COORDINATE_SYSTEM='ulcorner'
        self._create_parameters_from_locals(locals())
        
class StimulusDevelopmentMachineConfig(JobhandlerTestConfig):
    def _set_user_parameters(self):
        JobhandlerTestConfig._set_user_parameters(self)
        EXPERIMENT_CONFIG = 'StimulusPatternDevelopmentConfig'
        PLATFORM = 'standalone'
        COORDINATE_SYSTEM='center'
        self._create_parameters_from_locals(locals())

class StimulusPatternDevelopmentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'StimulusPatternDevelopment'
        self._create_parameters_from_locals(locals())
        
class StimulusPatternDevelopment(experiment.Experiment):
    def run(self):
        import numpy
        import time
        dot_diameters = numpy.array([[200, 100], [100, 50]])
        dot_positions = utils.rc(numpy.array([[0, 0], [100, 100]]))
        ndots = 2
        color = (1.0,  1.0,  1.0)
        color = [[1.0,  1.0,  1.0], [1.0,  0.0,  1.0]]
        self.show_shapes('r', dot_diameters, dot_positions, ndots, duration = 0,  color = color)
        time.sleep(2.0)
        
class FlowmeterDebug(peter_configurations.MEASetup):
    def _set_user_parameters(self):
        peter_configurations.MEASetup._set_user_parameters(self)
        EMULATE_FLOWMETER = True
        self._create_parameters_from_locals(locals())
