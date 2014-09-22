import os
import os.path
import numpy
import tempfile
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import ElphysRetinalCaImagingConfig


class ReiSetupConfig(ElphysRetinalCaImagingConfig):
    
    def _set_user_parameters(self):
        #### paths/data handling ####
        FULLSCREEN = not True
        self.root_folder = 'r:\\production\\rei-setup'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = self.root_folder
        DATA_STORAGE_PATH = os.path.join(self.root_folder, 'datastorage')
        CONTEXT_PATH = self.root_folder
        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        #### Network ####
        self.CONNECTIONS['stim']['ip']['stim'] = None
        self.CONNECTIONS['stim']['ip']['main_ui'] = '172.27.26.49'
        self.CONNECTIONS['ca_imaging']['ip']['ca_imaging'] = '172.27.26.49'#bind to specific network card
        self.CONNECTIONS['ca_imaging']['ip']['main_ui'] = '172.27.26.49'
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
        self.GUI['GUI_SIZE'] =  utils.cr((1280,1024))
#        self.GUI['GUI_SIZE'] =  utils.cr((1024,700))
#        if os.name == 'nt':
#            DAQ_CONFIG[0]['AI_TERMINAL'] = DAQmxConstants.DAQmx_Val_PseudoDiff


        self.SCANNER_CHARACTERISTICS['GAIN'] = [-1.12765460e-04,  -2.82919056e-06]#(p1+p2*A)*f+1, in PU
        self.SCANNER_CHARACTERISTICS['PHASE'] = \
                    [9.50324884e-08,  -1.43226725e-07, 1.50117389e-05,  -1.41414186e-04,   5.90072950e-04,   5.40402050e-03,  -1.18021600e-02]#(p1*a+p2)*f**2+(p3*a**2+p4*a+p5)*f+(p6*a+p7), in radians
        self._create_parameters_from_locals(locals())
