
try:
    import serial
except:
        pass
        
import os
import unittest
import time

import visexpman.engine.generic.configuration
import visexpman.engine.generic.utils as utils
import logging
import visexpman
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

class Instrument():
    '''
    The basic concept of enabling/disabling instruments: classes can be instantiated when the corresponding instrument is disabled. All the instrument classes shall be implemented in a way,
    that hardware calls are executed only in enabled state. The rationale behind this, is to ensure that the user do not have to take care of ENABLE* parameters at experiment level.
    '''
    def __init__(self, config,  caller, settings = None, id = 0):
        '''
        States: init, ready, running, closed
        '''
        self.state = 'init'
        self.id = id
        self.settings = settings
        self.config = config
        self.caller = caller
        self.init_communication_interface()
        self.init_instrument()
        self.started = False        
        self.state = 'ready'
        
    def init_communication_interface(self):
        '''
        Method for initializing communication interface via commands will be sent to instrument
        '''
        pass
        
    def init_instrument(self):
        '''
        Method for initialize the instrument
        '''
        pass

    def run( self ):
        '''
        Start instrument task by starting instrument operation
        '''
        self.state = 'running'
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
#TODO: this shall be removed        
        self.stop_instrument()

#TODO: this shall be removed        
    def stop_instrument(self):
        pass
        
    def release_instrument(self):
        '''
        Call this function to finish the operation of the instrument.
        '''
        self.close_instrument()
        self.close_communication_interface()
        self.state = 'closed'

    def close_instrument(self):
        '''
        Closes instrument, after this the instrument object has to be recreated.
        '''
        pass

    def close_communication_interface(self):
        pass
        
    def get_elapsed_time(self):
        elapsed_time = time.time()
        #This checking is necessary to ensure running test that does not have the full variable environment build up
        if hasattr(self.caller.experiment_control, 'start_time'):
            if isinstance(self.caller.experiment_control.start_time, float):
                elapsed_time = time.time() - self.caller.experiment_control.start_time
        return elapsed_time
        
    def log_during_experiment(self, log_message):
        if self.caller.state == 'experiment running':
            self.caller.experiment_control.log.info('%2.3f\t%s' %(self.get_elapsed_time(), log_message))

#    def __del__(self):        
#        self.release_instrument()

try:
    import parallel
    class InstrumentWithParallel(Instrument, parallel.Parallel):
        pass
    parallel_port_ancestors = InstrumentWithParallel
except ImportError:
    parallel_port_ancestors = Instrument

class ParallelPort(parallel_port_ancestors):
    '''
    This class stores the values of the data lines of parallel port to ensure bit level control of these pins.
    '''
    
    def init_instrument(self):
        if self.config.ENABLE_PARALLEL_PORT:
            parallel.Parallel.__init__(self)
        #Here create the variables that store the status of the IO lines
        self.iostate = {}
        self.iostate['data'] = 0
        self.iostate['data_strobe'] = 0
        self.iostate['auto_feed'] = 0

    def _update_io(self):
        self.setData(self.iostate['data'])
        self.setDataStrobe(self.iostate['data_strobe'])
        self.setAutoFeed(self.iostate['auto_feed'])
        
    def set_data_bit(self, bit, value,  log = True):
        '''
        This function is to be called to change the value of one data bit
        '''
        if self.config.ENABLE_PARALLEL_PORT:
            pin_value = 0
            if isinstance(value, bool):
                pin_value = int(value)
            elif isinstance(value, int):
                pin_value = value
            else:
                raise RuntimeError('Invalid value')
            if bit < 0 or bit > 7:
                raise RuntimeError('Invalid bit position')            
            if pin_value == 1:
                self.iostate['data'] |= 1 << bit
            elif pin_value == 0:
                self.iostate['data'] &= ~(1 << bit)
            self._update_io()
            
            #logging
            if log:                
                self.log_during_experiment('Parallel port data bits set to %i' % self.iostate['data'])                
                    
    def close_instrument(self):
        if self.config.ENABLE_PARALLEL_PORT:            
            if os.name == 'nt':
                if hasattr(parallel.Parallel, '__del__'):
                    parallel.Parallel.__del__(self)
            elif os.name == 'posix':
               parallel.Parallel.__del__(self)

