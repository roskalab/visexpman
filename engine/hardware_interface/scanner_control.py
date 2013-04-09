'''
Setting scanner position and speed

Factors limiting setting time:
- maximal acceleration - Tmin
- maximal speed - Tmin

Extreme setting: big movement, short setting time, big speed change
'''
#eliminate position and speed overshoots - not possible
#TODO: check generated scan for acceleration, speed and position limits
import numpy
import time

import daq_instrument
import instrument
from visexpman.engine.generic import utils
from visexpman.engine.generic import configuration
from visexpman.users.zoltan.test import unit_test_runner
import unittest

class ScannerTestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.SCANNER_MAX_SPEED = utils.rc((1e7, 1e7))#um/s
        self.SCANNER_MAX_ACCELERATION = utils.rc((1e12, 1e12)) #um/s2
        self.SCANNER_SIGNAL_SAMPLING_RATE = 250000 #Hz
        self.SCANNER_DELAY = 0#As function of scanner speed
        self.SCANNER_START_STOP_TIME = 0.02
        self.SCANNER_MAX_POSITION = 200.0
        self.POSITION_TO_SCANNER_VOLTAGE = 2.0/128.0
        self.XMIRROR_OFFSET = 0.0#um
        self.YMIRROR_OFFSET = 0.0#um
        self.SCANNER_RAMP_TIME = 70.0e-3
        self.SCANNER_HOLD_TIME = 30.0e-3
        self.SCANNER_SETTING_TIME = 1e-3
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'aio',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 100000,
        'AI_SAMPLE_RATE' : 200000,
        'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai0:2',
        'MAX_VOLTAGE' : 3.0,
        'MIN_VOLTAGE' : -3.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        {
        'DAQ_TIMEOUT' : 1.0, 
        'DO_CHANNEL' : unit_test_runner.TEST_daq_device + '/port0/line0',
        'ENABLE' : True
        }
        ]
        self._create_parameters_from_locals(locals())
        
def generate_lines_scan(lines, setting_time, frames_to_scan, config):
    start_stop_scanner = False
    dt = 1.0/config.SCANNER_SIGNAL_SAMPLING_RATE
    start_stop_time = config.SCANNER_START_STOP_TIME
    pos_x, pos_y, speed_x, speed_y, accel_x, accel_y, scan_mask, period_time = \
                generate_line_scan_series(lines, dt, setting_time, config.SCANNER_MAX_SPEED, config.SCANNER_MAX_ACCELERATION, scanning_periods = frames_to_scan, start_stop_scanner = start_stop_scanner, start_stop_time = start_stop_time)
    if abs(speed_x).max() < config.SCANNER_MAX_SPEED['col'] and abs(speed_y).max() < config.SCANNER_MAX_SPEED['row'] and\
        abs(accel_x).max() < config.SCANNER_MAX_ACCELERATION['col'] and abs(accel_y).max()< config.SCANNER_MAX_ACCELERATION['row'] and\
        abs(pos_x).max() < config.SCANNER_MAX_POSITION and abs(pos_y).max() < config.SCANNER_MAX_POSITION:
        result = True
    else:
        result = False
    speed_and_accel = {}
    speed_and_accel['speed_x'] = speed_x
    speed_and_accel['speed_y'] = speed_y
    speed_and_accel['accel_x'] = accel_x
    speed_and_accel['accel_y'] = accel_y
    return pos_x, pos_y, scan_mask, speed_and_accel, result

