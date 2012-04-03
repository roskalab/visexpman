'''
Setting scanner position and speed

Factors limiting setting time:
- maximal acceleration - Tmin
- maximal speed - Tmin

Extreme setting: big movement, short setting time, big speed change
'''

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
        
def generate_line_scan_series(lines, dt, setting_time, vmax, accmax):
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
                                                set_position_and_speed(p0['col'], line['p0']['col'], v0['col'], v1['col'], setting_time, dt, Amax = a_limits['col'])
        line_out['set_pos_y'], line_out['set_speed_y'], line_out['set_accel_y'], t, A, connect_line_y_safe = \
                                                set_position_and_speed(p0['row'], line['p0']['row'], v0['row'], v1['row'], setting_time, dt, Amax = a_limits['row'])
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
    #Connect final line scan with initial position to ensure periodic scanning
    carriage_return_time = 2 * setting_time
    pos_carriage_return_x, speed_carriage_return_x, accel_carriage_return_x, t, A, is_safe_x = set_position_and_speed(p0['col'], p_initial['col'], v0['col'], v_initial['col'], carriage_return_time, dt, Amax = a_limits['col'])
    pos_carriage_return_y, speed_carriage_return_y, accel_carriage_return_y, t, A, is_safe_y = set_position_and_speed(p0['row'], p_initial['row'], v0['row'], v_initial['row'], carriage_return_time, dt, Amax = a_limits['row'])
    scan_signal_length_counter += pos_carriage_return_x.shape[0]
    #Concetanate scan signals
    pos_x = numpy.zeros(scan_signal_length_counter-3)
    pos_y = numpy.zeros_like(pos_x)
    speed_x = numpy.zeros_like(pos_x)
    speed_y = numpy.zeros_like(pos_x)
    accel_x = numpy.zeros_like(pos_x)
    accel_y = numpy.zeros_like(pos_x)
    index = 0
    for line_out in lines_out:
        pos_x[index:index + line_out['set_pos_x'].shape[0]-1] = line_out['set_pos_x'][:-1]
        pos_y[index:index + line_out['set_pos_y'].shape[0]-1] = line_out['set_pos_y'][:-1]
        speed_x[index:index + line_out['set_speed_x'].shape[0]-1] = line_out['set_speed_x'][:-1]
        speed_y[index:index + line_out['set_speed_y'].shape[0]-1] = line_out['set_speed_y'][:-1]
        accel_x[index:index + line_out['set_accel_x'].shape[0]-1] = line_out['set_accel_x'][:-1]
        accel_y[index:index + line_out['set_accel_y'].shape[0]-1] = line_out['set_accel_y'][:-1]
        index += line_out['set_pos_y'].shape[0]-1
        print index
        pos_x[index:index + line_out['scan_pos_x'].shape[0]-1] = line_out['scan_pos_x'][:-1]
        pos_y[index:index + line_out['scan_pos_y'].shape[0]-1] = line_out['scan_pos_y'][:-1]
        speed_x[index:index + line_out['scan_speed_x'].shape[0]-1] = line_out['scan_speed_x'][:-1]
        speed_y[index:index + line_out['scan_speed_y'].shape[0]-1] = line_out['scan_speed_y'][:-1]
        accel_x[index:index + line_out['scan_accel_x'].shape[0]-1] = line_out['scan_accel_x'][:-1]
        accel_y[index:index + line_out['scan_accel_y'].shape[0]-1] = line_out['scan_accel_y'][:-1]
        index += line_out['scan_pos_y'].shape[0]-1
        print index
    pos_x[index:index + pos_carriage_return_x.shape[0]-1] = pos_carriage_return_x[:-1]
    pos_y[index:index + pos_carriage_return_y.shape[0]-1] = pos_carriage_return_y[:-1]
    speed_x[index:index + speed_carriage_return_x.shape[0]-1] = speed_carriage_return_x[:-1]
    speed_y[index:index + speed_carriage_return_y.shape[0]-1] = speed_carriage_return_y[:-1]
    accel_x[index:index + accel_carriage_return_x.shape[0]-1] = accel_carriage_return_x[:-1]
    accel_y[index:index + accel_carriage_return_y.shape[0]-1] = accel_carriage_return_y[:-1]
    
    from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
    figure(1)
    subplot(311)
    plot(pos_x)
    title('position')
    subplot(312)
    plot(speed_x)
    title('speed')
    subplot(313)
    plot(accel_x)
    title('acceleration')
    savefig('/home/zoltan/visexp/debug/data/x.pdf')
    pass
    
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
    return x_scanner_trajectory, y_scanner_trajectory, scanner_speed, is_safe

def check_position_setting_max_acceleration(s0, s1, v0, T, Amax):
    C1 = -2/(3*numpy.sqrt(3))
    ds = s1-s0
    A = (ds - v0 * T) * C1 * 15 / T**2
    return (A <= Amax)
    
def check_speed_setting_max_acceleration(v0, v1, T, Amax):
    A = numpy.pi/T*(v1-v0)/2 
    return (A <= Amax)

