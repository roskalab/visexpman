import os
import os.path
import numpy
import tempfile
import time
try:
    import serial
except:
    pass
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import HiMEAConfig

class MEAConfig(HiMEAConfig):
    
    def _set_user_parameters(self):
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([600, 600])
        SCREEN_EXPECTED_FRAME_RATE = 60
        COLOR_MASK = numpy.array([1.0, 1.0, 1.0])
        PLATFORM = 'hi_mea'
        
        # Scale:
        self.ELECTRODE_PITCH=17.5
        self.RETINA_ROOM_SCALE = 1.0/1.75
        SCREEN_UM_TO_PIXEL_SCALE = self.RETINA_ROOM_SCALE
        
        # Folders & paths:
        #self.root_folder = fileop.select_folder_exists(['/home/localadmin/tmp'])
        #folder = '/home/localadmin/recordings/'+time.strftime('%y%m%d'.format(os.sep))+'/data/'
        import getpass
        username = getpass.getuser()
        
        recordingMachineName = 'bs-hpws18' # retina room: bs-hpws19
        folder = '/mnt/' + recordingMachineName + '/' + username + '/' + time.strftime('%y%m%d'.format(os.sep)) + '/data/'
        folder = '/home/rolandd/rolandd-fileshare/tmp'
        
        if not os.path.isdir(folder):
            os.makedirs(folder)
        
        self.root_folder = folder
        
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #
        DIGITAL_IO_PORT = 'parallel port'
        ENABLE_PARALLEL_PORT = True
        # For USB: DIGITAL_IO_PORT = 'COM5'
        
        EXPERIMENT_DATA_PATH = self.root_folder
        #EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['/home/localadmin/tmp']) #'/links/rolandd/tmp/lightX_stim_logs/'+time.strftime('%y%m%d{0}data'.format(os.sep)), 
        CONTEXT_PATH = self.root_folder
        EXPERIMENT_FILE_FORMAT = 'mat'
#        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
#        os.mkdir(CAPTURE_PATH)
        
        RECORDING_MACHINE_PORT = recordingMachineName + ':75000'
        
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True # save each frame as an image
        CAPTURE_PATH = self.root_folder
        COORDINATE_SYSTEM='center'
        FRAME_TRIGGER_PIN = 1
        BLOCK_TRIGGER_PIN = 0
        self.ENABLE_MEA_START_COMMAND = not True # set True when stim software needs to start the recording
        self.INTENSITIES_425NM = numpy.array([0.96, 21, 37.3, 84.5, 127, 263.4, 419, 597, 815, 1080, 1282])
        self.INTENSITIES_550NM = numpy.array([15.6, 17, 20.8, 49, 87, 185, 288, 409, 564, 738, 888])
        self.GAMMA_CORRECTION = numpy.array([numpy.arange(0,1.1,0.1), self.INTENSITIES_425NM]).T
        self._create_parameters_from_locals(locals())

        #### Connect to tho other computers (experimental) ####
        stim_computer_ip = 'localadmin'
        #elphys_computer_ip = '172.27.26.48'
        #imaging_computer_ip = '172.27.26.49'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        #self.CONNECTIONS['ca_imaging']['ip']['ca_imaging'] = imaging_computer_ip #bind to specific network card
        #self.CONNECTIONS['ca_imaging']['ip']['main_ui'] = imaging_computer_ip
        #self.CONNECTIONS['analysis']['ip']['analysis'] = None
        #self.CONNECTIONS['analysis']['ip']['main_ui'] = '172.27.26.49'


class MEAConfigDebug(MEAConfig):
    def _set_user_parameters(self):
        MEAConfig._set_user_parameters(self)
        self.FULLSCREEN = False
