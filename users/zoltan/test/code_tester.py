import time
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import configuration
class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 100000,
        'AO_CHANNEL' : 'Dev1/ao0',
        'MAX_VOLTAGE' : 8.0,
        'MIN_VOLTAGE' : -8.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())
if __name__ == "__main__":
    duration = 50
    f = 200
    A = 1.0
    config = TestConfig()
    aio = daq_instrument.AnalogIO(config)
    fs = aio.ao_sample_rate
    t = numpy.linspace(0,  duration,  duration*fs, False)
    signal = 0.5*A*numpy.sin(2*numpy.pi*t*f)
    aio.waveform = signal
    aio.start_daq_activity()
    time.sleep(duration)
    aio.release_instrument()
#    from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
#    plot(t, signal)
#    show()
