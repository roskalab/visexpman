import os
import os.path
import serial
import numpy
import time

from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

class RcMicroscopeSetup(VisionExperimentConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self):
        TEXT_COLOR = [0.8, 0.0, 0.0]
        GUI_REFRESH_PERIOD = 10.0
        ENABLE_MESEXTRACTOR = True
        ENABLE_CELL_DETECTION = True
        EXPERIMENT_CONFIG = 'MyMovingGratingConfig'
        
        MES_TIMEOUT = 15.0
        CELL_MERGE_DISTANCE = 3.0
        ROI_PATTERN_SIZE = 4
        ROI_PATTERN_RADIUS = 3
        #MES scanning config
        XZ_SCAN_CONFIG = {'LINE_LENGTH':15.0, 'Z_PIXEL_SIZE' : 33.0, 'Z_RESOLUTION':3.03, 'Z_RANGE':80.0}
        ENABLE_ZIGZAG_CORRECTION = True
        #=== paths/data handling ===
        if os.name == 'nt':            
            v_drive_folder = 'V:\\'
            BACKUP_PATH='u:\\backup'
        else:            
            v_drive_folder = '/mnt/datafast'
            BACKUP_PATH='/mnt/databig/backup'
        ANIMAL_FOLDER='/mnt/datafast/animals'
        v_drive_data_folder = os.path.join(v_drive_folder,  'experiment_data')
        LOG_PATH = os.path.join(v_drive_folder, 'log')
        #CAPTURE_PATH = os.path.join(v_drive_folder, 'experiment_data')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        MES_DATA_FOLDER = 'V:\\experiment_data'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.CONTEXT_NAME = 'gui.hdf5'
        CONTEXT_PATH = os.path.join(v_drive_folder, 'context')
        if os.name != 'nt':
            DATABIG_PATH = '/mnt/databig/data'
            self.TAPE_PATH = '/mnt/tape/hillier/invivocortex/TwoPhoton'
            self.PROCESSED_FILES_PATH='/mnt/databig/processed'
        else:
            DATABIG_PATH = 'u:\\data'
        #CAPTURE_PATH = os.path.join(v_drive_folder, 'captured')

        #=== screen ===
        import sys
        if '--MICROLED'in sys.argv:
            SCREEN_RESOLUTION = utils.cr([16, 16])
            SCREEN_DISTANCE_FROM_MOUSE_EYE = [19.0, [0, 300]] #mm
            SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, 
            FULLSCREEN = False
            SCREEN_EXPECTED_FRAME_RATE = 1/50e-3
            SCREEN_MAX_FRAME_RATE = 1/50e-3
            ULED_SERIAL_PORT = 'COM4'
        else:
#            SCREEN_DISTANCE_FROM_MOUSE_EYE = [320.0, [0, 300]] #mm 
#            SCREEN_DISTANCE_FROM_MOUSE_EYE = [220.0, [0, 300]] #mm , screen
#            SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
#            SCREEN_PIXEL_WIDTH = [477.0/1280., [0, 0.99]] # mm, screen
#            SCREEN_RESOLUTION = utils.cr([800, 600])
#            SCREEN_RESOLUTION = utils.cr([1280, 720])#screen
#            self.SCREEN_UPSIDE_DOWN=True
#            FULLSCREEN = True
            SCREEN_EXPECTED_FRAME_RATE = 60.0
            SCREEN_MAX_FRAME_RATE = 60.0
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        #CAPTURE_PATH = os.path.join(v_drive_data_folder,'capture')
        #=== experiment specific ===
        if '--projector'in sys.argv:
            SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
            self.SCREEN_UPSIDE_DOWN=False
            SCREEN_RESOLUTION = utils.cr([800, 600])
            SCREEN_DISTANCE_FROM_MOUSE_EYE = [290.0, [0, 300]] #mm HERE YOU CAN ADJUST SCREEN  - MOUSE EYE DISTANCE
            gamma_corr_filename = os.path.join(CONTEXT_PATH, 'gamma_rc_cortical.hdf5')
        elif '--small_screen'in sys.argv:
            SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
            self.SCREEN_UPSIDE_DOWN=False
            SCREEN_RESOLUTION = utils.cr([800, 600])
            SCREEN_DISTANCE_FROM_MOUSE_EYE = [290.0, [0, 300]] #mm HERE YOU CAN ADJUST SCREEN  - MOUSE EYE DISTANCE
        #elif '--screen'in sys.argv:
        else:
            SCREEN_RESOLUTION = utils.cr([1280, 720])#screen
            self.SCREEN_UPSIDE_DOWN=True
            SCREEN_DISTANCE_FROM_MOUSE_EYE = [225.0, [0, 300]] #mm HERE YOU CAN ADJUST SCREEN  - MOUSE EYE DISTANCE
            SCREEN_PIXEL_WIDTH = [477.0/1280., [0, 0.99]] # mm, screen
            gamma_corr_filename = os.path.join(CONTEXT_PATH, 'gamma_rc_cortical_monitor.hdf5')
        IMAGE_PROJECTED_ON_RETINA = False
        FULLSCREEN = not False
        ONLINE_ANALYSIS_STIMS=['movinggrating','movingdot','led']
    

        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen        
        MAXIMUM_RECORDING_DURATION = [1100, [0, 10000]] #100
        PLATFORM = 'mes'
