import os.path
import os
if os.name == 'nt':
    import PyDAQmx.DAQmxConstants as DAQmxConstants
import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import experiment
from visexpman.users.peter import mea_configurations as peter_configurations
from visexpman.users.zoltan.test import unit_test_runner
from visexpman.engine.generic import utils
from visexpman.engine.generic import file


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
        ENABLE_UDP_TRIGGER= (os.name == 'nt')
        UDP_PORT = 446
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        self.BASE_PORT = 30000
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
            'GUI_STIM'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANALYSIS'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+6}, 'ANALYSIS' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 7}}, 
            'GUI_ELPHYS'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+8}, 'ANALYSIS' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 9}},
            }
        COORDINATE_SYSTEM='center'
        ######################### Ca imaging specific ################################ 
        self.CA_IMAGING_START_DELAY = 5.0#NEW
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
        {
        'ANALOG_CONFIG' : 'ai',
        'DAQ_TIMEOUT' : 3.0,
        'SAMPLE_RATE' : 5000,
        'AI_CHANNEL' : 'Dev1/ai2:3',
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
