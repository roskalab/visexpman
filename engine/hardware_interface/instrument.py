
try:
    import serial
except:
    pass
import os
import visexpman.engine.generic.configuration
import unittest
import time
import threading


class InvalidFilterPosition(Exception):
    pass
    
class InvalidFilterName(Exception):
    pass


#class Instrument(object):
class Instrument(threading.Thread):
    def __init__(self, config,  settings = None, id = 0):
        '''
        
        '''
        self.id = id
        self.settings = settings
        self.config = config
        self.init_communication_interface(config)
        self.init_instrument(config, settings)
        self.started = False
        threading.Thread.__init__( self )
        
    def init_communication_interface(self, config):
        '''
        Method for initializing communication interface via commands will be sent to instrument
        '''
        pass
        
    def init_instrument(self, config, settings):
        '''
        Method for initialize the instrument
        '''
        pass

    def run( self ):
        '''
        Start instrument task by starting instrument operation
        '''
        self.start_instrument()
        
    def start_instrument(self):
        '''
        Starts instrument operation assuming that the initialization has been performed before
        '''
        pass

    def stop( self ):
        '''
        Stops instrument operation
        '''
        
        self.stop_instrument()
        
    def stop_instrument(self):
        pass

    def close_instrument(self):
        '''
        Closes instrument, after this the instrument object has to be recreated 
        '''        
        pass

        
    def close_communication_interface(self):
        pass
        
    def __del__(self):
        self.close_instrument()
        self.close_communication_interface()
        
class Filterwheel(Instrument):
    def init_communication_interface(self, config):        
        self.serial_port = serial.Serial(port =config.FILTERWHEEL_SERIAL_PORT[self.id]['port'], 
                                                    baudrate = config.FILTERWHEEL_SERIAL_PORT[self.id]['baudrate'],
                                                    parity = config.FILTERWHEEL_SERIAL_PORT[self.id]['parity'],
                                                    stopbits = config.FILTERWHEEL_SERIAL_PORT[self.id]['stopbits'],
                                                    bytesize = config.FILTERWHEEL_SERIAL_PORT[self.id]['bytesize'])
        try:
            self.serial_port.open()
        except AttributeError:
            pass

    def set(self,  position = -1):        
        if self.config.FILTERWHEEL_VALID_POSITIONS[0] <= position and self.config.FILTERWHEEL_VALID_POSITIONS[1] >= position:
            self.serial_port.write('pos='+str(position) +'\r')
            time.sleep(self.config.FILTERWHEEL_SETTLING_TIME)
        else:
            raise InvalidFilterPosition
        
    def set_filter(self,  filter = ''):
        position_to_set = -1
        for k,  v in self.config.FILTERWHEEL_FILTERS[self.id].items():
            if k == filter:
                position_to_set = self.config.FILTERWHEEL_FILTERS[self.id][k]
                
        if position_to_set != -1:
            self.set(position_to_set)
        else:
            raise InvalidFilterName
        
        
    def close_communication_interface(self):
        try:
            self.serial_port.close()
        except AttributeError:
            pass
            
class testConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        if os.name == 'nt':
            port = 'COM6'
        else:
            port = '/dev/ttyUSB0'
            
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }] ]
                                    
        FILTERWHEEL_SETTLING_TIME = [2.0,  [0,  20]]

        FILTERWHEEL_VALID_POSITIONS = [[1, 6],  [[0, 0],  [100, 100]]]
        
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
        self._create_parameters_from_locals(locals())
   
class testFilterwheel(unittest.TestCase):
#test constructor
    def test_filterwheel_communication_port_open(self):
        conf = testConfig()
        fw = Filterwheel(conf)
#        self.assertRaises(NoneType,  Filterwheel,  communication_config = communication_config) 

    def test_filterwheel_communication_port_open_with_invalid_configuration_1(self):
        conf = testConfig()
        conf.FILTERWHEEL_SERIAL_PORT[0]['port'] = '/dev/mismatch/ttyUSB0'        
        self.assertRaises(serial.SerialException,  Filterwheel,  conf) 

    def test_filterwheel_communication_port_open_with_invalid_configuration_2(self):
        conf = testConfig()
        conf.FILTERWHEEL_SERIAL_PORT[0]['parity'] = 1        
        self.assertRaises(ValueError,  Filterwheel,  conf) 
        
#test set position
    def test_set_filterwheel_position(self):
        conf = testConfig()
        fw = Filterwheel(conf)
        fw.set(1)
        
    def test_set_filterwheel_invalid_position(self):
        conf = testConfig()
        fw = Filterwheel(conf)        
        self.assertRaises(InvalidFilterPosition,  fw.set,  100)
        
#test set filterwheel
    def test_set_filter(self):
        conf = testConfig()
        fw = Filterwheel(conf)
        fw.set_filter('ND50')
        
    def test_set_invalid_filter_name(self):
        conf = testConfig()
        fw = Filterwheel(conf)
        self.assertRaises(InvalidFilterName,  fw.set_filter,  10)        
        
if __name__ == "__main__":    
    unittest.main()

    
