import serial, multiprocessing, unittest, time,  numpy
from visexpman.engine.hardware_interface import daq_instrument
from pylab import *

class HitMissProtocolHandler(multiprocessing.Process):
    '''
    '''
    def __init__(self, serial_port, laser_voltage, pre_trial_interval, water_dispense_delay, 
                laser_duration = 0.2, 
                reponse_window_time = 0.5, 
                water_dispense_time = 0.2, 
                drink_time = 2):
        multiprocessing.Process.__init__(self)
        self.init_wait=10.0
        self.fsample=1000
        self.serial_port=serial_port
        self.pars=[laser_voltage, laser_duration,  pre_trial_interval, reponse_window_time, water_dispense_delay,\
                water_dispense_time, drink_time]
        self.log=multiprocessing.Queue()
        
    def cmd(self, cmd, wait=0):
        self.s.write(cmd);
        if wait>0:
            time.sleep(wait)
        resp=self.s.readline()
        self.log.put(resp)
        return resp
        
    def error(self, msg):
        self.log.put(msg)
        self.s.close()
        raise RuntimeError(msg)
        
    def run(self):
        self.s=serial.Serial(self.serial_port, 115200, timeout=1)
        #self.ai=daq_instrument.AnalogRecorder('Dev1/ai0:4' ,  self.fsample)
        #self.ai.start()
        time.sleep(self.init_wait)
        resp=self.cmd('ping\r\n')
        if 'pong' not in resp:
            self.s.close()
            raise RuntimeError('Lick detector does not respond')
        resp=self.cmd('reset_protocol\r\n')
        if 'Protocol state set to idle' not in resp:
            self.s.close()
            raise RuntimeError('Resetting lick detector failed')
        parstr=','.join(map(str, self.pars))
        cmd='start_protocol,{0}\r\n'.format(parstr)
        resp=self.cmd(cmd)
        resppars=map(float,resp.split(' ')[-1].split(',')[:-1])
        if 'Protocol parameters' not in cmd and self.pars!=resppars:
            self.s.close()
            raise RuntimeError('Protocol start failed, response: {0}'.format(resp))
        time.sleep(self.pars[2])
        while True:
            resp=self.s.readline()
            self.log.put(resp)
            time.sleep(0.1)
            if 'End of trial' in resp:
                break
        self.s.close()
        #self.ai.commandq.put('stop')
        #self.ai.join()
            
        
    
class TestProtocolHandler(unittest.TestCase):
    def setUp(self):
        pass
#        logging.basicConfig(filename= 'c:\\Data\\lick_detector.txt',
#                    format='%(asctime)s %(levelname)s\t%(message)s',
#                    level=logging.INFO)
    
    def test_01_no_lick(self):
        #logging.info('Test 1: no lick')
        #TODO: ai record duration, event time calculations
        self.ai=daq_instrument.AnalogRecorder('Dev1/ai0:4' ,  10000)
        self.ai.start()
        time.sleep(2)
        laser_voltage=1
        pre_trial_interval=2
        water_dispense_delay=0.5
        hmph=HitMissProtocolHandler('COM8',laser_voltage,pre_trial_interval,water_dispense_delay)
        hmph.start()
        time.sleep(pre_trial_interval+water_dispense_delay)
        hmph.join()
        time.sleep(2)
        self.ai.commandq.put('stop')
        time.sleep(3)
        d=self.ai.read()
        print self.ai.read()
        while not hmph.log.empty():
            print hmph.log.get()
        t=numpy.arange(d[:, 0].shape[0], dtype=numpy.float)/1e4
        [plot(t, d[:, i]+i*5) for i in range(5)];legend(['reward','lick signal', 'laser', 'lick detector output',  'debug']);show()
        self.ai.join()
    
if __name__ == "__main__":
    unittest.main()
