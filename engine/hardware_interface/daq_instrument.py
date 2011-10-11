import numpy
import time
import instrument
import visexpman.engine.generic.configuration as configuration
import visexpman.engine.generic.utils as utils
import unittest
import logging
import os


import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

if os.name == 'nt':
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes


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
        if os.name == 'nt':
            self.daq_config = self.config.DAQ_CONFIG[self.id]        
            if not self.daq_config.has_key('SAMPLE_RATE') and (not self.daq_config.has_key('AO_SAMPLE_RATE') or not self.daq_config.has_key('AI_SAMPLE_RATE')):
                raise RuntimeError('SAMPLE_RATE parameter or AO_SAMPLE_RATE, AI_SAMPLE_RATE parameters needs to be defined.')
                
            elif self.daq_config.has_key('SAMPLE_RATE'):            
                self.ai_sample_rate = self.daq_config['SAMPLE_RATE']
                self.ao_sample_rate = self.daq_config['SAMPLE_RATE']
            else:
                self.ai_sample_rate = self.daq_config['AI_SAMPLE_RATE']
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
                self.analog_input.CreateAIVoltageChan(self.daq_config['AI_CHANNEL'],
                                                            'ai',
                                                            DAQmxConstants.DAQmx_Val_RSE,
                                                            self.daq_config['MIN_VOLTAGE'], 
                                                            self.daq_config['MAX_VOLTAGE'], 
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
                self.read = DAQmxTypes.int32()
                channel_indexes = self.daq_config['AI_CHANNEL'].split('/')[-1].replace('ai','').split(':')
                self.number_of_ai_channels = abs(int(channel_indexes[-1]) - int(channel_indexes[0])) + 1

    def _configure_timing(self):    
        if os.name == 'nt':    
            if self.enable_ao:
                self.analog_output.CfgSampClkTiming("OnboardClock",
                                            self.ao_sample_rate,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            DAQmxConstants.DAQmx_Val_FiniteSamps,
                                            self.number_of_ao_samples)                                            
            if self.enable_ai:
                self.analog_input.CfgSampClkTiming("OnboardClock",
                                            self.ai_sample_rate,
                                            DAQmxConstants.DAQmx_Val_Rising,
                                            DAQmxConstants.DAQmx_Val_FiniteSamps,
                                            self.number_of_ai_samples)
        
    def _write_waveform(self):
        if os.name == 'nt':
            if self.enable_ao:
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
        if os.name == 'nt':
            if not hasattr(self, 'waveform') and self.enable_ao:
                raise RuntimeError('No waveform provided')
                
            if self.enable_ao:
                self.number_of_ao_samples = self.waveform.shape[0]
                self.waveform_duration = float(self.number_of_ao_samples) / float(self.ao_sample_rate)            
                self.number_of_ai_samples = int(self.number_of_ao_samples * self.ai_sample_rate / self.ao_sample_rate)
                self.analog_activity_time = self.waveform_duration
            else:
                self.number_of_ai_samples = int(self.daq_config['DURATION_OF_AI_READ'] * self.ai_sample_rate)
                self.analog_activity_time = self.daq_config['DURATION_OF_AI_READ']
                
            if self.enable_ai:
                #clear ai buffer
                self.ai_data = numpy.zeros((self.number_of_ai_samples*self.number_of_ai_channels), dtype=numpy.float64)
            self._configure_timing() #this cannot be done during init because the lenght of the signal is not known before waveform is set
            self._write_waveform()
            if self.enable_ao:
                self.analog_output.StartTask()
            if self.enable_ai:
                self.analog_input.StartTask()
            
    def finish_daq_activity(self):
        if os.name == 'nt':
            if self.enable_ai:
                self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                                self.daq_config['DAQ_TIMEOUT'],
                                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                                self.ai_data,
                                                self.number_of_ai_samples*self.number_of_ai_channels,
                                                DAQmxTypes.byref(self.read),
                                                None)
    
                #Make sure that all the acquisitions are completed
                self.analog_input.WaitUntilTaskDone(self.daq_config['DAQ_TIMEOUT'])
            if self.enable_ao:
                self.analog_output.WaitUntilTaskDone(self.daq_config['DAQ_TIMEOUT'])
            
            if self.enable_ao:
                self.analog_output.StopTask()
            if self.enable_ai:
                self.analog_input.StopTask()        
                self.ai_data = self.ai_data.reshape((self.number_of_ai_channels, self.number_of_ai_samples)).transpose()
    
    
    def start_instrument(self):
        if os.name == 'nt':
            self.start_daq_activity()        
            time.sleep(self.analog_activity_time)
            self.finish_daq_activity()
        

    def close_instrument(self):
        if os.name == 'nt':
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
        channels: [offset, width, amplitude], [offset, width, amplitude], ....
        
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
        self.state_machine('release_instrument')        
            
    def state_machine(self, command, parameters = None):        
        if self.state == 'running':
            while time.time() < self.end_time:
                pass
            self.finish_daq_activity()
            self.state = 'set'
    
        if command == 'set':
            if self.state == 'ready' or self.state == 'set':
                pulse_configs = numpy.array(parameters[0])
                duration = parameters[1]
                waveform = []
                if pulse_configs.shape[0] != self.number_of_ao_channels:
                    raise RuntimeError('Analog output channel number mismatch.')
                for pulse_config in pulse_configs:
                    channel_waveform = utils.generate_pulse_train(pulse_config[0], pulse_config[1], pulse_config[2], duration)
                    channel_waveform[-1] = 0.0
                    waveform.append(channel_waveform)
                waveform = numpy.array(waveform).transpose()
                self.waveform = waveform
                self.state = 'set'
        elif command == 'start':
            if self.state == 'set':
                self.start_daq_activity()
                self.end_time = time.time() + self.analog_activity_time
                self.state = 'running'
        elif command == 'stop':
            if self.state == 'running':
                self.finish_daq_activity()
        elif command == 'release_instrument':
            AnalogIO.release_instrument(self)

