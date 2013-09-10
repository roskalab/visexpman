import serial
import os
import time
import unittest
import instrument
import threading
import Queue

class SerialPortDigitalIO(instrument.Instrument):
    '''
    Serial port lines are controlled as digital io lines
    '''
    def init_instrument(self):
        self.s = serial.Serial(self.config.SERIAL_DIO_PORT)
        if os.name != 'nt':
            self.s.open()
        self.set_data_bit(0,0)
        self.set_data_bit(1,0)
        
    def release_instrument(self):
        self.s.close()

    def pulse(self, width):
        self.s.setRTS(False)
        self.s.setRTS(True)
        time.sleep(width)
        self.s.setRTS(False)
        
    def set_data_bit(self, channel, value, log = True):
        '''
        channel 0: TX (orange wire on usb-uart converter)
        channel 1: RTS (green wire on usb-uart converter)
        '''
        if channel == 0:
            self.s.setBreak(not bool(value))
        elif channel == 1:
            self.s.setRTS(not bool(value))
        if log:
            self.log_during_experiment('Serial DIO pin {0} set to {1}'.format(channel, value))
            
class Photointerrrupter(threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self)
        self.config=config
        self.queues = {}
        self.command_queue = Queue.Queue()
        self.s= {}
        self.state = {}
        self.t0 = time.time()
        for id in self.config.PHOTOINTERRUPTER_SERIAL_DIO_PORT.keys():
            self.queues[id] = Queue.Queue()
            self.s[id] = serial.Serial(self.config.PHOTOINTERRUPTER_SERIAL_DIO_PORT[id])
            if os.name != 'nt':
                self.s[id].open()
            self.state[id] = self.s[id].getCTS()
            self.queues[id].put((self.t0, self.state[id]))
            
    def run(self):
        while True:
            if not self.command_queue.empty() and self.command_queue.get() == 'TERMINATE':
                break
            now = time.time()
            for id in self.queues.keys():
                current_state = self.s[id].getCTS()
                if current_state != self.state[id]:
                    self.queues[id].put((now, self.state[id]))
            time.sleep(5e-3)
            
class TestConfig(object):
    def __init__(self):
        self.SERIAL_DIO_PORT = 'COM3'
    
class TestDigitalIO(unittest.TestCase):
    @unittest.skip('')
    def test_01_pulse(self):
        config = TestConfig()
        s = SerialPortDigitalIO(config)
        for i in range(2000):
            s.pulse(10e-3)
            time.sleep(0.05)
    #    s.s.setRTS(True)#pulse_with_power_supply(1e-3)
    #    time.sleep(200.0)
        s.release_instrument()
        
    @unittest.skip('')
    def test_02_test_io_lines(self):
        config = TestConfig()
        s = SerialPortDigitalIO(config)
        for i in range(10):
            s.set_data_bit(0, True)
            s.set_data_bit(1, True)
            s.set_data_bit(0, False)
            s.set_data_bit(1, False)
            time.sleep(10e-3)
        s.release_instrument()
        
    def test_03_test_photointerrupter(self):
        class Config():
            def __init__(self):
                self.PHOTOINTERRUPTER_SERIAL_DIO_PORT = {'0': 'COM3'}
                
        config = Config()
        pi = Photointerrrupter(config)
        pi.start()
        time.sleep(10.0)
        pi.command_queue.put('TERMINATE')
        time.sleep(1.0)
        for id in pi.queues.keys():
            print id
            while not pi.queues[id].empty():
                transition = pi.queues[id].get()
                print transition[0] - pi.t0, transition[1]

if __name__ == '__main__':
    unittest.main()