def generate_rectangular_scan(size, position, spatial_resolution, frames_to_scan, setting_time, config):
    '''
    size: in rc format, the horizontal and vertical size of the scannable area
    position: in rc format, the center of the scannable rectangle
    spatial resolution: in um/pixel
    '''
    start_stop_scanner = False
    dt = 1.0/config.SCANNER_SIGNAL_SAMPLING_RATE
    start_stop_time = config.SCANNER_START_STOP_TIME
    row_positions = numpy.linspace(position['row'] - 0.5*size['row'],  position['row'] + 0.5*size['row'],  numpy.ceil(size['row']/spatial_resolution)+1)
    lines = []
    for row_position in row_positions:
        line = {'p0': utils.rc((row_position, position['col'] - 0.5*size['col'])), 'p1': utils.rc((row_position, position['col'] + 0.5*size['col'])), 'ds': spatial_resolution}
        lines.append(line)
    pos_x, pos_y, speed_x, speed_y, accel_x, accel_y, scan_mask, period_time = \
                generate_line_scan_series(lines, dt, setting_time, config.SCANNER_MAX_SPEED, config.SCANNER_MAX_ACCELERATION, scanning_periods = frames_to_scan, start_stop_scanner = start_stop_scanner, start_stop_time = start_stop_time)
    if abs(speed_x).max() < config.SCANNER_MAX_SPEED['col'] and abs(speed_y).max() < config.SCANNER_MAX_SPEED['row'] and\
        abs(accel_x).max() < config.SCANNER_MAX_ACCELERATION['col'] and abs(accel_y).max()< config.SCANNER_MAX_ACCELERATION['row'] and\
        abs(pos_x).max() < config.SCANNER_MAX_POSITION and abs(pos_y).max() < config.SCANNER_MAX_POSITION:
        result = True
    else:
        result = False
    speed_and_accel = {}
    speed_and_accel['speed_x'] = speed_x
    speed_and_accel['speed_y'] = speed_y
    speed_and_accel['accel_x'] = accel_x
    speed_and_accel['accel_y'] = accel_y
    return pos_x, pos_y, scan_mask, speed_and_accel, result
    

#Line scan
def generate_line_scan_series(lines, dt, setting_time, vmax, accmax, scanning_periods = 1, start_stop_scanner = True, start_stop_time = 1.0):
    '''
    line is a list of dict. Each dict contains p0, p1 keys and either ds or v
    '''
    if not hasattr(vmax, 'dtype'):
        v_limits = utils.rc((vmax, vmax))
    else:
        v_limits = vmax
    if not hasattr(accmax, 'dtype'):
        a_limits = utils.rc((accmax, accmax))
    else:
        a_limits = accmax
    lines_out = []
    x_scanner_trajectory = []
    y_scanner_trajectory = []
    p_initial = utils.rc((0.0, 0.0))
    v_initial = utils.rc((0.0, 0.0))
    scan_signal_length_counter = 0        
    p0 = p_initial
    v0 = v_initial
    #Calculate initial speed and position from the parameters of the last line assuming that the scanning will be periodical
    p0 = lines[-1]['p1']
    if lines[-1].has_key('v'):
        ds, n = calculate_spatial_resolution(lines[-1]['p0'], lines[-1]['p1'], lines[-1]['v'], dt)
        v0, n = calculate_scanner_speed(lines[-1]['p0'], lines[-1]['p1'], ds, dt)
    else:
        v0, n = calculate_scanner_speed(lines[-1]['p0'], lines[-1]['p1'], lines[-1]['ds'], dt)
    if start_stop_scanner:
        start_pos_x, start_speed_x, start_accel_x, t, A, start_safe_x = \
                set_position_and_speed(p_initial['col'], p0['col'], v_initial['col'], v0['col'], start_stop_time, dt, Amax = a_limits['col'], omit_last = True)
        start_pos_y, start_speed_y, start_accel_y, t, A, start_safe_y = \
                set_position_and_speed(p_initial['row'], p0['row'], v_initial['row'], v0['row'], start_stop_time, dt, Amax = a_limits['row'], omit_last = True)
        scan_signal_length_counter += start_pos_y.shape[0]
    for repeat_i in range(scanning_periods):
