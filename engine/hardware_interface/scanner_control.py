'''
Setting scanner position and speed

Factors limiting setting time:
- maximal acceleration - Tmin
- maximal speed - Tmin

Extreme setting: big movement, short setting time, big speed change

Parameters:
        self.SCANNER_MAX_SPEED = utils.rc((1e7, 1e7))#um/s
        self.SCANNER_MAX_ACCELERATION = utils.rc((1e12, 1e12)) #um/s2
        self.SCANNER_SIGNAL_SAMPLING_RATE = 250000 #Hz
        self.SCANNER_DELAY = 0#As function of scanner speed
        self.SCANNER_START_STOP_TIME = 0.02 #speed up and down times at the beginning/end of scan pattern
        self.SCANNER_MAX_POSITION = 200.0 #Maximum allowed amplitude of scanner
        self.POSITION_TO_SCANNER_VOLTAGE = 2.0/128.0 #Maximum voltage range/ scanned range in um
        self.XMIRROR_OFFSET = 0.0#um
        self.YMIRROR_OFFSET = 0.0#um
        self.SCANNER_RAMP_TIME = 70.0e-3#Time to move the scanners into initial position
        self.SCANNER_HOLD_TIME = 30.0e-3
        self.SCANNER_SETTING_TIME = 1e-3#This is the time constraint to set the speed of scanner (lenght of transient)
        self.PMTS = {'TOP': {'AI': 0,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'AI': 1,  'COLOR': 'RED', 'ENABLE': False}}

'''
#eliminate position and speed overshoots - not possible
import numpy
import scipy.io
import time
import copy
import os.path
import scipy.optimize
import traceback
import daq_instrument
import instrument
import os
if os.name=='nt':
    try:
        import PyDAQmx
    except ImportError:
        pass
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import log
from visexpman.engine.generic import configuration
from visexpman.engine.generic import command_parser
from visexpman.engine.vision_experiment import experiment_data

try:
    from visexpman.users.test import unittest_aggregator    
except IOError:
    pass

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
        'AO_SAMPLE_RATE' : 400000,
        'AI_SAMPLE_RATE' : 800000,
        'AO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ao0:1',
        'AI_CHANNEL' : unittest_aggregator.TEST_daq_device + '/ai0:2',
        'MAX_VOLTAGE' : 3.0,
        'MIN_VOLTAGE' : -3.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        {
        'DAQ_TIMEOUT' : 1.0, 
        'DO_CHANNEL' : unittest_aggregator.TEST_daq_device + '/port0/line0',
        'ENABLE' : True
        }
        ]
        self._create_parameters_from_locals(locals())
        
def spectral_filtering(signal, fmax, fsample):
    '''
    The spectral components below fmax are used to reconstruct the bandwidth limited version of the signal
    '''
    import scipy
    import scipy.fftpack
    t = numpy.linspace(0,  float(signal.shape[0])/fsample, signal.shape[0], False)
    spectrum = scipy.fft(signal)
    phases = numpy.angle(spectrum)
    spectrum = abs(spectrum)/spectrum.shape[0]
    frq = scipy.fftpack.fftfreq(signal.shape[0], 1.0/fsample)
    peaks = []
    for i in range(1, spectrum.size/2):
            if frq[i] > fmax:
                break
            peaks.append([spectrum[i], frq[i], phases[i]])
    #Generate a signal from the components
    x = numpy.zeros_like(signal)
    for peak in peaks:
        A = peak[0]
        f = peak[1]
        ph = peak[2]
        x += 2*A*numpy.cos(t*2*numpy.pi*f + ph)
    x += 1*spectrum[0]
    return t, x
        
def sinus_pattern_rectangle_scan(scan_size, scan_center = utils.rc((0, 0)), resolution = 1.0, max_linearity_error = 19e-2, fsampling = 400000.0, backscan = True):
    '''
    Generates scanner signals for rectangular scan that contain only sinusoid signals, therefore it does not contain upharmonic components. 
    The highest frequency is the swinging of the x mirror
    '''
    if backscan:
        scanning_per_period = 2
    else:
        scanning_per_period = 1
    nlines = float(scan_size['row']/resolution)#Number of pixel in vertical size of scan area
    pixels_x_line = float(scan_size['col']/resolution)#Number of scannable pixels in each horizontal line
    pixels_y_line = pixels_x_line * nlines
    n_effective_sinus_periods_on_x = numpy.round(nlines / float(scanning_per_period))
    #Calculate effective angle range in a period of sinus with the given error limit:
    angle_range = utils.sinus_linear_range(max_linearity_error)
    efficiency  = 2*angle_range/(numpy.pi*2)#90-angle, 90+angle is considered, This is doubled by backscan but this factor is not required to scale up period times
    time_scaleup = numpy.ceil(1/efficiency) #Rounding is necessary to ensure integer frequency ratio and period time can be converted into samples
    #Calculate period time of sine wave on x mirror based on efficiency, number of pixel per horizontal line and signal generation sampling frequency
    scanner_period_time = {}
    scanner_period_time['x'] = (pixels_x_line / fsampling) * time_scaleup
    #Calculate period time of sine wave on y mirror: effective scanning takes: period time of one x line scan X number of lines
    scanner_period_time['y'] = (n_effective_sinus_periods_on_x * scanner_period_time['x']) * time_scaleup
    frequency_ratio = scanner_period_time['y'] / scanner_period_time['x']
    #Frequency ratio shall be dividable by 4
    modified_frequency_ratio = numpy.ceil(frequency_ratio/4.0)*4
    scanner_period_time['y'] = scanner_period_time['y'] * modified_frequency_ratio / frequency_ratio
    nsinus_periods_on_x = modified_frequency_ratio
    #Generate sine waves for x and y mirrors
    scanner_control = {}
    t = {}
    t['y'] = numpy.arange(0, scanner_period_time['y'],  1.0/fsampling)
    scanner_control['y'] = numpy.cos(t['y']/scanner_period_time['y']*2*numpy.pi)
    t['x'] = numpy.arange(0, scanner_period_time['y'],  1.0/fsampling)
    scanner_control['x'] = numpy.cos(t['y']/scanner_period_time['x']*2*numpy.pi)
    #Find and mark linear regions on y mirror signal
    #Find index range of sine periods that fall within the linear range of y mirror movement
    linearity_mask = {}
    linearity_mask['y'] = numpy.zeros(scanner_control['y'].shape, numpy.bool)
    for center in [nsinus_periods_on_x/4, 3*nsinus_periods_on_x/4]:
        index_range = numpy.array([center - n_effective_sinus_periods_on_x/2, center + n_effective_sinus_periods_on_x/2])*scanner_period_time['x']*fsampling
        linearity_mask['y'][index_range[0]:index_range[1]] = True
    #Find linear region of x scanner signals
    sample_step = scanner_period_time['x']/scanning_per_period*fsampling#number of sample distance between adjacent linear regions
    centers = numpy.arange(nsinus_periods_on_x*scanning_per_period)*sample_step + numpy.floor(scanner_period_time['x']*fsampling/4)#Phase shift with 1/4 period (pi/2)
    linearity_mask['x'] = numpy.zeros(scanner_control['x'].shape, numpy.bool)
    for center in centers:
        linearity_mask['x'][center - pixels_x_line/2:center + pixels_x_line/2] = True
    mask = linearity_mask['x']*linearity_mask['y']
    #Scale amplitude to scannable size
    scanner_control['x'] = scan_size['col']*scanner_control['x']/abs(scanner_control['x']*mask).max()+scan_center['col']
    scanner_control['y'] = scan_size['row']*scanner_control['y']/abs(scanner_control['y']*mask).max()+scan_center['row']
    frame_rate = 2/scanner_period_time['y']
    time_efficiency = float(mask.sum())/scanner_control['y'].shape[0]
    return scanner_control, mask, frame_rate, scanner_period_time, time_efficiency
    
def frame_from_sinus_pattern_scan(pmt, mask, backscan, binning_factor):
    '''
    Generates 2D data from one scanning period of a sinusoidal scan
    pmt: rawdata from one scanning period
    mask: valid data mask
    backscan: is data on backscan
    binning factor: ratio of ai and ao sampling rate
    '''
    binned_pmt = binning_data(pmt, binning_factor)
    nframes = 2
    nchannels = binned_pmt.shape[1]
    boundaries = numpy.nonzero(numpy.diff(mask))[0]+1
    line_starts = boundaries[0::2]
    line_ends = boundaries[1::2]
    frames = []
    frame = numpy.zeros((nframes, line_starts.shape[0]/nframes, line_ends[0]-line_starts[0], nchannels))
    two_frames = numpy.array((numpy.split(binned_pmt, boundaries)[1::2]))
    if backscan:
        two_frames[::2,:,:] = numpy.roll(two_frames[::2,:,:][:,::-1], 0, axis=1)#Reverse every second row, starting with the first one
    #Reverse row order of first frame
    nlines = line_starts.shape[0]/nframes
    two_frames[:nlines,:,:] = two_frames[:nlines,:,:][::-1]
    frame = numpy.reshape(two_frames, frame.shape)
    
#    from visexpman.engine.generic.colors import imsave
#
#    imsave(frame[0,:,:,0], '/mnt/datafast/debug/fr0ch0.png')
#    imsave(frame[0,:,:,1], '/mnt/datafast/debug/fr0ch1.png')
#    imsave(frame[1,:,:,0], '/mnt/datafast/debug/fr1ch0.png')
#    imsave(frame[1,:,:,1], '/mnt/datafast/debug/fr1ch1.png')

    return frame
    
                             
                             
#############################################
        
