import copy,visexpman,sys, multiprocessing, threading
from visexpman.engine.generic.introspect import Timer
import numpy
from contextlib import closing
from visexpman.engine.hardware_interface import instrument, digital_io
import time
import ctypes
import os
import unittest
try:
    import cv2
except ImportError:
    pass
from visexpman.engine.generic import configuration, fileop, command_parser
import tables
import ctypes

class SPOT_EXPOSURE_STRUCT2(ctypes.Structure):
    _fields_ = [('dwRedExpDur', ctypes.c_long),
                    ('dwGreenExpDur', ctypes.c_long),
                    ('dwBlueExpDur', ctypes.c_long),
                    ('dwExpDur', ctypes.c_long),
                    ('nGain', ctypes.c_short)]
                    
                    
class SPOT_EXPOSURE_STRUCT64(ctypes.Structure):
    _fields_ = [('qwRedExpDur', ctypes.c_longlong),
                    ('qwGreenExpDur', ctypes.c_longlong),
                    ('qwBlueExpDur', ctypes.c_longlong),
                    ('qwExpDur', ctypes.c_longlong),
                    ('nGain', ctypes.c_short)]


class VideoCamera(instrument.Instrument):
    def __init__(self, config=None,debug=False):
        self.config = config
        self.debug=debug
        self._init_camera()
        super(VideoCamera, self).__init__(config=config)
        
    def start(self):
        pass
        
    def stop(self):
        pass
        
    def save(self):
        pass
        
    def _init_camera(self, config = None):
        pass
        
    def close(self):
        pass
        
class SpotCam(VideoCamera):
    def _init_camera(self):
        if os.name != 'nt':
            raise NotImplementedError('Spot cam is only supported on Windows platform')
        self.live=True
        self.dll = ctypes.WinDLL (os.path.join(fileop.visexpman_package_path(), 'engine', 'external','spotcam', '64bit', 'SpotCamProxy.dll'))
        dll=self.dll
        res=[]
        res.append(dll.SpotStartUp(None))
        time.sleep(0.5)
        #Select camera 1
        #SPOT_DRIVERDEVICENUMBER
        tmp=ctypes.c_short(1)
        res.append(dll.SpotSetValue(204,ctypes.byref(tmp)))#Code 105: out of range
        time.sleep(0.5)
        res.append(dll.SpotInit())
        #SPOT_MAXIMAGERECTSIZE
        tmp=ctypes.c_long(0)
        res.append(dll.SpotGetValue(122,ctypes.byref(tmp)))
        h=(tmp.value>>16)&0xffff
        w=tmp.value&0xffff
#        print w,h
        #SPOT_AUTOEXPOSE
        res.append(dll.SpotSetValue(100,ctypes.byref(ctypes.c_bool(False))))
        self.set_exposure(100e-3,8)
        #SPOT_BINSIZE
        res.append(dll.SpotSetValue(103,ctypes.byref(ctypes.c_short(1))))
        #SPOT_BITDEPTH
        res.append(dll.SpotSetValue(113,ctypes.byref(ctypes.c_short(8))))
        #SPOT_ACQUIREDIMAGESIZE
        res.append(dll.SpotGetValue(153,ctypes.byref(tmp)))
        h=(tmp.value>>16)&0xffff
        w=tmp.value&0xffff
        if not self.live:
            res.append(dll.SpotClearStatus())
        ref =ctypes.create_string_buffer(h*w)
