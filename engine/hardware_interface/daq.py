import numpy, unittest, copy, time, multiprocessing,queue, pdb
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    print('No pydaqmx')

def check_device(dev):
    """
    Check if daq device is available
    """
    return PyDAQmx.SelfTestDevice(dev.split('/')[0])==0
    
def check_channel(channel):
    '''
    Check if channel is available and not used by other processes
    '''
    if 'ao' in channel.split('/')[1]:
        set_voltage(channel,0)
    elif 'ai' in channel.split('/')[1]:
        pass#TODO: read in couple samples
    
def set_voltage(channel, voltage):
    nchannels=int(numpy.diff(list(map(float, channel.split('/')[1][2:].split(':'))))[0]+1)
    set_waveform(channel, numpy.ones((nchannels, 10))*voltage,1000)
    
def set_waveform(channels,waveform,sample_rate = 1000):
    '''
    Waveform: first dimension channels, second: samples
    '''
    analog_output, wf_duration = set_waveform_start(channels,waveform,sample_rate = sample_rate)
    set_waveform_finish(analog_output, wf_duration)
    
def set_waveform_start(channels,waveform,sample_rate):
    if len(waveform.shape)!=2 or waveform.shape[0]>waveform.shape[1]:
        raise Exception('Invalid waveform dimensions: {0}'.format(waveform.shape))
    sample_per_channel = waveform.shape[1]
    wf_duration = float(sample_per_channel)/sample_rate
    analog_output = PyDAQmx.Task()
    analog_output.CreateAOVoltageChan(channels,
                                        'ao',
                                        -10.0,
                                        10.0,
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
    analog_output.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        sample_per_channel)

    analog_output.WriteAnalogF64(sample_per_channel,
                                False,
                                wf_duration+1.0,
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                waveform,
                                None,
                                None)
    analog_output.StartTask()
    return analog_output, wf_duration
    
def set_waveform_finish(analog_output, timeout,wait=True):
    if wait:
        analog_output.WaitUntilTaskDone(timeout+1.0)
        analog_output.StopTask()                            
        analog_output.ClearTask()
        
class AnalogRead():
    """
    Utility for recording finite analog signals in a non-blocking way
    """
    def __init__(self, channels, duration, fsample,limits=[-5,5]):
        try:
            self.n_ai_channels=int(numpy.diff(list(map(float, channels.split('/')[1][2:].split(':'))))[0]+1)
        except IndexError:
            raise NotImplementedError('Single channel not parsed')
        self.nsamples=int(duration*fsample)
        self.timeout=duration
        self.ai_data = numpy.zeros(int(self.nsamples*self.n_ai_channels), dtype=numpy.float64)
            
        self.analog_input = PyDAQmx.Task()
        self.analog_input.CreateAIVoltageChan(channels,
                                            'ai',
                                            DAQmxConstants.DAQmx_Val_RSE,
                                            limits[0], 
                                            limits[1], 
                                            DAQmxConstants.DAQmx_Val_Volts,
                                            None)
        self.readb = DAQmxTypes.int32()
        self.analog_input.CfgSampClkTiming("OnboardClock",
                                            fsample,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            DAQmxConstants.DAQmx_Val_FiniteSamps,
                                            self.nsamples)
        self.analog_input.StartTask()
        
    def read(self):
        self.analog_input.ReadAnalogF64(int(self.ai_data.shape[0]/self.n_ai_channels),
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        self.ai_data.shape[0],
                                        DAQmxTypes.byref(self.readb),
                                        None)
        self.ai_data = self.ai_data[:self.readb.value * self.n_ai_channels]
        self.ai_data = self.ai_data.flatten('F').reshape((self.n_ai_channels, self.readb.value))
        self.analog_input.StopTask()
        self.analog_input.ClearTask()
        return self.ai_data
        
def set_digital_line(channel, value):
    digital_output = PyDAQmx.Task()
    digital_output.CreateDOChan(channel,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
    digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([int(value)], dtype=numpy.uint8),
                                    None,
                                    None)
    digital_output.ClearTask()
    
def digital_pulse(channel,duration):
    """
    Software timed digital pulse
    """
    digital_output = PyDAQmx.Task()
    digital_output.CreateDOChan(channel,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
    digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([1], dtype=numpy.uint8),
                                    None,
                                    None)
    time.sleep(duration)
    digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([0], dtype=numpy.uint8),
                                    None,
                                    None)
    digital_output.ClearTask()
            
