import serial, multiprocessing, unittest, time, numpy, threading
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import introspect, signal
from pylab import *

#class HitMissProtocolHandler(multiprocessing.Process):
class HitMissProtocolHandler(threading.Thread):
    '''
    '''
    def __init__(self, serial_port, laser_voltage, pre_trial_interval, water_dispense_delay, 
                laser_duration = 0.2, 
                reponse_window_time = 0.5, 
                water_dispense_time = 0.2, 
                drink_time = 2,
                wait4lick=1):
        #multiprocessing.Process.__init__(self)
        threading.Thread.__init__(self)
        self.init_wait=2.0*0
        self.fsample=1000
        self.serial_port=serial_port
        self.pars=[laser_voltage, laser_duration,  pre_trial_interval, reponse_window_time, water_dispense_delay,\
                water_dispense_time, drink_time,wait4lick]
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
        ct=0
        while True:
            resp=self.s.readline()
            ct+=1
            if len(resp)>0:
                self.log.put(resp)
            time.sleep(0.1)
            if 'End of trial' in resp or ct>1000:
                break
        if not hasattr(self.serial_port, 'write'):
            self.s.close()
        
class LickProtocolRunner(object):
    def __init__(self, serialport, laser_voltage, pre_trial_interval, water_dispense_delay,  aichannels,  fsample):
        self.ai=daq_instrument.AnalogRecorder(aichannels , fsample)
        self.ai.start()
        time.sleep(3)
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
        
def detect_events(sync, fsample):
    '''
    sync signal order:
        raw lick signal
        lick detector output
        stimulus/laser
        reward
        debug/protocol state changes
        
    1) Converts sync signals to timestamps
    2) Lick number quanitfication
    '''
    #TODO: this function should go to behavioral_data module
    ts=1.0/fsample
    threshold=2.5
    lick=sync[:,1]
    stimulus=sync[:, 2]
    stimulusf=numpy.array([float(stimulus[i:i+5].mean()) for i in range(stimulus.shape[0]-5)])
    reward=sync[:, 3]
    protocol_state=sync[:, 4]
    reward_t=signal.trigger_indexes(reward, abs_threshold=threshold)*ts
    threshold_stim=stimulusf.min()+0.5*(stimulusf.max()-stimulusf.min())
    stimulus_t=signal.trigger_indexes(stimulusf, abs_threshold=threshold_stim)*ts
    if stimulus_t.shape[0]!=2:
        raise RuntimeError('Stim signal is noisy or corrupted. Using the laser may not be safe!!!')
    lick_t=(signal.trigger_indexes(lick, abs_threshold=threshold)*ts)[::2]
    post_stim_lick_happened=lick_t.shape[0]>0 and numpy.nonzero(lick_t>stimulus_t[0])[0].shape[0]>0
    protocol_state_t=(signal.trigger_indexes(protocol_state, abs_threshold=threshold)*ts)[::2]
    if protocol_state_t.shape[0]>=4:
        dt_pretrial=round(protocol_state_t[3]-protocol_state_t[2], 3)
    else:
        dt_pretrial=None
    stim_start=stimulus_t[0]
    stim_end=stimulus_t[1]
    lick_numbers={'total':int(lick_t.shape[0]),  'postflash' : int(numpy.where(lick_t>stimulus_t[0])[0].shape[0])}
    #Was it successful?
    result=reward_t.shape[0]==2
    stat={'lick_numbers':lick_numbers, 'result': result, 'pretrial_duration': dt_pretrial, 'lick_times':lick_t,'stimulus_t':stimulus_t, 'stimulus duration': stimulus_t[1]-stimulus_t[0]}
    stat['lick_result']=False
    if result:
        if post_stim_lick_happened:
            first_lick=lick_t[numpy.where(lick_t>stim_start)[0].min()]
            stat['lick_latency']= round(first_lick-stim_start, 3)
            try:
                first_lick_after_reward=lick_t[numpy.where(lick_t>reward_t[0])[0].min()]
                stat['reward_latency']=first_lick_after_reward-reward_t[0]
                stat['lick_result']=True
            except ValueError:
                pass
            stat['reward_delay']=round(reward_t[0]-first_lick, 3)
            lick_numbers['postreward']=int(numpy.where(lick_t>reward_t[0])[0].shape[0])
        else:#Lick protocol
            stat['reward_delay']=round(reward_t[0]-stimulus_t[0], 3)
        if protocol_state_t.shape[0]>=7:
            stat['drink_time']=round(protocol_state_t[6]-reward_t[1], 3)
    elif (not result) and protocol_state_t.shape[0]>=7:
        stat['response_window']=round(protocol_state_t[5]-protocol_state_t[3], 3)
        
    if 0:
        plot(protocol_state+5);plot(stimulus);plot(reward);plot(lick);show()
    return stat, lick_t, protocol_state_t, stimulus_t
    
    
