from . import instrument
import time
import ctypes
import os
import os.path
import unittest

class VideoCamera(instrument.Instrument):
    def __init__(self, config):
        self.config = config
        self._init_camera()
        
    def start(self):
        pass
        
    def stop(self):
        pass
        
    def save(self):
        pass
        
    def _init_camera(self):
        pass
        
    def close(self):
        pass

class ImagingSourceCamera(VideoCamera):
    def _init_camera(self):
        dllpath = r'c:\tis\bin\win32\tisgrabber.dll'
        wd = os.getcwd()
        os.chdir(os.path.dirname(dllpath))
        self.dllref = ctypes.windll.LoadLibrary(dllpath)
        os.chdir(wd)
        if self.dllref.IC_InitLibrary(None) != 1:
            raise RuntimeError('Initializing TIS library did not succeed')
        self.grabber_handle = self.dllref.IC_CreateGrabber()
        cam_name = 'DMK 22BUC03'
        cam_name = ctypes.c_char_p(cam_name)
        if self.dllref.IC_OpenVideoCaptureDevice(self.grabber_handle, cam_name) != 1:
            raise RuntimeError('Opening video capture device did not succeed')
        video_format = ctypes.c_char_p('RGB24')
        print(self.dllref.IC_SetVideoFormat(self.grabber_handle,video_format))
        self.isrunning = False
        
    def start(self):
        if not self.isrunning:
            print(self.dllref.IC_StartLive(self.grabber_handle, 0))
        else:
            raise RuntimeError('Camera is alredy recording')
        
    def save(self):
        image_path = ctypes.c_char_p('c:\\_del\\d.jpeg')
        print(self.dllref.IC_SaveImage(self.grabber_handle,  image_path, 1, 100))
        
    def stop(self):
        if self.isrunning:
            self.dllref.IC_StopLive(self.grabber_handle)
            
    def close(self):
        self.dllref.IC_CloseVideoCaptureDevice(self.grabber_handle) 
#        self.dllref.IC_ReleaseGrabber(self.grabber_handle)
        self.dllref.IC_CloseLibrary()

class TestCamera(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass
        
    def test_01_record_some_frames(self):
        cam = ImagingSourceCamera(None)
        cam.start()
        time.sleep(1.0)
        cam.stop()
        cam.save()
        cam.close()

if __name__ == '__main__':
    unittest.main()
