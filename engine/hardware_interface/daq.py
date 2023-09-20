import numpy, unittest, copy, time, multiprocessing,queue, pdb
import ctypes 
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
    if ':' not in channel:
        nchannels=1
    else:
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
        if hasattr(analog_output, 'WaitUntilTaskDone'):
            analog_output.WaitUntilTaskDone(timeout+1.0)
            analog_output.StopTask()                            
            analog_output.ClearTask()
        
class AnalogRead():
    """
    Utility for recording finite analog signals in a non-blocking way
    """
    def __init__(self, channels, duration, fsample,limits=[-5,5], differential=False, timeout=3):
        try:
            self.n_ai_channels=int(numpy.diff(list(map(float, channels.split('/')[1][2:].split(':'))))[0]+1)
        except IndexError:
            raise NotImplementedError('Single channel not parsed')
        self.nsamples=int(duration*fsample)
        self.timeout=timeout
        self.ai_data = numpy.zeros(int(self.nsamples*self.n_ai_channels), dtype=numpy.float64)
            
        self.analog_input = PyDAQmx.Task()
        channelcfg=DAQmxConstants.DAQmx_Val_Diff if differential else DAQmxConstants.DAQmx_Val_RSE
        self.analog_input.CreateAIVoltageChan(channels,
                                            'ai',
                                            channelcfg,
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
        try:
            self.analog_input.ReadAnalogF64(int(self.ai_data.shape[0]/self.n_ai_channels),
                                            self.timeout,
                                            DAQmxConstants.DAQmx_Val_GroupByChannel,
                                            self.ai_data,
                                            self.ai_data.shape[0],
                                            DAQmxTypes.byref(self.readb),
                                            None)
        except:
            pass
        self.ai_data = self.ai_data[:self.readb.value * self.n_ai_channels]
        self.ai_data = self.ai_data.flatten('F').reshape((self.n_ai_channels, self.readb.value))
        self.analog_input.StopTask()
        self.analog_input.ClearTask()
        return self.ai_data
        
    def abort(self):
        try:
            self.analog_input.StopTask()
            self.analog_input.ClearTask()
        except:
            pass
        
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
    def __init__(self, ai_channels, ao_channels, timeout=1, ao_channels2=None):
        self.timeout=timeout
        self.ai_channels=ai_channels
        self.ao_channels=ao_channels
        self.ao_channels2=ao_channels2
        check_device(ai_channels)
        check_channel(ai_channels)
        check_channel(ao_channels)
        if ao_channels2 is not None:
            check_channel(ao_channels2)
        self.n_ai_channels=int(numpy.diff(list(map(float, ai_channels.split('/')[1][2:].split(':'))))[0]+1)
        self.n_ao_channels=int(numpy.diff(list(map(float, ao_channels.split('/')[1][2:].split(':'))))[0]+1)
        if ao_channels2 is not None:
            self.n_ao_channels2=int(numpy.diff(list(map(float, ao_channels2.split('/')[1][2:].split(':'))))[0]+1)
        else:
            self.n_ao_channels2 = 0
            
        buf = ctypes.create_string_buffer(100)
        PyDAQmx.GetDevProductType(self.ai_channels.split('/')[0], buf, 100)
        ai_product_type = buf.value.decode("utf-8")  
        if ai_product_type == "PCIe-6374":
            print("PCIe-6374 detected!")
            self.ai_input_mode = DAQmxConstants.DAQmx_Val_Diff
        else:
            self.ai_input_mode = DAQmxConstants.DAQmx_Val_RSE
       
    def create_channels(self):
        PyDAQmx.DAQmxResetDevice(self.ao_channels.split('/')[0])
        if self.ao_channels2 is not None:
            PyDAQmx.DAQmxResetDevice(self.ao_channels2.split('/')[0])
        time.sleep(0.5)
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan(self.ao_channels,
                                                            'ao',
                                                            -7,
                                                            7,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        if self.ao_channels2 is None:
            self.analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(self.ao_channels.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        else:
            self.analog_output.CfgDigEdgeStartTrig('/{0}/RTSI1' .format(self.ai_channels.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        
        if self.ao_channels2 is not None:
            self.analog_output2 = PyDAQmx.Task()
            self.analog_output2.CreateAOVoltageChan(self.ao_channels2,
                                                                'ao',
                                                                -7,
                                                                7,
                                                                DAQmxConstants.DAQmx_Val_Volts,
                                                                None)
            self.analog_output2.CfgDigEdgeStartTrig('/{0}/RTSI1' .format(self.ai_channels.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        
        
        self.analog_input = PyDAQmx.Task()
        self.analog_input.CreateAIVoltageChan(self.ai_channels,
                                                            'ai',
                                                            self.ai_input_mode,
                                                            -10,
                                                            10,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        if self.ao_channels2 is not None:
            self.analog_input.ExportSignal(DAQmxConstants.DAQmx_Val_StartTrigger, '/{0}/RTSI1' .format(self.ai_channels.split('/')[0]))
            self.analog_output.ExportSignal(DAQmxConstants.DAQmx_Val_10MHzRefClock, '/{0}/RTSI0' .format(self.ao_channels.split('/')[0]))
            
        self.read_buffer = DAQmxTypes.int32()

        if self.ao_channels2 is not None:
            self.analog_output2.SetRefClkRate(10000000)
            self.analog_output2.SetRefClkSrc('/{0}/RTSI0' .format(self.ai_channels.split('/')[0]))

        
    def start(self, ai_sample_rate, ao_sample_rate,  waveform, waveform2=None):
        if len(waveform.shape)!=2 or waveform.shape[0]>waveform.shape[1]:
            raise Exception('Invalid waveform dimensions: {0}'.format(waveform.shape))
        if waveform2 is not None and (len(waveform2.shape)!=2 or waveform2.shape[0]>waveform2.shape[1]):
            raise Exception('Invalid waveform2 dimensions: {0}'.format(waveform2.shape))
        self.ai_sample_rate=ai_sample_rate
        self.ao_sample_rate=ao_sample_rate
        self.waveform=waveform
        self.number_of_ai_samples = int(waveform.shape[1] * float(self.ai_sample_rate) / float(self.ao_sample_rate))
        if waveform.shape[0]!=self.n_ao_channels:
            raise ValueError("AO channel number ({0}) and waveform dimensions ({1}) do not match".format(waveform.shape[0], self.n_ao_channels))
        if waveform2 is not None and (waveform2.shape[0]!=self.n_ao_channels2):
            raise ValueError("AO channel2 number ({0}) and waveform2 dimensions ({1}) do not match".format(waveform2.shape[0], self.n_ao_channels2))
        if self.n_ao_channels2 != 0 and waveform2 is None:
            raise ValueError("AO channel2 is present but waveform2 in None")
        if waveform2 is not None and waveform.shape[1] != waveform2.shape[1]:
            raise Exception('waveform and waveform2 length does not match. waveform length: {0} waveform2 length: {1}'.format(waveform.shape[1], waveform2.shape[1]))
        self.analog_output.CfgSampClkTiming("OnboardClock",
                                        ao_sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_ContSamps,
                                        waveform.shape[1])
        if self.ao_channels2 is not None:        
            self.analog_output2.CfgSampClkTiming("OnboardClock",
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
        if self.ao_channels2 is not None:                          
            self.analog_output2.WriteAnalogF64(waveform2.shape[1],
                                    False,
                                    self.timeout,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    waveform2,
                                    None,
                                    None)
        self.ai_frames = 0
        if self.ao_channels2 is not None:
            self.analog_output2.StartTask()
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
        if self.ao_channels2 is not None:
            self.analog_output2.StopTask()
        return ai_data
        
    def close(self):
        self.analog_output.ClearTask()
        self.analog_input.ClearTask()
        if self.ao_channels2 is not None:
            self.analog_output2.ClearTask()
        
        
class AnalogRecorder(multiprocessing.Process):
    '''
	Records analog inputs until stop signal is sent
	Usage:
	queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue()}
        d=daq_instrument.AnalogRecorder('Dev1/ai0:1' ,  1000)
        d.start()
        time.sleep(10)
        data=numpy.empty([0, 2])
        d.commandq.put('stop')
        while not d.dataq.empty():
            data=numpy.concatenate((data, d.dataq.get()))
        print data.shape
        d.join()

    '''
    def __init__(self, channels, sample_rate, differential=False, save_mode='queue', buffertime=3):
        self.commandq=multiprocessing.SimpleQueue()
        self.dataq=multiprocessing.Queue()
        self.responseq=multiprocessing.SimpleQueue()
        multiprocessing.Process.__init__(self)
        self.channels=channels
        self.sample_rate=int(sample_rate)
        self.timeout=3
        self.buffertime=buffertime
        self.buffer_size=int(self.buffertime*self.sample_rate*10)
        self.number_of_ai_channels= int(numpy.diff(list(map(float, channels.split('/')[1][2:].split(':'))))[0]+1)
        self.channelcfg=DAQmxConstants.DAQmx_Val_Diff if differential else DAQmxConstants.DAQmx_Val_RSE
        self.save_mode=save_mode
        
    def run(self):
        if self.save_mode=='array':
            data=numpy.empty([0, self.number_of_ai_channels])
        self.analog_input = PyDAQmx.Task()
        self.analog_input.CreateAIVoltageChan(self.channels,
                                                            'ai',
                                                            self.channelcfg,
                                                            -10,
                                                            10,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        self.analog_input.CfgSampClkTiming("OnboardClock",
                                        int(self.sample_rate),
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_ContSamps,
                                        self.buffer_size)
                                        
        self.read = DAQmxTypes.int32()
        self.analog_input.StartTask()
        self.number_of_ai_samples = int(self.buffer_size * self.sample_rate * self.number_of_ai_channels)
        self.responseq.put('started')
        self.nreads=0
        self.read_sizes=[]
        while True:
            if not self.commandq.empty():
                cmd=self.commandq.get()
                if cmd=='stop':
                    break
#            try:
            if 1:
                samples_to_read = self.sample_rate
                self.ai_data = numpy.zeros(self.buffer_size*self.number_of_ai_channels, dtype=numpy.float64)
                self.analog_input.ReadAnalogF64(-1,
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        samples_to_read,
                                        DAQmxTypes.byref(self.read),
                                        None)
                ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
                self.read_sizes.append([self.read.value, ai_data.shape])
                ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
                self.nreads+=1
                if self.save_mode=='array':
                    data=numpy.concatenate((data, ai_data))
                elif self.save_mode=='queue':
                    self.dataq.put(ai_data)
        
#            except PyDAQmx.DAQError:
#                pass
            time.sleep(0.15)
        
        self.analog_input.ClearTask()
        if self.save_mode=='array':
            self.dataq.put(data)
        self.responseq.put(f'ready {self.nreads}')
        from visexpman.engine.generic import fileop
#        fileop.write_text_file('d:\sync_read_sizes.txt', '\n'.join([str(i) for i in self.read_sizes]))
        
    def read(self):
        data=numpy.empty([0, self.number_of_ai_channels])
        i=0
        while not self.dataq.empty():
            r=self.dataq.get()
            data=numpy.concatenate((data, r))
            i+=1
            time.sleep(0.02)
#        print(f'number of reads: {i}')
        return data
        
    def stop(self):
        if not self.responseq.empty():
            print(self.responseq.get())
        self.commandq.put('stop')
        time.sleep(self.timeout+1)
        if not self.responseq.empty():
            print(self.responseq.get())
        if self.save_mode=='array':
            if self.dataq.empty():
                time.sleep(5)
            if not self.dataq.empty():
                return self.dataq.get()
            else:
                return numpy.empty([0, self.number_of_ai_channels])
        elif self.save_mode=='queue':
            return self.read()
            
        
class TestDaq(unittest.TestCase):
    def setUp(self):
        set_voltage('Dev6/ao0:1', 0)
    @unittest.skip('') 
    def test_1_terminate_waveform(self):
        #Test is waveform generator can be aborted
        analog_output, wf_duration=set_waveform_start('Dev1/ao0',numpy.ones((1,10000)),1000)
        time.sleep(0.2)
        set_waveform_finish(analog_output, 0.1,wait=False)
        
    @unittest.skip('')    
    def test_2_set_waveform(self):
        set_waveform('Dev1/ao0', numpy.linspace(3, 2, 1000)[:,None].T,1000)
        #TODO: check waveform with analog input recording
    
    @unittest.skip('') 
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
    
    @unittest.skip('') 
    def test_3_sync_analog_io_high_speed(self):
        from pylab import plot,show,figure,legend
        import pdb
        PyDAQmx.SelfTestDevice('Dev6')
        
        s=SyncAnalogIO('Dev6/ai0:3', 'Dev6/ao0:0')
        s.create_channels()
        waveform=numpy.array([numpy.linspace(1, 3, 10000)])
       
        #High speed test
        s.start(2000000,2000000, waveform)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        plot(waveform[0])
        [plot(reads[i][0]) for i in range(2)]
        legend(['waveform', 'input_AI0_0', 'input_AI0_1'])
        show()
        s.close()
        
        
    def test_3_sync_analog_io_high_speed_two_card(self):
        from pylab import plot,show,figure,legend
        import pdb
        PyDAQmx.SelfTestDevice('Dev6')
        
        s=SyncAnalogIO('Dev6/ai0:3', 'Dev6/ao0:0', ao_channels2='Dev5/ao0:0')
        s.create_channels()
        waveform=numpy.array([numpy.linspace(1, 3, 10000)])
        waveform2=numpy.concatenate(5*(numpy.ones(1000),numpy.zeros(1000)))[None,:]
        
        
        #s.start(200000, 100000, waveform2)
        #reads=[s.read() for i in range(3)]
        #reads.append(s.stop())
        #for r in reads:
         #   numpy.testing.assert_almost_equal(waveform2,r[:,1::2],2)
        #High speed test
        s.start(2500000, 2500000/2, waveform, waveform)
        reads=[s.read() for i in range(3)]
        reads.append(s.stop())
        plot(waveform[0])
        plot(waveform[0])
        [plot(reads[i][0][::2]) for i in range(4)]
        [plot(reads[i][1][::2]) for i in range(4)]
        legend(['waveform','waveform2', 'input_AI0_0', 'input_AI0_1', 'input__AI1_0', 'input__AI1_1'])
        show()
        s.close()
        

        
    @unittest.skip('')     
    def test_0_variable_length_ai_recording(self):
        t0=time.time()
        d=AnalogRecorder('Dev1/ai0:1' , 1000)
        d.start()
        time.sleep(10)
        print(d.stop().shape)
        print(time.time()-t0)
        
if __name__ == '__main__':
    unittest.main()