class TestProtocolHandler(unittest.TestCase):
    @unittest.skip('')
    def test_01_no_lick(self):
        reps=1
        laser_voltage=1.2
        pre_trial_interval=5
        water_dispense_delay=0.5
        serialport='COM9'
        serialport=serial.Serial(serialport, 115200, timeout=1)
        fsample=5e3
        aichannels='Dev2/ai0:4'
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
            detect_events(d, fsample)
            print deltats[-1]
            if reps==1:
                print log
                [plot(t, d[:, i]+i*5) for i in range(5)];legend(['lick raw','lick out', 'stim', 'reward',  'debug'], loc='lower left');show()
        if hasattr(serialport,  'write'):
            serialport.close()
        deltats=numpy.array(deltats)
        print 'timing std [us]',  deltats.std(axis=0)
    
    @unittest.skip('') 
    def test_02_lick_generated(self):
        import os, hdf5io
        datafolder='c:\\visexp\\data'
        aggregated_file=os.path.join(datafolder,'aggregated.hdf5')
        lick_indexes=hdf5io.read_item(aggregated_file,'indexes')
        lick=hdf5io.read_item(aggregated_file,'lick')
        wf=lick.values()[numpy.argmax(map(len, lick_indexes.values()))]
        wfs=[wf]
        nlicks=map(len, lick_indexes.values())
        import random
        random.seed(1)
        ntests=1
        indexes=[random.choice([i for i in range(len(nlicks)) if nlicks[i]>10]) for t in range(ntests-1)]
        wfs.extend([lick.values()[i] for i in indexes])
        fs=1000
        laser_voltage=1
        pre_trial_interval=16
        water_dispense_delay=0.5
        serialport='COM9'
        serialport=serial.Serial(serialport, 115200, timeout=1)
        figct=0
        for wf in wfs:
            if hasattr(serialport,  'write'):
                time.sleep(2)
            fsample=5e3
            aichannels='Dev2/ai0:4'
            lpr=LickProtocolRunner(serialport, laser_voltage, pre_trial_interval, water_dispense_delay,  aichannels,  fsample)
            daq_instrument.set_waveform( 'Dev2/ao0',wf.reshape(1, wf.shape[0]),sample_rate = fs)
            d, log=lpr.finish()
            detect_events(d, fsample)
            print log
            t=numpy.arange(d[:, 0].shape[0], dtype=numpy.float)/fsample
            [plot(t, d[:, i]) for i in range(4)];plot(t, d[:,4]+5)
            plot(t, numpy.ones_like(t)*0.25)
            legend(['lick raw','lick out', 'stim', 'reward',  'debug', 'lick threshold'], loc='upper left',  fontsize=4)
            savefig('c:\\Data\\{0}.png'.format(figct), dpi=300)
            cla()
            clf()
            figct+=1
            #show()
        if hasattr(serialport,  'write'):
            serialport.close()
            
    @unittest.skip('')         
    def test_03_detect_events(self):
        fsample=5e3
        #folder='c:\\Data\\mouse\\data4plotdev\\5\\20170124'
        import os,hdf5io
        #files=[os.path.join(folder,f) for f in  os.listdir(folder) if os.path.splitext(f)[1]=='.hdf5']
        #f=files[0]
        f='C:\\Data\\raicszol\\rtlick\\1\\20170125\\data_HitMiss1secResponseWindow_201701251220300.hdf5'
        d=hdf5io.read_item(f, 'sync')
        detect_events(d, fsample)
        
    
    def test_04_rerun_stat(self):
        import os,hdf5io
        from visexpman.engine.generic import fileop
        folder='c:\\Data\\raicszol\\data4plotdev'
        files=fileop.find_files_and_folders(folder)[1]
        for f in files:
            if os.path.splitext(f)[1]=='.hdf5' and 'animal' not in f:
                print f
                h=hdf5io.Hdf5io(f)
                h.load('sync')
                s=numpy.copy(h.sync)
                h.sync[:,0]=s[:,1]
                h.sync[:,1]=s[:,3]
                h.sync[:,3]=s[:,0]
                h.stat=detect_events(h.sync, 5e3)[0]
                h.save(['stat','sync'])
                h.close()
        
    
if __name__ == "__main__":
    unittest.main()