#        if self.live:
#            SpotSetCallback
        
        if self.live:
            res.append(dll.SpotClearStatus())
        self.buffer=ref
        self.h=h
        self.w=w
        if len([r for r in res if r!= 0])>0:
            raise RuntimeError('Could not initialize camera: {0}'.format(res))
        
    def set_exposure(self,exposure_time,gain):
        dll = self.dll
        res=[]
        tmp=ctypes.c_long(0)
        res.append(dll.SpotGetValue(221,ctypes.byref(tmp)))
        exposure_increment = tmp.value
        exposure_ct = int(exposure_time*1e9/exposure_increment)
        if 0 and self.live:
            res.append(dll.SpotSetValue(209,ctypes.byref(SPOT_EXPOSURE_STRUCT64(0,0,0,int(1e9*exposure_time),int(gain)))))#Set exposure, #SPOT_LIVEEXPOSURE64
        else:
            res.append(dll.SpotSetValue(105,ctypes.byref(SPOT_EXPOSURE_STRUCT2(0,0,0,exposure_ct,int(gain)))))#Set exposure, #SPOT_EXPOSURE2
        if len([r for r in res if r!= 0])>0:
            raise RuntimeError('Could not set exposure: {0}'.format(res))
    
    def close(self):
        time.sleep(1)
        res=[]
        dll = self.dll
        res.append(dll.SpotExit())
        res.append(dll.SpotShutDown())
        if len([r for r in res if r!= 0])>0:
            raise RuntimeError('Could not close camera: {0}'.format(res))
        
    def get_image(self):
        dll = self.dll
        res=[]
        if not self.live:
            res = dll.SpotGetImage(ctypes.c_short(0), ctypes.c_bool(False), ctypes.c_short(0), ctypes.cast(self.buffer, ctypes.c_void_p),None,None, None)
        else:
            self.buffer=ctypes.create_string_buffer(self.h*self.w)
            res = dll.SpotGetLiveImages(ctypes.c_bool(False), ctypes.c_short(0),  ctypes.c_short(0), ctypes.c_bool(False), ctypes.c_bool(False), ctypes.cast(self.buffer, ctypes.c_void_p))
        if res!=0:
            raise RuntimeError('Image could not be acquired, error code: {0}'.format(res))
        im=numpy.fromstring(self.buffer, dtype=numpy.uint8).reshape(self.h,self.w)
        return im

class SpotCamAcquisition(command_parser.ProcessLoop, SpotCam):
    def __init__(self, log=None):
        SpotCam.__init__(self)
        command_parser.ProcessLoop.__init__(self, log=log)
        
    def callback(self):
        if hasattr(self, 'cmd') and hasattr(self.cmd, 'has_key'):
            if self.cmd.has_key('exposure'):
                self.set_exposure(*self.cmd['set_exposure'])
            elif self.cmd.has_key('get_image'):
#                self.response.put(self.get_image())
                self.response.put(numpy.random.random((1600,1200)))

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
                print('frames: {0}, duration:{1} s, average framerate:{2} fps'.format(len(h1.root.rawdata),(h1.root.timestamps[-1]-h1.root.timestamps[0]),1.0/numpy.diff(h1.root.timestamps.read().flatten()).mean()))
        grabber_handle.release()
        cv2.destroyWindow('preview')
        
   

def opencv_camera_runner(filename, duration, config):
    cam = OpenCVCamera(config, debug=True)
    cam.start(duration, filename)
    cam.close()
    
class ImagingSourceCamera(object):
    def __init__(self,frame_rate, video_format='RGB24 (744x480)'):
        dllpath = os.path.join(os.path.dirname(visexpman.__file__),'engine', 'external','IC', 'tisgrabber_x64.dll')
        wd = os.getcwd()
        os.chdir(os.path.dirname(dllpath))
        self.dllref = ctypes.windll.LoadLibrary(dllpath)
        os.chdir(wd)
        if self.dllref.IC_InitLibrary(None) != 1:
            raise RuntimeError('Initializing TIS library did not succeed')
        self.grabber_handle = self.dllref.IC_CreateGrabber()
        cam_name = 'DMK 22BUC03'
        if sys.version_info.major==3:
            cam_name=bytes(cam_name, 'utf-8')
        cam_name = ctypes.c_char_p(cam_name)
        if self.dllref.IC_OpenVideoCaptureDevice(self.grabber_handle, cam_name) != 1:
            raise RuntimeError('Opening camera did not succeed')
        self.video_format = video_format
        if sys.version_info.major==3:
            self.video_format=bytes(self.video_format, 'utf-8')
        if self.dllref.IC_SetVideoFormat(self.grabber_handle,self.video_format) != 1:
            raise RuntimeError('Setting video format did not succeed')
        self.w = self.dllref.IC_GetVideoFormatWidth(self.grabber_handle)
        self.h = self.dllref.IC_GetVideoFormatHeight(self.grabber_handle)
        self.bytes_per_pixel = 3
        self.frame_size = self.h * self.w * self.bytes_per_pixel
        self.frame_shape = (self.h, self.w)
        self.frame_rate = frame_rate
        self.set_framerate()
        self.snap_timeout = self.dllref.IC_GetFrameRate(self.grabber_handle)
