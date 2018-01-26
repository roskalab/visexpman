import numpy
import time
import instrument
import unittest
import copy
import logging
import os
import platform
import multiprocessing

try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
    default_aimode=DAQmxConstants.DAQmx_Val_RSE
except:
    default_aimode=None
from visexpman.engine.generic import configuration,utils,fileop
try:
    from visexpman.users.test import unittest_aggregator
    test_mode=True
except:
    test_mode=False

WAVEFORM_MIN_DURATION = 0.06 #measured with test 08 on usb-6259, 0.054-0.058 also works

class DaqInstrumentError(Exception):
    '''
    Raised when Daq related error detected
    '''

def analogio(ai_channel,ao_channel,sample_rate,waveform,timeout=1, action=None, aimode=default_aimode, ailimit=5):
    try:
        n_ai_channels=numpy.diff(map(float, ai_channel.split('/')[1][2:].split(':')))[0]+1
    except IndexError:
        n_ai_channels=1
    if os.name=='nt':
        analog_output = PyDAQmx.Task()
        nsamples=waveform.shape[0]
        analog_output.CreateAOVoltageChan(ao_channel,
                                        'ao',
                                        waveform.min()-1, 
                                        waveform.max()+1, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(ai_channel.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        ai_data = numpy.zeros(waveform.shape[0]*n_ai_channels, dtype=numpy.float64)
        analog_input = PyDAQmx.Task()
        analog_input.CreateAIVoltageChan(ai_channel,
                                        'ai',
                                        aimode,
                                        -ailimit, 
                                        ailimit, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        read = DAQmxTypes.int32()
        analog_output.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        nsamples)
        analog_input.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        nsamples)
        analog_output.WriteAnalogF64(nsamples,
                                        False,
                                        timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        waveform,
                                        None,
                                        None)
        analog_output.StartTask()
        analog_input.StartTask()
        if callable(action):
            action()
        time.sleep(waveform.shape[0]/float(sample_rate))
        analog_input.ReadAnalogF64(int(ai_data.shape[0]/n_ai_channels),
                                    timeout,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    ai_data,
                                    ai_data.shape[0],
                                    DAQmxTypes.byref(read),
                                    None)
        ai_data = ai_data[:read.value * n_ai_channels]
        ai_data = ai_data.flatten('F').reshape((n_ai_channels, read.value)).transpose()
        analog_output.StopTask()
        analog_input.StopTask()
    else:
        if callable(action):
            action()
        time.sleep(waveform.shape[0]/float(sample_rate))
        ai_data = numpy.zeros((waveform.shape[0],n_ai_channels), dtype=numpy.float64)
    return ai_data
    
class SimpleAIO(object):
    def __init__(self,ai_channel,ao_channel,sample_rate,waveform,timeout=1):
        self.timeout=timeout
        n_ai_channels=numpy.diff(map(float, ai_channel.split('/')[1][2:].split(':')))[0]+1
        analog_output = PyDAQmx.Task()
        analog_output.CreateAOVoltageChan(ao_channel,
                                        'ao',
                                        waveform.min()-0.1, 
                                        waveform.max()+0.1, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(ai_channel.split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
        ai_data = numpy.zeros(waveform.shape[0]*n_ai_channels, dtype=numpy.float64)
        analog_input = PyDAQmx.Task()
        analog_input.CreateAIVoltageChan(ai_channel,
                                        'ai',
                                        DAQmxConstants.DAQmx_Val_RSE,
                                        -5, 
                                        5, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        self.read = DAQmxTypes.int32()
        analog_output.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        waveform.shape[0])
        analog_input.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        waveform.shape[0])
        analog_output.WriteAnalogF64(waveform.shape[0],
                                        False,
                                        timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        waveform,
                                        None,
                                        None)
        analog_output.StartTask()
        analog_input.StartTask()
        self.analog_input=analog_input
        self.analog_output=analog_output
        self.ai_data=ai_data
        self.n_ai_channels=n_ai_channels
        
    def finish(self):
        n_ai_channels=self.n_ai_channels
        self.analog_input.ReadAnalogF64(int(self.ai_data.shape[0]/n_ai_channels),
                                    self.timeout,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    self.ai_data,
                                    self.ai_data.shape[0],
                                    DAQmxTypes.byref(self.read),
                                    None)
        self.ai_data = self.ai_data[:self.read.value * n_ai_channels]
        self.ai_data = self.ai_data.flatten('F').reshape((n_ai_channels, self.read.value)).transpose()
        self.analog_output.StopTask()
        self.analog_input.StopTask()
        return self.ai_data
        
class SimpleAnalogIn(object):
    def __init__(self,ai_channel,sample_rate,duration, timeout=1, finite=True):
        self.n_ai_channels=numpy.diff(map(float, ai_channel.split('/')[1][2:].split(':')))[0]+1
        self.nsamples=int(duration*sample_rate)
        self.timeout=timeout
        self.finite=finite
        if os.name=='nt':
            if self.finite:
                self.ai_data = numpy.zeros(self.nsamples*self.n_ai_channels, dtype=numpy.float64)
            else:
                self.ai_frames=[]
            self.analog_input = PyDAQmx.Task()
            self.analog_input.CreateAIVoltageChan(ai_channel,
                                            'ai',
                                            DAQmxConstants.DAQmx_Val_RSE,
                                            -5, 
                                            5, 
                                            DAQmxConstants.DAQmx_Val_Volts,
                                            None)
            self.readb = DAQmxTypes.int32()
            self.analog_input.CfgSampClkTiming("OnboardClock",
                                            sample_rate,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            DAQmxConstants.DAQmx_Val_FiniteSamps if finite else DAQmxConstants.DAQmx_Val_ContSamps,
                                            self.nsamples)
            self.analog_input.StartTask()
            
            
    def read(self):
        if not self.finite:
            self.ai_data = numpy.zeros(self.nsamples*self.n_ai_channels, dtype=numpy.float64)
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
        else:
            self.analog_input.ReadAnalogF64(int(self.ai_data.shape[0]/self.n_ai_channels),
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        self.ai_data.shape[0],
                                        DAQmxTypes.byref(self.readb),
                                        None)
                
        self.ai_data = self.ai_data[:self.readb.value * self.n_ai_channels]
        self.ai_data = self.ai_data.flatten('F').reshape((self.n_ai_channels, self.readb.value)).transpose()
        if not self.finite:
            self.ai_frames.append(self.ai_data.copy())
            
    def finish(self):
        self.read()
        self.analog_input.StopTask()
        if not self.finite:
            self.ai_data=numpy.concatenate(self.ai_frames)
        return self.ai_data
    
def analogi(ai_channel,sample_rate,duration, timeout=1):
    n_ai_channels=numpy.diff(map(float, ai_channel.split('/')[1][2:].split(':')))[0]+1
    nsamples=int(duration*sample_rate)
    if os.name=='nt':
        ai_data = numpy.zeros(nsamples*n_ai_channels, dtype=numpy.float64)
        analog_input = PyDAQmx.Task()
        analog_input.CreateAIVoltageChan(ai_channel,
                                        'ai',
                                        DAQmxConstants.DAQmx_Val_RSE,
                                        -5, 
                                        5, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        read = DAQmxTypes.int32()
        analog_input.CfgSampClkTiming("OnboardClock",
                                        sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_FiniteSamps,
                                        nsamples)
        analog_input.StartTask()
        time.sleep(duration)
        analog_input.ReadAnalogF64(int(ai_data.shape[0]/n_ai_channels),
                                    timeout,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    ai_data,
                                    ai_data.shape[0],
                                    DAQmxTypes.byref(read),
                                    None)
        ai_data = ai_data[:read.value * n_ai_channels]
        ai_data = ai_data.flatten('F').reshape((n_ai_channels, read.value)).transpose()
        analog_input.StopTask()
    else:
        if callable(action):
            action()
        time.sleep(duration)
        ai_data = numpy.zeros((ai_data.shape[0],n_ai_channels), dtype=numpy.float64)
    return ai_data

class ControlLoop():
    def __init__(self):
        pass
        
    def run(self):
        nsamples = 10
        nsamples1 = 1000
        analog_output = PyDAQmx.Task()
        analog_output.CreateAOVoltageChan('/Dev1/ao0',
                                        'ao',
                                        -10.0,
                                        10.0,
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
                                        
        analog_input = PyDAQmx.Task()
        analog_input.CreateAIVoltageChan('/Dev1/ai0',
                                                        'ai',
                                                            DAQmxConstants.DAQmx_Val_RSE,
                                                            -10.0,
                                                            10.0,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        read = DAQmxTypes.int32()
        analog_input.CfgSampClkTiming("OnboardClock",
                                        1000,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        DAQmxConstants.DAQmx_Val_ContSamps,
                                        nsamples)
                                        
        analog_input.StartTask()
        analog_output.StartTask()
        data=[]
        vref = 5.0
        t0=time.time()
        error=0.0
        while True:
            ai_data = numpy.zeros(nsamples, dtype=numpy.float64)
            analog_input.ReadAnalogF64(nsamples,
                                        0.2,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        ai_data,
                                        nsamples,
                                        DAQmxTypes.byref(read),
                                        None)
            data.append(copy.deepcopy(ai_data))
#            error = vref - ai_data[-1]
            now = time.time()
            if now-t0>=3.0:
                break
            elif now-t0>=1.05:
                error = 0.0
            elif now-t0>=1.0:
                error = 5.0
            analog_output.WriteAnalogF64(1,True,10.0,
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                numpy.ones(1)*error,
                                None,
                                None)
            pass
            
        analog_output.StopTask()
        analog_input.StopTask()
        analog_input.ClearTask()
        analog_output.ClearTask()
        if 0:
            from pylab import plot,show
            plot(numpy.array(data).flatten())
            show()
        

def parse_channel_string(channels):
    '''
    Returns channel indexes, device name, channel type
    '''
    channel_indexes = map(int, channels.split('/')[-1].replace('ao','').replace('ai','').split(':'))
    device_name = channels.split('/')[0]
    if len(channel_indexes) == 1:
        nchannels = 1
    else:
        nchannels = channel_indexes[1]-channel_indexes[0]+1
    return device_name, nchannels, channel_indexes
    
    
def ai_channels2daq_channel_string(channels, daq_device):
    '''
    List of channel indexes/strings is converted to daq string
    '''
    if len(channels)==1:
        return '{0}/ai{1}'.format(daq_device,channels[0])
    elif len(channels)==2:
        return '{0}/ai{1}:{2}'.format(daq_device,channels[0],channels[1])
    else:
        if abs(numpy.diff(channels).max()) != 1:
            raise DaqInstrumentError('Only channels in consecutive order are supported: {0}'.format(channels))
        return '{0}/ai{1}:{2}'.format(daq_device,min(channels),max(channels))
           
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


def set_digital_pulse(channel, duration):
    digital_output = PyDAQmx.Task()
    digital_output.CreateDOChan(channel,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
    digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([int(1)], dtype=numpy.uint8),
                                    None,
                                    None)
    time.sleep(duration)
    digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([int(0)], dtype=numpy.uint8),
                                    None,
                                    None)

    digital_output.ClearTask()
    
def read_digital_line(channel):
    digital_input = PyDAQmx.Task()
    digital_input.CreateDIChan(channel,'di', DAQmxConstants.DAQmx_Val_ChanPerLine)
    data = numpy.zeros((1,), dtype=numpy.uint8 )
    total_samps = DAQmxTypes.int32()
    total_bytes = DAQmxTypes.int32()
    digital_input.ReadDigitalLines(1,0.1,DAQmxConstants.DAQmx_Val_GroupByChannel,data,1,DAQmxTypes.byref(total_samps),DAQmxTypes.byref(total_bytes),None)
    digital_input.ClearTask()
    return data[0]
    

def set_voltage(channel, voltage):
    set_waveform(channel, numpy.ones((parse_channel_string(channel)[1], 10))*voltage,1000)
    
def set_waveform(channels,waveform,sample_rate = 100000):
    '''
    Waveform: first dimension channels, second: samples
    '''
    analog_output, wf_duration = set_waveform_start(channels,waveform,sample_rate = sample_rate)
    set_waveform_finish(analog_output, wf_duration)
    
def set_waveform_start(channels,waveform,sample_rate = 100000):
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
    
def set_waveform_finish(analog_output, timeout):
    analog_output.WaitUntilTaskDone(timeout+1.0)
    analog_output.StopTask()                            
    analog_output.ClearTask()
    
def init_daq_queues():
    return {'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
    
class AnalogIoHelpers(object):
    def __init__(self, queues):
        self.n_ai_reads = 0
        if not hasattr(self, 'queues'):
            self.queues = queues

    def start_daq(self, **kwargs):
        self.queues['command'].put(['start', kwargs])
        t0 = time.time()
        timeout = kwargs.get('timeout', 30.0)
        while True:
            if not self.queues['response'].empty():
                return self.queues['response'].get()[0]
            time.sleep(0.1)
            if time.time()-t0>timeout:
                return 'timeout'
            
    def stop_daq(self,timeout = 30.0):
        '''
        Terminates waveform generation and/or data acquisition and returns data if any available
        '''
        self.queues['command'].put(['stop', {}])
        t0 = time.time()
        while True:
            if time.time()-t0>timeout:
                return 'timeout'
            if not self.queues['response'].empty():
                response = self.queues['response'].get(timeout = 5)
                self.printl(response)
                nframes = response[1]
                data = []
                for i in range(nframes - self.n_ai_reads):
                    data.append(self.queues['data'].get(timeout = 5))
                data_array = numpy.array(data)
                if data_array.dtype == numpy.object:#When buffer reads have different lenght
                    data_array = numpy.concatenate(tuple(data))
                return data_array, nframes
            else:
                time.sleep(0.1)
                
    def read_ai(self):
        '''
        Read analog input buffer
        '''
        if not self.queues['data'].empty():
            self.n_ai_reads +=1
            return self.queues['data'].get()
                
    def set_digital_output(self, **kwargs):
        self.queues['command'].put(['_set_digital_output', kwargs])
        
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
    def __init__(self, channels, sample_rate):
        self.commandq=multiprocessing.Queue()
        self.dataq=multiprocessing.Queue()
        self.responseq=multiprocessing.Queue()
        multiprocessing.Process.__init__(self)
        self.channels=channels
        self.sample_rate=int(sample_rate)
        self.timeout=3
        self.buffer_size=int(self.timeout*self.sample_rate*10)
        ai_device_name, self.number_of_ai_channels, ai_channel_indexes = parse_channel_string(self.channels)
        
    def run(self):
        self.analog_input = PyDAQmx.Task()
        self.analog_input.CreateAIVoltageChan(self.channels,
                                                            'ai',
                                                            DAQmxConstants.DAQmx_Val_RSE,
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
                ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
                self.dataq.put(ai_data)
        
#            except PyDAQmx.DAQError:
#                pass
            time.sleep(0.15)
        
        self.analog_input.ClearTask()
        
    def read(self):
        data=numpy.empty([0, self.number_of_ai_channels])
        while not self.dataq.empty():
            r=self.dataq.get()
            data=numpy.concatenate((data, r))
            time.sleep(0.03)
        return data
        
        
class AnalogIOProcess(AnalogIoHelpers, instrument.InstrumentProcess):
    '''
    At waveform generation always continous sampling mode is selected.
    
    Samples from analog inputs are always passed to data queue, such that a user intraface process could display it
    or could continously save it to file. No saving data to file takes place in this process.
    '''
    def __init__(self, instrument_name, queues, logger, ai_channels=None, ao_channels=None, limits = None):
        instrument.InstrumentProcess.__init__(self, instrument_name, queues, logger)
        AnalogIoHelpers.__init__(self,queues)
        self.ai_channels = ai_channels
        self.ao_channels = ao_channels
        if platform.system() != 'Windows':
            self.enable_ai = False
            self.enable_ao = False
        else:
            self.enable_ai = ai_channels is not None
            self.enable_ao = ao_channels is not None
        self.limits = limits
        if self.limits is None:
            self.limits = {}
            self.limits['min_ao_voltage'] = -5.0
            self.limits['max_ao_voltage'] = 5.0
            self.limits['min_ai_voltage'] = -5.0
            self.limits['max_ai_voltage'] = 5.0
            self.limits['timeout'] = 3.0
        self.running = False
        
    def _configure_timing(self, finite_samples = False):
        self.finite_samples = finite_samples
        if finite_samples:
            self.ao_sampling_mode = DAQmxConstants.DAQmx_Val_FiniteSamps
        else:
            self.ao_sampling_mode = DAQmxConstants.DAQmx_Val_ContSamps
        if self.enable_ao:
            self.analog_output.CfgSampClkTiming("OnboardClock",
                                        self.ao_sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        self.ao_sampling_mode,
                                        self.number_of_ao_samples)
                                        
        if self.enable_ai:
            self.analog_input.CfgSampClkTiming("OnboardClock",
                                        self.ai_sample_rate,
                                        DAQmxConstants.DAQmx_Val_Rising,
                                        self.ao_sampling_mode,
                                        self.number_of_ai_samples)
                                            
    def _create_tasks(self):
        if self.enable_ao:
            self.analog_output = PyDAQmx.Task()
            self.analog_output.CreateAOVoltageChan(self.ao_channels,
                                                            'ao',
                                                            self.limits['min_ao_voltage'],
                                                            self.limits['max_ao_voltage'],
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
            ao_device_name, self.number_of_ao_channels, ao_channel_indexes = parse_channel_string(self.ao_channels)
            if self.enable_ai:
                self.analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(ao_device_name), DAQmxConstants.DAQmx_Val_Rising)
            self.printl('Analog output task created')
        if self.enable_ai:
            self.analog_input = PyDAQmx.Task()
            for terminal_config in [DAQmxConstants.DAQmx_Val_PseudoDiff, DAQmxConstants.DAQmx_Val_RSE]:
                try:
                    self.analog_input.CreateAIVoltageChan(self.ai_channels,
                                                            'ai',
                                                            terminal_config,
                                                            self.limits['min_ai_voltage'],
                                                            self.limits['max_ai_voltage'],
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
                except PyDAQmx.DAQError:
                    pass
            self.read = DAQmxTypes.int32()
            ai_device_name, self.number_of_ai_channels, ai_channel_indexes = parse_channel_string(self.ai_channels)
            self.printl('Analog input task created')
            
    def _close_tasks(self):
        if self.enable_ao:
            self.analog_output.ClearTask()
            self.printl('Analog output task finished')
        if self.enable_ai:
            self.analog_input.ClearTask()
            time.sleep(0.01)#Ensures that next log is saved correctly
            self.printl('Analog input task finished')
            
    def _write_waveform(self):
        self.analog_output.WriteAnalogF64(self.number_of_ao_samples,
                                False,
                                self.limits['timeout'],
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                self.ao_waveform,
                                None,
                                None)
            
    def _start(self, **kwargs):
        '''
        Start daq activity
        
        Expected parameters:
        ao: waveform, infinite, ao_sample_rate
        ai: nsamples, ai_sample_rate
        
        '''
        if self.running:
            self.queues['response'].put(['Already running', ])
        #Checks for and sets expected arguments
        expected_kwargs = {}
        expected_kwargs['ai'] = ['ai_sample_rate']
        expected_kwargs['ao'] = ['ao_sample_rate', 'ao_waveform']
        for k in expected_kwargs.keys():
            if getattr(self, 'enable_' + k):
                for argname in expected_kwargs[k]:
                    if kwargs.has_key(argname):
                        setattr(self, argname, kwargs[argname])
                    else:
                        raise DaqInstrumentError('{0} argument is expected but not provided'.format(argname))
        if not self.enable_ao and self.enable_ai:
            if kwargs.has_key('ai_record_time'):
                self.ai_record_time = kwargs['ai_record_time']
            else:
                 raise DaqInstrumentError('ai_record_time argument is expected but not provided')
        #Calculate number of samples
        if self.enable_ao:
            self.number_of_ao_samples = self.ao_waveform.shape[1]
            if self.enable_ai:
                waveform_duration = float(self.number_of_ao_samples)/self.ao_sample_rate
                if waveform_duration < WAVEFORM_MIN_DURATION:
                    self.printl('Waveform duration ({0} s) is less than {1} s, analog samples might be lost'.format(waveform_duration, WAVEFORM_MIN_DURATION), loglevel = 'warning')
                self.number_of_ai_samples = int(self.number_of_ao_samples * float(self.ai_sample_rate) / float(self.ao_sample_rate))
        else:
            self.number_of_ai_samples = int(self.ai_record_time * self.ai_sample_rate)
        self.finite_samples = kwargs.get('finite_samples', False)
        self.printl('Daq started with parameters: {0}'.format(kwargs))
        self._configure_timing(self.finite_samples) #this cannot be done during init because the lenght of the signal is not known before waveform is set
        if self.enable_ao:
            self._write_waveform()
            self.analog_output.StartTask()
        if self.enable_ai:
            self.analog_input.StartTask()
        self.running = True
        self.ai_frames = 0
        self.printl('Daq started with parameters: {0}'.format(kwargs))
        self.queues['response'].put(['started'])

    def _stop(self, **kwargs):
        '''
        Stop daq activity
        '''
        if not self.running:
            self.queues['response'].put(['Not running, cannot be stopped', ])
        aborted = kwargs.has_key('aborted') and kwargs['aborted']
        if self.enable_ao and not aborted and self.finite_samples:
            #Timeout is daq timeout + duration of waveform    
            self.analog_output.WaitUntilTaskDone(self.limits['timeout'] + float(self.ao_waveform.shape[1])/self.ao_sample_rate)
            self.ai_data = self._read_ai()
        if self.enable_ao:
            self.analog_output.StopTask()
        if self.enable_ai:
            self.analog_input.StopTask()
        self.running = False
        self.printl('Daq stopped, ai frames: {0}'.format(self.ai_frames))
        self.queues['response'].put(['stop', self.ai_frames])
        return self.ai_data
        
    def _set_digital_output(self, **kwargs):
        set_digital_line(kwargs['channel'], kwargs['value'])
        
    def _read_ai(self):
        samples_to_read = self.number_of_ai_samples * self.number_of_ai_channels
        self.ai_data = numpy.zeros(self.number_of_ai_samples*self.number_of_ai_channels, dtype=numpy.float64)
        self.printl(self.ai_data.shape)
        try:
            self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                        self.limits['timeout'],
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        samples_to_read,
                                        DAQmxTypes.byref(self.read),
                                        None)
        except PyDAQmx.DAQError:
            if self.finite_samples:
                import traceback
                self.printl(traceback.format_exc())
        ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
        self.printl(self.ai_data.shape)
        ##self.ai_raw_data = self.ai_data
        ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
        self.queues['data'].put(ai_data)
        self.ai_frames += 1
        return ai_data

    def run(self):
        self.printl('aio process started')
        if platform.system() != 'Windows':
            self.printl('{0} platform not supported'.format(platform.system()))
            return
        try:
            self._create_tasks()
            while True:
                time.sleep(10e-3)
                if not self.queues['command'].empty():
                    command = self.queues['command'].get()
                    if command == 'terminate':
                        break
                    elif isinstance(command, list) and len(command) == 2:
                        parameters = command[1]
                        command = command[0]
                        if hasattr(self, '_' + command):
                            getattr(self, '_' + command)(**parameters)
                        else:
                            self.printl('Command not supported: {0}' .format(command), 'error')
                if self.running and self.enable_ai:
                    self._read_ai()
            self._close_tasks()
        except:
            import traceback
            self.printl(traceback.format_exc(), 'error')
        self.printl('aio process ended')
        
class DigitalIO(instrument.Instrument):
    def init_instrument(self):
        if hasattr(self.config,  'DAQ_CONFIG'):
            try:
                self.daq_config = self.config.DAQ_CONFIG[self.id]
            except IndexError:
                daq_config = {'ENABLE': False}
                self.daq_config = daq_config
        else:
            #Ensure that experiments referencing AnalogIO class will run without errors on machines where DAQ_CONFIG is not defined or daqmx driver is not available
            daq_config = {'ENABLE': False}
            self.daq_config = daq_config
        if os.name == 'nt' and self.daq_config['ENABLE']: 
            self.digital_output = PyDAQmx.Task()
            self.digital_output.CreateDOChan(self.daq_config['DO_CHANNEL'],
                                                            'do',
                                                            DAQmxConstants.DAQmx_Val_ChanPerLine)
                                                            
    def _set_line_value(self, state):
        digital_values = numpy.array([int(state)], dtype=numpy.uint8)
        self.digital_output.WriteDigitalLines(1,
                                    True,
                                    self.daq_config['DAQ_TIMEOUT'],
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    digital_values,
                                    None,
                                    None)
                                    
    def set(self):
        self._set_line_value(True)
        
    def clear(self):
        self._set_line_value(False)
                                    
    def close_instrument(self):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            self.digital_output.ClearTask()

class AnalogIO(instrument.Instrument):
    '''
    AnalogIO generates analog signals and reads the analog inputs of a daqmx device in a synchronized way
    
    Parameters:
    - ENABLE_AI
    - ENABLE_AO
    - SAMPLE_RATE - if defined for both ai and ao operations this frequency will be used
    - AI_SAMPLE_RATE
    - AO_SAMPLE_RATE
    - MAX_VOLTAGE, MIN_VOLTAGE 
    
    Run modes:
    - single run    
    - ai only
    - ao only   
    - continous acquisition - not implemented yet 
    '''
    
    def init_instrument(self):
        if hasattr(self.config,  'DAQ_CONFIG'):
            try:
                self.daq_config = self.config.DAQ_CONFIG[self.id]
            except IndexError:
                daq_config = {'ENABLE': False}
                self.daq_config = daq_config
        else:
            #Ensure that experiments referencing AnalogIO class will run without errors on machines where DAQ_CONFIG is not defined or daqmx driver is not available
            daq_config = {'ENABLE': False}
            self.daq_config = daq_config
        if os.name == 'nt' and self.daq_config['ENABLE']:            
            if not self.daq_config.has_key('SAMPLE_RATE') and (\
                (not self.daq_config.has_key('AO_SAMPLE_RATE') and not self.daq_config.has_key('AI_SAMPLE_RATE'))\
                or\
                (not self.daq_config.has_key('AI_SAMPLE_RATE') and (self.daq_config['ANALOG_CONFIG'] != 'ao'))\
                or\
                (not self.daq_config.has_key('AO_SAMPLE_RATE') and (self.daq_config['ANALOG_CONFIG'] != 'ai'))\
                ):
                #Exception shall be raised when none of these conditions are true:
                #- SAMPLE_RATE defined 
                #- both AI_SAMPLE_RATE and AO_SAMPLE_RATE defined but SAMPLE_RATE not
                #- AI_SAMPLE_RATE only and ANALOG_CONFIG = ai
                #- AO_SAMPLE_RATE only and ANALOG_CONFIG = ao
                raise RuntimeError('SAMPLE_RATE parameter or AO_SAMPLE_RATE, AI_SAMPLE_RATE parameters needs to be defined.')                
            elif self.daq_config.has_key('SAMPLE_RATE'):            
                self.ai_sample_rate = self.daq_config['SAMPLE_RATE']
                self.ao_sample_rate = self.daq_config['SAMPLE_RATE']
            else:
                if self.daq_config['ANALOG_CONFIG'] != 'ao':
                    self.ai_sample_rate = self.daq_config['AI_SAMPLE_RATE']
                if self.daq_config['ANALOG_CONFIG'] != 'ai':
                    self.ao_sample_rate = self.daq_config['AO_SAMPLE_RATE']
            if self.daq_config['ANALOG_CONFIG'] == 'aio':
                self.enable_ai = True
                self.enable_ao = True
            elif self.daq_config['ANALOG_CONFIG'] == 'ai':
                self.enable_ai = True
                self.enable_ao = False
            elif self.daq_config['ANALOG_CONFIG']== 'ao':
                self.enable_ai = False
                self.enable_ao = True
            else:
                raise RuntimeError('Invalid analog config')
            
            if self.enable_ao:
                self.analog_output = PyDAQmx.Task()
                self.analog_output.CreateAOVoltageChan(self.daq_config['AO_CHANNEL'],
                                                            'ao',
                                                            self.daq_config['MIN_VOLTAGE'], 
                                                            self.daq_config['MAX_VOLTAGE'], 
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
                channel_indexes = self.daq_config['AO_CHANNEL'].split('/')[-1].replace('ao','').split(':')
                self.number_of_ao_channels = abs(int(channel_indexes[-1]) - int(channel_indexes[0])) + 1
                #analog input task will trigger the start of the analog output task
                if self.enable_ai:
                    self.analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(self.daq_config['AI_CHANNEL'].split('/')[0]), DAQmxConstants.DAQmx_Val_Rising)
                
            if self.enable_ai:
                self.analog_input = PyDAQmx.Task()
                if self.daq_config.has_key('AI_TERMINAL'):
                    terminal_config = self.daq_config['AI_TERMINAL']
                else:
                    terminal_config = DAQmxConstants.DAQmx_Val_RSE #If PCI-6110 device is used: DAQmx_Val_PseudoDiff
                self.analog_input.CreateAIVoltageChan(self.daq_config['AI_CHANNEL'],
                                                            'ai',
                                                            terminal_config,
                                                            self.daq_config['MIN_VOLTAGE'], 
                                                            self.daq_config['MAX_VOLTAGE'], 
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
                self.read = DAQmxTypes.int32()
                channel_indexes = self.daq_config['AI_CHANNEL'].split('/')[-1].replace('ai','').split(':')
                self.number_of_ai_channels = abs(int(channel_indexes[-1]) - int(channel_indexes[0])) + 1

    def _configure_timing(self):    
        if os.name == 'nt' and self.daq_config['ENABLE']:    
            if self.enable_ao:
                if self.daq_config.has_key('AO_SAMPLING_MODE') and self.daq_config['AO_SAMPLING_MODE'] != 'finite':
                    self.ao_sampling_mode = DAQmxConstants.DAQmx_Val_ContSamps
                else:
                    self.ao_sampling_mode = DAQmxConstants.DAQmx_Val_FiniteSamps
                self.analog_output.CfgSampClkTiming("OnboardClock",
                                            self.ao_sample_rate,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            self.ao_sampling_mode,
                                            self.number_of_ao_samples)
            if self.enable_ai:
                sampling_mode = DAQmxConstants.DAQmx_Val_ContSamps #DAQmx_Val_ContSamps #DAQmxConstants.DAQmx_Val_FiniteSamps
                self.analog_input.CfgSampClkTiming("OnboardClock",
                                            self.ai_sample_rate,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            sampling_mode,
                                            self.number_of_ai_samples)
        
    def _write_waveform(self):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            if self.enable_ao:
#                print self.waveform.min(), self.waveform.max()
#                print self.waveform.shape
                self.analog_output.WriteAnalogF64(self.number_of_ao_samples,
                                    False,
                                    self.daq_config['DAQ_TIMEOUT'],
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    self.waveform,
                                    None,
                                    None)
                               
    def start_daq_activity(self):
        '''
        This function can be called directly to ensure the daq activity does not block the execution of the experiment
        '''
        if os.name == 'nt' and self.daq_config['ENABLE']:
            if not hasattr(self, 'waveform') and self.enable_ao:
                raise RuntimeError('No waveform provided')
            if self.enable_ao:
                self.number_of_ao_samples = self.waveform.shape[0]
                self.waveform_duration = float(self.number_of_ao_samples) / float(self.ao_sample_rate)
                if self.enable_ai:
                    self.number_of_ai_samples = int(self.number_of_ao_samples * self.ai_sample_rate / self.ao_sample_rate)
                self.analog_activity_time = self.waveform_duration
            else:
                self.number_of_ai_samples = int(self.daq_config['DURATION_OF_AI_READ'] * self.ai_sample_rate)
                self.analog_activity_time = self.daq_config['DURATION_OF_AI_READ']
                
            if self.enable_ai:
                #clear ai buffer
                self.ai_data = numpy.zeros(self.number_of_ai_samples*self.number_of_ai_channels, dtype=numpy.float64)
            self._configure_timing() #this cannot be done during init because the lenght of the signal is not known before waveform is set
            self._write_waveform()
            if self.enable_ao:
                self.analog_output.StartTask()
            if self.enable_ai:
                self.analog_input.StartTask()
            return True
        else:
            return False
            
    def read_analog(self):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            if self.enable_ai:
                samples_to_read = self.number_of_ai_samples * self.number_of_ai_channels
                try:
                    self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                                self.daq_config['DAQ_TIMEOUT'],
                                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                                self.ai_data,
                                                samples_to_read,
                                                DAQmxTypes.byref(self.read),
                                                None)
                except PyDAQmx.DAQError:
                    pass
                self.ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
                self.ai_raw_data = self.ai_data
                self.ai_data = self.ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose()
                return copy.deepcopy(self.ai_data)

    def finish_daq_activity(self, abort = False):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            if self.enable_ai:
                if abort:
                    samples_to_read = 10 * self.number_of_ai_channels
                else:
                    samples_to_read = self.number_of_ai_samples * self.number_of_ai_channels
                try:
                    self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                                self.daq_config['DAQ_TIMEOUT'],
                                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                                self.ai_data,
                                                samples_to_read,
                                                DAQmxTypes.byref(self.read),
                                                None)
                except PyDAQmx.DAQError:
                    pass
                #Make sure that all the acquisitions are completed                
#                 self.analog_input.WaitUntilTaskDone(self.daq_config['DAQ_TIMEOUT'])
            if self.enable_ao and not abort and self.ao_sampling_mode == DAQmxConstants.DAQmx_Val_FiniteSamps:
                self.analog_output.WaitUntilTaskDone(self.daq_config['DAQ_TIMEOUT'])
            if self.enable_ao:
                self.analog_output.StopTask()
            if self.enable_ai:
                self.analog_input.StopTask()
                if not hasattr(self, 'ao_sampling_mode') or self.ao_sampling_mode == DAQmxConstants.DAQmx_Val_FiniteSamps:
                    self.ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
                    self.ai_raw_data = self.ai_data
                    self.ai_data = self.ai_data.reshape((self.number_of_ai_channels, self.read.value)).transpose()
            return True
        else:
            return False
    

    def start_instrument(self):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            self.start_daq_activity()        
            time.sleep(self.analog_activity_time)
            self.finish_daq_activity()

    def close_instrument(self):
        if os.name == 'nt' and self.daq_config['ENABLE']:
            if self.enable_ao:
                self.analog_output.ClearTask()
            if self.enable_ai:
                self.analog_input.ClearTask()
        
class AnalogPulse(AnalogIO):
    '''
    1. User interface:
    
    set() - set the parameters of the pulses to be generated
    start() - (re)start generating pulse train
    stop() - stop generating pulse train
    release_instrument()    
    
    2. Usage:
    set(....)
    ...
    start() #non-blocking
    ...
    start()
    if ... :
        stop()
    start()
    ...
    ...
    release_instrument()
    
    3. State machine
                            init
                              |
                              | __init__()
                             \|/
                            ready
                              |
                              | set()
                             \|/
                             set ====| set()
                         /|\   |
          time elapsed    |    | start()
           stop           |   \|/
                           running

                            
    

    '''
    def set(self, pulse_config, duration):
        '''
        pulse_config : [channel0, channel1, ....]
        channels: [offset [s], width [s], amplitude], [offset [s], width [s], amplitude], ....
        duration is in seconds        
        '''
        parameters = [pulse_config, duration]
        self.state_machine('set', parameters)        
        self.log_during_experiment('Pulse train configuration: {0}' .format(str(parameters)))
        
    def start(self):
        self.log_during_experiment('Start pulse train')
        self.state_machine('start')
        
    def stop(self):
        self.log_during_experiment('Stop pulse train')
        self.state_machine('stop')
        
    def release_instrument(self):
        self.log_during_experiment('Daq instrument released')
        self.state_machine('release_instrument')        
            
    def state_machine(self, command, parameters = None):
        if self.daq_config['ENABLE'] and os.name == 'nt':
#         print '\nin:  {0}, {1}, {2}' .format(round(time.time() - 1319024000,3), self.state, command)
            if self.state == 'running':   
    #             print self.end_time   - 1319024000     
                while time.time() < self.end_time:
                    pass            
                self.finish_daq_activity()
                self.state = 'set'
        
            if command == 'set':
                if self.state == 'ready' or self.state == 'set':
                    if isinstance(parameters[0],list):
                        pulse_configs = numpy.array(parameters[0])
                        duration = parameters[1]
                        waveform = []                    
                        if pulse_configs.shape[0] != self.number_of_ao_channels:
                            raise RuntimeError('Analog output channel number mismatch.')
                        for pulse_config in pulse_configs:
                            channel_waveform = utils.generate_pulse_train(pulse_config[0], pulse_config[1], pulse_config[2], duration, sample_rate = self.ao_sample_rate)
                            channel_waveform[-1] = 0.0
                            waveform.append(channel_waveform)
                        waveform = numpy.array(waveform).transpose()
                    elif hasattr(parameters[0],'dtype'):#Workaround for loading a waveform instead of a series of pulses
                        waveform = numpy.cast['float64'](numpy.reshape(parameters[0],(1,parameters[0].shape[0])))
                    self.waveform = waveform.transpose()
                    self.state = 'set'
            elif command == 'start':
                if self.state == 'set':
                    self.start_daq_activity()
                    self.start_time = time.time()
                    self.end_time = self.start_time + self.analog_activity_time
                    self.state = 'running'
            elif command == 'stop':
                if self.state == 'running':
                    self.finish_daq_activity()
            elif command == 'release_instrument':
                if self.state == 'set' or self.state == 'running':
                    self.finish_daq_activity()
                AnalogIO.release_instrument(self)
#         print '\nout: {0}, {1}, {2}' .format(round(time.time() - 1319024000,3), self.state, command)
        

#=== TESTS ===
class InvalidTestConfig(configuration.Config):
    def _create_application_parameters(self):
        TEST_DATA_PATH = unittest_aggregator.TEST_working_folder        
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'aio',
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 100,
                    'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',
                    'AI_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ai5:0',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : True
                    }
                    ]
        
        self._create_parameters_from_locals(locals())

class InvalidTestConfig1(configuration.Config):
    def _create_application_parameters(self):
        TEST_DATA_PATH = unittest_aggregator.TEST_working_folder
        DAQ_CONFIG = [
                    {                    
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',
                    'AI_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ai5:0',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : True
                    }
                    ]
        
        self._create_parameters_from_locals(locals())

                
class testDaqConfig(configuration.Config):
    def _create_application_parameters(self):
        TEST_DATA_PATH = unittest_aggregator.TEST_working_folder
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'aio', #'ai', 'ao', 'aio', 'undefined'
        'DAQ_TIMEOUT' : 1.0, 
        'AO_SAMPLE_RATE' : 100,
        'AI_SAMPLE_RATE' : 1000,
        'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ai9:0',
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : 0.0,
        'DURATION_OF_AI_READ' : 1.0,
        'ENABLE' : True
        },
        {
        'ANALOG_CONFIG' : 'undefined',
        'DAQ_TIMEOUT' : 0.0, 
        'AO_SAMPLE_RATE' : 100,
        'AI_SAMPLE_RATE' : 1000,
        'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ai9:0',
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : 0.0,
        'DURATION_OF_AI_READ' : 1.0,
        'ENABLE' : True
        }, 
        {
        'DAQ_TIMEOUT' : 1.0, 
        'DO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/port0/line0',
        'ENABLE' : True
        }
        ]
        
        self._create_parameters_from_locals(locals())
        
class testAnalogPulseConfig(configuration.Config):
    def _create_application_parameters(self):
        TEST_DATA_PATH = unittest_aggregator.TEST_working_folder
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 1.0, 
        'SAMPLE_RATE' : 10000,        
        'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',        
        'MAX_VOLTAGE' : 10.0,
        'MIN_VOLTAGE' : 0.0,
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())