#        print scan_signal_length_counter
        counter_at_start_of_repeat = scan_signal_length_counter
        for line in lines:
            line_out = line
            #connect line's initial position with actual scanner position
            if line.has_key('v'):
                ds, n = calculate_spatial_resolution(line['p0'], line['p1'], line['v'], dt)
                v1, n = calculate_scanner_speed(line['p0'], line['p1'], ds, dt)
            else:
                v1, n = calculate_scanner_speed(line['p0'], line['p1'], line['ds'], dt)
                ds = line['ds']
            line_out['set_pos_x'], line_out['set_speed_x'], line_out['set_accel_x'], t, A, connect_line_x_safe = \
                                                    set_position_and_speed(p0['col'], line['p0']['col'], v0['col'], v1['col'], setting_time, dt, Amax = a_limits['col'], omit_last = True)
            line_out['set_pos_y'], line_out['set_speed_y'], line_out['set_accel_y'], t, A, connect_line_y_safe = \
                                                    set_position_and_speed(p0['row'], line['p0']['row'], v0['row'], v1['row'], setting_time, dt, Amax = a_limits['row'], omit_last = True)
            scan_signal_length_counter += line_out['set_pos_y'].shape[0]
            #Generate line scan
            line_out['scan_start_index'] = scan_signal_length_counter
            line_out['scan_pos_x'], line_out['scan_pos_y'], scanner_speed, scan_safe = generate_line_scan(line['p0'], line['p1'], ds, dt, v_limits)
            scan_signal_length_counter += line_out['scan_pos_y'].shape[0]
            line_out['scan_end_index'] = scan_signal_length_counter
            line_out['scan_speed_x'] = numpy.ones_like(line_out['scan_pos_x']) * scanner_speed['col']
            line_out['scan_speed_y'] = numpy.ones_like(line_out['scan_pos_y']) * scanner_speed['row']
            line_out['scan_accel_x'] = numpy.zeros_like(line_out['scan_pos_x'])
            line_out['scan_accel_y'] = numpy.zeros_like(line_out['scan_pos_y'])
            #Save final position and speed
            p0 = line['p1']
            v0 = scanner_speed
            #Gather scanner signals and notifications
            line_out['safe'] = [scan_safe, connect_line_x_safe, connect_line_y_safe]
            lines_out.append(line_out)
        period_time = (scan_signal_length_counter - counter_at_start_of_repeat) * dt
    #Connect final line scan with initial position to ensure scanner stopped correctly
    if start_stop_scanner:
        stop_pos_x, stop_speed_x, stop_accel_x, t, A, stop_safe_x = \
                set_position_and_speed(p0['col'], p_initial['col'], v0['col'], v_initial['col'], start_stop_time, dt, Amax = a_limits['col'], omit_last = True)
        stop_pos_y, stop_speed_y, stop_accel_y, t, A, stop_safe_y = \
                set_position_and_speed(p0['row'], p_initial['row'], v0['row'], v_initial['row'], start_stop_time, dt, Amax = a_limits['row'], omit_last = True)
        scan_signal_length_counter += stop_pos_y.shape[0]    #Concetanate scan signals
    pos_x = numpy.zeros(scan_signal_length_counter)
    pos_y = numpy.zeros_like(pos_x)
    speed_x = numpy.zeros_like(pos_x)
    speed_y = numpy.zeros_like(pos_x)
    accel_x = numpy.zeros_like(pos_x)
    accel_y = numpy.zeros_like(pos_x)
    scan_mask = numpy.zeros_like(pos_x)
    index = 0
    if start_stop_scanner:
        pos_x[index:index + start_pos_x.shape[0]] = start_pos_x
        pos_y[index:index + start_pos_y.shape[0]] = start_pos_y
        speed_x[index:index + start_speed_x.shape[0]] = start_speed_x
        speed_y[index:index + start_speed_y.shape[0]] = start_speed_y
        accel_x[index:index + start_accel_x.shape[0]] = start_accel_x
        accel_y[index:index + start_accel_y.shape[0]] = start_accel_y
        index += start_pos_y.shape[0]
    for line_out in lines_out:
        pos_x[index:index + line_out['set_pos_x'].shape[0]] = line_out['set_pos_x']
        pos_y[index:index + line_out['set_pos_y'].shape[0]] = line_out['set_pos_y']
        speed_x[index:index + line_out['set_speed_x'].shape[0]] = line_out['set_speed_x']
        speed_y[index:index + line_out['set_speed_y'].shape[0]] = line_out['set_speed_y']
        accel_x[index:index + line_out['set_accel_x'].shape[0]] = line_out['set_accel_x']
        accel_y[index:index + line_out['set_accel_y'].shape[0]] = line_out['set_accel_y']
        index += line_out['set_pos_y'].shape[0]
        pos_x[index:index + line_out['scan_pos_x'].shape[0]] = line_out['scan_pos_x']
        pos_y[index:index + line_out['scan_pos_y'].shape[0]] = line_out['scan_pos_y']
        scan_mask[index:index + line_out['scan_pos_y'].shape[0]] = numpy.ones_like(line_out['scan_pos_y'])
        speed_x[index:index + line_out['scan_speed_x'].shape[0]] = line_out['scan_speed_x']
        speed_y[index:index + line_out['scan_speed_y'].shape[0]] = line_out['scan_speed_y']
        accel_x[index:index + line_out['scan_accel_x'].shape[0]] = line_out['scan_accel_x']
        accel_y[index:index + line_out['scan_accel_y'].shape[0]] = line_out['scan_accel_y']
        index += line_out['scan_pos_y'].shape[0]
    if start_stop_scanner:
        pos_x[index:index + stop_pos_x.shape[0]] = stop_pos_x
        pos_y[index:index + stop_pos_y.shape[0]] = stop_pos_y
        speed_x[index:index + stop_speed_x.shape[0]] = stop_speed_x
        speed_y[index:index + stop_speed_y.shape[0]] = stop_speed_y
        accel_x[index:index + stop_accel_x.shape[0]] = stop_accel_x
        accel_y[index:index + stop_accel_y.shape[0]] = stop_accel_y
        index += stop_pos_y.shape[0]
    return pos_x, pos_y, speed_x, speed_y, accel_x, accel_y, scan_mask, period_time
    