def generate_lines_scan(lines, setting_time, frames_to_scan, config):
    start_stop_scanner = False
    dt = 1.0/config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
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
    dt = 1.0/config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
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
    if isinstance(setting_time, list):
        setting_time_x = setting_time[0]
        setting_time_y = setting_time[1]
    else:
        setting_time_x = setting_time
        setting_time_y = setting_time
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
        line_counter = 0
        for line in lines:
            line_out = line
            #connect line's initial position with actual scanner position
            if line.has_key('v'):
                ds, n = calculate_spatial_resolution(line['p0'], line['p1'], line['v'], dt)
                v1, n = calculate_scanner_speed(line['p0'], line['p1'], ds, dt)
            else:
                v1, n = calculate_scanner_speed(line['p0'], line['p1'], line['ds'], dt)
                ds = line['ds']
            if line_counter == 0 and setting_time_y > 2*setting_time_x :
                #Stopping x mirror
                intermediate_x_position = p0['col'] - 0.5*(p0['col'] - line['p0']['col'])
                set_pos_x1, set_speed_x1, set_accel_x1, t, A, connect_line_x_safe1 = \
                                                        set_position_and_speed(p0['col'], intermediate_x_position, v0['col'], 0.0, setting_time_x, dt, Amax = a_limits['col'], omit_last = True)
                set_pos_y1, set_speed_y1, set_accel_y1, t, A, connect_line_y_safe1 = \
                                                        set_position_and_speed(p0['row'], p0['row'], v0['row'], v0['row'], setting_time_x, dt, Amax = a_limits['row'], omit_last = True)
                #Setting y mirror
                set_pos_x2, set_speed_x2, set_accel_x2, t, A, connect_line_x_safe2 = \
                                                        set_position_and_speed(intermediate_x_position, intermediate_x_position, 0.0, 0.0, setting_time_y - 2*setting_time_x, dt, Amax = a_limits['col'], omit_last = True)
                set_pos_y2, set_speed_y2, set_accel_y2, t, A, connect_line_y_safe2 = \
                                                        set_position_and_speed(p0['row'], line['p0']['row'], v0['row'], v1['row'], setting_time_y - 2*setting_time_x, dt, Amax = a_limits['row'], omit_last = True)
                #Setting x mirror
                set_pos_x3, set_speed_x3, set_accel_x3, t, A, connect_line_x_safe3 = \
                                                        set_position_and_speed(intermediate_x_position, line['p0']['col'], 0.0, v1['col'], setting_time_x, dt, Amax = a_limits['col'], omit_last = True)
                set_pos_y3, set_speed_y3, set_accel_y3, t, A, connect_line_y_safe3 = \
                                                        set_position_and_speed(line['p0']['row'], line['p0']['row'], v1['row'], v1['row'], setting_time_x, dt, Amax = a_limits['row'], omit_last = True)

                line_out['set_pos_x'] = numpy.concatenate((set_pos_x1, set_pos_x2, set_pos_x3))
                line_out['set_pos_y'] = numpy.concatenate((set_pos_y1, set_pos_y2, set_pos_y3))
                line_out['set_speed_x'] = numpy.concatenate((set_speed_x1, set_speed_x2, set_speed_x3))
                line_out['set_speed_y'] = numpy.concatenate((set_speed_y1, set_speed_y2, set_speed_y3))
                line_out['set_accel_x'] = numpy.concatenate((set_accel_x1, set_accel_x2, set_accel_x3))
                line_out['set_accel_y'] = numpy.concatenate((set_accel_y1, set_accel_y2, set_accel_y3))
                connect_line_x_safe = (connect_line_x_safe1 and connect_line_x_safe2 and connect_line_x_safe3)
                connect_line_y_safe = (connect_line_y_safe1 and connect_line_y_safe2 and connect_line_y_safe3)
            else:
                line_out['set_pos_x'], line_out['set_speed_x'], line_out['set_accel_x'], t, A, connect_line_x_safe = \
                                                        set_position_and_speed(p0['col'], line['p0']['col'], v0['col'], v1['col'], setting_time_x, dt, Amax = a_limits['col'], omit_last = True)
                line_out['set_pos_y'], line_out['set_speed_y'], line_out['set_accel_y'], t, A, connect_line_y_safe = \
                                                        set_position_and_speed(p0['row'], line['p0']['row'], v0['row'], v1['row'], setting_time_x, dt, Amax = a_limits['row'], omit_last = True)
            line_counter += 1
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
    scanner_speed = utils.rc_x_const(utils.rc_add(p1, p0, '-'),  1.0/(number_of_points * dt))
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
        import visexpman
        self.load_calibdata(os.path.join(os.path.split(visexpman.__file__)[0], 'data', 'calibration', 'image_offset_calibration.hdf5'))
            
    def start_measurement(self, scanner_x, scanner_y, stimulus_trigger, frame_trigger):
        #Convert from position to voltage
        self.scanner_positions = numpy.array([scanner_x, scanner_y])
        self.scanner_control_signal = \
            numpy.array([scanner_x + self.config.XMIRROR_OFFSET, scanner_y + self.config.YMIRROR_OFFSET, stimulus_trigger/self.config.POSITION_TO_SCANNER_VOLTAGE, frame_trigger/self.config.POSITION_TO_SCANNER_VOLTAGE]) * self.config.POSITION_TO_SCANNER_VOLTAGE
        self._set_scanner_voltage(utils.cr((0.0, 0.0)), utils.cr(self.scanner_control_signal[:2,0]), self.config.SCANNER_RAMP_TIME, self.config.SCANNER_HOLD_TIME,  trigger = stimulus_trigger)
        self.aio.waveform = self.scanner_control_signal.T
        self.data = []
        self.pmt_raw = []
        #calculate scanning parameters
        self.frame_rate = float(self.aio.daq_config['AO_SAMPLE_RATE'])/self.scanner_positions.shape[1]
        self.scanner_time_efficiency = self.scan_mask.sum()/self.scan_mask.shape[0]
        #Calculate scanner phase shift
        if False:
            self.phase_shift, error = calculate_phase_shift(scanner_x, self.scan_mask, self.config)
        else:
            self.phase_shift = 0
        if hasattr(self, 'accel_speed'):
            #calculate speeds
            self.speeds = {}
            for axis in ['x', 'y']:
                self.speeds[axis] = {}
                self.speeds[axis]['max'] = abs(self.accel_speed['speed_'+axis]).max()
                if axis =='x':
                    speeds = abs(self.accel_speed['speed_'+axis])*self.scan_mask
                    self.speeds[axis]['scan'] = speeds[numpy.nonzero(speeds)[0]].mean()
        #calculate maximal movement on x axis
        self.maximal_movement = scanner_x.max() - scanner_x.min()
        if hasattr(self.scan_mask, 'dtype'):
            self.boundaries = numpy.nonzero(numpy.diff(self.scan_mask))[0]+1
        self.open_shutter()
        self.aio.start_daq_activity()
        
    def _set_scanner_voltage(self, initial_voltage, target_voltage, ramp_time, hold_time = 0, trigger=None):
        ramp_samples = int(self.aio.daq_config['AO_SAMPLE_RATE']*ramp_time)
        hold_samples = int(self.aio.daq_config['AO_SAMPLE_RATE']*hold_time)
        scanner_x_waveform = target_voltage['col'] * numpy.ones(ramp_samples + hold_samples)
        scanner_x_waveform[:ramp_samples] = numpy.linspace(initial_voltage['col'], target_voltage['col'], ramp_samples)
        scanner_y_waveform = target_voltage['row'] * numpy.ones(ramp_samples + hold_samples)
        scanner_y_waveform[:ramp_samples] = numpy.linspace(initial_voltage['row'], target_voltage['row'], ramp_samples)
        self.config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'finite'
        if self.aio.number_of_ao_channels == 4:
            self.aio.waveform = numpy.array([scanner_x_waveform, scanner_y_waveform, numpy.zeros_like(scanner_y_waveform), numpy.zeros_like(scanner_y_waveform)]).T
        else:
            raise RuntimeError('Analog output channel configuration incorrect')
        self.aio.run()
        self.config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        
    def start_sinus_pattern_rectangular_scan(self, scan_size, scan_center = utils.rc((0, 0)), resolution = 1.0, max_linearity_error = 19e-2, backscan = True):
        scanner_control, self.scan_mask, frame_rate, self.scanner_period_time, time_efficiency =\
            sinus_pattern_rectangle_scan(scan_size, scan_center, resolution, max_linearity_error, fsampling = self.aio.daq_config['AO_SAMPLE_RATE'], backscan = backscan)
        self.sinus_pattern = True
        self.backscan = backscan
        self.start_measurement(scanner_control['x'], scanner_control['y'])
        
    def start_rectangular_scan(self, size, position = utils.rc((0, 0)), spatial_resolution = 1.0, setting_time = None,  trigger_signal_config = None):
        '''
        spatial_resolution: pixel size in um
        '''
        if setting_time == None:
            setting_time = self.config.SCANNER_SETTING_TIME
        pos_x, pos_y, self.scan_mask, self.accel_speed, result = generate_rectangular_scan(size, position, spatial_resolution, 1, setting_time, self.config)
        if not result:
            raise RuntimeError('Scanning pattern is not feasable')
        self.image_offset = self.get_image_offset(size['col'], 1.0/spatial_resolution)
        self.is_rectangular_scan = True
        if trigger_signal_config is None or not trigger_signal_config['enable']:
            self.trigger_signal = numpy.zeros_like(self.scan_mask)
        else:
            self.trigger_signal = scan_mask2trigger(self.scan_mask, trigger_signal_config['offset'], trigger_signal_config['width'], trigger_signal_config['amplitude'], self.aio.daq_config['AO_SAMPLE_RATE'])
        self.frame_trigger = generate_frame_trigger(self.scan_mask,self.config.CA_FRAME_TRIGGER_AMPLITUDE)
        self.start_measurement(pos_x, pos_y, self.trigger_signal, self.frame_trigger)
        
    def start_line_scan(self, lines, setting_time = None, trigger_signal_config = None, filter = None):
        if setting_time == None:
            setting_time = self.config.SCANNER_SETTING_TIME
        pos_x, pos_y, self.scan_mask, self.accel_speed, result = generate_lines_scan(lines, setting_time, 1, self.config)
        if filter is not None and filter['enable_fft_filter']:
            t, pos_x = spectral_filtering(pos_x, filter['bandwidth'], self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])
            t, pos_y = spectral_filtering(pos_y, filter['bandwidth'], self.config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])
        if not result:
            raise RuntimeError('Scanning pattern is not feasable')
        self.is_rectangular_scan = False
        if trigger_signal_config is None:
            self.trigger_signal = numpy.zeros_like(self.scan_mask)
        else:
            scan_mask2trigger(trigger_signal_config['offset'], trigger_signal_config['width'], trigger_signal_config['amplitude'])
        self.start_measurement(pos_x, pos_y, self.trigger_signal)
        
    def read_pmt(self, collect_data):
        #This function shal run in the highest priority process
        self.raw_pmt_frame = self.aio.read_analog()
        if collect_data:
            self.pmt_raw.append(self.raw_pmt_frame)
        return copy.deepcopy(self.raw_pmt_frame)
        
    def finish_measurement(self, generate_frames = True):
        self.aio.finish_daq_activity()
        self.close_shutter()
        #value of ao at stopping continous generation is unknown
        try:
            time.sleep(0.05)
            self._set_scanner_voltage(utils.cr((0.0, 0.0)), utils.cr((0.0, 0.0)), self.config.SCANNER_RAMP_TIME)
        except PyDAQmx.DAQError:#Sometimes DAQ device is not yet available
            time.sleep(1.0)
            self._set_scanner_voltage(utils.cr((0.0, 0.0)), utils.cr((0.0, 0.0)), self.config.SCANNER_RAMP_TIME)
        #Gather measurment data
        if generate_frames:
            if hasattr(self, 'sinus_pattern') and self.sinus_pattern:
                self.data = numpy.array([frame_from_sinus_pattern_scan(raw_pmt_data, self.scan_mask, self.backscan, self.binning_factor) for raw_pmt_data in self.pmt_raw])#dimension: time, subframe, height, width, channels
            else:
                self.data = numpy.array([raw2frame(raw_pmt_data, self.binning_factor, self.boundaries, self.phase_shift) for raw_pmt_data in self.pmt_raw])#dimension: time, height, width, channels
    
    def get_image_offset(self, scan_range, resolution):
        '''
        Returns image offset in pixels based on calibration data
        '''
        if isinstance(self.calibdata['resolutions'], list):
            max_resolution = max(self.calibdata['resolutions'])
        elif hasattr(self.calibdata['resolutions'], 'dtype'):
            max_resolution = self.calibdata['resolutions'].max()
        offset_rel = self.image_offsets(scan_range, resolution) - self.image_offsets(scan_range, max_resolution)
        offset = scan_range * resolution * offset_rel
        return int(offset[0])
        
    def load_calibdata(self, filename):
        h = hdf5io.Hdf5io(filename, filelocking=False)
        self.calibdata = {}
        nodes = ['scan_ranges', 'resolutions', 'offsets_mg']
        for node in nodes:
            self.calibdata[node] = h.findvar(node)
        from scipy import interpolate
        self.image_offsets = interpolate.interp2d(self.calibdata['scan_ranges'], self.calibdata['resolutions'], self.calibdata['offsets_mg'], kind='linear')
        h.close()
        
    def open_shutter(self):
        self.shutter.set()
        
    def close_shutter(self):
        self.shutter.clear()
        
    def close_instrument(self):
        self.aio.release_instrument()
        self.shutter.release_instrument()
        
