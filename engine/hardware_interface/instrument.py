try:
    import serial
except ImportError:
        pass
import os
import unittest
import time
import multiprocessing
import threading

import visexpman.engine.generic.configuration
from visexpman.engine.generic import utils, fileop, log
import logging
import visexpman
try:
    from visexpman.users.test import unittest_aggregator
    test_mode=True
except:
    test_mode=False
    
class InstrumentProcess(threading.Thread, log.LoggerHelper):
    '''
    Superclass of instrument control related operations that need to run in a separate process
    
    It can be controlled via command_queue. This is available in experiment classes
    Queues:
    command: commands for controlling the process
    response: responses to commands are put here by the process
    data: data acquired by process
    '''
    def __init__(self, instrument_name, queues, logger):
        threading.Thread.__init__(self)
        self.queues = queues
        self.log = logger
        self.instrument_name = instrument_name
        if hasattr(self.log, 'add_source'):
            self.log.add_source(instrument_name)
        elif hasattr(self.log, 'put'):
            log.LoggerHelper.__init__(self, self.log)
            
    def terminate(self):
        self.queues['command'].put('terminate')
        self.join()
            
    def printl(self,msg, loglevel='info'):
        if hasattr(self.log, loglevel):
            logfunc = getattr(self.log,loglevel)
        elif hasattr(self, loglevel):
            logfunc = getattr(self,loglevel)
        else:
            return
        logfunc(str(msg), self.instrument_name)

class Instrument(object):
    '''
    The basic concept of enabling/disabling instruments: classes can be instantiated when the corresponding instrument is disabled. All the instrument classes shall be implemented in a way,
    that hardware calls are executed only in enabled state. The rationale behind this, is to ensure that the user do not have to take care of ENABLE* parameters at experiment level.
    '''
    def __init__(self, config,  log = None, experiment_start_time = None, settings = None, id = 0):
        '''
        States: init, ready, running, closed
        '''
        self.state = 'init'
        self.id = id
        self.settings = settings
        self.config = config
        self.log = log
        self.experiment_start_time = experiment_start_time
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
        if experiment_start_time != None:
            elapsed_time = time.time() - experiment_start_time
        else:        
            elapsed_time = time.time()
        return elapsed_time
        
    def log_during_experiment(self, log_message):
        if hasattr(self.log, 'info'):
            self.log.info(log_message)

#    def __del__(self):        
#        self.release_instrument()

#try:
#    import parallel
#    class InstrumentWithParallel(Instrument, parallel.Parallel):
#        pass
#    parallel_port_ancestors = InstrumentWithParallel
#except ImportError:
parallel_port_ancestors = Instrument

class ParallelPort(parallel_port_ancestors):
    '''
    This class stores the values of the data lines of parallel port to ensure bit level control of these pins.
    '''
    
    def init_instrument(self):
        if self.config.ENABLE_PARALLEL_PORT:
            if self.config.OS=='Windows':
                dllpath=os.environ['WINDIR'] + '\\system32\\inpout' + ('x64' if self.config.IS64BIT else '32')+'.dll'
                if not os.path.exists(dllpath):
                    raise WindowsError('{0} dll does not exists'.format(dllpath))
                from ctypes import windll
                self.p=windll.inpout32
                self.outp_func = getattr(self.p, 'Out'+('64' if self.config.IS64BIT else '32'))
            else:
            
                try:
                    parallel.Parallel.__init__(self)
                except WindowsError:
                    raise RuntimeError('Parallel port cannot be initialized, \
                                       make sure that parallel port driver is installed and started')
        #Here create the variables that store the status of the IO lines
        self.iostate = {}
        self.iostate['data'] = 0
        self.iostate['data_strobe'] = 0
        self.iostate['auto_feed'] = 0
        #Input pin assignments:
        self.input_pins = {'10' : 'getInAcknowledge', '11': 'getInBusy', '15': 'getInError', '12': 'getInPaperOut', '13': 'getInSelected'}
        self.iostate['in'] = {}
        if self.config.ENABLE_PARALLEL_PORT:
            self._update_io()#clear all output pins
            if self.config.OS=='Linux':
                for pin in self.input_pins.keys():
                    self.iostate['in'][pin] = self.read_pin(pin)

    def _update_io(self):
        if self.config.OS=='Windows':
            self.outp_func(0x378,self.iostate['data'])
        else:
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
                
    def read_pin(self, pin):
        '''
        Pin: physical pin number
        Input line - pin assignment:
        getInAcknowledge - 10
        getInBusy - 11
        getInError - 15
        getInPaperOut - 12
        getInSelected - 13
        '''
        if not isinstance(pin, str):
            pin_ = str(pin)
        else:
            pin_ = pin
        if not self.input_pins.has_key(pin_):
            raise RuntimeError('Invalid pin: {0},  Supported input pins: {1}'.format(pin_, self.input_pins.keys()))
        if self.config.ENABLE_PARALLEL_PORT:
            return bool(getattr(self, self.input_pins[pin_])())
        else:
            return False
                    
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