#=== TESTS ===
class InvalidTestConfig(configuration.Config):
    def _create_application_parameters(self):
        if os.name == 'nt':
            TEST_DATA_PATH = 'c:\\_del'
        elif os.name == 'posix':
            TEST_DATA_PATH = '/media/Common/visexpman_data/test'
        DAQ_CONFIG = [[
                    {
                    'ANALOG_CONFIG' : 'aio',
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 100,
                    'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
                    'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai5:0',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : 0.0,        
                    }
                    ]]
        
        self._create_parameters_from_locals(locals())

        
class testDaqConfig(configuration.Config):
    def _create_application_parameters(self):
        if os.name == 'nt':
            TEST_DATA_PATH = 'c:\\_del'
        elif os.name == 'posix':
            TEST_DATA_PATH = '/media/Common/visexpman_data/test'
        DAQ_CONFIG = [[
        {
        'ANALOG_CONFIG' : 'aio', #'ai', 'ao', 'aio', 'undefined'
        'DAQ_TIMEOUT' : 1.0, 
        'AO_SAMPLE_RATE' : 100,
        'AI_SAMPLE_RATE' : 1000,
        'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',        
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : 0.0,
        'DURATION_OF_AI_READ' : 1.0,
        },
        {
        'ANALOG_CONFIG' : 'undefined',
        'DAQ_TIMEOUT' : 0.0, 
        'AO_SAMPLE_RATE' : 100,
        'AI_SAMPLE_RATE' : 1000,
        'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : 0.0,
        'DURATION_OF_AI_READ' : 1.0,
        }
        ]]
        
        self._create_parameters_from_locals(locals())
        
