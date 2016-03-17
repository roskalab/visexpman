import os
import os.path
import numpy
import tempfile
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import ElphysRetinalCaImagingConfig
try:
    import serial
except:
    pass


class ReiSetupConfig(ElphysRetinalCaImagingConfig):
    def _set_user_parameters(self):
        #### paths/data handling ####
        FULLSCREEN = not True
        self.root_folder = 'r:\\production\\rei-setup'
        self.root_folder = 'd:\\Data\\cone'
        self.root_folder = 'q:\\'
        LOG_PATH = 'q:\\log'
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = 'q:\\Rei'
#        DATA_STORAGE_PATH = os.path.join(self.root_folder, 'datastorage')
        CONTEXT_PATH = self.root_folder
        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
        DELETED_FILES_PATH = 'd:\\deleted_files'
        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        #### Network ####
        stim_computer_ip = '172.27.26.55'
        elphys_computer_ip = '172.27.26.48'
        imaging_computer_ip = '172.27.26.49'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.CONNECTIONS['ca_imaging']['ip']['ca_imaging'] = imaging_computer_ip #bind to specific network card
        self.CONNECTIONS['ca_imaging']['ip']['main_ui'] = imaging_computer_ip
        self.CONNECTIONS['analysis']['ip']['analysis'] = None
        self.CONNECTIONS['analysis']['ip']['main_ui'] = '172.27.26.49'

        self.BASE_PORT = 10000
        
        COORDINATE_SYSTEM='center'
        ######################### Ca imaging specific ################################ 
        self.CA_IMAGING_START_DELAY = 5.0#NEW
        self.CA_IMAGING_START_TIMEOUT = 15.0
        PMTS = {'TOP': {'CHANNEL': 1,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'CHANNEL' : 0,'COLOR': 'RED', 'ENABLE': False}}
        POSITION_TO_SCANNER_VOLTAGE = 0.013
        self.GUI['SIZE'] =  utils.cr((1280,1024))
#        self.GUI['SIZE'] =  utils.cr((1024,700))
#        if os.name == 'nt':
#            DAQ_CONFIG[0]['AI_TERMINAL'] = DAQmxConstants.DAQmx_Val_PseudoDiff


        self.SCANNER_CHARACTERISTICS['GAIN'] = [-1.12765460e-04,  -2.82919056e-06]#(p1+p2*A)*f+1, in PU
        self.SCANNER_CHARACTERISTICS['PHASE'] = \
                    [9.50324884e-08,  -1.43226725e-07, 1.50117389e-05,  -1.41414186e-04,   5.90072950e-04,   5.40402050e-03,  -1.18021600e-02]#(p1*a+p2)*f**2+(p3*a**2+p4*a+p5)*f+(p6*a+p7), in radians
        DATAFILE_COMPRESSION_LEVEL = 5
        
        FILTERWHEEL = [{
                        'connected to': 'main_ui',
                        'port' :  'COM8',
                        'baudrate' : 115200,
                        'filters' : {
                                                'IR': 1, 
                                                'empty': 2, 
#                                                'empty': 3, 
#                                                'empty': 4, 
#                                                'empty': 5, 
#                                                'empty': 6, 
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
                                                'ND infinity': 5, 
                                                'ND0': 6, 
                                                }
                        }]
        self.DIGITAL_IO_PORT = 'parallel port'
        self.BLOCK_TRIGGER_PIN = 0
        self.ENABLE_PARALLEL_PORT = True
        self._create_parameters_from_locals(locals())

class TamasSetupConfig(ElphysRetinalCaImagingConfig):
    '''
    '''
    def _set_user_parameters(self):
        root_folder = 'c:\\Data'
        LOG_PATH = os.path.join(root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1024,768])
        COORDINATE_SYSTEM='center'
        
        ENABLE_FRAME_CAPTURE = False
        INSERT_FLIP_DELAY = True
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 0.377
        #SCREEN_PIXEL_WIDTH = 0.5#mm 200 pixels = 100 mm
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (os.name == 'nt')
        ACQUISITION_TRIGGER_PIN = 2
        BLOCK_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 1
        ENABLE_UDP = True
        
        ENABLE_FILTERWHEEL=True
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  'COM1',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },
                        {
                                    'port' :  'COM3',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },
                        ]