def set_filterwheel(filter, config):
    '''
    config is expected to have port baudrate and filters keys
    '''
    serial_port = serial.Serial(port = config['port'], baudrate = config['baudrate'])
    serial_port.write('pos='+str(config['filters'][filter]) +'\r')
    time.sleep(2)
    serial_port.close()

class testConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):        
            
        self.EXPERIMENT_LOG_PATH = fileop.select_folder_exists(unittest_aggregator.TEST_working_folder)
        self.TEST_DATA_PATH = fileop.select_folder_exists(unittest_aggregator.TEST_working_folder)
        self.ENABLE_FILTERWHEEL = unittest_aggregator.TEST_filterwheel
        return#TODO: rework all these instrument classes
        ENABLE_PARALLEL_PORT = True
        ENABLE_SHUTTER = True
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  unittest_aggregator.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }, ]                                    
        FILTERWHEEL_SETTLING_TIME = [2.0,  [0,  20]]
        FILTERWHEEL_VALID_POSITIONS = [[1, 6],  [[0, 0],  [100, 100]]]        
        FILTERWHEEL_FILTERS = [{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]                                                
        SHUTTER_SERIAL_PORT = [{
                                    'port' :  'TBD',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]                                     
        SHUTTER_COMMUNICATION = 'serial_port'        
        SHUTTER_PIN = [2, [0, 7]]        
        self._create_parameters_from_locals(locals())
        
class testLogClass():
    def __init__(self, config):
        self.logfile_path = fileop.generate_filename(config.TEST_DATA_PATH + os.sep + 'log_' +  utils.date_string() + '.txt')        
        self.log = logging.getLogger(self.logfile_path)
        self.handler = logging.FileHandler(self.logfile_path)
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.INFO)
        self.log.info('instrument test')

if test_mode:   
    class TestParallelPort(unittest.TestCase):
        def setUp(self):
            self.state = 'experiment running'
            self.config = testConfig()
            self.experiment_control = testLogClass(self.config)
            
        def tearDown(self):
            self.experiment_control.handler.flush()
            
    #== Parallel port ==
    
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_01_set_bit_on_parallel_port(self):        
            p = ParallelPort(self.config, self.experiment_control)
            p.set_data_bit(0, 1)
            self.assertEqual((p.iostate),  ({'data': 1, 'data_strobe' : 0, 'auto_feed': 0}))
            p.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_02_set_bit_on_parallel_port(self):        
            p = ParallelPort(self.config, self.experiment_control)
            p.set_data_bit(0, True)
            self.assertEqual((p.iostate),  ({'data': 1, 'data_strobe' : 0, 'auto_feed': 0}))
            p.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_03_set_invalid_bit_on_parallel_port(self):        
            p = ParallelPort(self.config, self.experiment_control)
            self.assertRaises(RuntimeError,  p.set_data_bit,  -1, 1)
            p.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_04_set_invalid_value_on_parallel_port(self):        
            p = ParallelPort(self.config, self.experiment_control)
            self.assertRaises(RuntimeError,  p.set_data_bit, 0, 1.0)
            p.release_instrument()
        
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_05_toggle_bit_on_parallel_port(self):        
            p = ParallelPort(self.config, self.experiment_control)
            p.set_data_bit(0, True)
            time.sleep(0.1)
            p.set_data_bit(0, False)
            self.assertEqual((p.iostate),  ({'data': 0, 'data_strobe' : 0, 'auto_feed': 0}))
            p.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_parallel_port,  'Parallel port tests disabled')
        def test_06_parallel_port_call_when_disabled(self):        
            self.config.ENABLE_PARALLEL_PORT = False
            p = ParallelPort(self.config, self.experiment_control)
            p.set_data_bit(0, True)        
            self.assertEqual((p.iostate),  ({'data': 0, 'data_strobe' : 0, 'auto_feed': 0}))
            p.release_instrument()        
        
