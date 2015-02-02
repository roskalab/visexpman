import time
import numpy
import serial
import visexpman
import os.path
import os
import tempfile
if os.name == 'nt':
    try:
        import PyDAQmx.DAQmxConstants as DAQmxConstants
    except ImportError:
        pass

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import configuration as config
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.test import unittest_aggregator
from visexpman.users.daniel import grating
from visexpman.users.peter import mea_configurations as peter_configurations
from visexpman.engine.generic import fileop

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

class SwDebugConfig(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):        
#        EXPERIMENT_CONFIG = 'IncreasingAnnulusParameters'
        PLATFORM = 'standalone'
        ENABLE_UDP=False
        BACKGROUND_COLOR = [0.5,0.5,0.5]
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COLOR_MASK = numpy.array([1.0, 1.0, 1.0])
        import copy
        TEXT_COLOR = copy.deepcopy(BACKGROUND_COLOR)
        TEXT_COLOR[1] += 0.15
#        self.GAMMA_CORRECTION = numpy.array([
#                                             [0, 15.6], 
#                                             [20, 54],
#                                             [40, 175], 
#                                             [60, 500],
#                                             [70, 725], 
#                                             [80, 996],
#                                             [90, 1300], 
#                                             [100, 1630],
#                                             [110, 2000],
#                                             [120, 2400], 
#                                             [130, 2850], 
#                                             [140, 3250], 
#                                             [150, 3810], 
#                                             [160, 4460],
#                                             [165, 4820], 
#                                             [170, 5130],  
#                                             [180, 5890], 
#                                             [190, 6630], 
#                                             [200, 7430],
#                                             [210, 8300], 
#                                             [220, 9000], 
#                                             [230, 9500],
#                                             [255, 9500], 
#                                             ])
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
            fileop.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([160, 160])
        SCREEN_RESOLUTION = utils.cr([800, 600])
#        SCREEN_UM_TO_PIXEL_SCALE = 0.5
        INSERT_FLIP_DELAY = not True
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE =  not True
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        gamma_corr_filename = 'c:\\visexp\\data\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            import hdf5io
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

class CaImagingTestConfig(configuration.ElphysRetinalCaImagingConfig):
    
    def _set_user_parameters(self):
        #### paths/data handling ####
        FULLSCREEN = not True
        self.root_folder = fileop.select_folder_exists(['/mnt/rzws/experiment_data','r:\\experiment_data', '/tmp'])
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = self.root_folder
        DATA_STORAGE_PATH = fileop.select_folder_exists([ '/mnt/rzws/dataslow', '/tmp', 'C:\\temp'])
        CONTEXT_PATH = self.root_folder
        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        #### Network ####
        self.CONNECTIONS['stim']['ip']['stim'] = None
        self.CONNECTIONS['stim']['ip']['main_ui'] = '172.27.26.45'
        self.CONNECTIONS['ca_imaging']['ip']['ca_imaging'] = '172.27.26.45'#bind to specific network card
        self.CONNECTIONS['ca_imaging']['ip']['main_ui'] = '172.27.26.45'
        self.CONNECTIONS['analysis']['ip']['analysis'] = None
        self.CONNECTIONS['analysis']['ip']['main_ui'] = '172.27.26.45'

        self.BASE_PORT = 10000
        
        COORDINATE_SYSTEM='center'
        ######################### Ca imaging specific ################################ 
        self.CA_IMAGING_START_DELAY = 5.0#NEW
        self.CA_IMAGING_START_TIMEOUT = 15.0
        PMTS = {'TOP': {'CHANNEL': 1,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'CHANNEL' : 0,'COLOR': 'RED', 'ENABLE': False}}
    
        self.GUI['GUI_SIZE'] =  utils.cr((1280,1024))
#        self.GUI['GUI_SIZE'] =  utils.cr((1024,700))
#        if os.name == 'nt':
#            DAQ_CONFIG[0]['AI_TERMINAL'] = DAQmxConstants.DAQmx_Val_PseudoDiff

        self.FILTERWHEEL = [{
                        'connected to': 'main_ui',
                        'port' :  'COM8',
                        'baudrate' : 115200,
                        'filters' : {
                                                'IR': 1, 
                                                'empty': 2, 
                                                }
                        },
                        {
                        'connected to': '',
                        'port' :  'COM1',
                        'baudrate' : 115200,
                        'filters' : {
                                                'ND10': 1, 
                                                'ND20': 2, 
                                                'ND30': 3, 
                                                'ND40': 4, 
                                                }
                        }]
        self._create_parameters_from_locals(locals())

class JobhandlerTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        #### paths/data handling ####
        self.root_folder = '/mnt/datafast/'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = unittest_aggregator.TEST_working_folder
        CONTEXT_PATH = os.path.join(self.root_folder, 'context')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        #### experiment specific ####
        self.PARSE_PERIOD = 0.1
        
        #### Network ####
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        self.COMMAND_RELAY_SERVER['ENABLE'] = False
        self.BASE_PORT = 20000
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
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
