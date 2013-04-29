import copy
from visexpman.engine.generic.introspect import Timer
import numpy
import instrument
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
        if hasattr(self.config, 'VIDEO_FORMAT'):
            self.video_format = ctypes.c_char_p(self.config.VIDEO_FORMAT)
        else:
            self.video_format = ctypes.c_char_p('RGB24 (744x480)')
        if self.dllref.IC_SetVideoFormat(self.grabber_handle,self.video_format) != 1:
            raise RuntimeError('Setting video format did not succeed')
        self.w = self.dllref.IC_GetVideoFormatWidth(self.grabber_handle)
        self.h = self.dllref.IC_GetVideoFormatHeight(self.grabber_handle)
        self.bytes_per_pixel = 3
        self.frame_size = self.h * self.w * self.bytes_per_pixel
        self.frame_shape = (self.h, self.w)
        if hasattr(self.config, 'CAMERA_FRAME_RATE'):
            self.frame_rate = self.config.CAMERA_FRAME_RATE
        else:
            self.frame_rate = 30.0
        if self.dllref.IC_SetFrameRate(self.grabber_handle,  ctypes.c_float(self.frame_rate)) != 1:
            raise RuntimeError('Setting frame rate did not succeed')
        self.snap_timeout = self.dllref.IC_GetFrameRate(self.grabber_handle)
        self.isrunning = False
        self.frame_counter = 0
        self.framep = []
        self.frames = []
#        self.video = numpy.zeros((1, self.h, self.w), numpy.uint8)
        
    def start(self):
        if not self.isrunning:
            if self.dllref.IC_StartLive(self.grabber_handle, 1) == 1:
                self.isrunning = True
        else:
            raise RuntimeError('Camera is alredy recording')
            
    def save(self):
        if self.dllref.IC_SnapImage(self.grabber_handle, int(self.snap_timeout)) == 1:
            addr = self.dllref.IC_GetImagePtr(self.grabber_handle)
            p = ctypes.cast(addr, ctypes.POINTER(ctypes.c_byte))
            buffer = numpy.core.multiarray.int_asbuffer(ctypes.addressof(p.contents), self.frame_size)
            frame = copy.deepcopy(numpy.reshape(numpy.frombuffer(buffer, numpy.uint8)[::3], self.frame_shape))
            self.frames.append(frame)
#            self.framep.append(p)

            if False or (False and self.frame_rate <= 7.5):
                image_path = ctypes.c_char_p('c:\\_del\\frame\\d{0}.jpeg'.format(self.frame_counter+1000))
                self.dllref.IC_SaveImage(self.grabber_handle, image_path, 1, 90)
            self.frame_counter += 1
#            import gc
#            gc.collect
            time.sleep(1e-3)
        
    def stop(self):
        if self.isrunning:
            self.isrunning = False
            self.dllref.IC_StopLive(self.grabber_handle)
            self.video = numpy.array(self.frames)            
#            if len(self.frames)>200:
#                self.video = numpy.array(self.frames)
#            else:
#                self.video = numpy.concatenate(tuple(self.frames))
#            self.video = numpy.array(self.frames)
#            self.video = numpy.zeros((len(self.framep), self.h, self.w), numpy.uint8)
#            for i in range(len(self.framep)):
#                buffer = numpy.core.multiarray.int_asbuffer(ctypes.addressof(self.framep[i].contents), self.frame_size)
#                self.video[i, :, :] = copy.deepcopy(numpy.reshape(numpy.frombuffer(buffer, numpy.uint8)[::3], self.frame_shape))
#                self.video[i, :, :] = numpy.reshape(numpy.array(self.framep[i][0:frame_size])[::3], frame_shape)
            return
            import tiffile
            from visexpman.engine.generic import file
            tiffile.imsave(file.generate_filename('c:\\_del\\calib.tiff'), self.video, software = 'visexpman')
            import Image
            Image.fromarray(numpy.cast['uint8'](self.video.mean(axis=0))).show()
            
    def close(self):
        self.dllref.IC_CloseVideoCaptureDevice(self.grabber_handle) 
        self.dllref.IC_CloseLibrary()
                
class TestCamera(unittest.TestCase):
    def test_01_record_some_frames(self):
        cam = ImagingSourceCamera(None)
        cam.start()
        with Timer(''):
            while cam.frame_counter <= 30*30: 
                cam.save()
        with Timer(''):
            cam.stop()
        cam.close()

if __name__ == '__main__':
    unittest.main()
