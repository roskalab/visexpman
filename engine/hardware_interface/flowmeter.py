try:
    import serial
except:
    pass
import time
import numpy
import struct
import os
import unittest

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
        self.response_time = 0.05
        self.s=serial.Serial(port='COM7' if os.name=='nt' else '/dev/ttyUSB0',baudrate=115200,timeout=0.3)
        self.cmd_SetResolutionto14bit = [0x7E, 0x00, 0x41, 0x01, 0x0C, 0xB1,0x7E]
        self.resp_SetResolutionto14bit = [0x7E, 0x00, 0x41, 0x0, 0x0, 0xBE,0x7E]
        self.cmd_DeviceReset = [0x7E, 0x00, 0xD3, 0x0, 0x2C,0x7E]
        self.resp_DeviceReset = [0x7E, 0x00, 0xD3, 0x0, 0x0, 0x2C,0x7E]
        self.cmd_StartSingleMeasurement = [0x7E, 0x00, 0x31, 0x0, 0xCE,0x7E]
        self.resp_StartSingleMeasurement = [0x7E, 0x00, 0x31, 0x0, 0x0, 0xCE,0x7E]
        self.cmd_GetSingleMeasurement = [0x7E, 0x00, 0x32, 0x0, 0xCD,0x7E]
        self.cmd_GetScaleFactor = [0x7E, 0x00, 0x53, 0x0, 0xAC,0x7E]
        self.cmd_FlowUnit = [0x7E, 0x00, 0x52, 0x0, 0xAD,0x7E]
        self.cmd_GetMeasurementDataType = [0x7E, 0x00, 0x55, 0x0, 0xAA,0x7E]
        self.cmd_GetLinearization = [0x7E, 0x00, 0x45, 0x0, 0xBA,0x7E]
        self.init_device()
        
    def init_device(self):
        cmds = [[self.cmd_DeviceReset, self.resp_DeviceReset], [self.cmd_SetResolutionto14bit, self.resp_SetResolutionto14bit]]
        for cmd, expected_resp in cmds:
            self.send_cmd(cmd)
            resp = self.read_response()
            if cmp(resp, expected_resp) != 0:
                raise RuntimeError('Expexted response is {1}, got: {0}'.format(resp, expected_resp))
        self.get_sensor_info()
            
    def get_sensor_info(self):
        self.send_cmd(self.cmd_GetScaleFactor)
        resp = self.read_response()
        self.scale_factor = float((numpy.array(resp[5:5+resp[4]])*numpy.array([256,1])).sum())
        self.send_cmd(self.cmd_FlowUnit)
        resp = self.read_response()
        val=hex((numpy.array(resp[5:5+resp[4]])*numpy.array([256,1])).sum())
        if val[-2] == '4':
            prefix = 'u'
        else:
            raise NotImplementedError(''.format(val))
        if val[-3] == '4':
            timebase = 'min'
        else:
            raise NotImplementedError(''.format(val))
        if val[-4] == '8':
            unit = 'l'
        else:
            raise NotImplementedError(''.format(val))
        self.send_cmd(self.cmd_GetMeasurementDataType)
        resp = self.read_response()
        self.measurement_data_signed = (resp[5] == 0)
        self.flow_rate_unit = '{0}{1}/{2}'.format(prefix, unit, timebase)
        if 0:
            self.send_cmd(self.cmd_GetLinearization)
            print self.read_response()
        
    def get_flow_rate(self):
        self.send_cmd(self.cmd_StartSingleMeasurement)
        resp = self.read_response()
        if cmp(resp, self.resp_StartSingleMeasurement) != 0:
            raise RuntimeError('Expected response is {1}, got: {0}'.format(resp, expected_resp))
        time.sleep(0.05)
        self.send_cmd(self.cmd_GetSingleMeasurement)
        resp = self.read_response()
        value=resp[5:5+resp[4]]
        if 0x7d in value:
            return
        if not self.measurement_data_signed:
            raise NotImplementedError('unsigned measurement data is not handled')
        raw = (numpy.array(value)*numpy.array([256,1])).sum() 
        flow_rate = int(numpy.cast['int16'](raw))
        return flow_rate/self.scale_factor
        
     
    def hex2str(self, cmd):
        return ''.join(map(chr,cmd))
        
    def str2hexstr(self, resp):
        return map(hex,self.str2hex(resp))
        
    def str2hex(self, resp):
        return map(ord,resp)
        
    def send_cmd(self, cmd):
        self.s.write(self.hex2str(cmd))
        
    def read_response(self):
        time.sleep(self.response_time)
        resp = self.str2hex(self.s.read(1000))
        self.check_response(resp)
        return resp
        
    def check_response(self,resp):
        if not (resp[0] == 0x7E and resp[-1] == 0x7E and resp[1] == 0x0 and resp[3] == 0x0):
            raise RuntimeError('Invalid response: {0}'.format(self.str2hexstr(resp)))
        
    def close(self):
        self.s.close()
        
class TestFlowmeter(unittest.TestCase):
    def test_01_sli2000(self):
        s=SLI_2000Flowmeter()
        for i in range(5):
            print s.get_flow_rate()
        s.close()
    
if __name__ == '__main__':
    if 0:
        f = Flowmeter()
        print f.init_ready
        f.measure()
        f.close()
    else:
        unittest.main()
