import copy
from visexpman.engine.generic.introspect import Timer
import numpy
from contextlib import closing
import instrument
import time
import ctypes
import os
import os.path
import unittest
import cv2
from visexpman.engine.generic import configuration
from visexpman.engine.generic import fileop
import tables

class VideoCamera(instrument.Instrument):
    def __init__(self, config,debug=False):
        self.config = config
        self.debug=debug
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

class OpenCVCamera(VideoCamera):
    def start(self, recording_length_s, filename):
        if self.config.SHOW_PREVIEW_WINDOW:
            self.preview_window=cv2.namedWindow("preview")
        else:
            self.preview_window=None
        #import motmot.cam_iface.cam_iface_ctypes as cam_iface
        grabber_handle = cv2.VideoCapture(0)
        if hasattr(self.config, 'CAMERA_WIDTH_PIXELS'):
            self.w = self.config.CAMERA_WIDTH_PIXELS
        else: 
            self.w = 640
        if hasattr(self.config, 'CAMERA_HEIGHT_PIXELS'):
            self.h = self.config.CAMERA_HEIGHT_PIXELS
        else:
            self.h=480
        grabber_handle.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,self.w)
        grabber_handle.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,self.h)
        grabber_handle.set(cv2.cv.CV_CAP_PROP_FPS, 15)
        #if hasattr(self.config, 'CAMERA_FRAME_RATE'):
           # self.frame_rate = self.config.CAMERA_FRAME_RATE
        #else:
        if grabber_handle.isOpened(): # try to get the first frame
            rval, frame = grabber_handle.read()
        else:
            rval = False
        with closing(tables.open_file(filename, 'w')) as h1:
            h1.create_earray(h1.root, 'rawdata', tables.UInt8Atom((self.h, self.w)), (0, ), 'Intrinsic', filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1))
            h1.create_earray(h1.root, 'timestamps', tables.Float64Atom((1, )), (0, ), 'Frame timestamps')
            h1.root.timestamps.append(time.time())
            while rval and h1.root.timestamps[-1][0]-h1.root.timestamps[0][0]<recording_length_s:
                if self.preview_window is not None:
                    cv2.imshow("preview", frame)
                rval, frame = grabber_handle.read()
                if rval: 
                    frame = frame[:, :, 0]
                    h1.root.rawdata.append(frame)
                    h1.root.timestamps.append(time.time())
                    #send sync signal here
                    #if communication_interface_available:
                        #send bit
                key = cv2.waitKey(1)
                if key == 27: # exit on ESC
                    break
            h1.flush()
            if self.debug and len(h1.root.timestamps)>1:
                print 'frames: {0}, duration:{1} s, average framerate:{2} fps'.format(len(h1.root.rawdata),(h1.root.timestamps[-1]-h1.root.timestamps[0]),1.0/numpy.diff(h1.root.timestamps.read().flatten()).mean())
        grabber_handle.release()
        cv2.destroyWindow('preview')
        
   

def opencv_camera_runner(filename, duration, config):
    cam = OpenCVCamera(config, debug=True)
    cam.start(duration, filename)
    cam.close()
        
        
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
#        print self.dllref.IC_SetCameraProperty(self.grabber_handle, 4, ctypes.c_long(self.snap_timeout))#Exposure time
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
            from visexpman.engine.generic import fileop
            tiffile.imsave(fileop.generate_filename('c:\\_del\\calib.tiff'), self.video, software = 'visexpman')
            try:
                import Image
            except ImportError:
                from PIL import Image
            Image.fromarray(numpy.cast['uint8'](self.video.mean(axis=0))).show()
            
    def close(self):
        self.dllref.IC_CloseVideoCaptureDevice(self.grabber_handle) 
        self.dllref.IC_CloseLibrary()

class TestISConfig(configuration.Config):
    def _create_application_parameters(self):
#        self.CAMERA_FRAME_RATE = 30.0
#        VIDEO_FORMAT = 'RGB24 (744x480)'
        self.CAMERA_FRAME_RATE = 160.0
        VIDEO_FORMAT = 'RGB24 (320x240)'
        self._create_parameters_from_locals(locals())
        
class TestCVCameraConfig(configuration.Config):
    def _create_application_parameters(self):
        self.CAMERA_HEIGHT_PIXELS = 480
        self.CAMERA_WIDTH_PIXELS = 640
        self.SHOW_PREVIEW_WINDOW= True
        self._create_parameters_from_locals(locals())

                
class TestCamera(unittest.TestCase):
    @unittest.skip('')
    def test_01_record_some_frames(self):
        cam = ImagingSourceCamera(TestISConfig())
        cam.start()
        with Timer(''):
            while cam.frame_counter <= 30: 
                cam.save()
        with Timer(''):
            cam.stop()
        cam.close()
        
    @unittest.skip('')    
    def test_02_record_some_frames_firewire_cam(self):
        simple_camera()
        
#    @unittest.skip('')    
    def test_02_record_some_frames_firewire_cam(self):
        threaded_camera()
        
def simple_camera():
    import os
    import os.path
    p = 'c:\\tmp\\testsuimple.hdf5'
    if os.path.exists(p):
        os.remove(p)
    cam = OpenCVCamera(TestCVCameraConfig(),debug=True)
    cam.start(7, p)
    
def threaded_camera():
    import os
    import os.path
    import threading
    p = 'c:\\tmp\\test.hdf5'
    duration = 20.0
    config = TestCVCameraConfig()
#        cam = OpenCVCamera(config, debug=False)
    for i in range(1):
        print i
        if os.path.exists(p):
            os.remove(p)
#            if os.path.exists(p+'.zip'):
#                os.remove(p+'.zip')
#            cam.start(p, duration)
#            t = threading.Thread(target = cam.start, args = (p, duration))
        t = threading.Thread(target = opencv_camera_runner, args = (p, duration, config))
        t.start()
        t.join()
        
        
if __name__ == '__main__':
    simple_camera()
    print('simple done')
    #threaded_camera()
    #unittest.main()