def calculate_spatial_resolution(p0, p1, v, dt):
    line_length = abs(utils.rc_distance(p0, p1))
    time_of_flight = line_length / v
    number_of_points = time_of_flight / dt
    spatial_resolution = line_length / number_of_points
    return spatial_resolution, number_of_points

def calculate_scanner_speed(p0, p1, ds, dt):
    '''
    ds: um per step, um per pixel
    '''
    line_length = abs(utils.rc_distance(p0, p1))
    number_of_points = numpy.round((line_length / ds), 0)
    scanner_speed = utils.rc_multiply_with_constant(utils.rc_add(p1, p0, '-'),  1.0/(number_of_points * dt))
    return scanner_speed, number_of_points
    
def generate_line_scan(p0, p1, ds, dt, vmax):
    '''
    Generates line scan trajectories for both scanners
    p0, p1: line endpoints in row,col format
    '''
    if not hasattr(vmax, 'dtype'):
        v_limits = utils.rc((vmax, vmax))
    else:
        v_limits = vmax
    scanner_speed, number_of_points = calculate_scanner_speed(p0, p1, ds, dt)
    if v_limits['row'] > scanner_speed['row'] and v_limits['col'] > scanner_speed['col']:
        is_safe = True
    else:
        is_safe = False
    x_scanner_trajectory = numpy.linspace(p0['col'], p1['col'], number_of_points+1)
    y_scanner_trajectory = numpy.linspace(p0['row'], p1['row'], number_of_points+1)
    return x_scanner_trajectory[:-1], y_scanner_trajectory[:-1], scanner_speed, is_safe
   
def calculate_parameters(s0,s1,v0,v1,T):
    ds = s1-s0
    dv = v1-v0
    a = s0
    b = v0
    def_parameters = numpy.matrix([[T**3,T**4,T**5],[3*T**2,4*T**3,5*T**4],[3, 6*T, 10*T**2]])
    def_values = numpy.linalg.inv(def_parameters)*numpy.matrix([ds-v0*T, dv, 0]).T
    d,e,f = numpy.array(def_values).T[0].tolist()
    #Maximal speed
    vmax = []
    discr = 36*e**2-120*d*f
    if discr >= 0 and f != 0:
        tvmax1 = (-6*e - numpy.sqrt(discr))/(20*f)
        tvmax2 = (-6*e + numpy.sqrt(discr))/(20*f)
        if 0  <= tvmax1 and tvmax1 <= T:
            t = tvmax1
            vmax.append(b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4)
        if 0  <= tvmax2 and tvmax2 <= T:
            t = tvmax2
            vmax.append(b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4)
    #Maximal acceleration
    amax = []
    discr = 16*e**2-40*d*f
    if discr >= 0 and f != 0:
        tamax1 = (-4*e - numpy.sqrt(discr))/(20*f)
        tamax2 = (-4*e + numpy.sqrt(discr))/(20*f)
        if 0  <= tamax1 and tamax1 <= T:
            t = tamax1
            amax.append(6*d*t + 12*e*t**2 + 20*f*t**3)
        if 0  <= tamax2 and tamax2 <= T:
            t = tamax2
            amax.append(6*d*t + 12*e*t**2 + 20*f*t**3)
    return a,b,d,e,f, vmax, amax
    
def set_position_and_speed(s0, s1, v0, v1, T, dt, Amax = None, omit_last = False):
    t = numpy.linspace(0,T,T/dt+1)
    ds = s1-s0
    dv = v1-v0
    #Polinom parameters
    a,b,d,e,f,vmax, amax = calculate_parameters(s0,s1,v0,v1,T)
    s = a + b*t + d*t**3 + e*t**4 + f*t**5
    v = b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4
    a = 6*d*t + 12*e*t**2 + 20*f*t**3
    A = abs(a).max()
    is_safe  = True
    if omit_last:
        t = t[:-1]
        s = s[:-1]
        v = v[:-1]
        a = a[:-1]
    return s, v, a, t, A, is_safe

