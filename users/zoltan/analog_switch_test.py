'''
Check how 4066BE IC can be used for modulated LED control
ao2: in/out
ao3: control

Different voltage levels: (3,5,8,10 V) are applied to both control and in pins.
A longer pulse is applied to <in> and a shorter to <control>. Then it is done the other
way around.

Finally the measurement has to be repeated by swapping in and out pins

'''
control_voltage =5
in_voltage = 7
short_pulse = 5e-5
long_pulse = 3e-4
sample_rate = 1e6
repeats = 2
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from pylab import plot,show
pulse_template = numpy.zeros((sample_rate*1.5*long_pulse,2))
pulse_template[pulse_template.shape[0]*0.1:pulse_template.shape[0]*0.1+sample_rate*long_pulse,1] = in_voltage
pulse_template[pulse_template.shape[0]*0.2:pulse_template.shape[0]*0.2+sample_rate*short_pulse,0]=control_voltage
pulse_template[pulse_template.shape[0]*0.5:pulse_template.shape[0]*0.5+sample_rate*short_pulse,0]=control_voltage
waveform = numpy.tile(pulse_template.T,repeats)
daq_instrument.set_waveform('Dev1/ao2:3',waveform,sample_rate = sample_rate)