class testAnalogPulseConfig(configuration.Config):
    def _create_application_parameters(self):
        if os.name == 'nt':
            TEST_DATA_PATH = 'c:\\_del'
        elif os.name == 'posix':
            TEST_DATA_PATH = '/media/Common/visexpman_data/test'
        DAQ_CONFIG = [[
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 1.0, 
        'SAMPLE_RATE' : 10000,        
        'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',        
        'MAX_VOLTAGE' : 10.0,
        'MIN_VOLTAGE' : 0.0,
        },        
        ]]        
        self._create_parameters_from_locals(locals())

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
        self.experiment_control = instrument.testLogClass(self.config, self)
        self.state = 'experiment running'

    def tearDown(self):
        pass

    #== AnalogIO test cases ==
    def test_01_test_sample_rate_parameters(self):
        self.config = InvalidTestConfig()
        self.assertRaises(RuntimeError,  AnalogIO, self.config, self)
        
    def test_02_test_sample_rate_parameters(self):
        self.config = InvalidTestConfig()
        self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 10
        aio = AnalogIO(self.config, self)
        self.assertEqual((aio.ai_sample_rate, aio.ao_sample_rate), (10, 100))
        
    def test_03_test_sample_rate_parameters(self):
        self.config = InvalidTestConfig()
        self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 90
        aio = AnalogIO(self.config, self)
        self.assertEqual((aio.ai_sample_rate, aio.ao_sample_rate), (90, 90))
        aio.release_instrument()
    
    def test_04_invalid_analog_config(self):
        self.config = InvalidTestConfig()
        self.config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = ''
        self.assertRaises(RuntimeError, AnalogIO, self.config, self)
        
    def test_05_no_waveform_provided(self):
        aio = AnalogIO(self.config, self)        
        self.assertRaises(RuntimeError,  aio.run)
        aio.release_instrument()
        
    def test_06_analog_input_and_output_are_synchronized(self):
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
                         
    def test_07_analog_input_and_output_are_synchronized_with_ramp_waveform(self):
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
                         
    def test_08_out_of_range_waveform(self):
        self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 1000
        aio = AnalogIO(self.config, self)       
        waveform = self.generate_waveform2(0.2) + 5.0
        aio.waveform = waveform
        self.assertRaises(PyDAQmx.DAQError, aio.run)        
        aio.release_instrument()

    def test_09_restart_playing_waveform(self):
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

    def test_10_reuse_analogio_class(self):
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
                            
    def test_11_analog_input_and_output_have_different_sampling_rates(self):
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
                         
    def test_12_analog_input_and_output_have_different_sampling_rates(self):
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

    def test_13_ai_ao_different_sample_rate(self):
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
    
             
    def test_14_single_channel_ai_ao(self):
        
        self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 80000
        self.config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 80000
        self.config.DAQ_CONFIG[0]['AO_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ao0'
        self.config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai0'
        
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
                         
    def test_15_enable_ai_ao_separately(self):
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
        
    def test_16_non_blocking_daq_activity_1(self):
        waveform = self.generate_waveform2(0.1)
        self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
        self.non_blocking_daq(1.0, waveform)
        
    def test_17_non_blocking_daq_activity_2(self):
        waveform = self.generate_waveform2(0.1)
        self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
        self.non_blocking_daq(0.0, waveform)

    def test_18_non_blocking_daq_activity_3(self):
        waveform = self.generate_waveform2(0.1)
        self.config.DAQ_CONFIG[0]['SAMPLE_RATE'] = 300
        self.non_blocking_daq(0.1, waveform)
        
    #== Analog pulse test cases
    def test_19_analog_pulse(self):
        self.config = testAnalogPulseConfig()
        offsets = [0, 10, 20]
        pulse_widths = 4
        amplitudes = 0.01
        duration = 200
        ap = AnalogPulse(self.config, self)
        self.assertRaises(RuntimeError, ap.set, [[offsets, pulse_widths, amplitudes]], duration)        
        ap.start()
        ap.release_instrument()
        
    def test_20_analog_pulse_one_channel(self):
        self.config = testAnalogPulseConfig()
        self.config.DAQ_CONFIG[0]['AO_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ao0:0'
        
        #Config for analog acquisition
        ai_config = testAnalogPulseConfig()        
        ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
        ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai9:0'        
        ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1

        
        ai = AnalogIO(ai_config, self)
        ai.start_daq_activity()               

        offsets = [0, 10, 20]
        pulse_widths = 5
        amplitudes = 2.0
        duration = 50
        ap = AnalogPulse(self.config, self)
        ap.set([[offsets, pulse_widths, amplitudes]], duration)
        ap.start()
        ap.release_instrument()
        ai.finish_daq_activity()
        ai.release_instrument()
        
        ai_data = numpy.round(ai.ai_data, 1)        
        ai0 = ai_data[:,-1]
        ai1 = ai_data[:,-2]        
        self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets) * pulse_widths * amplitudes, 0.0))

    def test_21_analog_pulse_two_channels(self):
        self.config = testAnalogPulseConfig()
        #Config for analog acquisition
        ai_config = testAnalogPulseConfig()        
        ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
        ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai9:0'        
        ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1
        
        ai = AnalogIO(ai_config, self)
        ai.start_daq_activity()               

        #Channel0
        offsets0 = [0, 10, 20]
        pulse_widths0 = 5
        amplitudes0 = 2.0
        #Channel1
        offsets1 = [0, 10, 20]
        pulse_widths1 = 2
        amplitudes1 = 2.5
        
        duration = 50
        ap = AnalogPulse(self.config, self)
        ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
        ap.start()
        ap.release_instrument()
        ai.finish_daq_activity()
        ai.release_instrument()
        
        ai_data = numpy.round(ai.ai_data, 1)        
        ai0 = ai_data[:,-1]
        ai1 = ai_data[:,-2]        
        self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets0) * pulse_widths0 * amplitudes0, len(offsets1) * pulse_widths1 * amplitudes1))
        
    def test_22_analog_pulse_two_channels(self):
        self.config = testAnalogPulseConfig()
        #Config for analog acquisition
        ai_config = testAnalogPulseConfig()        
        ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
        ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai9:0'        
        ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 0.1
        
        ai = AnalogIO(ai_config, self)
        ai.start_daq_activity()               

        #Channel0
        offsets0 = [0, 10, 20]
        pulse_widths0 = 5
        amplitudes0 = 2.0
        #Channel1
        offsets1 = [0, 10, 20]
        pulse_widths1 = 8
        amplitudes1 = [2.5, 1.0, 3.0]
        
        duration = 50
        ap = AnalogPulse(self.config, self)
        ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
        ap.start()
        ap.release_instrument()
        ai.finish_daq_activity()
        ai.release_instrument()
        
        ai_data = numpy.round(ai.ai_data, 1)        
        ai0 = ai_data[:,-1]
        ai1 = ai_data[:,-2]        
        self.assertEqual((ai0.sum(), ai1.sum()), (len(offsets0) * pulse_widths0 * amplitudes0, pulse_widths1 * numpy.array(amplitudes1).sum()))
        
    def test_23_restart_pulses(self):
        self.config = testAnalogPulseConfig()
        #Config for analog acquisition
        ai_config = testAnalogPulseConfig()        
        ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
        ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai9:0'        
        ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 1.0
        
        ai = AnalogIO(ai_config, self)
        ai.start_daq_activity()               

        #Channel0
        offsets0 = [0, 10, 200]
        pulse_widths0 = 5
        amplitudes0 = 2.0
        #Channel1
        offsets1 = [0, 10, 180]
        pulse_widths1 = 2
        amplitudes1 = 2.5
        
        duration = 300
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
        self.assertEqual((ai0.sum(), ai1.sum()), (2*len(offsets0) * pulse_widths0 * amplitudes0, 2*len(offsets1) * pulse_widths1 * amplitudes1))
        
    def test_24_restart_pulses_long_duration(self):
        self.config = testAnalogPulseConfig()
        #Config for analog acquisition
        ai_config = testAnalogPulseConfig()
        ai_config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'ai'        
        ai_config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai9:0'        
        ai_config.DAQ_CONFIG[0]['DURATION_OF_AI_READ'] = 30.0
        ai_config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        
        ai = AnalogIO(ai_config, self)
        ai.start_daq_activity()               

        duration = 100000
        #Channel0
        import random
        number_of_pulses = int(50 * random.random())
        offsets0 = []
        for i in range(number_of_pulses):
            offsets0.append(int(200 * random.random() + duration/200*i))
        pulse_widths0 = 50
        amplitudes0 = 2.0
        #Channel1
        offsets1 = [10, 500, 9088]
        pulse_widths1 = 200
        amplitudes1 = 2.5
        
        duration = 100000
        ap = AnalogPulse(self.config, self)
        ap.set([[offsets0, pulse_widths0, amplitudes0], [offsets1, pulse_widths1, amplitudes1]], duration)
        ap.start()
        time.sleep(13.0)
        ap.start()
        ap.release_instrument()
        ai.finish_daq_activity()
        ai.release_instrument()
        
        ai_data = numpy.round(ai.ai_data, 1)        
        ai0 = ai_data[:,-1]
        ai1 = ai_data[:,-2]        
        self.assertEqual((ai0.sum(), ai1.sum()), (2*len(offsets0) * pulse_widths0 * amplitudes0, 2*len(offsets1) * pulse_widths1 * amplitudes1))    
    
    #== Test utilities ==
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

if __name__ == '__main__':
    unittest.main()