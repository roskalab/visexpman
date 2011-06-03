import visual_stimulation.configuration
import os
import generic.parameter
import generic.utils as utils

class RetinaConfig(visual_stimulation.configuration.VisualStimulationConfig):   
    def _set_user_specific_parameters(self):
        FULLSCR = True
        SCREEN_EXPECTED_FRAME_RATE = [60.0]
        FRAME_DELAY_TOLERANCE = [1.0]
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0]]
        FRAME_WAIT_FACTOR = [0.9,  [0.0,  1.0]]
        
        #Coordinate system parameters
        ORIGO = utils.rc((0, 0))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = ['right']
        VERTICAL_AXIS_POSITIVE_DIRECTION = ['down']
        
        #pixel scaling
        SCREEN_UM_TO_PIXEL_SCALE = [1.0,  [1e-3,  1e3]] #um / pixel        
        
        #parallel port
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = [0,  PIN_RANGE]
        FRAME_TRIGGER_PIN = [2,  PIN_RANGE]
        FRAME_TRIGGER_PULSE_WIDTH = [1e-3,  [1e-4,  1e-1]]
        RUN_MODE = 'user interface'
        FULLSCR = True
        SCREEN_RESOLUTION = utils.rc([768, 1024])
        SCREEN__SCREEN_EXPECTED_FRAME_RATE= 75.0
                        
        SCREEN_UM_TO_PIXEL_SCALE = 3 # um/pixel
        SCREEN_DIRECTLY_ONTO_RETINA = True
#if ~isfield(monitor,'distancefrom_mouseeye')
        # error('monitor struct must have a field ''distancefrom_mouseeye'' in cm')

        #  if ~isfield(monitor,'pixelwidth')
        #   error('monitor struct must have a field ''pixelwidth'' in cm')
        
        up_left_corner_origo = False
        if up_left_corner_origo:
            ORIGO = utils.cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
        else:
            ORIGO = utils.cr((0, 0))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
        
        FILTERWHEEL_ENABLE = True
        ENABLE_PARALLEL_PORT = True 
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ARCHIVE_PATH = self.BASE_PATH + os.sep + 'data'
        LOG_PATH = self.BASE_PATH + os.sep + 'data'        
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
                                    
        