########## Helpers ##################
def time_vector(T, dt):
    return numpy.linspace(0.0,T,T/dt+1)

def plot_a_v_s(a, v, s, t):
    from matplotlib.pyplot import plot, show,figure,legend
    plot(t,a)
    plot(t,v)
    plot(t,s)
    legend(['a','v','s'])
    show()
    
class TwoPhotonScanner(instrument.Instrument):
    def init_instrument(self):
        self.shutter = daq_instrument.DigitalIO(self.config, id=1)
        self.aio = daq_instrument.AnalogIO(self.config)
        self.binning_factor = float(self.aio.daq_config['AI_SAMPLE_RATE'])/self.aio.daq_config['AO_SAMPLE_RATE']
        if self.binning_factor != numpy.round(self.binning_factor, 0):
            raise RuntimeError('AI sample rate must be the multiple of AO sample rate')
        else:
            self.binning_factor = int(self.binning_factor)
            
    def start_measurement(self, scanner_x, scanner_y,  trigger = None):
        #Convert from position to voltage
        self.scanner_positions = numpy.array([scanner_x, scanner_y])
        if trigger is not None:
            self.scanner_control_signal = numpy.array([scanner_x + self.config.XMIRROR_OFFSET, scanner_y + self.config.YMIRROR_OFFSET,  trigger/self.config.POSITION_TO_SCANNER_VOLTAGE]) * self.config.POSITION_TO_SCANNER_VOLTAGE
        else:
            self.scanner_control_signal = numpy.array([scanner_x + self.config.XMIRROR_OFFSET, scanner_y + self.config.YMIRROR_OFFSET]) * self.config.POSITION_TO_SCANNER_VOLTAGE
        self._set_scanner_voltage(utils.cr((0.0, 0.0)), utils.cr(self.scanner_control_signal[:2,0]), self.config.SCANNER_RAMP_TIME, self.config.SCANNER_HOLD_TIME,  trigger = trigger)
        self.aio.waveform = self.scanner_control_signal.T
        self.data = []
        self.pmt_raw = []
        self.frame_rate = float(self.aio.daq_config['AO_SAMPLE_RATE'])/self.scanner_positions.shape[1]
        self.boundaries = numpy.nonzero(numpy.diff(self.scan_mask))[0]+1
        self.open_shutter()
        self.aio.start_daq_activity()
        
    def _set_scanner_voltage(self, initial_voltage, target_voltage, ramp_time, hold_time = 0, trigger = None):
        ramp_samples = int(self.aio.daq_config['AO_SAMPLE_RATE']*ramp_time)
        hold_samples = int(self.aio.daq_config['AO_SAMPLE_RATE']*hold_time)
        scanner_x_waveform = target_voltage['col'] * numpy.ones(ramp_samples + hold_samples)
        scanner_x_waveform[:ramp_samples] = numpy.linspace(initial_voltage['col'], target_voltage['col'], ramp_samples)
        scanner_y_waveform = target_voltage['row'] * numpy.ones(ramp_samples + hold_samples)
        scanner_y_waveform[:ramp_samples] = numpy.linspace(initial_voltage['row'], target_voltage['row'], ramp_samples)
        self.config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'finite'
        if self.aio.number_of_ao_channels == 3:
            self.aio.waveform = numpy.array([scanner_x_waveform, scanner_y_waveform, numpy.zeros_like(scanner_y_waveform)]).T
        elif trigger is None or self.aio.number_of_ao_channels == 2:
            self.aio.waveform = numpy.array([scanner_x_waveform, scanner_y_waveform]).T
        self.aio.run()
        self.config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        
    def start_rectangular_scan(self, size, position = utils.rc((0, 0)), spatial_resolution = 1.0, setting_time = None,  trigger_signal_config = None):
        '''
        spatial_resolution: pixel size in um
        '''
        if setting_time == None:
            setting_time = self.config.SCANNER_SETTING_TIME
        pos_x, pos_y, self.scan_mask, accel_speed, result = generate_rectangular_scan(size, position, spatial_resolution, 1, setting_time, self.config)
        if not result:
            raise RuntimeError('Scanning pattern is not feasable')
        self.is_rectangular_scan = True
        if trigger_signal_config is None:
            self.trigger_signal = None
        else:
            self._scan_mask2trigger(trigger_signal_config['offset'], trigger_signal_config['width'], trigger_signal_config['amplitude'])
        self.start_measurement(pos_x, pos_y, self.trigger_signal)
        
    def start_line_scan(self, lines, setting_time = None, trigger_signal_config = None):
        if setting_time == None:
            setting_time = self.config.SCANNER_SETTING_TIME
        pos_x, pos_y, self.scan_mask, accel_speed, result = generate_lines_scan(lines, setting_time, 1, self.config)
        if not result:
            raise RuntimeError('Scanning pattern is not feasable')
        self.is_rectangular_scan = False
        if trigger_signal_config is None:
            self.trigger_signal = None
        else:
            self._scan_mask2trigger(trigger_signal_config['offset'], trigger_signal_config['width'], trigger_signal_config['amplitude'])
        self.start_measurement(pos_x, pos_y, self.trigger_signal)
        
    def _scan_mask2trigger(self,  offset,  width,  amplitude):
        '''
        Converts scan mask to trigger signal that controls the projector
        '''
        trigger_mask = numpy.logical_not(numpy.cast['bool'](self.scan_mask))
        offset_samples = int(numpy.round(self.aio.daq_config['AO_SAMPLE_RATE'] * offset))
        width_samples = int(numpy.round(self.aio.daq_config['AO_SAMPLE_RATE'] * width))
        if trigger_mask[0]:#Consider if the first item is True, consequenctly it cannot be detected as a rising edge
            edge_offset = 1
        else:
            edge_offset = 0
        trigger_rising_edges = numpy.nonzero(numpy.diff(trigger_mask))[0][edge_offset::2]+offset_samples
        if trigger_mask[0]:
            trigger_rising_edges = trigger_rising_edges.tolist()
            trigger_rising_edges.insert(0, 0)
            trigger_rising_edges = numpy.array(trigger_rising_edges)
        high_value_indexes = (numpy.array([range(width_samples)]*trigger_rising_edges.shape[0])+numpy.array([trigger_rising_edges.tolist()]*width_samples).T).flatten()
        self.trigger_signal = numpy.zeros_like(trigger_mask, dtype = numpy.float64)
        self.trigger_signal[high_value_indexes] = amplitude
        self.trigger_signal *= trigger_mask
        
    def read_pmt(self):
        #This function shal run in the highest priority process
        raw_pmt_data = self.aio.read_analog()
        self.pmt_raw.append(raw_pmt_data)
        
    def finish_measurement(self):
        self.aio.finish_daq_activity()
        self.close_shutter()
        #value of ao at stopping continous generation is unknown
        self._set_scanner_voltage(utils.cr((0.0, 0.0)), utils.cr((0.0, 0.0)), self.config.SCANNER_RAMP_TIME)
        #Gather measurment data
        self.data = numpy.array([self._raw2frame(raw_pmt_data) for raw_pmt_data in self.pmt_raw])#dimension: time, height, width, channels
        
    def _raw2frame(self, rawdata):
        binned_pmt_data = self._binning_data(rawdata, self.binning_factor)
        return numpy.array((numpy.split(binned_pmt_data, self.boundaries)[1::2]))
        
    def open_shutter(self):
        self.shutter.set()
        
    def close_shutter(self):
        self.shutter.clear()
        
    def close_instrument(self):
        self.aio.release_instrument()
        self.shutter.release_instrument()
        
    ####### Helpers #####################
    def _binning_data(self, data, factor):
        return numpy.reshape(data, (data.shape[0]/factor, factor, data.shape[1])).mean(1)
        
