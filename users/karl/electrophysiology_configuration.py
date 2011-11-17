
        
class KarlWindowsConfig(Configuration.PresentinatorConfig):   
    def _set_user_specific_parameters(self):
        RUN_MODE = 'user interface' 
        ENABLE_FILTERWHEEL = True       
        ENABLE_PARALLEL_PORT = True        
        FULLSCR = True
        SCREEN_RESOLUTION = [1024,  768]
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0        
        ARCHIVE_PATH = self.BASE_PATH + os.sep + 'data'
        LOG_PATH = self.BASE_PATH + os.sep + 'data'
        SCREEN_EXPECTED_FRAME_RATE = 75.0
        SCREEN_MAX_FRAME_RATE = 75.0
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

        
        self._set_parameters_from_locals(locals())
        

        
if __name__ == "__main__":
    c = KarlWindowsConfig()
    c.print_parameters() 