#        print self.dllref.IC_SetCameraProperty(self.grabber_handle, 4, ctypes.c_long(self.snap_timeout))#Exposure time
        self.isrunning = False
        self.frame_counter = 0
        self.framep = []
        self.frames = []
        self.timestamps=[]
        #disable triggering
        if self.dllref.IC_EnableTrigger(self.grabber_handle,  0)!=1:
            raise RuntimeError('Could not disable camera triggering')
        self.get_frame_rates()
#        self.video = numpy.zeros((1, self.h, self.w), numpy.uint8)

    def set_framerate(self):
        if self.dllref.IC_SetFrameRate(self.grabber_handle,  ctypes.c_float(self.frame_rate)) != 1:
            raise RuntimeError('Setting frame rate did not succeed')
        fr=round(1000.0/self.dllref.IC_GetFrameRate(self.grabber_handle))
        if fr !=self.frame_rate:
            raise RuntimeError('{0} Hz requested, {1} Hz is possible'.format(self.frame_rate,  fr))
        
    def start(self, show=False):
        if not self.isrunning:
            if self.dllref.IC_StartLive(self.grabber_handle, int(show)) == 1:
                self.isrunning = True
        else:
            raise RuntimeError('Camera is already recording')
            
    def save(self):
        if self.dllref.IC_SnapImage(self.grabber_handle, int(self.snap_timeout)) == 1:
            addr = self.dllref.IC_GetImagePtr(self.grabber_handle)
            if 0:
                p = ctypes.cast(addr, ctypes.POINTER(ctypes.c_byte))
                buffer = numpy.core.multiarray.int_asbuffer(ctypes.addressof(p.contents), self.frame_size)
            else:
                a=self.frame_size*ctypes.c_byte
                buffer=numpy.ctypeslib.as_array(a.from_address(addr))
            frame = copy.deepcopy(numpy.reshape(numpy.frombuffer(buffer, numpy.uint8)[::3], self.frame_shape))
            self.frames.append(frame)
            self.frame_counter += 1
            self.timestamps.append(time.time())
            time.sleep(1e-3)
            return True
        else:
            return False
            
    def set_filename(self, filename):
        self.datafile=tables.open_file(filename, 'w')
        self.datafile.create_earray(self.datafile.root, 'ic_frames', tables.UInt8Atom((480, 744)), (0, ), 'Frames', filters=tables.Filters(complevel=5, complib='blosc', shuffle = 1))
            
    def read(self,  save=False):
        '''
        Read frame from camera
        '''
        if self.dllref.IC_SnapImage(self.grabber_handle, int(self.snap_timeout)) == 1:
            addr = self.dllref.IC_GetImagePtr(self.grabber_handle)
            a=self.frame_size*ctypes.c_byte
            buffer=numpy.ctypeslib.as_array(a.from_address(addr))
            frame = copy.deepcopy(numpy.reshape(numpy.frombuffer(buffer, numpy.uint8)[::3], self.frame_shape))
            if save:
                self.datafile.root.ic_frames.append(numpy.expand_dims(frame,0))
            return frame
            
    def close_file(self):
        self.datafile.close()
        
    def stop(self):
        if self.isrunning:
            self.isrunning = False
            self.dllref.IC_StopLive(self.grabber_handle)
            self.video = numpy.array(self.frames)

    def close(self):
        if hasattr(self,  'closed'): return
        self.dllref.IC_CloseVideoCaptureDevice(self.grabber_handle) 
        self.dllref.IC_CloseLibrary()
        self.closed=True
        
    def get_frame_rates(self):
        val=ctypes.c_float()
        p=ctypes.POINTER(ctypes.c_float)
        frame_rates=[]
        for i in range(10):
            if self.dllref.IC_GetAvailableFrameRates(self.grabber_handle, int(i),  ctypes.byref(val))!=1:
                break
            frame_rates.append(val.value)
        pass
        
    def mark_dropped_frames(self):
        '''
        Returns indexes of frames where there was a more than one frame shift in timestamps. Also returns the number of frames in the recording
        '''
        expected_frame_time=1000.0/self.frame_rate
        dt=numpy.diff(self.timestamps)*1000
        frame_steps=numpy.cast['uint8'](numpy.round(dt/expected_frame_time))
        return numpy.where(frame_steps>1)[0].shape[0], dt.shape[0]+1
        
