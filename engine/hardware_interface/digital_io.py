try:
    import serial
except:
    pass
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
except:
    pass
import os,numpy
import time
import unittest
import instrument
import threading
import Queue

class SerialPortDigitalIO(instrument.Instrument):
    '''
    Serial port lines are controlled as digital io lines
    pin 0: orange
    pin1: green
    input pin: brown
    '''
    def init_instrument(self):
        if isinstance(self.config.DIGITAL_IO_PORT, list) and len(self.config.DIGITAL_IO_PORT)>1:
            self.s = []
            for port in self.config.DIGITAL_IO_PORT:
                self.s.append(serial.Serial(port))
        else:
            self.s = [serial.Serial(self.config.DIGITAL_IO_PORT)]
            
    def clear_pins(self):
        if isinstance(self.config.DIGITAL_IO_PORT, list):
            n = len(self.config.DIGITAL_IO_PORT)
        else:
            n=1
        for i in range(n):
            self.set_data_bit(i*2,0)
            self.set_data_bit(i*2+1,0)
        
    def release_instrument(self):
        for s in self.s:
            s.close()

    def pulse(self, channel, width, log=True):
        self.set_data_bit(channel, False, log = log)
        self.set_data_bit(channel, True, log = log)
        time.sleep(width)
        self.set_data_bit(channel, False, log = log)

    def set_pin(self, channel,value):
        self.set_data_bit(channel, value)
        
    def set_data_bit(self, channel, value, log = True):
        '''
        channel 0: TX (orange wire on usb-uart converter)
        channel 1: RTS (green wire on usb-uart converter)
        '''
        device_id = channel/2
        if len(self.s)-1 < device_id:
            raise RuntimeError('Invalid data bit')
        if channel%2 == 0:
            if hasattr(self.s[device_id], 'setBreak'):
                self.s[device_id].setBreak(not bool(value))
            else:
                self.s[device_id].sendBreak(0)
        elif channel%2 == 1:
            self.s[device_id].setRTS(not bool(value))
        if log:
            self.log_during_experiment('Serial DIO pin {0} set to {1}'.format(channel, value))
            
    def read_pin(self,channel=0,inverted=False):
        '''
        pin 0: cts
        Theoretically receiving brake via rx could be pin 1 but no function available for that in pyserial
        '''
        if channel == 0:
            v= self.s[0].getCTS()
            if inverted:
                return not v
            else:
                return v
        else:
            raise NotImplementedError()
            
class Photointerrupter(threading.Thread):
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
                    self.state[id] = current_state
                    self.queues[id].put((now, self.state[id]))
            time.sleep(5e-3)

class ArduinoIO(object):
    def __init__(self,port):
        self.s=serial.Serial(port, baudrate=115200,timeout=1)
        self.state=0
        self.t0=time.time()
        self.wait_done=False
        self.set_do(self.state)
        
    def _wait(self):
        '''
        Wait before sending first commands to arduino to ensure that it is ready for receiving them
        '''
        if self.wait_done:
            return
        while True:
            now=time.time()
            if now-self.t0>0.5:
                self.wait_done=True
                break
            time.sleep(0.1)
        
    def set_pin(self,channel,value):
        if value:
            self.state|=1<<channel
        else:
            self.state&=~(1<<channel)
        self.set_do(self.state)
        #self.s.write('p(\xff)');self.s.read(100)
        
    def set_do(self,value):
        self._wait()
        self.s.write('o'+chr(value))
        time.sleep(2e-3)#On windows computers this delays prevents firmware crash
        
    def pulse_trigger(self,channel):
        self._wait()
        self.s.write('p'+chr(1<<channel))
        time.sleep(2e-3)
        
    def enable_waveform(self, pin,frequency):
        self._wait()
        self.s.write('f'+chr(int(frequency)))
        time.sleep(1e-3)
        self.s.write('w'+chr(1<<pin))
        
    def disable_waveform(self):
        self._wait()
        self.s.write('w'+chr(1<<1))
        
    def close(self):
        self.s.close()
        
class DaqDio(object):
    def __init__(self,channels):
        if not isinstance(channels, list):
            channels=[channels]
        self.daq=[]
        for channel in channels:
            daq = PyDAQmx.Task()
            daq.CreateDOChan(channel,
                                                    'do',
                                                    DAQmxConstants.DAQmx_Val_ChanPerLine)    
            self.daq.append(daq)
            
    def set_data_bit(self, pin, state, log=None):
        digital_values = numpy.array([int(state)], dtype=numpy.uint8)
        self.daq[pin].WriteDigitalLines(1,
                                True,
                                1.0,
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                digital_values,
                                None,
                                None)

    def set_pin(self, channel,value):
        self.set_data_bit(channel, value)

    def close(self):
        for d in self.daq:
            d.ClearTask()
           
class TestConfig(object):
    def __init__(self):
        self.SERIAL_DIO_PORT = 'COM4'
    
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
    
    @unittest.skip('')
    def test_03_test_photointerrupter(self):
        class Config():
            def __init__(self):
                self.PHOTOINTERRUPTER_SERIAL_DIO_PORT = {'0': 'COM12'}
                
        config = Config()
        pi = Photointerrupter(config)
        pi.start()
        time.sleep(10.0)
        pi.command_queue.put('TERMINATE')
        time.sleep(1.0)
        for id in pi.queues.keys():
            print id
            while not pi.queues[id].empty():
                transition = pi.queues[id].get()
                print transition[0] - pi.t0, transition[1]
    
    @unittest.skip('')    
    def test_04_pwm(self):
        config = TestConfig()
        s = SerialPortDigitalIO(config)
        frq = 10.0
        duty_cycle = 0.1
        duration = 10.0
        ton = 1.0/frq*duty_cycle
        toff =1.0/frq*(1.0-duty_cycle)
        print ton, toff,int(duration*frq)
        from visexpman.engine.generic.introspect import Timer
        with Timer(''):
            for i in range(int(duration*frq)):
                s.set_data_bit(1, True)
                time.sleep(ton)
                s.set_data_bit(1, False)
                time.sleep(toff)
        s.release_instrument()
        
    def test_05_AIO(self):
        a=ArduinoIO('COM11' if os.name=='nt' else '/dev/ttyACM0')
        #time.sleep(5e-3)
        pin=5
        for i in range(100):
            a.pulse_trigger(pin)
            #time.sleep(5e-3)
        for i in range(100):
            a.set_pin(pin,1)
            time.sleep(5e-3)
            a.set_pin(pin,0)
            time.sleep(5e-3)
        time.sleep(1)
        a.enable_waveform(pin,20)
        time.sleep(1)
        a.disable_waveform()
        a.close()

if __name__ == '__main__':
    unittest.main()