class SyncAnalogIO():
    def __init__(self, ai_channels,  ao_channels,  timeout=1):
        self.timeout=timeout
        self.ai_channels=ai_channels
        self.ao_channels=ao_channels
        check_device(ai_channels)
        check_channel(ai_channels)
        check_channel(ao_channels)
        self.n_ai_channels=int(numpy.diff(list(map(float, ai_channels.split('/')[1][2:].split(':'))))[0]+1)
        self.n_ao_channels=int(numpy.diff(list(map(float, ao_channels.split('/')[1][2:].split(':'))))[0]+1)
        
    def create_channels(self):
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan(self.ao_channels,
                                                            'ao',
                                                            -5,
                                                            5,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        self.analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(self.ao_channels.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        self.analog_input = PyDAQmx.Task()
        self.analog_input.CreateAIVoltageChan(self.ai_channels,
                                                            'ai',
                                                            DAQmxConstants.DAQmx_Val_RSE,
                                                            -10,
                                                            10,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        self.read_buffer = DAQmxTypes.int32()
        
    def start(self, ai_sample_rate, ao_sample_rate,  waveform):
        if len(waveform.shape)!=2 or waveform.shape[0]>waveform.shape[1]:
            raise Exception('Invalid waveform dimensions: {0}'.format(waveform.shape))
        self.ai_sample_rate=ai_sample_rate
        self.ao_sample_rate=ao_sample_rate
        self.waveform=waveform
        self.number_of_ai_samples = int(waveform.shape[1] * float(self.ai_sample_rate) / float(self.ao_sample_rate))
        if waveform.shape[0]!=self.n_ao_channels:
            raise ValueError("AO channel number ({0}) and waveform dimensions ({1}) do not match".format(waveform.shape[0], self.n_ao_channels))
        self.analog_output.CfgSampClkTiming("OnboardClock",
                                        ao_sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_ContSamps,
                                        waveform.shape[1])
        self.analog_input.CfgSampClkTiming("OnboardClock",
                                        ai_sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_ContSamps,
                                        self.number_of_ai_samples)
        self.analog_output.WriteAnalogF64(waveform.shape[1],
                                False,
                                self.timeout,
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                waveform,
                                None,
                                None)
        self.ai_frames = 0
        self.analog_output.StartTask()
        self.analog_input.StartTask()
                                
    def read(self):
        samples_to_read = int(self.number_of_ai_samples * self.n_ai_channels)
        self.ai_data = numpy.zeros(int(self.number_of_ai_samples*self.n_ai_channels), dtype=numpy.float64)
        self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        samples_to_read,
                                        DAQmxTypes.byref(self.read_buffer),
                                        None)
        ai_data = self.ai_data[:int(self.read_buffer.value * self.n_ai_channels)]
        ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.n_ai_channels, self.read_buffer.value)))
        self.ai_frames += 1
        return ai_data.copy()
        
    def stop(self):
        ai_data=self.read()
        self.analog_output.StopTask()
        self.analog_input.StopTask()
        return ai_data
        
    def close(self):
        self.analog_output.ClearTask()
        self.analog_input.ClearTask()
        
class TestDaq(unittest.TestCase):
    def setUp(self):
        set_voltage('Dev1/ao0:1', 0)
    
    def test_1_terminate_waveform(self):
        #Test is waveform generator can be aborted
        analog_output, wf_duration=set_waveform_start('Dev1/ao0',numpy.ones((1,10000)),1000)
        time.sleep(0.2)
        set_waveform_finish(analog_output, 0.1,wait=False)
        
    def test_2_set_waveform(self):
        set_waveform('Dev1/ao0', numpy.linspace(3, 2, 1000)[:,None].T,1000)
        #TODO: check waveform with analog input recording
    
    def test_3_sync_analog_io_basic(self):
        from pylab import plot,show,figure
        import pdb
        PyDAQmx.SelfTestDevice('Dev1')
        s=SyncAnalogIO('Dev1/ai14:15',  'Dev1/ao0:1')
        s.create_channels()
        waveform=numpy.ones((2, 1000))
        waveform[1]*=.5
        s.start(10000, 10000, waveform)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        for r in reads:
            numpy.testing.assert_almost_equal(waveform[:,1:-1],r[:,1:-1],2)
        s.close()
        #Test different sampling rates with time variant waveform
        s=SyncAnalogIO('Dev1/ai14:15',  'Dev1/ao0:1')
        s.create_channels()
        waveform2=numpy.array([numpy.linspace(1, 2, 10000),numpy.linspace(3, 2, 10000)])
        s.start(200000, 100000, waveform2)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        for r in reads:
            numpy.testing.assert_almost_equal(waveform2,r[:,1::2],2)
        #Restart task
        s.start(10000, 10000, waveform)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        for r in reads:
            numpy.testing.assert_almost_equal(waveform[:,1:-1],r[:,1:-1],2)
        #High speed test
        s.start(1000000,1000000, waveform2)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        for r in reads:
            numpy.testing.assert_almost_equal(waveform2[1:-1],r[1:-1],3)
        #Readout rate
        fsample= 400000
        s.start(fsample,fsample, waveform2)
        t0=time.time()
        reads=[s.read() for i in range(10)]
        dt=time.time()-t0
        expected_runtime=numpy.array(reads).shape[0]*numpy.array(reads).shape[2]/fsample
        numpy.testing.assert_almost_equal(dt,expected_runtime,2)
        print(dt)
        reads.append(s.stop())
        self.assertEqual(len(numpy.array(reads).shape),3)
        s.close()
        
if __name__ == '__main__':
    unittest.main()