class ImagingSourceCameraSaver(ImagingSourceCamera):
    def __init__(self,filename,frame_rate):
        ImagingSourceCamera.__init__(self,frame_rate)
        self.filename=filename
        self.datafile=tables.open_file(filename, 'w')
        self.datafile.create_earray(self.datafile.root, 'ic_frames', tables.UInt8Atom((480, 744)), (0, ), 'Frames', filters=tables.Filters(complevel=5, complib='blosc', shuffle = 1))
        self.datafile.create_earray(self.datafile.root, 'ic_timestamps', tables.Float64Atom((1, )), (0, ), 'Frame timestamps')
#        self.codec=self.dllref.IC_Codec_Create("MJPEG Compressor")
#        self.dllref.IC_SetCodec(self.grabber_handle,self.codec)
#        print(self.dllref.IC_SetAVIFileName(self.grabber_handle, filename+'.avi'))
#IC_SetPropertySwitch(hGrabber,"Exposure","Auto",0);
        self.start()
        
    def save(self):
        if  ImagingSourceCamera.save(self):
            return
            self.datafile.root.ic_timestamps.append(numpy.array([[time.time()]]))
            self.datafile.root.ic_frames.append(numpy.expand_dims(self.frames[-1],0))
            
    def stop(self):
        ImagingSourceCamera.stop(self)
        res=self.mark_dropped_frames()
        self.datafile.close()
        self.close()
        return res
        
    def mark_dropped_frames(self):
        expected_frame_time=1000.0/self.frame_rate
        dt=numpy.diff(self.datafile.root.ic_timestamps.read().flatten())*1000
        ic_frame_steps=numpy.cast['uint8'](numpy.round(dt/expected_frame_time))
        self.datafile.create_array(self.datafile.root, 'ic_frame_steps',ic_frame_steps, 'Frame steps')
        self.ic_frame_steps=ic_frame_steps
        return numpy.where(ic_frame_steps>1)[0].shape[0], dt.shape[0]+1
        
