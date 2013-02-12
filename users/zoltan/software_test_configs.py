import os.path
import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import experiment
from visexpman.users.peter import mea_configurations as peter_configurations
from visexpman.users.zoltan.test import unit_test_runner
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

class CaImagingTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        #### paths/data handling ####
        self.root_folder = '/mnt/datafast/'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
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
        COORDINATE_SYSTEM='ulcorner'
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
        pass