def generate_test_lines(scanner_range, repeats, speeds):
    lines1 = [
                 {'p0': utils.rc((0.5*scanner_range, 0)), 'p1': utils.rc((-0.5*scanner_range, 0))}, 
                 {'p0': utils.rc((-0.5*scanner_range, 0)), 'p1': utils.rc((0.5*scanner_range, 0))}, 
                 ]
    lines2 = [
                 {'p0': utils.rc((0, 0.5*scanner_range)), 'p1': utils.rc((0, -0.5*scanner_range))}, 
                 {'p0': utils.rc((0, -0.5*scanner_range)), 'p1': utils.rc((0, 0.5*scanner_range))}, 
                 ]
    line_patterns = [lines1, lines2]
    lines = []
    for speed in speeds:
        for line_pattern in line_patterns:
            for repeat in range(repeats):
                for line in line_pattern:
                    import copy
                    line_to_add = copy.copy(line)
                    line_to_add['v'] = speed
                    lines.append(line_to_add)
        
    return lines

class TestScannerControl(unittest.TestCase):
    def setUp(self):
        self.dt = 1e-3
        
    def test_01_set_position_and_speed(self):
        inputs = [
                  {'s0': 1.0, 's1': 0.0,'v0':0.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 0.0, 's1': 0.0,'v0':-2.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 100.0, 's1': -100.0,'v0':2.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 100.0, 's1': 200.0,'v0':2.0, 'v1':12.0,  'T': 1.0}, 
                  {'s0': 0.0, 's1': 100.0,'v0':10.0, 'v1':1.0,  'T': 0.1}, 
                  {'s0': 0.0, 's1': -100.0,'v0':100.0, 'v1':0.0,  'T': 1.0}, 
                  ]
        results = []
        max_error = 1e-5
        for input in inputs:
            s0 = input['s0']
            s1 = input['s1']
            v0 = input['v0']
            v1 = input['v1']
            T = input['T']
            s, v, a, t, A, issafe = set_position_and_speed(s0, s1, v0, v1, T, self.dt)