def set_position(s0,  s1,  v0,  T,  dt):
    '''
    Generates a curve that connects s0 position with s1 such that at the end the speed is v0 and the acceleration is 0.
    Inputs: s0: initial position
    s1: final position
    v0: initial/final speed
    T: time of movement in s
    dt: time resolution in s
    Outputs:
    s: generated trajectory
    v: speed of movement along generated trajectory
    a: acceleration of movement along generated trajectory
    t: time vector
    A: maximal acceleration
    '''
    C1 = -2/(3*numpy.sqrt(3))
    tau = 0.5 * T
    ds = s1 - s0
    if ds != v0*T:
        A = (ds - v0 * T) * C1 * 15 / T**2
    else:
        A = 1e-6*C1*15/T**2 #allowing 1 ppm change in speed
    C = A/C1
    t = time_vector(T,  dt)
    s = C*(t**5/(20*tau**3)-t**4/(4*tau**2)+t**3/(3*tau))+v0*t+s0
    v = C*(t**4/(4*tau**3)-t**3/(tau**2)+t**2/(tau)) + v0
    a = C*(t**3/(tau**3)-3*t**2/(tau**2)+2*t/tau)
    return s,  v,  a, t,  abs(A)
    
def set_speed(s0, v0, v1, T, dt):
    '''
    Generates a curve that changes trajectory speed from v0 to v1 such that at the end the acceleration is 0.
    Inputs: s0: initial position
    v0: initial speed
    v1: final speed
    T: time of movement in s
    dt: time resolution in s
    Outputs:
    s: generated trajectory
    v: speed of movement along generated trajectory
    a: acceleration of movement along generated trajectory
    t: time vector
    A: maximal acceleration
    ds: position change after setting speed
    '''
#    tau = 0.5 * T
#    dv = v1 - v0
    t = time_vector(T,  dt)
#    tmaxaccel = tau * (9+numpy.sqrt(17))/8
#    Ascale = tmaxaccel*(((tmaxaccel-tau)/(tau))**3 - tmaxaccel/(tau)+1)
#    A = - dv * Ascale * 15 / T**2
#    C = A/Ascale
#    s = C * (t**6/(30*tau**3) - 3*t**5/(20*tau**2)+t**4/(6*tau)) + v0*t + s0
#    ds = v0 * T
#    a = C*t*(((t-tau)/(tau))**3 - t/(tau)+1) #refactored to polynom: a = C*(t**4/tau**3-3*t**3/tau**2+2*t**2/tau)
#    v = C*(t**5/(5*tau**3)-3*t**4/(4*tau**2)+2*t**3/(3*tau))+v0
    a = numpy.pi/T*(v1-v0)/2*numpy.sin(numpy.pi*t/T)
    v = -(v1-v0)/2*numpy.cos(numpy.pi*t/T)+v0 + 0.5*(v1-v0) 
    s = -(v1-v0)/2*T/numpy.pi*numpy.sin(numpy.pi*t/T)+(v0 + 0.5*(v1-v0))*t+s0 
    A = numpy.pi/T*(v1-v0)/2 
    ds = (v0+v1)/2*T 
    return s, v, a,  t,  abs(A),  ds
    
    
    
def set_position_and_speed(s0, s1, v0, v1, T, dt, Amax = None):
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
    #TODO: do not generate set speed curve when v1==v0
    #First adjust speed
    s_speed_up, v_speed_up, a_speed_up,  t_speed_up,  A_speed_up,  ds = set_speed(s0, v0, v1, Tset_speed, dt)
    #Then position
    s_set_position, v_set_position, a_set_position, t_set_position, A_set_position = set_position(s0+ds,  s1,  v1, Tset_position, dt)
    s = numpy.zeros(s_speed_up.shape[0] + s_set_position.shape[0])
    v = numpy.zeros_like(s)
    a = numpy.zeros_like(s)
    t = numpy.zeros_like(s)
    s[:s_speed_up.shape[0]] = s_speed_up
    s[s_speed_up.shape[0]:] = s_set_position
    v[:v_speed_up.shape[0]] = v_speed_up
    v[v_speed_up.shape[0]:] = v_set_position
    a[:a_speed_up.shape[0]] = a_speed_up
    a[a_speed_up.shape[0]:] = a_set_position
    t = time_vector(T,  dt)
    A = max(abs(A_speed_up), abs(A_set_position))
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
    