#            if os.name == 'nt':
#                if hasattr(parallel.Parallel, '__del__'):
#                    self.parallel.__del__()
#            elif os.name == 'posix':
#               self.parallel.__del__()
               
        #here a small delay may be inserted        

    def __del__(self):
        #Here we need to override the destructor of parallel.Parallel so that the ParallelPort class could be recalled
        pass        


class Shutter(Instrument):
    def init_communication_interface(self):
        if self.config.ENABLE_SHUTTER:
            if self.config.SHUTTER_COMMUNICATION == 'serial_port':
                self.serial_port = serial.Serial(port =self.config.SHUTTER_SERIAL_PORT[self.id]['port'],
                                                            baudrate = self.config.SHUTTER_SERIAL_PORT[self.id]['baudrate'],
                                                            parity = self.config.SHUTTER_SERIAL_PORT[self.id]['parity'],
                                                            stopbits = self.config.SHUTTER_SERIAL_PORT[self.id]['stopbits'],
                                                            bytesize = self.config.SHUTTER_SERIAL_PORT[self.id]['bytesize'])
            elif self.config.SHUTTER_COMMUNICATION == 'parallel_port':
                pass
        self.shutter_state = 'closed'

    def toggle(self):
        if self.config.ENABLE_SHUTTER:        
            if self.config.SHUTTER_COMMUNICATION == 'serial_port':
                self.serial_port.write('ens\r')
            elif self.config.SHUTTER_COMMUNICATION == 'parallel_port':
                pass
            if self.shutter_state == 'closed':
                self.shutter_state = 'open'
            elif self.shutter_state == 'open':
                self.shutter_state = 'closed'

    def open(self):
        if self.config.ENABLE_SHUTTER:
            if self.config.SHUTTER_COMMUNICATION == 'serial_port':
                if self.shutter_state == 'closed':
                    self.serial_port.write('ens\r')
            elif self.config.SHUTTER_COMMUNICATION == 'parallel_port':
                pass
        
    def close(self):
        if self.config.ENABLE_SHUTTER:
            if self.config.SHUTTER_COMMUNICATION == 'serial_port':
                if self.shutter_state == 'open':
                    self.serial_port.write('ens\r')
            elif self.config.SHUTTER_COMMUNICATION == 'parallel_port':
                pass

    def close_communication_interface(self):
        if self.config.ENABLE_SHUTTER:
            if self.config.SHUTTER_COMMUNICATION == 'serial_port':
                try:
                    self.serial_port.close()
                except AttributeError:
                    pass

class Filterwheel(Instrument):
    def init_communication_interface(self):
        self.position = -1        
        if self.config.ENABLE_FILTERWHEEL:
            self.serial_port = serial.Serial(port =self.config.FILTERWHEEL_SERIAL_PORT[self.id]['port'], 
                                                    baudrate = self.config.FILTERWHEEL_SERIAL_PORT[self.id]['baudrate'],
                                                    parity = self.config.FILTERWHEEL_SERIAL_PORT[self.id]['parity'],
                                                    stopbits = self.config.FILTERWHEEL_SERIAL_PORT[self.id]['stopbits'],
                                                    bytesize = self.config.FILTERWHEEL_SERIAL_PORT[self.id]['bytesize'])
        try:
            if os.name != 'nt':
                self.serial_port.open()
        except AttributeError:
            pass

    def set(self,  position = -1, log = True):
        if self.config.ENABLE_FILTERWHEEL:
            if self.config.FILTERWHEEL_VALID_POSITIONS[0] <= position and self.config.FILTERWHEEL_VALID_POSITIONS[1] >= position:
                self.serial_port.write('pos='+str(position) +'\r')
                time.sleep(self.config.FILTERWHEEL_SETTLING_TIME)
                self.position = position
            else:
                raise RuntimeError('Invalid filter position')
                
            #logging
            if log:
                self.log_during_experiment('Filterwheel set to %i' % position)                
        
    def set_filter(self,  filter = '', log = True):
        if self.config.ENABLE_FILTERWHEEL:
            position_to_set = -1
            for k,  v in self.config.FILTERWHEEL_FILTERS[self.id].items():
                if k == filter:
                    position_to_set = self.config.FILTERWHEEL_FILTERS[self.id][k]
                    
            if position_to_set != -1:
                self.set(position_to_set, log = False)
            else:
                raise RuntimeError('Invalid filter name')
                
            #logging
            if log:
                self.log_during_experiment('Filterwheel set to %s' % filter)                

    def close_communication_interface(self):
        if self.config.ENABLE_FILTERWHEEL:
            try:
                self.serial_port.close()
            except AttributeError:
                pass
            
class testConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        if os.name == 'nt':
            port = 'COM4'
        else:
            port = '/dev/ttyUSB0'
            EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data'
            
        ENABLE_FILTERWHEEL = unit_test_runner.TEST_filterwheel_enable
        ENABLE_PARALLEL_PORT = True
        ENABLE_SHUTTER = True
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
                                                
        SHUTTER_SERIAL_PORT = [[{
                                    'port' :  port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }] ]
                                    
        SHUTTER_COMMUNICATION = 'serial_port'
        
        SHUTTER_PIN = [2, [0, 7]]
        
        if os.name == 'nt':
            TEST_DATA_PATH = 'c:\\_del'
        elif os.name == 'posix':
            TEST_DATA_PATH = '/media/Common/visexpman_data/test'
        
        self._create_parameters_from_locals(locals())
        
class testLogClass():
    def __init__(self, config, caller):
        self.logfile_path = utils.generate_filename(config.TEST_DATA_PATH + os.sep + 'log_' +  utils.date_string() + '.txt')        
        self.log = logging.getLogger(self.logfile_path)
        self.handler = logging.FileHandler(self.logfile_path)
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.INFO)
        self.log.info('instrument test')
   
class testInstruments(unittest.TestCase):
    def setUp(self):
        self.state = 'experiment running'
        self.config = testConfig()
        self.experiment_control = testLogClass(self.config, self)
        
    def tearDown(self):
        self.experiment_control.handler.flush()
        
#== Parallel port ==
    def test_01_set_bit_on_parallel_port(self):        
        p = ParallelPort(self.config, self)
        p.set_data_bit(0, 1)
        self.assertEqual((p.iostate),  ({'data': 1, 'data_strobe' : 0, 'auto_feed': 0}))
        p.release_instrument()
        
    def test_02_set_bit_on_parallel_port(self):        
        p = ParallelPort(self.config, self)
        p.set_data_bit(0, True)
        self.assertEqual((p.iostate),  ({'data': 1, 'data_strobe' : 0, 'auto_feed': 0}))
        p.release_instrument()
        
    def test_03_set_invalid_bit_on_parallel_port(self):        
        p = ParallelPort(self.config, self)
        self.assertRaises(RuntimeError,  p.set_data_bit,  -1, 1)
        p.release_instrument()
        
    def test_04_set_invalid_value_on_parallel_port(self):        
        p = ParallelPort(self.config, self)
        self.assertRaises(RuntimeError,  p.set_data_bit, 0, 1.0)
        p.release_instrument()
    
    def test_05_toggle_bit_on_parallel_port(self):        
        p = ParallelPort(self.config, self)
        p.set_data_bit(0, True)
        time.sleep(0.1)
        p.set_data_bit(0, False)
        self.assertEqual((p.iostate),  ({'data': 0, 'data_strobe' : 0, 'auto_feed': 0}))
        p.release_instrument()
        
    def test_06_parallel_port_call_when_disabled(self):        
        self.config.ENABLE_PARALLEL_PORT = False
        p = ParallelPort(self.config, self)
        p.set_data_bit(0, True)        
        self.assertEqual((p.iostate),  ({'data': 0, 'data_strobe' : 0, 'auto_feed': 0}))
        p.release_instrument()        