####### Helpers #####################
def raw2frame(rawdata, binning_factor, boundaries, offset = 0):
    binned_pmt_data = binning_data(rawdata, binning_factor)
    if offset != 0:
        binned_pmt_data = numpy.roll(binned_pmt_data, -offset)
    return numpy.array((numpy.split(binned_pmt_data, boundaries)[1::2]))

def binning_data(data, factor):
    '''
    data: two dimensional pmt data : 1. dim: pmt signal, 2. dim: channel
    '''
    return numpy.reshape(data, (data.shape[0]/factor, factor, data.shape[1])).mean(1)
    
def scan_mask2trigger(scan_mask,  offset,  width,  amplitude, ao_sample_rate):
    '''
    Converts scan mask to trigger signal that controls the projector
    '''
    trigger_mask = numpy.logical_not(numpy.cast['bool'](scan_mask))
    offset_samples = int(numpy.round(ao_sample_rate * offset))
    width_samples = int(numpy.round(ao_sample_rate * width))
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
    trigger_signal = numpy.zeros_like(trigger_mask, dtype = numpy.float64)
    if len(high_value_indexes) > 0:
        trigger_signal[high_value_indexes] = amplitude
    trigger_signal *= trigger_mask
    return trigger_signal
    
def generate_frame_trigger(scan_mask, amplitude):
    frame_trigger = amplitude * numpy.ones_like(scan_mask)
    frame_trigger[:numpy.nonzero(scan_mask)[0][0]] = 0.0
    frame_trigger[-1] = 0.0
    return frame_trigger
        
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
    
#OBSOLETE
class TwoPhotonScannerLoop(command_parser.CommandParser):
    def __init__(self, config, queues):
        self.config = config
        self.queues = queues
        self.log = log.Log('2p log', fileop.generate_filename(os.path.join(self.config.LOG_PATH, 'twophotonloop_log.txt')), local_saving = False)
        command_parser.CommandParser.__init__(self, queues['out'], queues['in'], log = self.log, failsafe = True)
        self.run = True
        self.daq_parameter_names = ['AO_SAMPLE_RATE', 'AI_SAMPLE_RATE', 'AO_CHANNEL',  'AI_CHANNEL']
        self.parameter_names = ['SCANNER_SIGNAL_SAMPLING_RATE',  'SCANNER_DELAY', 'SCANNER_START_STOP_TIME',  'SCANNER_MAX_POSITION',  \
                                            'POSITION_TO_SCANNER_VOLTAGE','XMIRROR_OFFSET', 'YMIRROR_OFFSET', 'SCANNER_RAMP_TIME', \
                                        'SCANNER_HOLD_TIME',  'SCANNER_SETTING_TIME',  'SCANNER_TRIGGER_CONFIG']
        self.printc('started')
        
    def printc(self, txt, local_print = True):
        self.queue_out.put(str(txt))
        self.log.info(txt)
        if local_print:
            print txt
        
    def quit(self):
        self.run = False
        return 'quit'
        
    def exit(self):
        self.quit()
        
    def ping(self):
        self.printc('pong')
        
    def start_scan(self):
        if os.name != 'nt':
            self.printc('scan_ready')
            return
        if not self.queues['parameters'].empty():
            #Copy scan parameters
            parameters = self.queues['parameters'].get()
            config = self._update_config(parameters)
            self.filenames = parameters['filenames']
            #Initialize scanner  devices
            self.tp = TwoPhotonScanner(config)
            try:
                self.tp.start_rectangular_scan(parameters['scan_size'], parameters['scan_center'], parameters['resolution'], setting_time = config.SCANNER_SETTING_TIME, 
                                      trigger_signal_config = config.SCANNER_TRIGGER_CONFIG)
                if parameters.has_key('duration'):
                    if parameters['duration'] == 0:
                        nframes = 1
                    else:
                        nframes = int(numpy.round(parameters['duration'] * self.tp.frame_rate))
                elif parameters.has_key('nframes'):
                    nframes = parameters['nframes']
                else:
                    nframes = -1
                if parameters['enable_recording']:
                    from visexpA.engine.datahandlers.datatypes import ImageData
                    import tables
                    self.h = ImageData(self.filenames['datafile'][0], filelocking=self.config.ENABLE_HDF5_FILELOCKING)
                    n_columns_per_frame = int(parameters['scan_size']['col']*parameters['resolution'])
                    if nframes == -1:
                        expectedrows = 100* self.tp.frame_rate*n_columns_per_frame
                    else:
                        expectedrows = nframes*n_columns_per_frame
                    raw_data = self.h.h5f.create_earray(self.h.h5f.root, 'raw_data', 
                                                                                tables.Float64Atom(), 
                                                                                (0, ), 
                                                                                filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1), 
                                                                                expectedrows=expectedrows)
            except:
                self.printc(traceback.format_exc())
                self.printc('scan_ready')
                return
            self._estimate_memory_demand()
            self._send_scan_parameters2guipoller(config, parameters)
            self.printc('scan_started')
            frame_ct = 0
            #start scan loop
            self.abort = False
            while True:
                pmtdata = self.tp.read_pmt(collect_data = False and parameters['enable_recording']) #TMP
                if parameters['enable_recording']:
                    raw_data.append(pmtdata.flatten())
                self.queues['frame'].put(pmtdata)
                frame_ct += 1
                if (not self.queue_in[0].empty() and self.queue_in[0].get() == 'stop_scan') or frame_ct == nframes or frame_ct >= self.max_nframes:
                    break
                    self.abort = True
                time.sleep(0.01)
            self.recorded_frames = frame_ct
            #Finish, save
            self.printc('Scanning ended, {0} frames recorded' .format(frame_ct))
            self.tp.finish_measurement(generate_frames = False and parameters['enable_recording'])#TMP
            if parameters['enable_recording']:
                self._save_cadata(config, parameters)
            self.printc('scan_ready')
            self.tp.release_instrument()
        else:
            self.printc('Scan not started, parameters not provided')
            
    def _estimate_memory_demand(self):
#        self.printc(        (self.tp.aio.number_of_ai_samples,  self.tp.aio.number_of_ai_channels))
        max_memory = 70700*2*724#in case of hdf5 file format
        #70000, 1448 frame, 2500000, 20 frames
        memory_usage_per_frame =  self.tp.aio.number_of_ai_samples * self.tp.aio.number_of_ai_channels
        self.max_nframes = int(float(max_memory)/(memory_usage_per_frame))
#        print self.max_nframes , max_memory, memory_usage_per_frame
            
    def _send_scan_parameters2guipoller(self, config, parameters):
        '''
        Some parameters are needed for generating live image and displaying status on gui.
        '''
        #Send image parameters to poller
        pnames = ['frame_rate',  'binning_factor', 'boundaries',  'scanner_time_efficiency', 'speeds', 'image_offset']
        self.scan_parameters = {}
        for p in pnames:
            self.scan_parameters[p] = getattr(self.tp, p)
        #calculate overshoot
        self.scan_parameters['overshoot'] = self.tp.maximal_movement-parameters['scan_size']['row']
        self.printc('Scanner time efficiency is {0:1.2f} %'.format(self.tp.scanner_time_efficiency*100))
        self.queues['data'].put(self.scan_parameters)
        
    def _save_cadata(self, scan_config,parameters):
        self.printc('saving_data')
        #gather data to save
        data_to_save = {}
        #data_to_save['raw_data'] = numpy.rollaxis(self.tp.data, 0, 3)#TMP:rawdata cannot be saved
        data_to_save['scan_parameters'] = self.scan_parameters
        data_to_save['scan_parameters']['waveform'] = copy.deepcopy(self.tp.scanner_control_signal.T)
        data_to_save['scan_parameters']['mask'] = copy.deepcopy(self.tp.scan_mask)
        data_to_save['scan_parameters']['scan_config'] = copy.deepcopy(scan_config.get_all_parameters())
        data_to_save['scan_parameters']['raw_frame_shape'] = self.tp.raw_pmt_frame.shape
        data_to_save['scan_parameters']['nframes'] = self.recorded_frames
        data_to_save['scan_parameters'].update(parameters)
        if False:
            data_to_save['animal_parameters'] = {}
            data_to_save['experiment_log'] = {}
        data_to_save['software_environment'] = experiment_data.pack_software_environment()
        if self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            data_to_save['machine_config'] = copy.deepcopy(self.config.get_all_parameters())
            scipy.io.savemat(self.filenames['datafile'][0], data_to_save, oned_as = 'row', long_field_names=True)
        elif self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            data_to_save['machine_config'] = experiment_data.pickle_config(self.config)
            self.h.cadata = data_to_save
            self.h.save('cadata')
            self.h.close()
