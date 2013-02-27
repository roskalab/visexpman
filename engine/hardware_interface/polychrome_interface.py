import instrument
import unittest
import ctypes
import os.path
import os

class Polychrome(instrument.Instrument):
    '''
    Thorlabs PM100USB interface
    '''
    def init_instrument(self):
        '''
        Method for initialize the instrument
        '''
        if os.name == 'nt':
            self.dllref = ctypes.WinDLL(os.path.join(config.BASE_PATH,'till','TILLPolychrome.dll'))
            self.handle = ctypes.c_void_p()
            self.dllref.TILLPolychrome_Open(ctypes.pointer(self.handle),ctypes.c_int(0))
            return (self.handle,self.dllref)
        else:
            print 'Polychrome not supported on this OS'
        
    def set_wavelength(self, wavelength):
        if os.name == 'nt':
            self.handle[1].TILLPolychrome_SetRestingWavelength(self.handle[0],ctypes.c_double(float(wavelength)))
        
    def get_intensity_range(self):
        motorized_control = ctypes.c_bool()
        min_intensity = ctypes.c_double()
        max_intensity = ctypes.c_double()
        self.handle[1].TILLPolychrome_GetIntensityRange(self.handle[0],ctypes.pointer(motorized_control),ctypes.pointer(min_intensity),ctypes.pointer(max_intensity))
        return motorized_control,min_intensity,max_intensity
        
    def close_instrument(self):
        '''
        Closes instrument, after this the instrument object has to be recreated.
        '''
        if os.name == 'nt':
            self.handle[1].TILLPolychrome_Close(self.handle[0])

class TestPolychrome(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_01_lightmeter(self):
        p = Polychrome(None)
        p.set_wavelength(500)
        p.release_instrument()

if __name__ == "__main__":
    unittest.main()