class DummyInstrumentProcess(InstrumentProcess):
    def run(self):
        counter = 0
        while True:
            if not self.queues['command'].empty():
                if self.queues['command'].get() == 'terminate':
                    break
            self.queues['data'].put(counter)
            counter += 1
            self.printl('counter: {0}'.format(counter))
            time.sleep(0.1)
        self.printl('Done')

class TestInstrument(unittest.TestCase):
    def test_01_instrument_process(self):
        fn = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_working_folder), 'log_instrument_test_{0}.txt'.format(int(1000*time.time())))
        instrument_name = 'test instrument'
        logger = log.Logger(filename=fn)
        logger.add_source(instrument_name)
        logqueue = logger.get_queues()[instrument_name]
        ip = DummyInstrumentProcess(instrument_name, {'command': multiprocessing.Queue(), 
                                                                            'response': multiprocessing.Queue(), 
                                                                            'data': multiprocessing.Queue()}, logqueue)
        processes = [ip, logger]
        [p.start() for p in processes]
        time.sleep(5.0)
        ip.terminate()
        time.sleep(1)
        logger.terminate()
#        [p.terminate() for p in processes]
        keywords = map(str,range(5))
        keywords.extend([instrument_name, 'counter', 'Done'])
        map(self.assertIn, keywords, len(keywords)*[fileop.read_text_file(fn)])
        self.assertFalse(ip.queues['data'].empty())
        self.assertTrue(ip.queues['response'].empty())
        
class ProScanIIIShutter(object):
    def __init__(self, serial_port, baudrate=9600,timeout=1):
        self.s=serial.Serial(serial_port,baudrate=baudrate)
        self.s.setTimeout(timeout)
        self.s.write('?\r')
        txt=self.s.read(1000)
        import pdb
        #pdb.set_trace()
        if len(txt)==0:
            raise RuntimeError('Serial communication does not work to ProscanIII Shutter')
        elif not ('PROSCAN' in txt and 'SHUTTERS' in txt):
            raise RuntimeError('Invalid device')
        
        
    def _toggle_shutter(self,state):
        self.s.write('8,A,{0}\r'.format('0' if state else '1'))
        if self.s.read(2)!='R\r':
            raise RuntimeError('Shutter may not be accessible')
            
    def open_shutter(self):
        self._toggle_shutter(True)
        
    def close_shutter(self):
        self._toggle_shutter(False)
        
    def flash(self,duration):
        self.open_shutter()
        time.sleep(duration)
        self.close_shutter()
        
    def close(self):
        self.s.close()
        
class TestShutter(unittest.TestCase):
    def test_01_shutteronoff(self):
        s=ProScanIIIShutter('COM6')
        s.open_shutter()
        time.sleep(2)
        s.close_shutter()
        time.sleep(3)
        s.flash(1)
        s.close()
        
if __name__ == "__main__":    
    unittest.main()
