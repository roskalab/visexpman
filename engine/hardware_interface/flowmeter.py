try:
    import serial
except:
    pass
import time
import numpy
import struct
import os

class Flowmeter(object):
    def __init__(self, config):
        self.config = config
        self.init_ready = False
        self.running = False
        if hasattr(self.config, 'EMULATE_FLOWMETER'):
            self.emulate = self.config.EMULATE_FLOWMETER
        else:
            self.emulate = False
        if not self.config.FLOWMETER['ENABLE']:
            return
        if self.emulate:
            self.init_ready = True
        else:
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
        if self.emulate:
            if hasattr(self, 'printc'):
                self.printc('Flowmeter reset')
            return True
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
        if self.emulate:
            if hasattr(self, 'printc'):
                self.printc('Measurement started')
            self.start_time = time.time()
            self.sample_counter = 0
            self.running = True
            return True
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
        if self.emulate:
            if hasattr(self, 'printc'):
                self.printc('Measurement stopped')
            self.running = False
            return True
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
            if self.emulate:
                emulated_data = []
                for i in range(int(number_of_records)):
                    emulated_data.append(0.1*(int(time.time()* 1000)%100000-50000))
                return True, numpy.array(emulated_data)
            else:
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
            
class SLI_2000Flowmeter(object):
    def __init__(self):
        self.s=serial.Serial(port='COM6' if os.name=='nt' else '/dev/ttyUSB0',baudrate=115200,timeout=1)
        self.cmd_SetResolutionto14bit = [0x7E, 0x00, 0x41, 0x01, 0x0C, 0xB1,0x7E]
        self.cmd_SetTotalizatorStatusEnabled = [0x7E, 0x00, 0x37, 0x01, 0x01, 0xC6,0x7E]
        self.cmd_StartContinuousMeasurement20ms = [0x7E, 0x00, 0x33, 0x02, 0x0, 0x14, 0xB6,0x7E]
        self.cmd_ResetTotalizator = [0x7E, 0x00, 0x39, 0x0, 0xC6,0x7E]
        self.cmd_DeviceReset = [0x7E, 0x00, 0xD3, 0x0, 0x2C,0x7E]
        self.cmd_GetTotalizatorValue = [0x7E, 0x0, 0x38, 0x0, 0xC7, 0x7E]
        self.init_procedure()
        
    def init_procedure(self):
        cmds = [self.cmd_DeviceReset, self.cmd_SetResolutionto14bit, self.cmd_StartContinuousMeasurement20ms, self.cmd_SetTotalizatorStatusEnabled, self.cmd_ResetTotalizator, self.cmd_GetTotalizatorValue]
        for cmd in cmds:
            self.send_cmd(cmd)
            time.sleep(0.1)
            print self.read_response()
     
    def hex2str(self, cmd):
        return ''.join(map(chr,cmd))
        
    def str2hex(self, resp):
        return map(hex,map(ord,resp))
        
    def send_cmd(self, cmd):
        self.s.write(self.hex2str(cmd))
        
    def read_response(self):
        return self.str2hex(self.s.read(1000))
        
    def close(self):
        self.s.close()
    
if __name__ == '__main__':
    if 0:
        f = Flowmeter()
        print f.init_ready
        f.measure()
        f.close()
    else:
        s=SLI_2000Flowmeter()
        s.close()
