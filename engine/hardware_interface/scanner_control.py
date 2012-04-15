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

from visexpman.engine.generic import utils
from visexpman.engine.generic import configuration

import unittest

class ScannerTestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.SCANNER_MAX_SPEED = [50000, 40000]#um/s
        self.SCANNER_MAX_ACCELERATION = [3000000, 2000000] #um/s2
        self.SCANNER_ACCELERATION = 200000000
        self.SCANNER_SIGNAL_SAMPLING_RATE = 500000 #Hz
        self.SCANNER_DELAY = 0#As function of scanner speed
        self._create_parameters_from_locals(locals())

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
            v0 = line['v']
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
                v1 = line['v']
                ds, n = calculate_spatial_resolution(line['p0'], line['p1'], line['v'], dt)
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

def set_position_and_speed1(s0, s1, v0, v1, T, dt, Amax = None, omit_last = False):
    #Determine setting times
    if v1 != v0:
        Tset_position = 0.5 * T
        Tset_speed = 0.5 * T
    else:
        Tset_position = T
        Tset_speed = 0
    if check_position_setting_max_acceleration(s0, s1, v0, Tset_position, Amax) and check_speed_setting_max_acceleration(v0, v1, Tset_speed, Amax):
        is_safe = True
    else:
        is_safe = False
    #First adjust speed
    s_speed_up, v_speed_up, a_speed_up,  t_speed_up,  A_speed_up,  ds = set_speed(s0, v0, v1, Tset_speed, dt, omit_last)
    #Then position
    s_set_position, v_set_position, a_set_position, t_set_position, A_set_position = set_position(s0+ds,  s1,  v1, Tset_position, dt, omit_last)
    s = numpy.zeros(s_speed_up.shape[0] + s_set_position.shape[0])
    v = numpy.zeros_like(s)
    a = numpy.zeros_like(s)
    s[:s_speed_up.shape[0]] = s_speed_up
    s[s_speed_up.shape[0]:] = s_set_position
    v[:v_speed_up.shape[0]] = v_speed_up
    v[v_speed_up.shape[0]:] = v_set_position
    a[:a_speed_up.shape[0]] = a_speed_up
    a[a_speed_up.shape[0]:] = a_set_position
    t = time_vector(T,  dt)
    A = max(abs(A_speed_up), abs(A_set_position))
    return s, v, a, t, A, is_safe
    
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
def integral_function(y, dx, y0 = 0):
    Y = []
    for i in range(len(y)):
        if i == 0:
            Y.append(0)
        else:
            Y.append(y[:i].sum()*dx)
    Y = numpy.array(Y)+y0
    return Y

def time_vector(T, dt):
    return numpy.linspace(0.0,T,T/dt+1)

def plot_a_v_s(a, v, s, t):
    from matplotlib.pyplot import plot, show,figure,legend
    plot(t,a)
    plot(t,v)
    plot(t,s)
    legend(['a','v','s'])
    show()

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
        
    def test_03_generate_line_scans(self):
        lines = [
                 {'p0': utils.rc((0, -10)), 'p1': utils.rc((0, 10)), 'ds': 1.0}, 
                 {'p0': utils.rc((10, 10)), 'p1': utils.rc((10, -10)), 'ds': 1.0}, 
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
        pos_x, pos_y, speed_x, speed_y, accel_x, accel_y, scan_mask, period_time = generate_line_scan_series(lines, self.dt, setting_time, vmax, accmax, scanning_periods = 2, start_stop_time = start_stop_time)
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

if __name__ == "__main__":
    unittest.main()


#import numpy
#from matplotlib.pyplot import plot, show,legend
#
#def calculate_parameters(s0,s1,v0,v1,T):
#    ds = s1-s0
#    dv = v1-v0
#    a = s0
#    b = v0
#    def_parameters = numpy.matrix([[T**3,T**4,T**5],[3*T**2,4*T**3,5*T**4],[3, 6*T, 10*T**2]])
#    def_values = numpy.linalg.inv(def_parameters)*numpy.matrix([ds-v0*T, dv, 0]).T
#    d,e,f = numpy.array(def_values).T[0].tolist()
#    #Maximal speed
#    vmax = []
#    discr = 36*e**2-120*d*f
#    if discr >= 0 and f != 0:
#        tvmax1 = (-6*e - numpy.sqrt(discr))/(20*f)
#        tvmax2 = (-6*e + numpy.sqrt(discr))/(20*f)
#        if 0  <= tvmax1 and tvmax1 <= T:
#            t = tvmax1
#            vmax.append(b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4)
#        if 0  <= tvmax2 and tvmax2 <= T:
#            t = tvmax2
#            vmax.append(b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4)
#    #Maximal acceleration
#    amax = []
#    discr = 16*e**2-40*d*f
#    if discr >= 0 and f != 0:
#        tamax1 = (-4*e - numpy.sqrt(discr))/(20*f)
#        tamax2 = (-4*e + numpy.sqrt(discr))/(20*f)
#        if 0  <= tamax1 and tamax1 <= T:
#            t = tamax1
#            amax.append(6*d*t + 12*e*t**2 + 20*f*t**3)
#        if 0  <= tamax2 and tamax2 <= T:
#            t = tamax2
#            amax.append(6*d*t + 12*e*t**2 + 20*f*t**3)
#    return a,b,d,e,f, vmax, amax
#    
#def set_position_and_speed(s0, s1, v0, v1, T, dt, Amax = None, omit_last = False):
#    t = numpy.linspace(0,T,T/dt+1)
#    ds = s1-s0
#    dv = v1-v0
#    #Polinom parameters
#    a,b,d,e,f,vmax, amax = calculate_parameters(s0,s1,v0,v1,T)
#    s = a + b*t + d*t**3 + e*t**4 + f*t**5
#    v = b + 3*d*t**2 + 4*e*t**3 + 5*f*t**4
#    a = 6*d*t + 12*e*t**2 + 20*f*t**3
#    A = abs(a).max()
#    is_safe  = True
#    if omit_last:
#        t = t[:-1]
#        s = s[:-1]
#        v = v[:-1]
#        a = a[:-1]
#    return s, v, a, t, A, is_safe
#    
#
#
#v0 = -100.0
#v1 = 2.0
#s0 = 10.0
#s1 = 0.0
#T = 10.0
#dt = 1e-3
#s, v, a, t, A, is_safe = set_position_and_speed(s0, s1, v0, v1, T, dt)
#plot(t,a)
#plot(t,v)
#plot(t,s)
#legend(['a','v','s'])
#show()
