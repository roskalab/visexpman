import numpy, unittest, copy, time
import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes

def check_device(dev):
    """
    Check if daq device is available
    """
    return PyDAQmx.SelfTestDevice(dev.split('/')[0])==0
    
def check_channel(channel):
    '''
    Check if channel is available and not used by other processes
    '''

class SyncAnalogIO():
    def __init__(self, ai_channels,  ao_channels,  timeout=1):
        self.timeout=timeout
        self.ai_channels=ai_channels
        self.ao_channels=ao_channels
        check_device(ai_channels)
        check_channel(ai_channels)
        check_channel(ao_channels)
        self.n_ai_channels=numpy.diff(list(map(float, ai_channels.split('/')[1][2:].split(':'))))[0]+1
        self.n_ao_channels=numpy.diff(list(map(float, ao_channels.split('/')[1][2:].split(':'))))[0]+1
        
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
        self.read = DAQmxTypes.int32()
        
    def start(self, ai_sample_rate, ao_sample_rate,  waveform):
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
                                
    def read(self):
        samples_to_read = self.number_of_ai_samples * self.number_of_ai_channels
        self.ai_data = numpy.zeros(self.number_of_ai_samples*self.number_of_ai_channels, dtype=numpy.float64)
        self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        samples_to_read,
                                        DAQmxTypes.byref(self.read),
                                        None)
        ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
        ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
        self.ai_frames += 1
        return ai_data
        
    def stop(self):
        self.analog_output.WaitUntilTaskDone(self.timeout+ float(self.waveform.shape[1])/self.ao_sample_rate)
        ai_data=self.read()
        self.analog_output.StopTask()
        self.analog_input.StopTask()
        return ai_data
        
    def close(self):
        self.analog_output.ClearTask()
        self.analog_input.ClearTask()

class TestDaq(unittest.TestCase):
    def test_sync_analog_io_basic(self):
#        s=SyncAnalogIO('Dev1/ai14:15',  'Dev1/ao0:1')
        s=SyncAnalogIO('Dev3/ai0:1',  'Dev3/ao0:1')
        s.create_channels()
        waveform=numpy.zeros((2, 1000))
        s.start(10000, 10000, waveform)
        time.sleep(3)
        res1=s.stop()
        waveform2=numpy.ones((2, 10000))
        waveform2[1]*=2
        s.start(200000, 100000, waveform2)
        time.sleep(1)
        res2=s.stop()
        waveform3=numpy.ones((2, 10000))
        waveform3[1]=numpy.linspace(1, 2, waveform3.shape[1])
        s.start(200000, 100000, waveform3)
        time.sleep(1)
        res3=s.stop()
        s.close()
        #Todo: compare input/output signals

if __name__ == '__main__':
    unittest.main()
