"""
This is an interpretation of the example program
C:\Program Files\National Instruments\NI-DAQ\Examples\DAQmx ANSI C\Analog Out\Generate Voltage\Cont Gen Volt Wfm-Int Clk\ContGen-IntClk.c
This routine will play an arbitrary-length waveform file.
This module depends on:
numpy
Adapted by Martin Bures [ mbures { @ } zoll { . } com ]
"""
# import system libraries
import ctypes
import numpy
import threading
import time
import Instrument
import Configuration


# load any DLLs
nidaq = ctypes.windll.nicaiu # load the DLL
##############################
# Setup some typedefs and constants
# to correspond with values in
# C:\Program Files\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h
# the typedefs
int32 = ctypes.c_long
uInt32 = ctypes.c_ulong
uInt64 = ctypes.c_ulonglong
float64 = ctypes.c_double
TaskHandle = uInt32
# the constants
DAQmx_Val_Cfg_Default = int32(-1)
DAQmx_Val_Volts = 10348
DAQmx_Val_Rising = 10280
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_GroupByChannel = 0
##############################
class AnalogOut(Instrument.Instrument):
    """
    Generic, single channel analog signal generation using any daqmx device. The range of generated signal is 0..10 V.
    Ni Daqmx driver shall be installed. Only Windows operating system is supported.
    Assuming the following variables exist in config:
        - LED_CONTROL_SAMPLE_RATE
        - LED_CONTROL_CHANNEL
    Assuming the following item in settings dictionary: 'waveform'
    """

    def init_instrument( self, config, settings ):

        self.sample_rate = config.LED_CONTROL_SAMPLE_RATE
        self.period_length = len(settings['waveform'])
        self.duration = float(self.period_length) / float(self.sample_rate)
        self.taskHandle = TaskHandle(0)
        self.data = numpy.zeros((self.period_length,), dtype=numpy.float64)
        # convert waveform to a numpy array
        for i in range( self.period_length ):
            self.data[ i ] = settings['waveform'][ i ]
        self.init_daq(config)

    def init_daq(self, config):
        # setup the DAQ hardware
        self.check_daq_error(nidaq.DAQmxCreateTask("", ctypes.byref( self.taskHandle )))
        self.check_daq_error(nidaq.DAQmxCreateAOVoltageChan( self.taskHandle,
                                   config.LED_CONTROL_CHANNEL,
                                   "",
                                   float64(0.0),
                                   float64(10.0),
                                   DAQmx_Val_Volts,
                                   None))
        self.check_daq_error(nidaq.DAQmxCfgSampClkTiming( self.taskHandle,
                                "",
                                float64(self.sample_rate),
                                DAQmx_Val_Rising,
                                DAQmx_Val_FiniteSamps,
                                uInt64(self.period_length)))
        self.check_daq_error(nidaq.DAQmxWriteAnalogF64( self.taskHandle,
                              int32(self.period_length),
                              0,
                              float64(-1),
                              DAQmx_Val_GroupByChannel,
                              self.data.ctypes.data,
                              None,
                              None))
    def check_daq_error( self, err ):
        """a simple error checking routine"""
        if err < 0:
            buf_size = 100
            buf = ctypes.create_string_buffer('\000' * buf_size)
            nidaq.DAQmxGetErrorString(err,ctypes.byref(buf),buf_size)
            raise RuntimeError('nidaq call failed with error %d: %s'%(err,repr(buf.value)))
        if err > 0:
            buf_size = 100
            buf = ctypes.create_string_buffer('\000' * buf_size)
            nidaq.DAQmxGetErrorString(err,ctypes.byref(buf),buf_size)
            raise RuntimeError('nidaq generated warning %d: %s'%(err,repr(buf.value)))
        
    def start_instrument( self ):
        counter = 0
        nidaq.DAQmxStartTask( self.taskHandle )
        
    def stop_instrument( self ):
##        self.running = False
        nidaq.DAQmxStopTask( self.taskHandle )
        
    def close_instrument(self):
        nidaq.DAQmxClearTask( self.taskHandle )

    def play_waveform(self):
        if self.started:
            self.start_instrument()
        else:
            self.started = True
            self.start()    
        time.sleep(self.duration)
        self.stop()

class LedController(AnalogOut):
    def __init__(self, config, timing, current_amplitude):
        '''
        Generating trigger pulses for Led controller (Thorlabs DC2100 and Thorlabs DC4100 are supported).
        Timing and LED current can be controlled individually for each pulse.
        config: The following parameters are assumed:
            LED_CONTROL_SAMPLE_RATE: sample rate of trigger signal generation in Hz
            LED_CONTROL_CHANNEL: the name of analog output channel including device name
            LED_CURRENT_TO_CONTROL_VOLTAGE: Conversion rate between control voltage and led current.
                                            At DC4100 device 10 V corresponds to 1000 mA, at DC2100 10 V is 2000 mA
        timing: list of timing values in seconds, interpretation:
                        ___     ___     ___
                    ___|   |___|   |___|   |___
                    t0  t1   t2  t3 t4  t5 ...

        current_amplitude: current amplitude for each pulses in mA. For multiple pulses with different amplitudes
                                a list of current amplitudes shall be provided

        Usage:
        led = LedController(conf, timing, amplitude)
        led.run()        
        '''
        
        if not isinstance(current_amplitude, list):
            amplitude = numpy.ones(len(timing)) * current_amplitude * config.LED_CURRENT_TO_CONTROL_VOLTAGE
        else:
            amplitude = numpy.array(current_amplitude) * config.LED_CURRENT_TO_CONTROL_VOLTAGE
        state = 0
        waveform = numpy.array(())
        for i in range(len(timing)):
            if state == 0:
                new_segment = numpy.zeros(timing[i] * config.LED_CONTROL_SAMPLE_RATE, dtype=numpy.float64)
                state = 1
            elif state == 1:
                new_segment = numpy.ones(timing[i] * config.LED_CONTROL_SAMPLE_RATE, dtype=numpy.float64) * amplitude[int((i - 1) * 0.5)]
                state = 0                
            waveform = numpy.concatenate((waveform, new_segment))

        waveform[-1] = 0.0        
        settings = {'waveform':waveform}
        self.ao = AnalogOut(config, settings = settings)
        
    def start_instrument(self):
        self.ao.play_waveform()
    
class testConfig(Configuration.Config):
    def _create_application_parameters(self):
        LED_CONTROL_SAMPLE_RATE = [10, [1, 100000]]
        LED_CONTROL_CHANNEL = "DevUsb/ao1"
        LED_CURRENT_TO_CONTROL_VOLTAGE = [10.0/2000.0, [0, 10000]]
        self._create_parameters_from_locals(locals())    

if __name__ == '__main__':
    import time
    st = time.time()
    conf = testConfig()

    timing = [0.1, 0.1, 0.1, 0.5, 1.0, 0.5]
    amp = [100,200,100]
    led = LedController(conf, timing, amp)
    led.run()
    led.run()

    print time.time() - st