#            plot_a_v_s(a, v, s, t)
            ds_error = s1-s0 - (s[-1]-s[0])
            if ds_error < max_error:
                ds_error = 0.0
            dv_error = (v0-v1) - (v[0]-v[-1])
            if dv_error < max_error:
                dv_error = 0.0
            max_acceleration_error = abs(a).max() - A
            if max_acceleration_error < max_error:
                max_acceleration_error = 0.0
            results.append([ds_error, dv_error, numpy.round(a[0],8), numpy.round(a[-1],8),  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
        
    def test_02_set_speed_position_withmax_acceleration(self):
        inputs = [
                  {'s0': 1.0, 's1': 0.0,'v0':0.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 0.0, 's1': 0.0,'v0':-2.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 100.0, 's1': -100.0,'v0':2.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 100.0, 's1': 200.0,'v0':2.0, 'v1':12.0,  'T': 1.0}, 
                  {'s0': 0.0, 's1': 100.0,'v0':10.0, 'v1':1.0,  'T': 0.1}, 
                  {'s0': 0.0, 's1': -100.0,'v0':100.0, 'v1':0.0,  'T': 1.0}, 
                  {'s0': 0.0, 's1': 100.0,'v0':0.0, 'v1':100.0,  'T': 1.0}, 
                  ]
        results = []
        max_error = 1e-5
        for input in inputs:
            s0 = input['s0']
            s1 = input['s1']
            v0 = input['v0']
            v1 = input['v1']
            T = input['T']
            s, v, a, t, A, is_safe = set_position_and_speed(s0, s1, v0, v1, T, self.dt, Amax = 1000)
#            print is_safe
#            plot_a_v_s(a, v, s, t)
            ds_error = s1-s0 - (s[-1]-s[0])
            if ds_error < max_error:
                ds_error = 0.0
            dv_error = (v0-v1) - (v[0]-v[-1])
            if dv_error < max_error:
                dv_error = 0.0
            max_acceleration_error = abs(a).max() - A
            if max_acceleration_error < max_error:
                max_acceleration_error = 0.0
            results.append([ds_error, dv_error, numpy.round(a[0],8), numpy.round(a[-1],8),  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
        
    @unittest.skip('Run only for debug purposes')
    def test_03_generate_line_scans(self):
        plot_enable = False
        lines = [
                 {'p0': utils.rc((0, -10)), 'p1': utils.rc((0, 10)), 'ds': 1.0}, 
                 {'p0': utils.rc((10, -10)), 'p1': utils.rc((10, 10)), 'ds': 1.0}, 
#                 {'p0': utils.rc((20, -10)), 'p1': utils.rc((20, 10)), 'ds': 1.0}, 
#                 {'p0': utils.rc((30, 10)), 'p1': utils.rc((30, -10)), 'ds': 1.0}, 
                 ]
#        lines = [
#                 {'p0': utils.rc((0,0)), 'p1': utils.rc((10, 10)), 'ds': 1.0}, 
#                 {'p0': utils.rc((0,0)), 'p1': utils.rc((10, 10)), 'ds': 1.0}, 
#                 ]

        setting_time = 0.02
        start_stop_time = 0.02
        accmax = 100000
        vmax = 5000
        pos_x, pos_y, speed_x, speed_y, accel_x, accel_y, scan_mask, period_time = generate_line_scan_series(lines, self.dt, setting_time, vmax, accmax, scanning_periods = 2, start_stop_scanner = True, start_stop_time = start_stop_time)
        if plot_enable:
            print period_time
            print abs(pos_x).max(), abs(pos_y).max(), abs(speed_x).max(), abs(speed_y).max(), abs(accel_x).max(), abs(accel_y).max()
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
            figure(1)
            subplot(411)
            plot(pos_x)
            plot(pos_y)
            title('position')
            subplot(413)
            plot(speed_x)
            plot(speed_y)
            title('speed')
            subplot(414)
            plot(accel_x)
            plot(accel_y)
            title('acceleration')
            subplot(412)
            plot(scan_mask)
            title('scan mask')
    #        show()
    #        savefig('/home/zoltan/visexp/debug/data/x.pdf')
    
    @unittest.skip('Run only for debug purposes')
    def test_04_generate_rectangular_scan(self):
        plot_enable = not False
        config = ScannerTestConfig()
        spatial_resolution = 20.0
        position = utils.rc((0, 0))
        size = utils.rc((100, 100))
        setting_time = 0.00005
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        if plot_enable:
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
            figure(2)
            subplot(411)
            plot(pos_x)
            plot(pos_y)
            title('position')
            subplot(413)
            plot(speed_and_accel['speed_x'])
            plot(speed_and_accel['speed_y'])
            title('speed')
            subplot(414)
            plot(speed_and_accel['accel_x'])
            plot(speed_and_accel['accel_y'])
            title('acceleration')
            subplot(412)
            plot(scan_mask)
            title('scan mask')
            show()
            
#    @unittest.skip('Run only for debug purposes')
    def test_05_twophoton(self):
        import time
        plot_enable = not False
        config = ScannerTestConfig()
        config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'aio'
        config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 250000
        config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 500000
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai0:1'
        config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        lines = [
                 {'p0': utils.rc((50, 0)), 'p1': utils.rc((-50, 0)), 'v': 1000.0}, 
                 {'p0': utils.rc((-50, 0)), 'p1': utils.rc((50, 0)), 'v': 1000.0}, 
                 ]
        lines = generate_test_lines(100, 1, [500, 1000, 2000, 4000])
        tp = TwoPhotonScanner(config)
#        tp.start_rectangular_scan(utils.rc((100, 100)), spatial_resolution = 1.0, setting_time = 0.3e-3)
        tp.start_line_scan(lines, setting_time = 20e-3)
        for i in range(1):
            tp.read_pmt()
        tp.finish_measurement()
        tp.release_instrument()
        #Image.fromarray(normalize(tp.images[0][:,:,0],numpy.uint8)).save('v:\\debug\\pmt1.png')
        if plot_enable:
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
            figure(1)
            plot(tp.pmt_raw[0])
            figure(2)
            plot(tp.data[0][0][:,0])
            plot(tp.data[0][0][:,1])
            figure(3)
            plot(tp.data[0][1][:,0])
            plot(tp.data[0][1][:,1])
            figure(4)
            plot(tp.scanner_positions.T)
            show()
            
    @unittest.skip('Run only for debug purposes')
    def test_06_calibrate_scanner_parameters(self):
        import time
        plot_enable = not False
        config = ScannerTestConfig()
        config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'aio'
        config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 250000
        config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 500000
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unit_test_runner.TEST_daq_device + '/ai0:1'
        config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        lines = generate_test_lines(100, 1, [300, 600, 1000, 2000, 4000])
        tp = TwoPhotonScanner(config)
        tp.start_line_scan(lines, setting_time = 40e-3)
        tp.read_pmt()
        tp.finish_measurement()
        tp.release_instrument()
        if plot_enable:
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
            figure(1)
            plot(tp.pmt_raw[0])
            figure(4)
            plot(tp.scanner_positions.T)
            show()
        
    def _ramp(self):
        waveform = numpy.linspace(0.0, 1.0, 10000)
        waveform = numpy.array([waveform, waveform])
        waveform[1, :] =1*waveform[1, :]
        waveform[:, -1] = numpy.zeros(2)
        waveform[:, -2] = numpy.zeros(2)
        waveform[:, -3] = numpy.zeros(2)
        return waveform.T
        
if __name__ == "__main__":
    unittest.main()
