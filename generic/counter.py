import ctypes
import ctypes.wintypes
import unittest,time,os

class Counter(object):
    def __init__(self):
        if os.name!='nt':
            raise NotImplementedError()
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.frequency = ctypes.wintypes.LARGE_INTEGER()
        self.kernel32.QueryPerformanceFrequency(ctypes.byref(self.frequency)) 
        self.value=ctypes.wintypes.LARGE_INTEGER()
        
    def read(self, microseconds=True):
        self.kernel32.QueryPerformanceCounter(ctypes.byref(self.value))
        if microseconds:
            return int(self.value.value/float(self.frequency.value)*1e6)
        else:
            return self.value.value
        
    def wait(self, duration):
        self.kernel32.QueryPerformanceCounter(ctypes.byref(self.value))
        expected=int(duration*self.frequency.value)+self.value.value
        while True:
            self.kernel32.QueryPerformanceCounter(ctypes.byref(self.value))
            if self.value.value>expected:
                break
            time.sleep(0)
        
class Test(unittest.TestCase):
    def test_counter(self):
        c=Counter()
        t1=c.read()
        c.wait(1e-3)
        t2=c.read()
        print(t2-t1)
        self.assertTrue(t2-t1<1300)
        
if __name__ == "__main__":
    unittest.main()
