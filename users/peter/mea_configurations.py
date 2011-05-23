        
class PetersConfig(Configuration.PresentinatorConfig):
    
    def _set_user_specific_parameters(self):
        ACQUISITION_TRIGGER_PIN = 4
        FRAME_TRIGGER_PIN = 6
        RUN_MODE = 'user interface'
        LOG_PATH = '../data'
        ARCHIVE_PATH = '../data'
        CAPTURE_PATH = '../data'
        ENABLE_PARALLEL_PORT = True
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCR = True
        SCREEN_RESOLUTION = [800,   600]
        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 30.0
        SCREEN_MAX_FRAME_RATE = 30.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = True

        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  '/dev/ttyUSB0',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]
        
        self._set_parameters_from_locals(locals())
        

        
if __name__ == "__main__":
    c = PetersConfig()
    c.print_parameters()