#            import shutil
#            shutil.move(self.filenames['local_datafile'][0], self.filenames['datafile'][0])
        self.printc('Data saved to {0}'.format(self.filenames['datafile'][0]))
        return
        if self.filenames.has_key('other_files') and 'tiff' in self.filenames['other_files'][0]:#Converting datafile to tiff shall take place in main_ui/main gui
            import tiffile
            from visexpA.engine.dataprocessors import generic
            tiff_description = 'Roskalab'
            resolution_dpi = data_to_save['scan_parameters']['resolution'] * 25.4e3#1 um = 25.4e3 um
            tiff_resolution = (resolution_dpi, resolution_dpi)#dpi
            #TODO: support saving multiple channels
            tiffile.imsave(self.filenames['other_files'][0], generic.normalize(self.tp.data[:, :, :, 0], outtype = numpy.uint16), software = 'visexpman', description = tiff_description, resolution = tiff_resolution)
            self.printc('Data saved to {0}'.format(self.filenames['other_files'][0]))
        
    def _update_config(self, parameters):
        config = copy.deepcopy(self.config)
        for p in self.parameter_names:
            if parameters.has_key(p):
                setattr(config, p, parameters[p])
        for p in self.daq_parameter_names:
            if parameters.has_key(p):
                config.DAQ_CONFIG[0][p] = parameters[p]
        if not hasattr(config, 'SCANNER_TRIGGER_CONFIG'):
            config.SCANNER_TRIGGER_CONFIG = None
        return config

    def start_calibration(self):
        if os.name != 'nt':
            return
        if not self.queues['parameters'].empty():
            #Copy scan parameters
            parameters = self.queues['parameters'].get()
            config = self._update_config(parameters)
            missing_keys = [k for k in ['repeats', 'scanning_range', 'scanner_speed', 'SCANNER_SETTING_TIME'] if not parameters.has_key(k)]
            if len(missing_keys) > 0:
                self.printc('{0} parameters must be provided' .format(missing_keys))
                self.printc('calib_ready')
                return
            if not isinstance(parameters['scanner_speed'],  list):
                parameters['scanner_speed'] = [parameters['scanner_speed']]
            if parameters['pattern']  == 'Scanner':
                lines = generate_test_lines(parameters['scanning_range'], int(parameters['repeats']), parameters['scanner_speed'])
            self.tp = TwoPhotonScanner(config)
            try:
                if parameters['pattern']  == 'Scanner':
                    self.tp.start_line_scan(lines, setting_time = parameters['SCANNER_SETTING_TIME'], filter = parameters)
                elif parameters['pattern']  == 'Sine':
                    self.tp.scan_mask_per_axis = {}
                    pos_x, pos_y, self.tp.scan_mask_per_axis['x'], self.tp.scan_mask_per_axis['y'], speeds = \
                                generate_sinus_calibration_signal(parameters['scanner_speed'], parameters['scanning_range'], int(parameters['repeats']), self.tp.aio.daq_config['AO_SAMPLE_RATE'], max_linearity_error = self.config.SINUS_CALIBRATION_MAX_LINEARITY_ERROR)
                    self.tp.scan_mask = self.tp.scan_mask_per_axis['x'] + self.tp.scan_mask_per_axis['y']
                    self.tp.start_measurement(pos_x, pos_y, trigger = numpy.zeros_like(pos_x))
            except:
                self.printc(traceback.format_exc())
                self.printc('calib_ready')
                return
            self.printc('calib_started')
            calibration_time = self.tp.scanner_control_signal.T.shape[0]/self.tp.aio.ai_sample_rate
            self.printc('Calibration time {0}'.format(calibration_time))
            if calibration_time < 10.0:
                self.tp.read_pmt()
            else:
                self.printc('Calibration would take long, skipping')
            try:
                self.tp.finish_measurement()
            except:
                self.printc(traceback.format_exc())
                self.printc('calib_ready')
                return
            self.tp.release_instrument()
            if hasattr(self.tp, 'raw_pmt_frame'):
                calibdata = {}
                calibdata['pmt'] = copy.deepcopy(self.tp.raw_pmt_frame)
                calibdata['waveform'] = copy.deepcopy(self.tp.scanner_control_signal.T)
                parameters['binning_factor'] = self.tp.binning_factor
                if parameters['pattern']  == 'Scanner':
                    calibdata['scanner_speed'] = parameters['scanner_speed']
                    calibdata['accel_speed'] = self.tp.accel_speed
                elif parameters['pattern']  == 'Sine':
                    calibdata['scanner_speed'] = speeds
                calibdata['mask'] = self.tp.scan_mask
                calibdata['parameters'] = parameters
                if parameters['pattern']  == 'Scanner':
                    profile_parameters, line_profiles = process_calibdata(calibdata['pmt'], calibdata['mask'], calibdata['parameters'])
                    calibdata['profile_parameters'] = profile_parameters
                    calibdata['line_profiles'] = line_profiles
                elif parameters['pattern']  == 'Sine':
                    calibdata['bode'] = scanner_bode_diagram(calibdata['pmt'], calibdata['mask'], calibdata['parameters']['scanner_speed'], self.config.SINUS_CALIBRATION_MAX_LINEARITY_ERROR)
                hdf5io.save_item(fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH,  'calib.hdf5')), 'calibdata', calibdata, overwrite=True, filelocking=False)
                self.queues['data'].put(calibdata)
            self.printc('calib_ready')
    
def two_photon_scanner_process(config, queues):
    '''
    The scanner process has a command interface where two photon scanning operations can be initiated. Communication
    takes place via queues since large amount of data has to be returned to the caller process.
    
    '''
    tl = TwoPhotonScannerLoop(config, queues)
    while tl.run:
        res = tl.parse()[0]
        if res != '' and res != None:
            tl.printc('Two photon process: ' + str(res))
        time.sleep(0.1)
    tl.printc('Scanner process ended')
    
def gauss(x, *p):
    A, mu, sigma = p
    return A*numpy.exp(-(x-mu)**2/(2.*sigma**2))

def process_calibdata(pmt, mask, parameters):
    mask_indexes = numpy.nonzero(numpy.diff(mask))[0].tolist()
    mask_indexes.append(mask.shape[0]-1)
    #Split data into individual line scans
    nlines = len(mask_indexes)/2
    nspeeds = nlines / 4 / parameters['repeats'] #For lines in each unit: y mirror down, y mirror up, x mirror down, x mirror up
    lines = []
    mask_index_counter = 0
    line_sizes = []#will be used for determining common line size for visualization
    for speed_i in range(int(nspeeds)):
        line_per_speed = {}
        for repeat in range(int(parameters['repeats'])):
            line_ids = ['y_down',  'y_up',  'x_down',  'x_up']#Order matters
            for i in range(len(line_ids)):
                curve = pmt[mask_indexes[mask_index_counter]:mask_indexes[mask_index_counter+1], 0]/parameters['repeats']#Only first channel is used, it is assumed that a calibration only one pmt is sampled
                mask_index_counter +=2
                if not line_per_speed.has_key(line_ids[i]):
                    line_per_speed[line_ids[i]] = curve
                else:
                    line_per_speed[line_ids[i]] += curve
                pass
        line_sizes.append(curve.shape[0])
        lines.append(line_per_speed)
    #Initialize image for line profile display
    line_width = 10
    nrows = nspeeds * 2 #up and down
    nrows *= line_width
    ncols = 2*nrows
    line_profiles = numpy.zeros((2*nrows, ncols, 3))
    #Calculate peak center and generate images visualizing line profiles
    line_counter = 0
    profile_parameters = {}
    for axis in ['x', 'y']:
        profile_parameters[axis] = {}
        for dir in ['up', 'down']:
            profile_parameters[axis][dir] = {}
            profile_parameters[axis][dir]['sigma'] = []
            profile_parameters[axis][dir]['delay'] = []
    for line in lines:
        for k, v in line.items():
            try:
                p0 = [1., v.shape[0]/2.0, 1.]
                coeff, var_matrix = scipy.optimize.curve_fit(gauss, numpy.arange(v.shape[0]), v, p0=p0)
                delay = coeff[1]/(v.shape[0])
                sigma = coeff[2]/(v.shape[0])
            except:
                delay = 0.5
                sigma = 0.25
            profile_parameters[k.split('_')[0]][k.split('_')[1]]['delay'].append(delay)
            profile_parameters[k.split('_')[0]][k.split('_')[1]]['sigma'].append(sigma)
            resampled = scipy.misc.imresize(numpy.array([v]), (1, int(ncols)))[0,:]
            line_index = line_counter
            if 'up' in k:
                line_index += 1
            if 'x' in k:
                row_offset = 0
            elif 'y' in k:
                row_offset = nrows
            line_index = line_index * line_width+row_offset
            line_profiles[line_index: line_index + line_width,:, 1] = resampled
            calculated = numpy.zeros_like(resampled)
            calculated[calculated.size*delay] = resampled.max()
            calculated[calculated.size*(delay - sigma)] = resampled.max()
            calculated[calculated.size*(delay + sigma)] = resampled.max()
            line_profiles[line_index: line_index + line_width,:, 2] = calculated
        line_counter += 2
    return profile_parameters, line_profiles
    
def generate_sinus_calibration_signal(frqs, amplitude, repeats, fs, max_linearity_error=1e-2):
    chunks = []
    speeds = numpy.array(frqs)*amplitude*numpy.pi
    mask  = []
    for frq in frqs:
        duration = repeats/float(frq)
        t = numpy.linspace(0, duration, fs*duration, False)
        phases = 2*numpy.pi*t*frq
        chunk = 0.5*amplitude*numpy.sin(phases)
        chunks.append(chunk)
        linearity_range = utils.sinus_linear_range(max_linearity_error)
        linearity_range_samples = int(numpy.round(linearity_range/(2*numpy.pi*repeats)*duration*fs))
        step = t.shape[0]/repeats
        offset = step/2
        starts = numpy.arange(repeats)*step+offset - linearity_range_samples
        mask_chunk = numpy.zeros_like(t)
        for start in starts:
            mask_chunk[start:start+2*linearity_range_samples] = 1.0
        mask.append(mask_chunk)
    pos_x = numpy.concatenate(chunks)
    mask = numpy.concatenate(mask)
    mask_x = numpy.concatenate((mask, numpy.zeros_like(mask)))
    mask_y = numpy.concatenate((numpy.zeros_like(mask), mask))
    t = numpy.linspace(0, pos_x.shape[0]/float(fs)*2, pos_x.shape[0]*2, False)
    pos_y = numpy.concatenate((numpy.zeros_like(pos_x), pos_x))
    pos_x = numpy.concatenate((pos_x, numpy.zeros_like(pos_x)))
#    from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
#    plot(t, pos_x)
#    plot(t, pos_y)
#    plot(t, mask_x)
#    plot(t, mask_y)
#    show()
    return pos_x, pos_y, mask_x, mask_y, speeds
    
