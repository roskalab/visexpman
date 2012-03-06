import numpy

from visexpman.engine.generic import utils
from visexpman.engine.generic import configuration

import unittest

class ScannerControl(object):
    def __init__(self, config):
        self.config = config
        
    def connect_scans(self,trajectory1,trajectory2, max_speed, max_acceleration):
        '''
        Connects trajectory1 with trajectory2 ensuring that the acceleration and 
        the speed of the scanner will not exceed hardware limits.
        (trajectory1 and trajectory2 are 1D numpy arrays)
        
        Between two line scans the speed and the position of the scanner shall be adjusted.
        
        
        
        
        
        '''
        trajectory1_speed = (trajectory1[-1] - trajectory1[0])/(trajectory1.shape[0] / self.config.SCANNER_SIGNAL_SAMPLING_RATE)
        trajectory2_speed = (trajectory2[-1] - trajectory2[0])/(trajectory2.shape[0] / self.config.SCANNER_SIGNAL_SAMPLING_RATE)
        positioning_movement = trajectory2[0] - trajectory1[-1]
        
        
    def adjust_scanner(self, s0, s1, v0, v1, adjust_time):
        dv = v1-v0
        a = dv / adjust_time
        if a > self.config.SCANNER_MAX_ACCELERATION:
            a = self.config.SCANNER_MAX_ACCELERATION
        dt = 1.0/self.config.SCANNER_SIGNAL_SAMPLING_RATE
        t = numpy.linspace(0, adjust_time-dt, adjust_time/dt)
        s = s0 + v0 * t + 0.5 * a * t ** 2
        return s
        
    def accelerate_scanner(self, s0, v0, v1, t_acceleration):
        dv = v1-v0
        a = dv / t_acceleration
        if a > self.config.SCANNER_MAX_ACCELERATION:
            a = self.config.SCANNER_MAX_ACCELERATION
        dt = 1.0/self.config.SCANNER_SIGNAL_SAMPLING_RATE
        t = numpy.linspace(0, t_acceleration-dt, t_acceleration/dt)
        s = s0 + v0 * t + 0.5 * a * t ** 2
        return s
    
    def line_scan_trajectory(self, start_point, end_point, spatial_resolution):
        '''
        Input parameters:
        start_point: x,y coordinates of starting point of scanned line in um
        end_ point: x,y coordinates of endpoint of scanned line in um
        spatial_resolution: points per um
        Output:
        x values of trajectory
        y values of trajectory
        '''
        #Check whether maximal speed in not exceeded
        movement = numpy.sqrt(((start_point - end_point)**2).sum())
        number_of_points = int(movement * spatial_resolution)
        movement_time = float(number_of_points) / self.config.SCANNER_SIGNAL_SAMPLING_RATE
        
        movement_per_axis = abs(start_point - end_point)
        speeds_per_axis = movement_per_axis / movement_time
        if speeds_per_axis[0] <= self.config.SCANNER_MAX_SPEED[0] and \
                speeds_per_axis[1] <= self.config.SCANNER_MAX_SPEED[1]:
            #If speed of required movement is below speed limit, then positions for individual axes calculated
            scanner_control_x = numpy.linspace(start_point[0], end_point[0], number_of_points)
            scanner_control_y = numpy.linspace(start_point[1], end_point[1], number_of_points)
            scanner_control = numpy.array([scanner_control_x, scanner_control_y])
        else:
            scanner_control = None
        return scanner_control
        
class ScannerTestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.SCANNER_MAX_SPEED = [50000, 40000]#um/s
        self.SCANNER_MAX_ACCELERATION = [3000000, 2000000] #um/s2
        self.SCANNER_ACCELERATION = 200000000
        self.SCANNER_SIGNAL_SAMPLING_RATE = 500000 #Hz
        self.SCANNER_DELAY = 0#As function of scanner speed
        
        self._create_parameters_from_locals(locals())

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
    return numpy.linspace(0.0,T,T/dt+1)

def set_position(s0,  s1,  v0,  T,  dt):
    C1 = -2/(3*numpy.sqrt(3))
    tau = 0.5 * T
    ds = s1 - s0
    A = (ds - v0 * T) * C1 * 15 / T**2
    C = A/C1
    t = time_vector(T,  dt)
    s = C*(t**5/(20*tau**3)-t**4/(4*tau**2)+t**3/(3*tau))+v0*t+s0
    return s,  t,  A
    
def set_speed(s0, v0, v1, T,  dt):
    C1 = -2/(3*numpy.sqrt(3))
    tau = 0.5 * T
    dv = v1 - v0
    A = - dv * C1 * 15 / T**2
    t = time_vector(T,  dt)
    tmaxaccel = tau * (9+numpy.sqrt(17))/8
    Ascale = tmaxaccel*(((tmaxaccel-tau)/(tau))**3 - tmaxaccel/(tau)+1)
    C = A/Ascale
    s = C * (t**6/(30*tau**3) - 3*t**5/(20*tau**2)+t**4/(6*tau)) + v0*t + s0
    ds = v0 * T
    a = C*t*(((t-tau)/(tau))**3 - t/(tau)+1)
    v = C*(t**5/(5*tau**3)-3*t**4/(4*tau**2)+2*t**3/(3*tau))+v0
    return s,  t,  A,  ds,  a,  v
    
if __name__ == "__main__":
    
    from matplotlib.pyplot import plot, show,figure,legend
    T = 0.01
    v0 = 1.0
    v1 = 0.0
    s0 = 1.0
    s1 = -10.0
    dt = 1e-6
    s,  t,  A = set_position(s0, s1, v0, T, dt)
    
    s,  t,  A,  ds,  a,  v = set_speed(s0, v0, v1, T,  dt)
    print ds    
    print max(abs(a)), abs(A)
    
    
    plot(t,a)
    plot(t,v)
    plot(t,s)
    legend(['a','v','s'])
    show()
#    figure(1)
#    plot(s)
#    figure(2)
#    plot(numpy.diff(s)*sc.config.SCANNER_SIGNAL_SAMPLING_RATE)
#    show()