#        PLATFORM = 'standalone'
        #=== Network ===
        self.JOBHANDLER_PUSHER_PORT=10100
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '192.168.2.4'#'172.27.27.221'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP_FROM_TABLE'] = True
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
            'GUI_MES'  : {'GUI' : {'IP': '192.168.2.4', 'LOCAL_IP': '192.168.2.4', 'PORT': self.BASE_PORT}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT + 1}}, 
            'STIM_MES'  : {'STIM' : {'IP': '192.168.2.4', 'LOCAL_IP': '192.168.2.3', 'PORT': self.BASE_PORT+2}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT + 3}}, 
            'GUI_STIM'  : {'GUI' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': '192.168.2.4', 'LOCAL_IP': '192.168.2.3',  'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANALYSIS'  : {'GUI' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT+6}, 'ANALYSIS' : {'IP': '192.168.2.4', 'LOCAL_IP': '192.168.2.2', 'PORT': self.BASE_PORT + 7}}, 
            }
        self.COMMAND_RELAY_SERVER['SERVER_IP'] = {\
                     'GUI_MES': ['192.168.2.4','192.168.2.4'],
                     'STIM_MES': ['192.168.2.4',''],
                     'GUI_STIM': ['', '192.168.2.4'],
                     'GUI_ANALYSIS'  : ['', '192.168.2.4'],
                     }        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        DIGITAL_OUTPUT='daq'
        FRAME_TRIGGER_LINE='dev1/port0/line1'
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM7',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        goniometer_serial_port = {
                                    'port' :  'COM5',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }
        degree_factor = 0.9/(8*252)
        degree_factor = 0.00045*4 #According to manufacturer
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
                 'ENABLE': True,
                 'SPEED': 2000,
                 'ACCELERATION' : 1000,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : (0.75/51.0)*numpy.ones(3, dtype = numpy.float)
                 }, 
                 {'SERIAL_PORT' : goniometer_serial_port,
                 'ENABLE':True,
                 'SPEED': 1000000,
                 'ACCELERATION' : 1000000,
                 'MOVE_TIMEOUT' : 15.0,
                 'DEGREE_PER_USTEP' : degree_factor * numpy.ones(2, dtype = numpy.float)}]
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:4',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : True
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : True
                    }
                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}

        MAX_REALIGNMENT_OFFSET = 50.0
        ACCEPTABLE_REALIGNMENT_OFFSET = 5.0
        REALIGNMENT_XY_THRESHOLD = 2.0
        REALIGNMENT_Z_THRESHOLD = 1.0
        #MES scanning config
        ADD_CELLS_TO_MOUSE_FILE = False
        
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
        GREEN_LABELING = ['','scaav 2/1 hsyn gcamp3', 'aav 2/1 ef1a gcamp5', 'scaav 2/1 gcamp3 only']
        IMAGING_CHANNELS = 'from_animal_parameter'#'default'#'both', 'from_animal_parameter'
        DEFAULT_PMT_CHANNEL = 'pmtUGraw'#This needs to be set to pmtURraw if scan region xy and xz images are to be acquired using red pmt
        BLACK_SCREEN_DURING_PRE_SCAN = True
        TEXT_COLOR = [0.3,0.0,0.0]
        SYNC_SIGNAL_MIN_AMPLITUDE = 1.3
        
        #gamma_corr_filename = os.path.join(CONTEXT_PATH, 'gamma_rc_cortical_monitor.hdf5')
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction',filelocking=False))
        else:
            pass
            #raise
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":
    pass
    