class CameraRecorderProcess(multiprocessing.Process):
    def __init__(self, frame_rate,  config=None):
        self.command=multiprocessing.Queue(5)
        self.data=multiprocessing.Queue(2)
        self.frame=multiprocessing.Queue(10)
        self.error=multiprocessing.Queue(5)
        self.started=multiprocessing.Queue(1)
        self.frame_rate=frame_rate
        self.machine_config=config
        multiprocessing.Process.__init__(self)
        
    def run(self):
        try:
            if self.machine_config!=None and not self.machine_config.CAMERA_TIMING_ON_STIM:
                self.io=digital_io.IOBoard(self.machine_config.CAMERA_IO_PORT,  timeout=3e-3, initial_wait=3)
                self.io.set_pin(self.machine_config.CAMERA_TIMING_PIN,  0)
            self.cam=ImagingSourceCamera(self.frame_rate)
            self.cam.start()
            if 0 and hasattr(self,  'io'):
                self.io.set_pin(self.machine_config.CAMERA_TIMING_PIN,  1)
            self.started.put(True)
            pulsemsg='pulse,{0},{1}\r\n'.format(self.machine_config.CAMERA_TIMING_PIN, 5)
            if sys.version_info[0] == 3:
                pulsemsg=bytes(pulsemsg,'utf-8')
            while True:
                time.sleep(0.5/self.frame_rate)
                if self.cam.save():
                    if hasattr(self,  'io'):
                        self.io.s.write(pulsemsg)
                        #self.io.pulse(self.machine_config.CAMERA_TIMING_PIN,  5e-3)
                    if len(self.cam.frames)%3==1:
                        self.frame.put(self.cam.frames[-1])
                if not self.command.empty():
                    if self.command.get()=='stop':
                        self.cam.stop()
                        break
#            if hasattr(self,  'io'):
#                self.io.set_pin(self.machine_config.CAMERA_TIMING_PIN,  0)
            if hasattr(self,  'io'):
                self.io.close()
            dropped_frames=self.cam.mark_dropped_frames()
            frames=numpy.array(self.cam.frames)
            data={'frames': frames, 'timestamps': self.cam.timestamps,  'dropped_frames': dropped_frames}
            self.data.put(data)
            self.cam.close()
        except:
            import traceback
            self.error.put(traceback.format_exc())
        
    def stop(self):
        self.command.put('stop')
        while self.data.empty():
            pass
        d=self.data.get()
        if not self.error.empty():
            return self.error.get()
        return d
        
    def wait(self,  timeout=10):
        '''
        Waits for camera to start
        '''
        t0=time.time()
        while True:
            if not self.started.empty():
                res=True
                break
            time.sleep(0.1)
            if time.time()-t0>timeout:
                res=False
                break
        return res
        