def scanner_bode_diagram(pmt, mask, frqs, max_linearity_error):
    '''
    Generate Bode diagram of both scanners based on calibration data
    '''
    bode_amplitudes = []
    bode_phases = []
    sigmas = []
    means = []
    signals = []
    gauss_amplitudes = []
    for axis_i in range(2):#x and y part of the data
        pmt_chunk = pmt[axis_i*pmt.shape[0]/2:(axis_i+1)*pmt.shape[0]/2]
        mask_chunk = mask[axis_i*mask.shape[0]/2:(axis_i+1)*mask.shape[0]/2]
        boundaries = numpy.nonzero(numpy.diff(mask_chunk))[0]
        repeats = boundaries.shape[0]/2/len(frqs)
        bode_amplitude = []
        bode_phase = []
        for frq_i in range(len(frqs)):
            traces = []
            for repeat in range(repeats):
                start_i = boundaries[2*(frq_i*repeats+repeat)]
                end_i = boundaries[2*(frq_i*repeats+repeat)+1]
                traces.append(pmt_chunk[start_i: end_i][:,0])
            signal = numpy.array(traces).mean(axis=0)
            try:
                p0 = [1., 0.5*signal.shape[0], 1.]
                p0 = [1., signal.argmax(), 1.]
                coeff, var_matrix = scipy.optimize.curve_fit(gauss, numpy.arange(signal.shape[0]), signal, p0=p0)
                mean = coeff[1]/(signal.shape[0])#phase characteristic
                print coeff[1],frqs[frq_i]
                sigma = coeff[2]/(signal.shape[0])#amplitude characteristic
            except RuntimeError:
                mean = 0.5
                sigma = 0.25
            sigmas.append(sigma)
            means.append(mean)
            signals.append(signal)
            gauss_amplitudes.append(coeff[0])
            bode_amplitude.append(sigma)
            bode_phase.append(mean)
        bode_amplitude = numpy.array(bode_amplitude)/bode_amplitude[0]#assuming that amplitude gain is 1.0 at the lowest frequency
        bode_phase = 2*utils.sinus_linear_range(max_linearity_error)*(numpy.array(bode_phase) - bode_phase[0])#assuming that there is not phase shift at the lowest frequency
        bode_amplitudes.append(bode_amplitude)
        bode_phases.append(bode_phase)
    return {'frq': numpy.array(frqs), 'amplitude': bode_amplitudes, 'phase': bode_phases, 'sigmas': sigmas, 'means':means, 'signals' :signals, 'gauss_amplitudes':gauss_amplitudes}

def apply_scanner_transfer_function(x, fsample, phase_params = [ 0.00043265, -0.02486131],debug=False):
    phase = numpy.arange(x.shape[0]/2)*fsample/(x.shape[0]/2)*phase_params[0]+phase_params[1]
    phase = numpy.where(phase<0, 0, phase)
    gain = numpy.ones(x.shape[0]/2)
    #Mirror phase
    phase_r = phase.tolist()
    phase_r.reverse()
    phase = numpy.concatenate((-phase, numpy.array(phase_r)))
    #Mirror gain
    gain_r = gain.tolist()
    gain_r.reverse()
    gain = numpy.concatenate((gain, numpy.array(gain_r)))
    #Calculate filtered signal
    X = numpy.fft.fft(x)
    H = numpy.vectorize(complex)(gain*numpy.cos(phase), gain*numpy.sin(phase))
    y = numpy.fft.ifft(H*X)
    if debug:
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        figure(10)
        plot(X.real)
        plot(X.imag)        
    return y.real
    
def calculate_phase_shift(pos_x, scan_mask, config, debug = False):
    indexes = numpy.nonzero(numpy.where(numpy.diff(scan_mask)>0, 1, 0))[0]
    nperiods = 10#The more periods are used, the better accuracy we get
    if indexes.shape[0] < nperiods:
        nperiods = indexes.shape[0]-1
    indexes = numpy.array([indexes[0], indexes[nperiods]])
    if numpy.diff(indexes)%2 == 1:
        indexes[1] += 1
    pos_x_period = pos_x[indexes[0]:indexes[1]]
    pos_x_est=apply_scanner_transfer_function(pos_x_period,config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'], phase_params = [ 0.00043265, -0.02486131], debug= debug)
    from scipy.signal import correlate
    shift = correlate(pos_x_est, pos_x_period).argmax() - pos_x_period.shape[0]+1
    error = numpy.roll(pos_x_period, shift) - pos_x_est
    if debug:
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        print (pos_x_est.max()-pos_x_est.min()) - (pos_x_period.max() - pos_x_period.min())
        figure(1)
        plot(pos_x_period)
        plot(pos_x_est)
        figure(2)
        plot(pos_x_period/abs(pos_x_period).max())
        plot(scan_mask[indexes[0]:indexes[1]]*error)
        figure(3)
        plot(numpy.roll(pos_x_period, shift))
        plot(pos_x_est)
        print shift, abs(error).max()
    return shift, error

class TestScannerControl(unittest.TestCase):
    def setUp(self):
        self.dt = 1e-3
        
    @unittest.skip('')
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
        
    @unittest.skip('')
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
            show()
    #        savefig('/home/zoltan/visexp/debug/data/x.pdf')
    
    @unittest.skip('Run only for debug purposes')
    def test_04_generate_rectangular_scan(self):
        plot_enable = not False
        config = ScannerTestConfig()

        spatial_resolution = 2
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((128, 128))
        setting_time = [3e-4, 2e-3]
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        
        print ' ', abs(abs(pos_x.max()-pos_x.min())- size['col']), abs(abs(pos_y.max()-pos_y.min())- size['row'])
        import scipy
        import scipy.fftpack
        spectrum = abs(scipy.fft(pos_x))
        fs = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        frq = scipy.fftpack.fftfreq(pos_x.size, 1.0/fs)
        bandwidth = numpy.nonzero(numpy.where(spectrum<spectrum.max()*1e-5, 0, spectrum)[:spectrum.shape[0]/2])[0].max()/float(spectrum.size)*fs
        print bandwidth
        if plot_enable:
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
            figure(1)
            plot(frq, spectrum)
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
            
    @unittest.skip('Run only for debug purposes')
    def test_05_twophoton(self):
        import time
        plot_enable = not False
        config = ScannerTestConfig()
        config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'aio'
        config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 400000
        config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 400000
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai0:1'
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
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai0:1'
        config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        lines = generate_test_lines(100, 1, [300])
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
            
    @unittest.skip('Run only for debug purposes')
    def test_07_sine_scan_pattern(self):
        #In each period two frames are scanned
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        scan_size = utils.rc((10.0, 10.0))
        scan_center = utils.rc((0.0, 0.0))
        resolution = 0.1#um/pixel
        max_linearity_error = 19e-2#Max 1-pi/2
        fs = 400000.0
        backscan = True
        scanner_control, mask, frame_rate, scanner_period_time, time_efficiency =\
            sinus_pattern_rectangle_scan(scan_size, scan_center, resolution, max_linearity_error, fsampling = fs, backscan = backscan)
        #Reconstruct image from signal
        pmt = numpy.array([scanner_control['x'], scanner_control['y']]).T
        frame_from_sinus_pattern_scan(pmt, mask, backscan, 1)
        figure(1)
        plot(scanner_control['x'])
        plot(scanner_control['y'])
        
#        plot(linearity_mask['x'])
#        plot(linearity_mask['y'])
        plot(mask)
        figure(2)
        plot(scanner_control['x']*mask)
        plot(scanner_control['y']*mask)
        show()
        
    @unittest.skip('Run only for debug purposes')    
    def test_08_sinus_pattern_scan_daq(self):
        config = ScannerTestConfig()
        config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'aio'
        config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 250000
        config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 500000
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai0:1'
        config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        scan_size = utils.rc((100, 100))
        resolution = 0.2
        tp = TwoPhotonScanner(config)
        tp.start_sinus_pattern_rectangular_scan(scan_size, resolution = resolution, max_linearity_error = 19e-2, backscan = True)
        tp.read_pmt()
        tp.finish_measurement()
        tp.release_instrument()
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        from visexpman.engine.generic.colors import imsave
        imsave(tp.data[0,0,:,:,0],'c:\\_del\\fr0ch0.png')
        imsave(tp.data[0,0,:,:,1],'c:\\_del\\fr0ch1.png')
        imsave(tp.data[0,1,:,:,1],'c:\\_del\\fr1ch1.png')
        imsave(tp.data[0,1,:,:,0],'c:\\_del\\fr1ch0.png')
        figure(1)
        plot(tp.pmt_raw[0])
        figure(4)
        plot(tp.scanner_positions.T)
        show()
        
    @unittest.skip('Run only for debug purposes')    
    def test_09_fft_scan_signal(self):
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        import scipy
        import scipy.fftpack
        from visexpman.engine.generic.introspect import Timer
        config = ScannerTestConfig()
#        fs = 10000
#        
#        tup = 0.75
#        tdown = 1-tup
#        ideal_signal = numpy.concatenate((numpy.linspace(0, 1, t.shape[0]*tup, False), numpy.linspace(1, 0, t.shape[0]*tdown, False)))
#        ideal_signal = numpy.sin(2*numpy.pi*t)

        #NOTE1: Is there significant difference between pixel size of the different lines??????
        #NOTE2: how to use interpolation for distorting samples by pixel_size
        #NOTE3: Applying scanner transfer function shall be faster, consider transformation to complex frequency domain 
        #NOTE4: nominal, real scanner position, fix interpretation/terminology of signals
        spatial_resolution = 2
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((128, 128))
        setting_time = [3e-4, 2e-3]
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        fmax = 2200
        with Timer(''):
            t, x = spectral_filtering(pos_x, fmax, config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])
            t, y = spectral_filtering(pos_y, fmax, config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])
        #Error
        x_error = abs(pos_x-x)*scan_mask
        y_error = abs(pos_y-y)*scan_mask
        print x_error.max()#, numpy.histogram(x_error)
        print y_error.max()#, numpy.histogram(y_error)
        #small rotation caused y signal:
        print numpy.arctan(4*y_error.max()/size['col'])*180/numpy.pi 
        figure(1)
        plot(t, pos_x)
        plot(t, x*scan_mask)
        plot(t, scan_mask*2*max(pos_x.max(), x.max())-max(pos_x.max(), x.max()))
