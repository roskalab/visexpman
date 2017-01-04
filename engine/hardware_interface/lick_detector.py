import serial, multiprocessing, unittest, time, numpy, threading
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import introspect
from pylab import *

#class HitMissProtocolHandler(multiprocessing.Process):
class HitMissProtocolHandler(threading.Thread):
    '''
    '''
    def __init__(self, serial_port, laser_voltage, pre_trial_interval, water_dispense_delay, 
                laser_duration = 0.2, 
                reponse_window_time = 0.5, 
                water_dispense_time = 0.2, 
                drink_time = 2):
        #multiprocessing.Process.__init__(self)
        threading.Thread.__init__(self)
        self.init_wait=2.0
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
        self.log.put('Expected duration: {0}'.format(self.pars[1]+self.pars[2]+self.pars[3]))
        if not hasattr(self.serial_port, 'write'):
            self.s=serial.Serial(self.serial_port, 115200, timeout=1)
        else:
            self.s=self.serial_port
        time.sleep(self.init_wait)
        resp=self.cmd('ping\r\n')
        if 'pong' not in resp:
            self.s.close()
            raise RuntimeError('Lick detector does not respond')
        resp=self.cmd('reset_protocol\r\n')
        if 'Protocol state set to idle' not in resp:
            self.s.close()
            raise RuntimeError('Resetting lick detector failed')
        self.pars[2]-=self.init_wait
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
        if not hasattr(self.serial_port, 'write'):
            self.s.close()
        
class LickProtocolRunner(object):
    def __init__(self, serialport, laser_voltage, pre_trial_interval, water_dispense_delay,  aichannels,  fsample):
        self.ai=daq_instrument.AnalogRecorder(aichannels , fsample)
        self.ai.start()
        time.sleep(0.1)
        self.hmph=HitMissProtocolHandler(serialport,laser_voltage,pre_trial_interval,water_dispense_delay)
        self.hmph.start()
        
    def isrunning(self):
        return self.hmph.is_alive()
        
    def finish(self):
        self.hmph.join()
        self.ai.commandq.put('stop')
        while True:
            d=self.ai.read()
            if d.shape[0]>0: 
                #self.ai.read()
                break
            time.sleep(0.01)
        log=[]
        while not self.hmph.log.empty():
            l=self.hmph.log.get()
            log.append(l)
        self.ai.join()
        return d,  log
    
class TestProtocolHandler(unittest.TestCase):
    @unittest.skip('')
    def test_01_no_lick(self):
        reps=1
        laser_voltage=1
        pre_trial_interval=5
        water_dispense_delay=0.5
        serialport='COM8'
        serialport=serial.Serial(serialport, 115200, timeout=1)
        fsample=5e3
        aichannels='Dev1/ai0:4'
        deltats=[]
        if hasattr(serialport,  'write'):
            time.sleep(2)
        for i in range(reps):
            lpr=LickProtocolRunner(serialport, laser_voltage, pre_trial_interval, water_dispense_delay,  aichannels,  fsample)
            with introspect.Timer(''):
                d, log=lpr.finish()
            t=numpy.arange(d[:, 0].shape[0], dtype=numpy.float)/fsample
            events=t[numpy.where(numpy.diff(numpy.where(d[:,4]>d[:,4].max()/2,1,0))==1)[0]]
            deltats.append((numpy.cast['int'](numpy.diff(events)*1000000))[2:-1])
            print deltats[-1]
            if reps==1:
                print log
                [plot(t, d[:, i]+i*5) for i in range(5)];legend(['reward','lick signal', 'laser', 'lick detector output',  'debug'], loc='lower left');show()
        if hasattr(serialport,  'write'):
            serialport.close()
        deltats=numpy.array(deltats)
        print 'timing std [us]',  deltats.std(axis=0)
    
    #@unittest.skip('') 
    def test_02_lick_generated(self):
        import os, hdf5io
        datafolder='c:\\visexp\\data'
        aggregated_file=os.path.join(datafolder,'aggregated.hdf5')
        lick_indexes=hdf5io.read_item(aggregated_file,'indexes')
        lick=hdf5io.read_item(aggregated_file,'lick')
        wf=lick.values()[numpy.argmax(map(len, lick_indexes.values()))]
        fs=1000
        laser_voltage=1
        pre_trial_interval=15
        water_dispense_delay=0.5
        serialport='COM8'
        serialport=serial.Serial(serialport, 115200, timeout=1)
        if hasattr(serialport,  'write'):
            time.sleep(2)
        fsample=5e3
        aichannels='Dev1/ai0:4'
        lpr=LickProtocolRunner(serialport, laser_voltage, pre_trial_interval, water_dispense_delay,  aichannels,  fsample)
        daq_instrument.set_waveform( 'Dev1/ao0',wf.reshape(1, wf.shape[0]),sample_rate = fs)
        d, log=lpr.finish()
        print log
        t=numpy.arange(d[:, 0].shape[0], dtype=numpy.float)/fsample
        [plot(t, d[:, i]+i*5) for i in range(5)];legend(['reward','lick signal', 'laser', 'lick detector output',  'debug'], loc='lower left');show()
        if hasattr(serialport,  'write'):
            serialport.close()
    
if __name__ == "__main__":
    unittest.main()