def time_vector(T,  dt):
    return numpy.linspace(0.0,T,T/dt)


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
        
    def test_01_set_position(self):       
        inputs = [
                  {'s0': 0.0, 's1':1.0, 'v0':1.0,  'T': 1.0}, 
                  {'s0': -10.0, 's1':1.0, 'v0':0.0,  'T': 1.0}, 
                  {'s0': -10.0, 's1':0.0, 'v0':-4.0,  'T': 10.0}, 
                  {'s0': 10.0, 's1':20.0, 'v0':-4.0,  'T': 0.1}, 
                  {'s0': 10.0, 's1':4.0, 'v0':100.0,  'T': 1.0}, 
                  {'s0': 1e-3, 's1':-1000.0, 'v0':0.01,  'T': 0.01},
                  {'s0': 0.5, 's1':100.0, 'v0':1.0,  'T': 0.05},
                  ]
        
        results = []
        max_error = 1e-5
        for input in inputs:
            s0 = input['s0']
            s1 = input['s1']
            v0 = input['v0']
            T = input['T']
            s, v, a, t, A = set_position(s0,  s1,  v0,  T, self.dt)
            ds_error = (s0-s1) - (s[0]-s[-1])
            if ds_error < max_error:
                ds_error = 0.0
            dv_error = v[0]-v[-1]
            if dv_error < max_error:
                dv_error = 0.0
            max_acceleration_error = abs(a).max() - A
            if max_acceleration_error < max_error:
                max_acceleration_error = 0.0
            results.append([ds_error, dv_error, a[0], a[-1],  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
    
    def test_02_set_speed(self):
        inputs = [
                  {'s0': 1.0, 'v0':0.0, 'v1':2.0,  'T': 1.0}, 
                  {'s0': 0.0, 'v0':-10.0, 'v1':10.0,  'T': 1.0}, 
                  {'s0': 0.0, 'v0':-10.0, 'v1':1.0,  'T': 1.0}, 
                  {'s0': 3.0, 'v0':10.0, 'v1':1.0,  'T': 1.0}, 
                  {'s0': -3.0, 'v0':10.0, 'v1':1.0,  'T': 0.1}, 
                  ]
        
        results = []
        max_error = 1e-5
        for input in inputs:
            s0 = input['s0']
            v0 = input['v0']
            v1 = input['v1']
            T = input['T']
            s, v, a,  t,  A,  ds = set_speed(s0, v0, v1, T, self.dt)
#            plot_a_v_s(a, v, s, t)            
            ds_error = ds - (s[-1]-s[0])
            if ds_error < max_error:
                ds_error = 0.0
            dv_error = (v0-v1) - (v[0]-v[-1])
            if dv_error < max_error:
                dv_error = 0.0
            max_acceleration_error = abs(a).max() - A
            if max_acceleration_error < max_error:
                max_acceleration_error = 0.0
            if a[0] < max_error:
                a[0] = 0.0
            if a[-1] < max_error:
                a[-1] = 0.0
            results.append([ds_error, dv_error, a[0], a[-1],  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
        
    def test_03_set_position_and_speed(self):
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
            results.append([ds_error, dv_error, a[0], a[-1],  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
        
    def test_04_set_speed_position_withmax_acceleration(self):
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
            results.append([ds_error, dv_error, a[0], a[-1],  max_acceleration_error])
        self.assertListEqual(results, len(results)*[5*[0.0]])
    def test_05_generate_line_scans(self):
        lines = [
                 {'p0': utils.rc((0, 0)), 'p1': utils.rc((30, 30)), 'ds': 1.0}, 
                 {'p0': utils.rc((0, 0)), 'p1': utils.rc((30, 30)), 'ds': 1.0}, 
                 {'p0': utils.rc((0, 0)), 'p1': utils.rc((30, 30)), 'ds': 1.0}, 
                 ]
        setting_time = 1.0
        accmax = 1000
        vmax = 500
        generate_line_scan_series(lines, self.dt, setting_time, vmax, accmax)

if __name__ == "__main__":
    unittest.main()
    
#    from matplotlib.pyplot import plot, show,figure,legend
#    v0 = 0
#    s0=0
#    T = 1.0
#    k = 0.5
#    A = 1.0
#    dt = 1e-2
#    t= time_vector(T, dt)
#    t1 = time_vector(T*k, dt)
#    a1 = t1 * A/(k*T)
#    t2 = time_vector(T - k*T, dt)+k*T
#    a2 = -A * t2/(T*(1-k)) + A*k/(1-k) + A
#    a = numpy.concatenate((a1, a2))
#    
#    v1 = t1**2/2*A/(k*T)+v0
#    v2 = -A*t2**2/(2*T*(1-k)) + A*t2/(1-k) + v0
#    v = numpy.concatenate((v1, v2))
#    
#    s1 = t1**3/6*A/(k*T)+v0*t1+s0
#    s2 = -A*t2**3/(6*T*(1-k))+A*t2**2/(2*(1-k)) + v0*t2 + s0
#    s = numpy.concatenate((s1, s2))
#    
#    v = integral_function(a, dt)
#    s = integral_function(v, dt)
#    
#    plot(t, a)
#    plot(t, v)
#    plot(t, s)
#    show()
    
#    T = 0.01
#    v0 = 1.0
#    v1 = 0.0
#    s0 = 1.0
#    s1 = -10.0
#    dt = 1e-6
#    s,  t,  A = set_position(s0, s1, v0, T, dt)
#    s,  t,  A,  ds,  a,  v = set_speed(s0, v0, v1, T,  dt)
#    print ds    
#    print max(abs(a)), abs(A)
#    plot(t,a)
#    plot(t,v)
#    plot(t,s)
#    legend(['a','v','s'])
#    show()