#        figure(2)
#        plot(t, pos_y)
#        plot(t, y)
#        plot(t, scan_mask*2*max(pos_x.max(), x.max())-max(pos_x.max(), x.max()))
        with Timer(''):
            pixel_size = numpy.zeros_like(scan_mask)
            pixel_size[1:] = numpy.diff(x)
            masked_sample_size = numpy.zeros_like(scan_mask)
            masked_sample_size[1:] = numpy.diff(pos_x)*scan_mask[:-1]
            if masked_sample_size.min() >= 0 and masked_sample_size.max() > 0:
                pixel_size = numpy.where(pixel_size<0, 0, pixel_size)
            elif masked_sample_size.min() < 0 and masked_sample_size.max() <= 0:
                pixel_size = numpy.where(pixel_size>0, 0, pixel_size)        
        figure(3)
        plot(numpy.diff(pos_x)*scan_mask[:-1])
        plot(numpy.diff(x)*scan_mask[:-1])
        plot(pixel_size)
        #Pixels shall be dropped where resolution (step size between adjecent samples) is subzero.
        #Where step size increases, horizontal size of pixels are also increased, thus multiple pixels have the same value on the output image.
        #At smaller step sizes multiple samples are averaged into one pixel
        show()
        
    @unittest.skip('')    
    def test_10_process_calibdata(self):
        p = '/mnt/databig/software_test/ref_data/scanner_calib/calib_repeats.hdf5'
        calibdata = hdf5io.read_item(p, 'calibdata', filelocking=False)
        from visexpman.engine.hardware_interface import scanner_control
        profile_parameters, line_profiles = process_calibdata(calibdata['pmt'], calibdata['mask'], calibdata['parameters'])
        from visexpman.engine.generic import colors
        colors.imshow(line_profiles)
    
    @unittest.skip('')    
    def test_11_process_sine_calibdata(self):
        p = '/mnt/databig/software_test/ref_data/scanner_calib/sine_calib.hdf5'
        calibdata = hdf5io.read_item(p, 'calibdata', filelocking=False)
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        pmt = calibdata['pmt']
        mask = calibdata['mask']
        frqs = calibdata['parameters']['scanner_speed']
        print scanner_bode_diagram(pmt, mask, frqs)
        pass
    
    @unittest.skip('')
    def test_12_calculate_trigger_signal(self):
        config = ScannerTestConfig()
        spatial_resolution = 2
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((128, 128))
        setting_time = [3e-4, 2e-3]
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        trigger_signal = scan_mask2trigger(scan_mask, 0, 20.0e-6, 1.0, config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'])
        frame_trigger = generate_frame_trigger(scan_mask,5)
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        plot(pos_x)
        plot(pos_y)
        plot(scan_mask)
        plot(frame_trigger)
        show()
        
    @unittest.skip('Run only for debug purposes')
    def test_13_run_twophoton(self):
        import time
        try:
            import Image
        except ImportError:
            from PIL import Image
        from visexpA.engine.dataprocessors.generic import normalize
        plot_enable = not False
        config = ScannerTestConfig()
        config.DAQ_CONFIG[0]['ANALOG_CONFIG'] = 'aio'
        config.DAQ_CONFIG[0]['DAQ_TIMEOUT'] = 10.0
        config.DAQ_CONFIG[0]['AO_SAMPLE_RATE'] = 200000
        config.DAQ_CONFIG[0]['AI_SAMPLE_RATE'] = 200000
        config.DAQ_CONFIG[0]['AO_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ao0:1'
        config.DAQ_CONFIG[0]['AI_CHANNEL'] = unittest_aggregator.TEST_daq_device + '/ai0:1'
        config.DAQ_CONFIG[0]['AO_SAMPLING_MODE'] = 'cont'
        config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
        spatial_resolution = 2
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((128, 128))
        setting_time = [3e-4, 2e-3]        
        tp = TwoPhotonScanner(config)
        tp.start_rectangular_scan(size, spatial_resolution =  spatial_resolution, setting_time = setting_time)
        for i in range(3):
            tp.read_pmt()
        tp.finish_measurement()
        tp.release_instrument()
        Image.fromarray(numpy.cast['uint8'](80*(tp.data[0,:,:,0]+2))).save('v:\\debug\\ch0.png')
        Image.fromarray(numpy.cast['uint8'](80*(tp.data[0,:,:,1]+2))).save('v:\\debug\\ch1.png')
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
    def test_14_generate_sinus_calibration_signal(self):
        repeats = 3
        amplitude = 20#um
        speeds = [1000, 2000]#um/s
        fs = 400000
        posx, posy, mask_x, mask_y, speeds = generate_sinus_calibration_signal(speeds, amplitude, repeats, fs)
        
    @unittest.skip('Run only for debug purposes')
    def test_15_scanner_transfer_function(self):
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        frqs = [300, 600,1600]
        for i in range(len(frqs)):
            fs = 1e6
            f = frqs[i]
            tmax = 10.0/f
    #        tmax = 1.0
            nsamples = int(fs*tmax)
            if nsamples/2.0 != numpy.round(nsamples/2.0):
                nsamples += 1
            t = numpy.linspace(0, tmax,nsamples, False)
            x = numpy.sin(numpy.pi*2*t*f)
            y=apply_scanner_transfer_function(x,fs, phase_params = [ 0.00043265, -0.02486131])
            figure(i)
            plot(x)
            plot(y)
            print x.max(), y.max()
            from scipy.signal import correlate
            print correlate(y, x).argmax() - x.shape[0]+1
        show()

    @unittest.skip('Run only for debug purposes')
    def test_16_estimate_scanner_position_shift(self):
        from visexpman.engine.generic.introspect import Timer
        config = ScannerTestConfig()
        spatial_resolution = 1
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((128, 128))
        setting_time = [3e-4, 2e-3]
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        with Timer(''):
            shift, error = calculate_phase_shift(pos_x, scan_mask, config,True)
        print shift, abs(error).max()
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        figure(20)
        plot(pos_x)
        show()
        
    @unittest.skip('')
    def test_17_rectangular_scan_timing(self):
        plot_enable = not False
        config = ScannerTestConfig()

        spatial_resolution = 2
        spatial_resolution = 1.0/spatial_resolution
        position = utils.rc((0, 0))
        size = utils.rc((20, 20))
        setting_time = [3e-4, 1e-3]
        frames_to_scan = 1
        pos_x, pos_y, scan_mask, speed_and_accel, result = generate_rectangular_scan(size,  position,  spatial_resolution, frames_to_scan, setting_time, config)
        spectrum = abs(scipy.fft(pos_x))
        fs = 400000.0
        t = numpy.arange(0, scan_mask.shape[0])/fs*1e6
        #calculate duty cycle, line frequency, flash duration
        times = numpy.diff(numpy.nonzero(numpy.diff(scan_mask))[0])
        fline = fs/times[0:2].sum()
        tline = 1/fline
        tflash = times[1]/fs
        duty_cycle = tflash/tline
        frame_rate = fs/scan_mask.shape[0]
        print size['row'],  1/spatial_resolution, round(fline), round(tline*1e6), round(tflash*1e6), round(duty_cycle*100), round(frame_rate, 1)        
        #Generate screen sync signal
        frq = 200
        duty_cycle = 0.3
        screen_sync_signal = numpy.zeros_like(scan_mask)
        nflashpoints = (1.0/frq*duty_cycle)*fs
        for phase in range(int(nflashpoints)):
            screen_sync_signal[phase::fs/frq]=1
        if plot_enable:
            from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title, xlabel
            figure(2)
            plot(t, pos_x)
            plot(t, pos_y)
#            plot(t, scan_mask)
            plot(t, scan_mask)
            plot(t, screen_sync_signal)
#            legend(['scanner position',  'valid data'])
            xlabel('t [us]')
            show()
            
    def test_18_scanner_signal(self):
        from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
        from visexpman.engine.generic.introspect import Timer
        from visexpman.users.zoltan import scanner_calibration
        constraints = {}
        constraints['x_flyback_time']=0.2e-3
        constraints['f_sample']=500e3
        constraints['y_flyback_time'] = 1e-3
        constraints['x_max_frq'] = 1500
        constraints['enable_flybackscan']=False
        constraints['enable_scanner_phase_characteristics']=True
        constraints['movement2voltage']=1.0/128.0#includes voltage to angle factor
        constraints['xmirror_max_frequency']=1400
        constraints['ymirror_flyback_time']=1e-3
        constraints['sample_frequency']=1000e3
        constraints['max_linearity_error']=5e-2
        constraints['phase_characteristics']=[9.50324884e-08,  -1.43226725e-07, 1.50117389e-05,  -1.41414186e-04,   5.90072950e-04,   5.40402050e-03,  -1.18021600e-02]
        constraints['gain_characteristics']=[-1.12765460e-04,  -2.82919056e-06]
        
        scan_configs = [
                                    [utils.rc((50,50)), 3, False, 100e3,5e-2],
                                    [utils.rc((100,100)), 1, False, 100e3,5e-2],
                                    [utils.rc((100,100)), 2, True, 400e3,5e-2],
                                    [utils.rc((100,100)), 2, False, 400e3,5e-2],
                                    [utils.rc((100,100)), 2, False, 400e3,1e-2],
                                    [utils.rc((100,100)), 1, False, 500e3,5e-2],
                                    [utils.rc((100,100)), 4, False, 100e3,1e-2],
                                    [utils.rc((20,10)), 1, True, 400e3,1e-2],
                                    [utils.rc((20,20)), 1, False, 400e3,1e-2],
                                    [utils.rc((30,20)), 1, True, 400e3,5e-2],
                                    [utils.rc((10,15)), 1, False, 100e3,5e-2],
                                    [utils.rc((128,128)), 2, False, 500e3,30e-2],
                                    [utils.rc((100,100)), 1, True, 300e3,5e-2],
                                    [utils.rc((10,10)), 5, False, 250e3,5e-2],
                                    [utils.rc((100,100)), 2, False, 1000e3,5e-2]
                                   ]
        for scan_size, resolution, constraints['enable_flybackscan'], constraints['sample_frequency'], constraints['max_linearity_error'] in scan_configs:
            center = utils.rc((1*0,10*0))
            xsignal,ysignal,frame_trigger_signal, stim_sync, valid_data_mask,signal_attributes =\
                            generate_scanner_signals(scan_size, resolution, center, constraints)
            continue
            self.assertGreaterEqual(signal_attributes['ymirror_flyback_time'],constraints['ymirror_flyback_time'])
            number_of_periods = numpy.where(numpy.diff(numpy.where(xsignal>xsignal.mean(),1,0))>0,1,0).sum()
            xperiod_length = float(xsignal.shape[0])/number_of_periods
            self.assertEqual(xperiod_length,xsignal.shape[0]/number_of_periods)
            #check number of periods
            if constraints['enable_flybackscan']:
                factor = 0.5
            else:
                factor = 1.0
            self.assertEqual(number_of_periods - (signal_attributes['ymirror_flyback_time']*constraints['sample_frequency'])/xperiod_length,
                                                                                                         scan_size['row']*resolution*factor)
            #check y signal
            self.assertAlmostEqual(numpy.where(numpy.diff(ysignal)<0,1,0).sum()/constraints['sample_frequency'], 
                                                    signal_attributes['ymirror_flyback_time'],
                                                    int(numpy.log10(constraints['sample_frequency']))-1)
            self.assertAlmostEqual(numpy.where(numpy.diff(ysignal)>=0,1,0).sum()/constraints['sample_frequency'], 
                                                          1.0/signal_attributes['frame_rate'] - signal_attributes['ymirror_flyback_time'],
                                                          int(numpy.log10(constraints['sample_frequency']))-1)
            #test x scanner signal amplitude
            masked_signal = numpy.roll(valid_data_mask,-signal_attributes['phase_shift'])*xsignal#shift back to match with x signal
            gain = scanner_calibration.gain_estimator([signal_attributes['fxscanner'],scan_size['col']*constraints['scanner_position_to_voltage']],*constraints['gain_characteristics'])
            masked_signal = masked_signal[numpy.nonzero(masked_signal)[0]]
            if constraints['enable_flybackscan']:
                decimal_places = 5
            else:
                decimal_places = -1
            self.assertAlmostEqual((masked_signal.max()-masked_signal.min())*gain/constraints['scanner_position_to_voltage'], 
                                                                          float(scan_size['col']), decimal_places)
            self.assertAlmostEqual(xsignal.mean()/constraints['scanner_position_to_voltage'], center['col'],5)
            #test y scanner signal amplitude
            self.assertAlmostEqual((ysignal.max()-ysignal.min())/constraints['scanner_position_to_voltage'], float(scan_size['row']), 5)
            self.assertAlmostEqual(ysignal.mean()/constraints['scanner_position_to_voltage'], center['row'],5)
            #check frame trigger signal
            self.assertLess(constraints['sample_frequency']*constraints['ymirror_flyback_time'], 
                             frame_trigger_signal.shape[0]-frame_trigger_signal.sum())
            if False:
                print ', '.join(['{0}={1}'.format(k, numpy.round(v, 3)) for k,v in signal_attributes.items()])
            duty_cycle = 0.2
            delay = 10e-6
            stimulus_flash_trigger_signal, rdc = generate_stimulus_flash_trigger(duty_cycle, delay, signal_attributes, constraints)
            self.assertEqual((stimulus_flash_trigger_signal+valid_data_mask).max(), 1.0)#If more than 1, data and flash overlaps which is not acceptable
            stimulus_flash_trigger_signal, rdc = generate_stimulus_flash_trigger(1.0, delay, signal_attributes, constraints)
            self.assertEqual((stimulus_flash_trigger_signal+valid_data_mask).max(), 1.0)#If more than 1, data and flash overlaps which is not acceptable
            stimulus_flash_trigger_signal, rdc = generate_stimulus_flash_trigger(1.0, 0.0, signal_attributes, constraints)
            self.assertEqual((stimulus_flash_trigger_signal+valid_data_mask).max(), 1.0)#If more than 1, data and flash overlaps which is not acceptable
            self.assertEqual((valid_data_mask+stimulus_flash_trigger_signal).sum(),stimulus_flash_trigger_signal.shape[0])#100% duty cycle, no delay: data mask and trigger signal covers the whole time
#        plot(ysignal)
#        plot(xsignal)
#        plot(valid_data_mask)
#        plot(stimulus_flash_trigger_signal)
#        show()

    def test_19_reconstruct_signal(self):#TODO:uncomplete test
        from pylab import plot, show
        from PIL import Image
        from visexpman.engine.generic import signal,introspect
        from visexpman.users.test import unittest_aggregator
        if unittest_aggregator.TEST_data_folder is None:
            return
            
        constraints = {}
        constraints['x_flyback_time']=0.1e-3
        constraints['f_sample']=500e3
        constraints['y_flyback_time'] = 0.5e-3
        constraints['x_max_frq'] = 1500
        constraints['enable_flybackscan']=False
        constraints['movement2voltage']=1.0/128.0#includes voltage to angle factor
        x,y,frame_sync,stim_sync,valid_data_mask,signal_attributes = \
                            generate_scanner_signals(utils.rc((50,50)), 3, utils.rc((0,0)), constraints)
        folder = os.path.join(unittest_aggregator.TEST_data_folder, 'two-photon-snapshots', 'data')
        PMTS = {'TOP': {'CHANNEL': 0,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'CHANNEL' : 1,'COLOR': 'RED', 'ENABLE': False}}
                            
        p=constraints
        p.update(signal_attributes)
        data=numpy.zeros((x.shape[0]*2,1))
        p['analog_input_sampling_rate'] = 2*constraints['f_sample']
        p['analog_output_sampling_rate'] = constraints['f_sample']
        p['valid_data_mask']=valid_data_mask
        p['channels']=['TOP']
        frames = signal2image(data, p, PMTS)
                            
        fns=os.listdir(folder)
        fns.sort()
        if len(fns)==0:
            print 'No test data for testing signal2image'
        for fn in fns:
#            print fn
            data = utils.array2object(numpy.load(os.path.join(folder,fn)))
            ai_data=data['ai_data']
            parameters=data['parameters']
            sh0=0
            ai_data_shifted = numpy.roll(ai_data,sh0)#simulate phase shift
            frames = signal2image(ai_data_shifted, parameters, PMTS)
#            Image.fromarray(numpy.cast['uint8'](255*signal.scale(frames[0]))).show()
            #Shift between consecutive lines
#            ref=frames[0][0,0]
#            shift1 = numpy.nonzero(numpy.diff(numpy.where(frames[0][1]>ref,1,0)))[0][0]
#            shift2 = numpy.nonzero(numpy.diff(numpy.where(frames[0][1]<ref,1,0)))[0][0]
#            print shift1,shift2
#                Image.fromarray(numpy.cast['uint8'](255*signal.scale(frames[1]))).show()
#            plot(ai_data[:,0])
#            plot(ai_data[:,1])
#            show()
            pass
            
            


    def _ramp(self):
        waveform = numpy.linspace(0.0, 1.0, 10000)
        waveform = numpy.array([waveform, waveform])
        waveform[1, :] =1*waveform[1, :]
        waveform[:, -1] = numpy.zeros(2)
        waveform[:, -2] = numpy.zeros(2)
        waveform[:, -3] = numpy.zeros(2)
        return waveform.T

class ScannerError(Exception):
    '''
    Raised when problem occurs something related to scanning
    '''

def signal2image(ai_data, parameters, pmt_config):
    '''
    Transforms ai_data to a two dimensional image per channel. 
    From the acquired waveform (ai_data) the valid and invalid data are separeted by using valid_data_mask from parameters
    '''
    binning_factor = int(numpy.round(parameters['analog_input_sampling_rate']/parameters['analog_output_sampling_rate']))
    binned = numpy.zeros((ai_data.shape[0]/binning_factor, ai_data.shape[1]))
    frames = []
    for ch_i in range(ai_data.shape[1]):
        binned[:,ch_i] = ai_data[:,ch_i].reshape((ai_data.shape[0]/binning_factor,binning_factor)).mean(axis=1)
        if False:#Method 1, longer runtime
            indexes = numpy.nonzero(numpy.diff(valid_data_mask))[0]
            lines=numpy.split(binned[:,ch_i],indexes)[1::2]
            frame = numpy.array(lines)
        else:
            indexes = numpy.nonzero(numpy.diff(parameters['valid_data_mask']))[0]+1
            if parameters['valid_data_mask'][0]!=0:
                indexes = numpy.insert(indexes, 0,0)
            if indexes.shape[0] ==3 and parameters['valid_data_mask'][-1] == 1:
                #If end of valid range is at period end (numpy.diff cannot detect it)
                indexes = numpy.append(indexes, parameters['valid_data_mask'].shape[0])
            valid_x_lines = int(parameters['nxlines'] - parameters['yflyback_nperiods'])
            linelenght = parameters['valid_data_mask'].shape[0]
            if 0:
                print binned[:linelenght*valid_x_lines,ch_i].shape,(valid_x_lines,linelenght)
            binned_without_flyback =  binned[:linelenght*valid_x_lines,ch_i].reshape((valid_x_lines,linelenght))
            if parameters.has_key('enable_flybackscan') and parameters['enable_flybackscan']:
                frame=numpy.zeros((2*valid_x_lines,parameters['valid_data_mask'].sum()/2))
                frame[0::2,:] = binned_without_flyback[:,indexes[0]:indexes[1]]
                frame[1::2,:] = numpy.fliplr(binned_without_flyback[:,indexes[2]:indexes[3]])
            else:
                frame = binned_without_flyback[:,indexes[0]:indexes[1]]
        frames.append(frame)
    #Colorize channels
    colorized_frame = numpy.zeros((frame.shape[0],frame.shape[1],3))
    frame = numpy.array(frames)
    for color_channel_assignment in [[pmt_config[ch]['COLOR'],pmt_config[ch]['CHANNEL']] for ch in parameters['channels']]:
        if len(parameters['channels']) == 1:
            frame_index = 0
        else:
            frame_index = color_channel_assignment[1]
        if color_channel_assignment[0] == 'RED':
            colorized_frame[:,:,0] = frames[frame_index]
        elif color_channel_assignment[0] == 'GREEN':
            colorized_frame[:,:,1] = frames[frame_index]
        elif color_channel_assignment[0] == 'BLUE':
            colorized_frame[:,:,2] = frames[frame_index]
        else:
            raise NotImlementedError('')
        
    #calculate grid
    if 0:
        valid_data_mask_phase_shifted_back = numpy.roll(parameters['one_period_valid_data_mask'],parameters['phase_shift'])
        indexes_valid_data = numpy.nonzero(numpy.diff(valid_data_mask_phase_shifted_back))[0]
        valid_data_xscanner_signal = parameters['one_period_x_scanner_signal'][indexes_valid_data[0]:indexes_valid_data[1]][::-1]
#        x_grid_min = parameters['scan_center']['row']-0.5*parameters['scanning_range']['row']
#        x_grid_max = parameters['scan_center']['row']+0.5*parameters['scanning_range']['row']
#        y_grid_min = parameters['scan_center']['col']-0.5*parameters['scanning_range']['col']
#        y_grid_max = parameters['scan_center']['col']+0.5*parameters['scanning_range']['col']
    #TODO: Shift gridline spacing with the nonlinearity of sinus (user can disable it)
        
    return colorized_frame, frame
    
def generate_scanner_signals(size,resolution,center,constraints):
    '''
    resolution: pixel/um
    Generated signals: x,y scanner, stim sync, frame sync
    
    constraints['x_flyback_time']
    constraints['y_flyback_time']
    constraints['x_max_frq']
    constraints['f_sample']
    constraints['movement2voltage']
    calibration:
        x scan contraction->size['row'] 
        x scanner delay-> scan center['row'] 
    
    '''
    from pylab import plot,show
    
    x_scan=numpy.linspace(-0.5*size['row'], 0.5*size['row'], size['row']*resolution)+center['row']
    x_n_min_samples = numpy.ceil(constraints['f_sample']/constraints['x_max_frq'])
    if x_n_min_samples>x_scan.shape[0]:
        flyback_samples = x_n_min_samples-x_scan.shape[0]
    else:
        flyback_samples=constraints['f_sample']*constraints['x_flyback_time']
    x_flyback=numpy.linspace(0.5*size['row'], -0.5*size['row'], flyback_samples)+center['row']
    x_one_period=numpy.concatenate((x_scan,x_flyback))
    y_flyback_lines = numpy.ceil(constraints['y_flyback_time']*constraints['f_sample']/x_one_period.shape[0])
    nlines = int(size['col']*resolution+y_flyback_lines)
    x=numpy.tile(x_one_period,nlines)*constraints['movement2voltage']
    y_scan=numpy.linspace(-0.5*size['col'], 0.5*size['col'], x_one_period.shape[0]*(nlines-y_flyback_lines))+center['col']
    y_flyback = numpy.linspace(0.5*size['col'], -0.5*size['col'], x_one_period.shape[0]*(y_flyback_lines))+center['col']
    y=numpy.concatenate((y_scan,y_flyback))*constraints['movement2voltage']
    valid_data_mask=numpy.concatenate((numpy.ones_like(x_scan),numpy.zeros_like(x_flyback)))
    frame_sync = numpy.tile(valid_data_mask,nlines)
    if y.shape[0] != x.shape[0]:
        raise ScannerError('x and y signal length must be the same: {0}, {1}. Adjust a little on resolution or scan range.'.format(y.shape[0], x.shape[0]))
    stim_sync=numpy.tile(numpy.concatenate((numpy.zeros_like(x_scan),numpy.ones_like(x_flyback))),nlines)
    signal_attributes={}
    signal_attributes['frame_rate']=constraints['f_sample']/float(y.shape[0])
    signal_attributes['x_frequency'] = constraints['f_sample']/float(x_one_period.shape[0])
    signal_attributes['x_flyback_time'] = float(flyback_samples)/constraints['f_sample']
    signal_attributes['y_flyback_time'] = float(y_flyback.shape[0])/constraints['f_sample']
    signal_attributes['nxlines'] = nlines
    signal_attributes['yflyback_nperiods'] = y_flyback_lines
    return x,y,frame_sync,stim_sync,valid_data_mask,signal_attributes
    

#OBSOLETE
def generate_scanner_signals1(scan_size, resolution, center, constraints):
    '''
    resolution: pixel/um
    scan_size: height and width of scannable area in um and in row,col format (see utils.rc)
    center: center of scannable area in um in row,col format
    constraints: constraint parameters that should not be exceeded or should be considered
        constraints['enable_flybackscan']=False
        constraints['scanner_position_to_voltage']=0.1#includes voltage to angle factor
        constraints['xmirror_max_frequency']=1500Hz
        constraints['ymirror_flyback_time']=1e-3
        constraints['sample_frequency']=400e3
        constraints['max_linearity_error']=5e-2
        constraints['phase_characteristics']=[-0.00074166, -0.00281492]
        constraints['gain_characteristics']=[9.92747933e-01, 2.42763029e-06, -2.40619419e-08]
    '''
    from visexpman.engine.generic import signal
    xpixels = resolution*scan_size['col']
    ypixels = resolution*scan_size['row']
    for f in numpy.arange(1, constraints['xmirror_max_frequency'])[::-1]:
        linear_range = signal.sinus_linear_range(f, constraints['sample_frequency'], constraints['max_linearity_error'])
        if xpixels <= linear_range:
            xperiod_samples = numpy.ceil((constraints['sample_frequency']/f)/4)*4#period must be divided to four equal compartments
            fxscanner = constraints['sample_frequency']/xperiod_samples
            one_period_x_scanner_signal = signal.wf_sin(1,fxscanner,1.0/fxscanner,constraints['sample_frequency'],phase=90)[:-1]
            #valid signal mask: two intervals in one period, around pi/2 and 3pi/2
            mask = numpy.zeros_like(one_period_x_scanner_signal)
            mask[mask.shape[0]/4-xpixels/2:mask.shape[0]/4+xpixels/2]=1
            if constraints['enable_flybackscan']:
                mask[3*mask.shape[0]/4-xpixels/2:3*mask.shape[0]/4+xpixels/2]=1
            overshoot = one_period_x_scanner_signal.max()/(mask*one_period_x_scanner_signal).max()#in percent
            #x signal amplitude is increseased to fit the required amplitude into the linear range of the sinus wave
            one_period_x_scanner_signal *= overshoot
            #correct x amplitude with gain at given frq
            from visexpman.users.zoltan import scanner_calibration
            if constraints['enable_scanner_phase_characteristics']:
                gain = scanner_calibration.gain_estimator([fxscanner,scan_size['col']*constraints['scanner_position_to_voltage']],*constraints['gain_characteristics'])
                one_period_x_scanner_signal /= gain#constraints['gain_characteristics'][0] \
                                            #+constraints['gain_characteristics'][1] * fxscanner + constraints['gain_characteristics'][2] * fxscanner**2
            else:
                gain=1.0
            one_period_x_scanner_signal *= scan_size['col']*constraints['scanner_position_to_voltage']
            one_period_x_scanner_signal += center['col']*constraints['scanner_position_to_voltage']
            if constraints['enable_scanner_phase_characteristics']:
                #Shift mask with phase
                phase = scanner_calibration.phase_estimator([fxscanner,scan_size['col']*constraints['scanner_position_to_voltage']],*constraints['phase_characteristics'])
                phase_shift = int(numpy.round(phase/(numpy.pi*2)*one_period_x_scanner_signal.shape[0],0))#phase shift of pmt signal to mirro control signal
            else:
                phase_shift = 0
            mask = numpy.roll(mask,phase_shift)#shift valid data mask with phase shift. At signal reconstruction the valid data mask will tell which items of the recorded stream are part of the image
            if constraints['enable_flybackscan']:
                factor = 0.5#two lines are scanned in one period
            else:
                factor = 1.0
            flash_time = (one_period_x_scanner_signal.shape[0] - xpixels/factor)#overall, split to two flashes
            max_flash_duty_cycle = float(flash_time)/one_period_x_scanner_signal.shape[0]
            #y flyback time does not exceed ymirror_flyback_time
            yflyback_nperiods = numpy.ceil(constraints['ymirror_flyback_time']/(1.0/fxscanner))
            yflyback_time_corrected = yflyback_nperiods/fxscanner
            #total number of periods of x mirror in one frame
            nxlines = ypixels*factor + yflyback_nperiods
            t_up = ypixels/(fxscanner/factor)
            t_down = yflyback_time_corrected
            frame_rate = 1.0/(t_up+t_down)
            ysignal = signal.wf_triangle(1.0, t_up, t_down, t_up +t_down, constraints['sample_frequency'], offset = -0.5)
            frame_trigger_signal = numpy.zeros_like(ysignal)
            frame_trigger_signal[:int(constraints['sample_frequency']*t_up)] = 1.0
            #scale y signal to voltage and add offset
            ysignal *= scan_size['row']*constraints['scanner_position_to_voltage']
            ysignal += center['row']*constraints['scanner_position_to_voltage']
            xsignal = numpy.tile(one_period_x_scanner_signal,nxlines)
            if ysignal.shape[0] != xsignal.shape[0]:
                raise ScannerError('x and y signal length must be the same: {0}, {1}. Adjust a little on resolution or scan range.'.format(ysignal.shape[0], xsignal.shape[0]))
            valid_data_mask = numpy.tile(mask,nxlines)
            break
    signal_attributes = {}
    signal_attributes['ymirror_flyback_time'] = t_down
    signal_attributes['overshoot'] = overshoot
    signal_attributes['max_flash_duty_cycle'] = max_flash_duty_cycle
    signal_attributes['frame_rate'] = frame_rate
    signal_attributes['fxscanner'] = fxscanner
    signal_attributes['phase_shift'] = phase_shift
    signal_attributes['gain'] = gain
    signal_attributes['one_period_x_scanner_signal'] = one_period_x_scanner_signal
    signal_attributes['one_period_valid_data_mask'] = mask
    signal_attributes['nxlines'] = nxlines
    signal_attributes['yflyback_nperiods'] = yflyback_nperiods
    return xsignal,ysignal,frame_trigger_signal,valid_data_mask,signal_attributes

def generate_stimulus_flash_trigger(duty_cycle, delay, signal_attributes, constraints):
    '''
    From valid data mask generate trigger signal
    If duty_cycle is 1.0, then maximal possible duty cycle is presented but delay is applyed too.
    0.5 duty cycle means 50% time during the whole scanning is used for flashing the stimulus
    '''
    if duty_cycle >1:
        raise RuntimeError('Duty cycle shall be between 0.0...1.0')
    mask = signal_attributes['one_period_valid_data_mask']#calculate it for one period
    if signal_attributes['max_flash_duty_cycle']<duty_cycle and duty_cycle<1.0:
        raise ScannerError('Requested duty cycle ({0:0.2f}) shall be below {1:0.2f}'.format(duty_cycle, signal_attributes['max_flash_duty_cycle']))
    if constraints['enable_flybackscan']:
        factor = 0.5
    else:
        factor = 1.0
    flash_samples = int(factor * duty_cycle/signal_attributes['fxscanner']*constraints['sample_frequency']) #flashed in two pulses if flyback enabled
    delay_samples = int(delay * constraints['sample_frequency'])
    max_flash_samples =  int(factor*(mask.shape[0]-mask.sum()))
    if max_flash_samples<flash_samples + delay_samples and duty_cycle<1.0:
        raise ScannerError('Not enough time for requested duty cycle and delay. Reduce duty cycle or delay')
    if duty_cycle == 1.0:#If 1.0 duty cycle is provided, truncate flash samples
        flash_samples = max_flash_samples - delay_samples
    #Shift temporarily the mask to the beginning of the first valid data interval
    shift = numpy.nonzero(numpy.diff(mask))[0][0]
    stimulus_flash_trigger_signal = numpy.zeros_like(mask)
    start_indexes = (numpy.nonzero(numpy.diff(mask))[0]-shift)[1::2]+delay_samples#Starts one sample later after last data valid pixel
    end_indexes = start_indexes + flash_samples
    for i in range(start_indexes.shape[0]):
        stimulus_flash_trigger_signal[start_indexes[i]:end_indexes[i]]=1
    #Shift mask back
    stimulus_flash_trigger_signal = numpy.roll(stimulus_flash_trigger_signal, shift+1)
    stimulus_flash_trigger_signal = numpy.tile(stimulus_flash_trigger_signal, signal_attributes['nxlines'])
    real_duty_cycle = float(stimulus_flash_trigger_signal.sum())/float(stimulus_flash_trigger_signal.shape[0])
    return stimulus_flash_trigger_signal, real_duty_cycle

if __name__ == "__main__":
    unittest.main()