if test_mode:
    class TestDaqInstruments(unittest.TestCase):
        '''
        Test conenctions on USB-6212
         * AO GND - AI GND
         * AO0 - AI0, AI2
         * AO1 - AI1, AI3
         * AO0 GND - AI4
        
        '''
        def setUp(self):
            self.config = testDaqConfig()
            try:
                self.experiment_control = instrument.testLogClass(self.config)
            except:
                pass
            self.state = 'experiment running'
    
        def tearDown(self):
            pass
    
        #== AnalogIO test cases ==
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_01_test_sample_rate_parameters(self):
            self.config = InvalidTestConfig()
            self.assertRaises(RuntimeError,  AnalogIO, self.config, self)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_02_test_sample_rate_parameters(self):
            self.config = InvalidTestConfig()
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 10
            aio = AnalogIO(self.config, self)
            self.assertEqual((aio.ai_sample_rate, aio.ao_sample_rate), (10, 100))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_03_test_sample_rate_parameters(self):
            self.config = InvalidTestConfig()
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 90
            aio = AnalogIO(self.config, self)
            self.assertEqual((aio.ai_sample_rate, aio.ao_sample_rate), (90, 90))
            aio.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_04_sample_rate_and_analog_config(self):
            self.config = InvalidTestConfig1()
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 100
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'
            aio = AnalogIO(self.config, self)
            self.assertEqual((aio.ai_sample_rate), (100))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_05_sample_rate_and_analog_config(self):
            self.config = InvalidTestConfig1()
            self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 100
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ao'
            aio = AnalogIO(self.config, self)
            self.assertEqual((aio.ao_sample_rate), (100))
        
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_06_invalid_analog_config(self):
            self.config = InvalidTestConfig()
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = ''
            self.assertRaises(RuntimeError, AnalogIO, self.config, self)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_07_no_waveform_provided(self):
            aio = AnalogIO(self.config, self)        
            self.assertRaises(RuntimeError,  aio.run)
            aio.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_08_analog_input_and_output_are_synchronized(self):
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            aio = AnalogIO(self.config, self)       
            waveform = self.generate_waveform1(0.02)
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()       
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform, aio.ai_data)
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_09_analog_input_and_output_are_synchronized_with_ramp_waveform(self):
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            aio = AnalogIO(self.config, self)       
            waveform = self.generate_waveform2(0.2)
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()       
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform, aio.ai_data)        
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_10_out_of_range_waveform(self):
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            aio = AnalogIO(self.config, self)       
            waveform = self.generate_waveform2(0.2) + 5.0
            aio.waveform = waveform
            self.assertRaises(PyDAQmx.DAQError, aio.run)        
            aio.release_instrument()
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_11_restart_playing_waveform(self):
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            aio = AnalogIO(self.config, self)       
            waveform = self.generate_waveform1(0.02)
            aio.waveform = waveform
            aio.run()
            ai_data_first_run = aio.ai_data
            waveform_1 = 2*self.generate_waveform1(0.02)
            aio.waveform = waveform_1
            aio.run()
            aio.release_instrument()       
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform_1, aio.ai_data)
            ao0_1, ao1_1, ai0_1, ai1_1, ai2_1, ai3_1, ai4_1 = self.to_analog_channels(waveform, ai_data_first_run)
            self.assertEqual((abs(ai0-ao0).sum(), 
                                abs(ai1-ao1).sum(), 
                                abs(ai2-ao0).sum(), 
                                abs(ai3-ao1).sum(), 
                                ai4.sum()),
                               (abs(ai0_1-ao0_1).sum(), 
                                abs(ai1_1-ao1_1).sum(), 
                                abs(ai2_1-ao0_1).sum(), 
                                abs(ai3_1-ao1_1).sum(), 
                                ai4_1.sum()),
                                (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_12_reuse_analogio_class(self):
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            aio = AnalogIO(self.config, self)       
            waveform_1 = self.generate_waveform1(0.02)
            aio.waveform = waveform_1
            aio.run()
            ai_data_1 = aio.ai_data        
            aio.release_instrument()
            #second run
            aio = AnalogIO(self.config, self)
            waveform_2 = 1.5*self.generate_waveform1(0.02)
            aio.waveform = waveform_2
            aio.run()
            ai_data_2 = aio.ai_data
            aio.release_instrument()
            ao0_2, ao1_2, ai0_2, ai1_2, ai2_2, ai3_2, ai4_2 = self.to_analog_channels(waveform_2, ai_data_2)
            ao0_1, ao1_1, ai0_1, ai1_1, ai2_1, ai3_1, ai4_1 = self.to_analog_channels(waveform_1, ai_data_1)
            self.assertEqual((abs(ai0_2-ao0_2).sum(), 
                                abs(ai1_2-ao1_2).sum(), 
                                abs(ai2_2-ao0_2).sum(), 
                                abs(ai3_2-ao1_2).sum(), 
                                ai4_2.sum()),
                               (abs(ai0_1-ao0_1).sum(), 
                                abs(ai1_1-ao1_1).sum(), 
                                abs(ai2_1-ao0_1).sum(), 
                                abs(ai3_1-ao1_1).sum(), 
                                ai4_1.sum()),
                                (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_13_analog_input_and_output_have_different_sampling_rates(self):
            self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 50
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 20000
            aio = AnalogIO(self.config, self)
            waveform = self.generate_waveform1(0.2)
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()        
            ai_ao_sample_rate_ratio = int(self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] / self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])        
            waveform_interpolated = utils.interpolate_waveform(waveform, ai_ao_sample_rate_ratio)
            
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform_interpolated, aio.ai_data)
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_14_analog_input_and_output_have_different_sampling_rates(self):
            self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 200000
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 100
            aio = AnalogIO(self.config, self)
            waveform = self.generate_waveform2(0.2)
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()        
    
            ao_ai_sample_rate_ratio = int(self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] / self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'])
            waveform_sampled = utils.resample_waveform(waveform, ao_ai_sample_rate_ratio)
            
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform_sampled, aio.ai_data)
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_15_ai_ao_different_sample_rate(self):
            self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 1000
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 40000
            aio = AnalogIO(self.config, self)
            waveform = self.generate_waveform1(0.02)
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()
    
            sample_rate_ratio = float(self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']) / self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE']
            if sample_rate_ratio > 1.0:
                waveform_resampled = utils.resample_waveform(waveform, int(sample_rate_ratio))
            else:
                waveform_resampled = utils.interpolate_waveform(waveform, int(1.0/sample_rate_ratio))
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform_resampled, aio.ai_data)
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
        
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_16_single_channel_ai_ao(self):
            
            self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 80000
            self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 80000
            self.config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0'
            self.config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai0'
            
            aio = AnalogIO(self.config, self)
            waveform = self.generate_waveform1(0.1)[:,0]
            
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()
    
            sample_rate_ratio = float(self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']) / self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE']
            if sample_rate_ratio > 1.0:
                waveform_resampled = utils.resample_waveform(waveform, int(sample_rate_ratio))
            else:
                waveform_resampled = utils.interpolate_waveform(waveform, int(1.0/sample_rate_ratio))
            #This is necessary because there is a one sample shift on the first sampled channel            
            waveform_resampled = numpy.roll(waveform_resampled, 1)        
            
            self.assertEqual((abs(numpy.round(aio.ai_data, 2).transpose() - waveform_resampled).sum()
                             ),
                             (0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_17_enable_ai_ao_separately(self):
            voltage_level = 2.0
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ao'
            aio1 = AnalogIO(self.config, self)
            waveform = voltage_level * numpy.ones((100,2))
            aio1.waveform = waveform
            aio1.run()
            aio1.release_instrument()       
            
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 100
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'
            self.config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.05
            aio2 = AnalogIO(self.config, self)        
            aio2.run()
            aio2.release_instrument()
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(voltage_level * numpy.ones_like(aio2.ai_data), aio2.ai_data)
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
            
            #Set analog outputs to 0V
            waveform = numpy.zeros((100,2))
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ao'
            aio3 = AnalogIO(self.config, self)
            aio3.waveform = waveform
            aio3.run()
            aio3.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_18_non_blocking_daq_activity_1(self):
            waveform = self.generate_waveform2(0.1)
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
            self.non_blocking_daq(1.0, waveform)
        
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_19_non_blocking_daq_activity_2(self):
            waveform = self.generate_waveform2(0.1)
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
            self.non_blocking_daq(0.0, waveform)
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_20_non_blocking_daq_activity_3(self):
            waveform = self.generate_waveform2(0.1)
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
            self.non_blocking_daq(0.1, waveform)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_21_disabled_daq(self):
            waveform = self.generate_waveform2(0.1)
            self.config.DAQ_CONFIG[0]['ENABLE'] = False
            aio = AnalogIO(self.config, self)
            waveform = self.generate_waveform1(0.1)        
            aio.waveform = waveform
            aio.run()
            aio.release_instrument()
            self.assertEqual((hasattr(aio, 'ai_data'), hasattr(self, 'daq_config')), (False, False))
            
        #== Analog pulse test cases
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_22_analog_pulse(self):
            self.config = testAnalogPulseConfig()
            offsets = [0, 0.005, 0.007]
            pulse_widths = 0.001
            amplitudes = 0.01
            duration = 0.1
            ap = AnalogPulse(self.config, self)
            self.assertRaises(RuntimeError, ap.set, [[offsets, pulse_widths, amplitudes]], duration)        
            ap.start()
            ap.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_23_analog_pulse_one_channel(self):
            self.config = testAnalogPulseConfig()
            self.config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0:0'
            
            #Config for analog acquisition
            ai_config = testAnalogPulseConfig()        
            ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
            ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai9:0'        
            ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1
            
            ai = AnalogIO(ai_config, self)
            ai.start_daq_activity()
    
            offsets = [1e-4, 3e-4]
            pulse_widths = 1e-4
            amplitudes = 2.0
            duration = 5e-4
            ap = AnalogPulse(self.config, self)
            ap.set([[offsets, pulse_widths, amplitudes]], duration)
            ap.start()
            ap.release_instrument()
            ai.finish_daq_activity()
            ai.release_instrument()
            
            ai_data = numpy.round(ai.ai_data, 1)        
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]        
            self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets) * pulse_widths * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']) * amplitudes, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_24_analog_pulse_two_channels(self):
            self.config = testAnalogPulseConfig()
            #Config for analog acquisition
            ai_config = testAnalogPulseConfig()        
            ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
            ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai9:0'        
            ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1
            
            ai = AnalogIO(ai_config, self)
            ai.start_daq_activity()               
    
            #Channel0
            offsets0 = [0, 1e-3, 2e-3]
            pulse_widths0 = 5e-4
            amplitudes0 = 2.0
            #Channel1
            offsets1 = [0, 1e-3, 2e-3]
            pulse_widths1 = 2e-4
            amplitudes1 = 2.5
            
            duration = 5e-3
            ap = AnalogPulse(self.config, self)
            ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
            ap.start()
            ap.release_instrument()
            ai.finish_daq_activity()
            ai.release_instrument()
            
            ai_data = numpy.round(ai.ai_data, 1)        
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]        
            self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets0) * pulse_widths0 * amplitudes0 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']), 
                                                        len(offsets1) * pulse_widths1 * amplitudes1 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE'])))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_25_analog_pulse_two_channels(self):
            self.config = testAnalogPulseConfig()
            #Config for analog acquisition
            ai_config = testAnalogPulseConfig()        
            ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
            ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai9:0'        
            ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1
            
            ai = AnalogIO(ai_config, self)
            ai.start_daq_activity()               
    
            #Channel0
            offsets0 = [0, 1e-3, 2e-3]
            pulse_widths0 = 5e-4
            amplitudes0 = 2.0
            #Channel1
            offsets1 = [0, 1e-3, 2e-3]
            pulse_widths1 = 8e-4
            amplitudes1 = [4.0, 1.0, 3.0]
            
            duration = 5e-3
            ap = AnalogPulse(self.config, self)
            ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
            ap.start()
            ap.release_instrument()
            ai.finish_daq_activity()
            ai.release_instrument()
            
            ai_data = numpy.round(ai.ai_data, 1)        
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]        
            self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets0) * pulse_widths0 * amplitudes0 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']), 
                                                        pulse_widths1 * numpy.array(amplitudes1).sum() * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE'])))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_26_restart_pulses(self):
            self.config = testAnalogPulseConfig()
            #Config for analog acquisition
            ai_config = testAnalogPulseConfig()        
            ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
            ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai9:0'        
            ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 1.0
            
            ai = AnalogIO(ai_config, self)
            ai.start_daq_activity()               
    
            #Channel0
            offsets0 = [0, 1e-3, 20e-3, 28e-3]
            pulse_widths0 = 5e-4
            amplitudes0 = 2.0
            #Channel1
            offsets1 = [0, 1e-3, 18e-3]
            pulse_widths1 = 2e-4
            amplitudes1 = 2.5
            
            duration = 30e-3
            ap = AnalogPulse(self.config, self)
            ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
            ap.start()
            ap.start()
            ap.release_instrument()
            ai.finish_daq_activity()
            ai.release_instrument()
            
            ai_data = numpy.round(ai.ai_data, 1)        
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]        
            self.assertEqual((ai0.sum(), ai1.sum()), (2*len(offsets0) * pulse_widths0 * amplitudes0 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']),
                                                     2*len(offsets1) * pulse_widths1 * amplitudes1 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE'])))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_27_restart_pulses_long_duration(self):
            self.config = testAnalogPulseConfig()        
            #Config for analog acquisition
            ai_config = testAnalogPulseConfig()
            ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'
            ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai9:0'
            ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 10.0
            ai_config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
            
            ai = AnalogIO(ai_config, self)
            ai.start_daq_activity()
            duration = 4.0
            #Channel0
            import random
            number_of_pulses = 100
            offsets0 = []        
            offsets0=numpy.linspace(0,0.8*duration,number_of_pulses)        
            pulse_widths0 = 0.02
            amplitudes0 = 2.0
            #Channel1
            offsets1 = [0.1*duration, 0.2*duration, 0.3*duration]
            pulse_widths1 = 0.02 * duration
            amplitudes1 = 3.0
            
            ap = AnalogPulse(self.config, self)
            ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
            ap.start()
            time.sleep(0.9 * duration)
            ap.start()        
            ap.release_instrument()        
            ai.finish_daq_activity()
            ai.release_instrument()
            
            ai_data = numpy.round(ai.ai_data, 1)
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]
            ai0_sum = numpy.round(ai0.sum(),1)
            ai1_sum = numpy.round(ai1.sum(),1)
            
            ai0_sum_ref = numpy.round(2 * len(offsets0) * pulse_widths0 * amplitudes0 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']),1)
            ai1_sum_ref = numpy.round(2 * len(offsets1) * pulse_widths1 * amplitudes1 * float(self.config.DAQ_CONFIG[0]['SAMPLE_RATE']),1)        
            
    #         numpy.savetxt('c:\\_del\\txt\\ai0.csv', ai0, delimiter='\t')
    #         numpy.savetxt('c:\\_del\\txt\\wave.csv', ap.waveform, delimiter='\t')
    
            
            self.assertEqual((ai0_sum, ai1_sum), (ai0_sum_ref, ai1_sum_ref))
        
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_28_stop_ai_before_ai_duration(self):
            ai_read_time = 1.2
            
            #Generate signals on AO's
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ao'
            
            waveform = numpy.ones(3 * ai_read_time * self.config.DAQ_CONFIG[0]['SAMPLE_RATE'])
            waveform[-1] = 0
            voltage_levels = [1.0, 2.0]
            waveform = numpy.array([waveform * voltage_levels[0], waveform * voltage_levels[1]]).transpose()
            
            ao1 = AnalogIO(self.config, self)
            ao1.waveform = waveform
            ao1.start_daq_activity()
        
            #Start the ai
            self.config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 10.0
            self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 10000
            self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'
            
            aio = AnalogIO(self.config, self)
            aio.start_daq_activity()
            time.sleep(ai_read_time)
            aio.finish_daq_activity()
            aio.release_instrument()
            
            #Finish AO
            time.sleep(2*ai_read_time)
            ao1.finish_daq_activity()
            ao1.release_instrument()
    
            ai_data = numpy.round(aio.ai_data,2)
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]
            ai2 = ai_data[:,-3]
            ai3 = ai_data[:,-4]
            ai4 = ai_data[:,-5]
            ao0 = numpy.ones_like(ai0) * voltage_levels[0]
            ao1 = numpy.ones_like(ai0) * voltage_levels[1]
            
            self.assertEqual((abs(ai0 - ao0).sum(),
                                abs(ai1 - ao1).sum(),
                                abs(ai2 - ao0).sum(),
                                abs(ai3 - ao1).sum(),
                                ai4.sum()),
                                (0.0, 0.0, 0.0, 0.0, 0.0))
                                
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_29_test_digital_output(self):
            do = DigitalIO(self.config, self, id=2)
            for i in range(100):
                do.set()
                time.sleep(0.0)
                do.clear()
                time.sleep(0.0)
            do.release_instrument()
        
        #== Test utilities ==
        def zero_non_zero_ratio(self, data):
            return float(numpy.nonzero(data)[0].shape[0]) / float(data.shape[0])
    
        def non_blocking_daq(self, activity_time, waveform):        
            aio = AnalogIO(self.config, self)        
            aio.waveform = waveform
            aio.start_daq_activity()
            time.sleep(activity_time)
            aio.finish_daq_activity()
            aio.release_instrument()       
            ao0, ao1, ai0, ai1, ai2, ai3, ai4 = self.to_analog_channels(waveform, aio.ai_data)        
            self.assertEqual((abs(ai0-ao0).sum(),
                             abs(ai1-ao1).sum(), 
                             abs(ai2-ao0).sum(), 
                             abs(ai3-ao1).sum(), 
                             ai4.sum()),
                             (0.0, 0.0, 0.0, 0.0, 0.0))
                
        def to_analog_channels(self, ao_data, ai_data):
            ai_data = numpy.round(ai_data, 2)
            ai0 = ai_data[:,-1]
            ai1 = ai_data[:,-2]
            ai2 = ai_data[:,-3]
            ai3 = ai_data[:,-4]
            ai4 = ai_data[:,-5]
            ao0 = ao_data[:,0]
            ao1 = ao_data[:,1]
            return ao0, ao1, ai0, ai1, ai2, ai3, ai4
    
        def generate_waveform1(self, duration):
            if self.config.DAQ_CONFIG[0].has_key('SAMPLE_RATE'):
                fsample = self.config.DAQ_CONFIG[0]['SAMPLE_RATE']
            elif self.config.DAQ_CONFIG[0].has_key('AO_SAMPLE_RATE'):
                fsample = self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
            waveform = numpy.zeros(fsample * duration)
            waveform[1] = 1.0
            waveform = numpy.array([waveform, 2.0 * waveform]).transpose()
            return waveform
    
        def generate_waveform2(self, duration):        
            if self.config.DAQ_CONFIG[0].has_key('SAMPLE_RATE'):
                fsample = self.config.DAQ_CONFIG[0]['SAMPLE_RATE']
            elif self.config.DAQ_CONFIG[0].has_key('AO_SAMPLE_RATE'):
                fsample = self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
            waveform = numpy.linspace(2.0, 0.0, fsample * duration)
            waveform = numpy.array([waveform, 1.0 + 2.0 * waveform]).transpose()
            waveform[-1] = [0.0, 0.0]
            return numpy.round(waveform, 2)
            
    
            
    class TestAnalogIOProcess(unittest.TestCase):
        '''
        Expected connections:
        AO0 - AI0
        AO1 - AI1
        '''
        def setUp(self):
            import multiprocessing
            from visexpman.engine.generic import log
            self.logfile = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_working_folder), 'log_daq_test_{0}.txt'.format(int(1000*time.time())))
            self.logger = log.Logger(filename=self.logfile)
            self.instrument_name = 'test aio'
            self.logger.add_source(self.instrument_name)
            self.logqueue = self.logger.get_queues()[self.instrument_name]
            self.queues = {'command': multiprocessing.Queue(), 
                                                                                'response': multiprocessing.Queue(), 
                                                                                'data': multiprocessing.Queue()}
            from visexpman.engine.generic import signal
            self.ao_sample_rate = 40000
            self.ao_sample_rate2 = 10000
            tup = 0.02
            tdown = 0.001
            amplitudes = [-1, 1,3]
            self.test_waveform = [signal.wf_triangle(amplitude, tup, tdown, tup+tdown, self.ao_sample_rate) for amplitude in amplitudes]
            self.test_waveform = numpy.concatenate(tuple(self.test_waveform))
            self.test_waveform2 = numpy.linspace(0, 1, 1000)
            
            self.expected_logs = ['test aio', 'Daq started with parameters', 'Daq stopped']
            self.ai_expected_logs = ['Analog input task created', 'Analog input task finished']
            self.ao_expected_logs = ['Analog output task created', 'Analog output task finished']
            self.not_expected_logs = ['WARNING', 'ERROR', 'default']
            
        def tearDown(self):
            if unittest_aggregator.TEST_daq:
                set_voltage('Dev1/ao0', 0)
                set_voltage('Dev1/ao1', 0)
            if self.logger.is_alive():
                self.logger.terminate()
                
        def _aio_restarted(self,logger,test_waveform):
            aio_binning_factor1 = 4
            aio_binning_factor2 = 5
            duration1 = 4.0
            duration2 = 8.0
            aio = AnalogIOProcess(self.instrument_name, self.queues, logger,
                                    ai_channels = 'Dev1/ai0:1',
                                    ao_channels='Dev1/ao0:1')
            self.test_waveform2ch = numpy.tile(test_waveform,2).reshape((2, test_waveform.shape[0]))
            self.test_waveform22ch = -self.test_waveform2ch
            processes = [aio,logger]
            [p.start() for p in processes if hasattr(p, 'start') and not p.is_alive()]
            aio.start_daq(ai_sample_rate = aio_binning_factor1*self.ao_sample_rate, ao_sample_rate = self.ao_sample_rate, 
                          ao_waveform = self.test_waveform2ch,
                          timeout = 30) 
            time.sleep(duration1)
            data1 = aio.stop_daq()
            aio.start_daq(ai_sample_rate = aio_binning_factor2*self.ao_sample_rate2, ao_sample_rate = self.ao_sample_rate2, 
                          ao_waveform = self.test_waveform22ch,
                          timeout = 30) 
            time.sleep(duration2)
            data2 = aio.stop_daq()
            aio.terminate()
            time.sleep(0.5)#Wait till log flushed to file
            map(self.assertNotIn, self.not_expected_logs, len(self.not_expected_logs)*[fileop.read_text_file(self.logfile)])
            for el in [self.expected_logs, self.ai_expected_logs, self.ao_expected_logs]:
                map(self.assertIn, el, len(el)*[fileop.read_text_file(self.logfile)])
            #Check if two channel data is aquired
            self.assertEqual(data1[0].shape[2],2)
            self.assertEqual(data2[0].shape[2],2)
            #check if length of recorded analog input data is realistic
            self.assertAlmostEqual(data1[0].shape[0]*data1[0].shape[1]/float(aio_binning_factor1*self.ao_sample_rate), duration1, delta = 0.5)
            self.assertAlmostEqual(data2[0].shape[0]*data2[0].shape[1]/float(self.ao_sample_rate2*aio_binning_factor2), duration2, delta = 0.5)
            #Compare generated and acquired waveforms
            numpy.testing.assert_allclose(data1[0][:,:,0].mean(axis=0)[1:], numpy.repeat(test_waveform,aio_binning_factor1)[:-1], 0, 2e-3)
            numpy.testing.assert_allclose(data2[0][:,:,0].mean(axis=0)[1:], numpy.repeat(-test_waveform,aio_binning_factor2)[:-1], 0, 3e-3)
            numpy.testing.assert_allclose(data1[0][:,:,1].mean(axis=0), numpy.repeat(test_waveform,aio_binning_factor1), 0, 5e-3)
            numpy.testing.assert_allclose(data2[0][:,:,1].mean(axis=0), numpy.repeat(-test_waveform,aio_binning_factor2), 0, 5e-3)
            return aio
        
        def test_01_parse_channel_string(self):
            channels_strings = ['Dev1/ao0:2', 'Dev2/ao1', 'Dev3/ai2:3']
            expected_devnames = ['Dev1', 'Dev2', 'Dev3']
            expected_nchannels = [3, 1, 2]
            expected_channel_indexes = [[0,2], [1], [2,3]]
            for i in range(len(channels_strings)):
                device_name, nchannels, channel_indexes = parse_channel_string(channels_strings[i])
                self.assertEqual(device_name, expected_devnames[i])
                self.assertEqual(nchannels, expected_nchannels[i])
                self.assertEqual(channel_indexes, expected_channel_indexes[i])
                
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_02_set_voltage(self):
            set_voltage('Dev1/ao0', 3)
            set_voltage('Dev1/ao0', 0)
            set_voltage('Dev1/ao0:1', 3)
            set_voltage('Dev1/ao0:1', 0)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_03_set_do_line(self):
            set_digital_line('Dev1/port0/line0', 0)
            set_digital_line('Dev1/port0/line0', 1)
            set_digital_line('Dev1/port0/line0', 0)
                
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_04_aio_multichannel(self):
            '''
            Analog IO process started and two consecutive analog waveform generation and analog input sampling 
            is initiated. Different ao sampling rates and binning factors are used.
            
            First ai channel has one sample delay and ao sampling rate increase does not work
            '''
            self._aio_restarted(self.logger, self.test_waveform)
        
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_05_single_ai_channel(self):
            #Setting 3 V on analog output 3
            voltage = 3.0
            set_voltage('Dev1/ao1', voltage)
            #Sampling analog input starts
            ai_record_time = 5.0
            ai_sample_rate = 1000000
            aio = AnalogIOProcess(self.instrument_name, self.queues, self.logger,
                                    ai_channels = 'Dev1/ai1')
            processes = [aio,self.logger]
            [p.start() for p in processes]
            aio.start_daq(ai_sample_rate = ai_sample_rate,
                          ai_record_time = ai_record_time,
                          timeout = 30) 
            time.sleep(ai_record_time)
            data = aio.stop_daq()
            aio.terminate()
            time.sleep(0.5)
            map(self.assertNotIn, self.not_expected_logs, len(self.not_expected_logs)*[fileop.read_text_file(self.logfile)])
            for el in [self.expected_logs, self.ai_expected_logs]:
                map(self.assertIn, el, len(el)*[fileop.read_text_file(self.logfile)])
            #constant 3 V is expected in data
            numpy.testing.assert_allclose(data[0].mean(), voltage, 0, 1e-3)
            numpy.testing.assert_allclose(data[0].max()-data[0].min(), 0.0, 0, 1e-2*voltage)
            self.assertGreaterEqual(data[0].shape[0]/float(ai_sample_rate), ai_record_time)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_06_aio_start_without_params(self):
            aio = AnalogIOProcess('test aio', self.queues, self.logger,
                                    ai_channels = 'Dev1/ai0:1',
                                    ao_channels='Dev1/ao0:1')
            processes = [aio,self.logger]
            [p.start() for p in processes]
            aio.start_daq(timeout = 10.0) 
            aio.terminate()
            self.assertIn('DaqInstrumentError', fileop.read_text_file(self.logfile))
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')        
        def test_07_aio_process_run_twice(self):
            '''
            Tests:
             - In one session multiple consecutive AnalogIO process can be run
             - if small buffer (short waveform) is handled properly
            '''
            self.logger.start()
            for wf in [numpy.repeat(self.test_waveform,2),0.5*self.test_waveform,numpy.repeat(-0.2*self.test_waveform,3)]:
                self._aio_restarted(self.logqueue, wf)
                
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_08_short_waveform(self):
            from pylab import plot, show
            self.logger.start()
            configs = [(200000,12000), (10000, 600), (100000, 6000)]
            for sample_rate, wf_size in configs:
                waveform = numpy.linspace(0,1,wf_size)
                duration = 3.0
                for rep in range(3):
                    aio = AnalogIOProcess(self.instrument_name, self.queues, self.logqueue,
                                            ai_channels = 'Dev1/ai0:1',
                                            ao_channels='Dev1/ao0:1')
                    aio.start()
                    aio.start_daq(ai_sample_rate = sample_rate, ao_sample_rate = sample_rate, 
                                  ao_waveform = numpy.tile(waveform,2).reshape((2, waveform.shape[0])),
                                  timeout = 30) 
                    time.sleep(duration)
                    data = aio.stop_daq()
                    aio.terminate()
                    self.assertGreaterEqual(data[0].shape[0]*data[0].shape[1]/float(sample_rate), duration)
                    self.assertAlmostEqual(data[0].shape[0]*data[0].shape[1]/float(sample_rate), duration, delta = 0.3)
                    numpy.testing.assert_allclose(data[0][:,:,1].flatten(), numpy.tile(waveform,data[1]), 0, 2e-2)
                if not True:
                    plot(data[0][:,:,1].flatten())
                    plot(numpy.tile(waveform,data[1]))
                    show()
            #check log
            map(self.assertNotIn, self.not_expected_logs, len(self.not_expected_logs)*[fileop.read_text_file(self.logfile)])
            for el in [self.expected_logs, self.ai_expected_logs]:
                map(self.assertIn, el, len(el)*[fileop.read_text_file(self.logfile)])
                
        @unittest.skipIf(not unittest_aggregator.TEST_daq, 'Daq tests disabled')
        def test_09_nonprocess_aio(self):
            from pylab import plot, show
            self.logger.start()
            sample_rate = 100000
            waveform = numpy.tile(numpy.linspace(0,1,10000),2)
            aio = AnalogIOProcess(self.instrument_name, self.queues, self.logqueue,
                                            ai_channels = 'Dev1/ai0:1',
                                            ao_channels='Dev1/ao0:1')
            aio._create_tasks()
            aio._start(ai_sample_rate = sample_rate, ao_sample_rate = sample_rate, 
                          ao_waveform = numpy.tile(waveform,2).reshape((2, waveform.shape[0])),
                          finite_samples=True,timeout = 30)
            ai_data = aio._stop()
            aio._close_tasks()
            numpy.testing.assert_allclose(ai_data[:,0][1:], waveform[:-1], 0, 1e-2)
            numpy.testing.assert_allclose(ai_data[:,1], waveform, 0, 2e-2)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq, 'Daq tests disabled')
        def test_10_set_waveform(self):
            waveform = numpy.linspace(0,2,10000)[:,None].T
            set_waveform('Dev1/ao0',waveform,sample_rate = 100000)
            set_voltage('Dev1/ao0',0)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq or True, 'Daq tests disabled')
        def test_11_non_process_aio_then_process_aio(self):
            sample_rate = 100000
            waveform = numpy.tile(numpy.linspace(0,1,10000),2)
            aio = AnalogIOProcess(self.instrument_name, self.queues, self.logqueue,
                                            ai_channels = 'Dev1/ai0:1',
                                            ao_channels='Dev1/ao0:1')
            aio._create_tasks()
            aio._start(ai_sample_rate = sample_rate, ao_sample_rate = sample_rate, 
                          ao_waveform = numpy.tile(waveform,2).reshape((2, waveform.shape[0])),
                          finite_samples=True,timeout = 30)
            ai_data = aio._stop()
            aio._close_tasks()
            PyDAQmx.DAQmxResetDevice('Dev1')
            time.sleep(2)
            numpy.testing.assert_allclose(ai_data[:,0][1:], waveform[:-1], 0, 1e-2)
            numpy.testing.assert_allclose(ai_data[:,1], waveform, 0, 2e-2)
            aio=self._aio_restarted(self.logger, self.test_waveform)
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq, 'Daq tests disabled')
        def test_12_analog_control(self):
            ControlLoop().run()
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq, 'Daq tests disabled')
        def test_13_analogio(self):
            analogio('Dev1/ai0:4','Dev1/ao0',1000,numpy.linspace(0,3,1000),timeout=1)
            numpy.testing.assert_almost_equal(numpy.roll(ai_data[:,0],-1),numpy.linspace(0,3,1000),2)
        
        
if __name__ == '__main__':
    unittest.main()
    #analogio('Dev1/ai0:4','Dev1/ao0',1000,numpy.linspace(0,3,1000),timeout=1)
