import os
import os.path
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class BehavioralTester(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Behavioral tester',  'POLLER':'BehavioralTesterPoller'}
        if os.name == 'nt':
            root_folder = 'c:\\temp'
        else:
            root_folder = '/mnt/datafast/log'
            if not os.path.exists(root_folder):
                root_folder = '/mnt/rznb/log'
        LOG_PATH = root_folder
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        GUI_SIZE = utils.rc((400, 400))
        GUI_REFRESH_PERIOD = 0.1
        if os.name == 'nt':
            comport = 'COM3'
        else:
            comport = '/dev/ttyUSB0'
        self.PHOTOINTERRUPTER_SERIAL_DIO_PORT = {'0': comport}
        self._create_parameters_from_locals(locals())