class ImagingSourceCameraHandler(multiprocessing.Process):
    def __init__(self, frame_rate, exposure_time, ioboard_com, filename=None, watermark=False):
        self.frame_rate=frame_rate
        self.exposure_time=exposure_time
        self.filename=filename
        self.ioboard_com=ioboard_com
        self.watermark=watermark
        multiprocessing.Process.__init__(self)
        self.command=multiprocessing.Queue()
        self.log=multiprocessing.Queue()
        self.frame=multiprocessing.Queue()
        self.timestamps=multiprocessing.Queue()
        self.display_frame=multiprocessing.Queue(1)
        
    def run(self):
        try:
            if self.filename!=None:
                self.saver=SaverProcess(self.filename,  self.frame, 100)
                self.saver.start()
            from visexpur.tis import tisgrabber_import
            lib=tisgrabber_import.TIS_grabber()
            lib.InitLibrary()
            camera_name=lib.Kamera_finden()[0]
            ch= lib.Kamera_verbinden(camera_name)
            if ch.open()!=1:
                raise RuntimeError()
            ch.set_exposure(self.exposure_time)
            ch.StartLive()
            self.log.put('Connected to {0}'.format(camera_name))
            self.frame_counter=0
            timestamps=[]
            if self.ioboard_com!=None:
                self.ioboard='line' not in self.ioboard_com
                if self.ioboard:
                    import serial
                    io=serial.Serial(self.ioboard_com, baudrate=115200, timeout=1e-3)
                    time.sleep(2)
                else:
                    import PyDAQmx
                    import PyDAQmx.DAQmxConstants as DAQmxConstants
                    digital_output = PyDAQmx.Task()
                    digital_output.CreateDOChan(self.ioboard_com,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
            
            w=1.0/self.frame_rate-4e-3
            w=1e-3
            tlast=time.time()
            while True:
                now=time.time()
                if now-tlast>1.0/self.frame_rate:
                    if ch.SnapImage()==1:
                        frame=numpy.copy(ch.GetImage())
                        tlast=now
                        if self.filename!=None:
                            timestamps.append(time.time())
                        if self.ioboard_com!=None:
                            if self.ioboard:
                                cmd='pulse,5,3\r\n'
                                if sys.version_info.major==3:
                                    cmd=bytes(cmd, 'utf-8')
                                io.write(cmd)
                                io.reset_input_buffer()
                            else:
                                digital_output.WriteDigitalLines(1,
                                        True,
                                        1.0,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        numpy.array([int(1)], dtype=numpy.uint8),
                                        None,
                                        None)
                                time.sleep(1e-3)
                                digital_output.WriteDigitalLines(1,
                                        True,
                                        1.0,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        numpy.array([int(0)], dtype=numpy.uint8),
                                        None,
                                        None)
                        if self.watermark:
                            low=self.frame_counter%256
                            high=self.frame_counter/256
                            frame[0, 0, :]=high
                            frame[0, 1, :]=low
                        if self.filename!=None:
                            self.frame.put(frame)
                        self.frame_counter+=1
                        if self.display_frame.empty():
                            self.display_frame.put(frame)
                time.sleep(w)
                if not self.command.empty():
                    self.frame.put('terminate')#stop saver
                    self.log.put("Stop received")
                    break
            self.timestamps.put(timestamps)
            ch.StopLive()
            ch.close()
            if self.ioboard_com!=None:
                if self.ioboard:
                    io.close()
                else:
                    digital_output.ClearTask()
            if hasattr(self,  'saver'):
                while self.saver.done.empty():
                    time.sleep(1)
                self.saver.terminate()
                self.saver.join()
            self.log.put('Camera process ended')
        except:
            import traceback
            self.log.put(traceback.format_exc())
            
    def stop(self):
        self.command.put('terminate')
        time.sleep(0.3)
        log=[]
        while not self.log.empty():
            log.append(self.log.get())
        if self.filename!=None:
            ts=self.timestamps.get()
            while self.log.empty():
                time.sleep(1)
            log.append(self.log.get())
        else:
            ts=[]
        self.terminate()
        return ts, log
        
class SaverProcess(multiprocessing.Process):
    def __init__(self, filename, data,  chunksize):
        self.filename=filename
        self.dataq=data
        self.chunksize=chunksize
        self.done=multiprocessing.Queue()
        multiprocessing.Process.__init__(self)
        
    def run(self):
        if self.filename[-4:]=='hdf5':
            self.datafile=tables.open_file(self.filename, 'w')
            self.datafile.create_earray(self.datafile.root, 'frames', tables.UInt8Atom((480, 744, 3)), (0, ), 
                                'Frames', 
                                filters=tables.Filters(complevel=2, complib='zlib', shuffle = 1), 
                                )
        elif self.filename[-3:]=='mp4':
            fps=30
            import skvideo.io
            self.video_writer=skvideo.io.FFmpegWriter(self.filename, inputdict={'-r':fps}, outputdict={'-r':fps})
            
        ct=0
        chunk=[]
        frames=[]
        while True:
            if not self.dataq.empty():
                frame=self.dataq.get()
                if not hasattr(frame,  'dtype'):
                    if len(chunk)>0:
                        self.datafile.root.frames.append(numpy.array(chunk))
                    chunk=[]
                    break
                else:
#                    frames.append(frame)
                    chunk.append(frame)
                    if len(chunk)==self.chunksize:
                        if hasattr(self,  'datafile'):
                            self.datafile.root.frames.append(numpy.array(chunk))
                            self.datafile.root.frames.flush()
                            chunk=[]
                        elif hasattr(self,  'video_writer'):
                            for fr in chunk:
                                self.video_writer.writeFrame(numpy.rollaxis(numpy.array([fr]*3),0,3))
                            
                    else:
                        time.sleep(1e-3)
                    ct+=1
#                    if ct%3==1:
#                        self.datafile.root.frames.flush()
            else:
                time.sleep(5e-3)
#        self.datafile.root.frames.append(numpy.array(frames))
        if hasattr(self,  'datafile'):
            self.datafile.root.frames.flush()
            self.datafile.close()
        elif hasattr(self,  'video_writer'):
            self.video_writer.close()
        self.done.put(True)
        
class TestISConfig(configuration.Config):
    def _create_application_parameters(self):
#        self.CAMERA_FRAME_RATE = 30.0
#        VIDEO_FORMAT = 'RGB24 (744x480)'
        self.CAMERA_FRAME_RATE = 160.0
        #VIDEO_FORMAT = 'RGB24 (320x240)'
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
        fr=30
        cam = ImagingSourceCameraSaver('c:\\temp\\{0}.hdf5'.format(int(time.time())),fr)
        time.sleep(0.2)
        tacq=10
        t0=time.time()
        with Timer(''):
            while cam.frame_counter < fr*tacq: 
                t1=time.time()
                cam.save()
                t2=time.time()
                #tleft=1.0/fr-(t0-t1)
                #time.sleep(tleft)
                
        print(cam.stop())
        print([ cam.ic_frame_steps])
        print(('frame rate',  len(cam.frames)/(time.time()-t0)))
        print(cam.frames[0].shape)
        pass
        
    @unittest.skip('')    
    def test_02_record_some_frames_firewire_cam(self):
        simple_camera()

    @unittest.skip('')      
    def test_03_set_camera_exposure(self):
        dllpath = os.path.join(os.path.dirname(visexpman.__file__),'engine', 'external','IC', 'tisgrabber_x64.dll')
        wd = os.getcwd()
        os.chdir(os.path.dirname(dllpath))
        self.dllref = ctypes.windll.LoadLibrary(dllpath)
        os.chdir(wd)
        if self.dllref.IC_InitLibrary(None) != 1:
            raise RuntimeError('Initializing TIS library did not succeed')
        self.grabber_handle = self.dllref.IC_CreateGrabber()
        cam_name = 'DMK 22BUC03'
        if sys.version_info.major==3:
            cam_name=bytes(cam_name, 'utf-8')
        cam_name = ctypes.c_char_p(cam_name)
        if self.dllref.IC_OpenVideoCaptureDevice(self.grabber_handle, cam_name) != 1:
            raise RuntimeError('Opening camera did not succeed')
        print(self.dllref.IC_StartLive(self.grabber_handle, int(0)))
        self.dllref.IC_CloseVideoCaptureDevice(self.grabber_handle) 
        self.dllref.IC_CloseLibrary()
        
    def test_04_camera_process(self):
        for i in range(3):
            print(i)
            fn='c:\\Data\\test{0}.hdf5'.format(time.time())
            from visexpman.engine.hardware_interface import daq_instrument
            ai=daq_instrument.SimpleAnalogIn('Dev1/ai6:7', 1000, 600, finite=False)
            cc=ImagingSourceCameraHandler(35, 1/60., 'COM6',  filename=fn)
            cc.start()
            time.sleep(30)
            ts=cc.stop()
            print(1/numpy.diff(ts), (1/numpy.diff(ts)).mean() , (1/numpy.diff(ts)).std(),  len(ts))
            import hdf5io
            nframes=hdf5io.read_item(fn,  'frames').shape
            print(nframes)
            data=ai.finish()
            from pylab import plot, show
            plot(data[:, 0]);show()
#            while cc.log.empty():
#                time.sleep(1)
#            
#            cc.terminate()
            break
        print('done')
#        import pdb
#        pdb.set_trace()
        
        
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
        print(i)
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
    #simple_camera()
    #print('simple done')
    #threaded_camera()
    unittest.main()
