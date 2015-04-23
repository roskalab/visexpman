import instrument
import unittest
import ctypes
import os.path
import os
import time
import visexpman

class Polychrome(instrument.Instrument):
    '''
    
    '''
    def init_instrument(self):
        '''
        Method for initialize the instrument
        '''
        if os.name == 'nt':
            self.dllref = ctypes.WinDLL(os.path.join(os.path.split(visexpman.__file__)[0],'engine', 'external', 'till','TILLPolychrome.dll'))
            self.handle = ctypes.c_void_p()
            self.dllref.TILLPolychrome_Open(ctypes.pointer(self.handle),ctypes.c_int(0))
            self.bandwidth = 15.0
            return (self.handle,self.dllref)
        else:
            print 'Polychrome not supported on this OS'
        
    def set_wavelength(self, wavelength, duration = 0.01,  blocking = False):
        if os.name == 'nt':
            self.dllref.TILLPolychrome_SetWavelength(self.handle,ctypes.c_double(float(wavelength)), ctypes.c_double(float(duration*1000)), ctypes.c_bool(False))
            if blocking:
                time.sleep(duration)
            
    def set_resting_wavelength(self, wavelength):
        if os.name == 'nt':
            self.dllref.TILLPolychrome_SetRestingWavelength(self.handle,ctypes.c_double(float(wavelength)))
        
    def get_intensity_range(self):
        motorized_control = ctypes.c_bool()
        min_intensity = ctypes.c_double()
        max_intensity = ctypes.c_double()
        self.dllref.TILLPolychrome_GetIntensityRange(self.handle,ctypes.pointer(motorized_control),ctypes.pointer(min_intensity),ctypes.pointer(max_intensity))
        return motorized_control,min_intensity,max_intensity
        
    def get_bandwidth(self):
        minimum = ctypes.c_double()
        maximum = ctypes.c_double()
        startup = ctypes.c_double()
        self.dllref.TILLPolychrome_GetBandwidthRange(self.handle,ctypes.pointer(minimum),ctypes.pointer(maximum),ctypes.pointer(startup))
        return minimum.value,maximum.value,startup.value
        
    def set_intensity(self, intensity):
        if os.name == 'nt':
            bandwidth = ctypes.c_double(self.bandwidth)
            intensity = ctypes.c_double(float(intensity))
            self.dllref.TILLPolychrome_SetBandwidth(self.handle, bandwidth, intensity)
    
    def close_instrument(self):
        '''
        Closes instrument, after this the instrument object has to be recreated.
        '''
        if os.name == 'nt':
            self.dllref.TILLPolychrome_Close(self.handle)

from visexpman.engine.vision_experiment import configuration
class PolyTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):     
        COORDINATE_SYSTEM='center'
        self._create_parameters_from_locals(locals())
            
class TestPolychrome(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_01_poly(self):
        cfg = PolyTestConfig()
        p = Polychrome(cfg)
        print p.get_intensity_range()
        print p.get_bandwidth()
        p.set_intensity(1.0)
#         time.sleep(1.0)
#         p.set_wavelength(450)
#         time.sleep(1.0)
#         p.set_wavelength(500)
#         time.sleep(1.0)
        p.set_wavelength(480, duration = 1.0)
#        time.sleep(1.0)
#        p.set_intensity(0.0)
#        time.sleep(1.0)
#        p.set_intensity(1.0)
#        time.sleep(1.0)
#        p.set_intensity(0.5)
#        time.sleep(1.0)
#        p.set_intensity(0.0)
        p.release_instrument()

if __name__ == "__main__":
    unittest.main()