#== Filterwheel ==    
#test constructor
    def test_05_filterwheel_communication_port_open(self):        
        fw = Filterwheel(self.config, self)        
        self.assertEqual((hasattr(fw, 'serial_port'), fw.position, fw.state), (True, -1, 'ready'))
        fw.release_instrument()

    def test_06_filterwheel_communication_port_open_with_invalid_configuration_1(self):        
        self.config.FILTERWHEEL_SERIAL_PORT[0]['port'] = '/dev/mismatch/ttyUSB0'        
        self.assertRaises(serial.SerialException,  Filterwheel,  self.config, self)        

    def test_07_filterwheel_communication_port_open_with_invalid_configuration_2(self):        
        self.config.FILTERWHEEL_SERIAL_PORT[0]['parity'] = 1
        self.assertRaises(ValueError,  Filterwheel,  self.config, self)         
        
#test set position
    def test_08_set_filterwheel_position(self):        
        fw = Filterwheel(self.config, self)
        fw.set(1)
        self.assertEqual((hasattr(fw, 'serial_port'), fw.position, fw.state), (True, 1, 'ready'))
        fw.release_instrument()
        
    def test_09_set_filterwheel_invalid_position(self):
        self.config = testConfig()
        fw = Filterwheel(self.config, self)        
        self.assertRaises(RuntimeError,  fw.set,  100)
        fw.release_instrument()
        
#test set filterwheel
    def test_10_set_filter(self):        
        fw = Filterwheel(self.config, self)
        fw.set_filter('ND50')
        self.assertEqual((hasattr(fw, 'serial_port'), fw.position, fw.state), (True, 6, 'ready'))
        fw.release_instrument()
        
    def test_11_set_invalid_filter_name(self):
        fw = Filterwheel(self.config, self)
        self.assertRaises(RuntimeError,  fw.set_filter,  10)
        fw.release_instrument()
        
    def test_12_set_filterwheel_position_when_disabled(self):        
        self.config.ENABLE_FILTERWHEEL = False
        fw = Filterwheel(self.config, self)
        fw.set(1)
        self.assertEqual((hasattr(fw, 'serial_port'), fw.position, fw.state), (False, -1, 'ready'))
        fw.release_instrument()        
        
#== Shutter ==
#    def test_12_shutter_communication_port_open(self):        
#        sh = Shutter(self.config, self)        
#        self.assertEqual(hasattr(sh, 'serial_port'),  True)
#        sh.release_instrument()
#        
#    def test_13_shutter_toggle(self):        
#        sh = Shutter(self.config, self)
#        print 'The shutter should open and close'
#        sh.toggle()
#        time.sleep(1.0)
#        sh.toggle()
#        self.assertEqual(hasattr(sh, 'serial_port'),  True)
#        sh.release_instrument()
#        
#    def test_14_open_shutter(self):
#        pass
#        
#    def test_15_close_shutter(self):
#        pass
#        
#    def test_XX_open_shutter_when_disabled(self):
#        pass
#        
#    def test_16_shutter_parallelport_init(self):
#        pass
#        
#    def test_17_shutter_parallelport_toggle(self):
#        pass
#        
#    def test_18_open_parallelport_shutter(self):
#        pass
#        
#    def test_15_close_parallelport_shutter(self):
#        pass
#        
#    def test_XX_open_parallel_port_shutter_when_disabled(self):
#        pass
        
    
        
if __name__ == "__main__":    
    unittest.main()
#    tc = testConfig()
#    p = ParallelPort(tc)
#    p.set_data_bit(0, 1)

    
