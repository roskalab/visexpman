import serial
import time
import numpy
import struct

class Flowmeter(object):
    def __init__(self, config):
        self.config = config
        self.init_ready = False
        self.running = False
        if not self.config.FLOWMETER['ENABLE']:
            return
        self.s = serial.Serial(self.config.FLOWMETER['SERIAL_PORT']['port'])
        self.s.baudrate = self.config.FLOWMETER['SERIAL_PORT']['baudrate']
        self.s.setTimeout(self.config.FLOWMETER['TIMEOUT'])
        self.s.write('s')#Stopping acquisition if any is running
        if self.reset():
            time.sleep(0.1)
            self.s.write('res={0}\r\n'.format(self.config.FLOWMETER['RESOLUTION']))
            if 'OK' in self.s.read(1000):
                self.init_ready = True
        
    def reset(self):
        if not self.config.FLOWMETER['ENABLE'] and self.running:
            return False
        self.s.write('\r\n')
        time.sleep(0.1)
        self.s.write('reset\r\n')
        time.sleep(5.0)
        response = self.s.read(200)
        if 'wait...' in response and 'INIT...' in response and 'OK' in response:
            self.running = False
            if hasattr(self, 'printc'):
                self.printc('Flowmeter reset')
            return True
        else:
            return False

    def start_measurement(self):
        if not (self.config.FLOWMETER['ENABLE'] and self.init_ready and not self.running):
            return False
        self.s.read(100)
        self.s.write('go\r\n')
        if 'OK' in self.s.read(100):
            self.start_time = time.time()
            self.sample_counter = 0
            self.running = True
            if hasattr(self, 'printc'):
                self.printc('Measurement started')
            return True
        else:
            return False
            
    def stop_measurement(self):
        if not (self.config.FLOWMETER['ENABLE'] and self.init_ready and self.running):
            return False
        self.s.write('s')
        if 'OK' in self.s.read(100):
            self.running = False
            if hasattr(self, 'printc'):
                self.printc('Measurement stopped')
            return True
        else:
            return False
        
    def measure(self):
        if self.config.FLOWMETER['ENABLE'] and self.start_measurement():
            response = self.s.read(100)
            self.parse(response)
            self.stop_measurement()
            
    def read(self, number_of_records):
        if self.running:
            return self.parse(self.s.read(4 * int(number_of_records)))
        else:
            return False, None

    def parse(self, raw):
        bytes = numpy.array(struct.unpack('B'*len(raw),raw))
        start_index = None
        for i in range(len(bytes)-2):
            if bytes[i] == 127 and bytes[i + 1] == 127 and bytes[i + 2] != 127:
                start_index = i
                break
        if start_index is None:
            return False, None
        raw = raw[start_index:]
        number_of_integers = len(raw) / 2.0
        if number_of_integers - int(number_of_integers) == 0:
            values = numpy.array(struct.unpack('>' + 'h'* int(number_of_integers),raw))[1::2]/float(self.config.FLOWMETER['FACTOR'])
            self.sample_counter += values.shape[0]
            return True, values
        else:
            return False, None
        
    def close(self):
        if self.config.FLOWMETER['ENABLE']:
            self.s.close()
            self.init_ready = False
        
if __name__ == '__main__':
    f = Flowmeter()
    print f.init_ready
    f.measure()
    f.close()
