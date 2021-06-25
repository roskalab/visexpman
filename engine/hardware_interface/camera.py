from visexpman.engine.generic import gui
import os,unittest,multiprocessing,time,pdb,numpy, cv2, ctypes, queue
try:
    from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
except:
    print('No thorlabs camera driver installed')

try:
    import tisgrabber
except:
    print('No Imaging source camera driver installed')
import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes
from visexpman.engine.hardware_interface import instrument

class ThorlabsCamera(object):
    def __init__(self, dll_path, nbit=8):
        os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']
        self.sdk=TLCameraSDK()
        self.camera=self.sdk.open_camera(self.sdk.discover_available_cameras()[0])
        self.nbit=nbit
        
    def set(self, exposure=None, roi=None, gain=None):
        if exposure !=None:
            self.camera.exposure_time_us = exposure
        if roi != None:
            self.camera.roi = roi
        if gain != None:
            self.camera.gain=gain
            
    def start_(self):
        self.camera.arm(2)
        self.camera.issue_software_trigger()
        
    def get_frame(self):
        frame = self.camera.get_pending_frame_or_null()
        if frame == None:
            return None
        if self.nbit==8:
            frame8bit=frame.image_buffer >> (self.camera.bit_depth-8)
            return frame8bit
        elif self.nbit==16:
            return frame.image_buffer
        
    def stop(self):
        self.camera.disarm()
        
    def close(self):
        self.camera.dispose()
        self.sdk.dispose()
        print ("sdk dispose")
        
class ThorlabsCameraProcess(ThorlabsCamera, instrument.InstrumentProcess):
    def __init__(self,dll_path,logfile,roi=None):
        self.roi=roi
        self.dll_path=dll_path
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self,self.queues,logfile)
        self.control=multiprocessing.Queue()
        self.data=multiprocessing.Queue()
        
    def start_(self):
        self.queues['command'].put('start')
        
    def stop(self):
        self.queues['command'].put('stop')
        
    def set(self, **kwargs):
        self.queues['command'].put(('set',list(kwargs.keys())[0],list(kwargs.values())[0]))
        
    def read(self):
        if not self.queues['data'].empty():
            return self.queues['data'].get()
        
    def run(self):
        self.setup_logger()
        self.printl(f'pid: {os.getpid()}')
        self.running=False
        ThorlabsCamera.__init__(self, dll_path=self.dll_path,nbit=16)
        if self.roi is not None:
            ThorlabsCamera.set(self,roi=self.roi)
        while True:
            try:
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd=='start':
                        ThorlabsCamera.start_(self)
                        self.running=True
                    elif cmd=='stop':
                        ThorlabsCamera.stop(self)
                        self.running=False
                    elif cmd=='terminate':
                        if self.running:
                            ThorlabsCamera.stop(self)
                        self.close()
                        break
                    elif cmd[0]=='set':
                        kwarg={cmd[1]:cmd[2]}
                        ThorlabsCamera.set(self,**kwarg)
                if self.running:
                    frame=self.get_frame()
                    if self.queues['data'].empty() and frame is not None:#Send frame when queue empty (previous frame was taken
                        self.queues['data'].put(frame)
                time.sleep(50e-3)
            except:
                import traceback
                self.printl(traceback.format_exc())
    
    
class CameraCallbackUserdata(ctypes.Structure):
    def __init__(self):
        self.camera = None # Reference to the camera object
        self.frame_queue = None
  
class ISCamera(instrument.InstrumentProcess):
    def __init__(self,camera_id,logfile,digital_line, frame_rate=60, exposure=1/65, filename=None, show=False):
        self.filename=filename
        self.camera_id=camera_id
        self.frame_rate=frame_rate
        self.digital_line=digital_line
        self.exposure=exposure
        self.show=show
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self,self.queues,logfile)
        self.control=multiprocessing.Queue()
        self.data=multiprocessing.Queue()
        print(self.logfile)
        self.Userdata = CameraCallbackUserdata()
        
    def stop(self):
        self.queues['command'].put('stop')
        
    def read(self):
        if not self.queues['data'].empty():
            return self.queues['data'].get()
            
    def save(self, fn):
        self.queues['command'].put(['save', fn])

    def stop_saving(self):
        self.queues['command'].put('stop_saving')
        t0=time.time()
        while True:
            if not self.queues['response'].empty():
                msg=self.queues['response'].get()
                if msg=='save done':
                    break
                if time.time()-t0>60:
                    break
                time.sleep(0.5)
                    
                
    def FrameReadyCallback(self, hGrabber, pBuffer, framenumber, pData):
        BildDaten = pData.camera.GetImageDescription()[:4]
        lWidth=BildDaten[0]
        lHeight= BildDaten[1]
        iBitsPerPixel=BildDaten[2]//8

        buffer_size = lWidth*lHeight*iBitsPerPixel*ctypes.sizeof(ctypes.c_uint8)            
                
        Bild = ctypes.cast(pBuffer, ctypes.POINTER(ctypes.c_ubyte * buffer_size))
        frame = numpy.ndarray(buffer = Bild.contents, dtype = numpy.uint8, shape = (lHeight, lWidth, iBitsPerPixel))
         
        frame = frame[:,:,0]
        pData.frame_queue.put(frame)
            
    def run(self):
        try:
            self.setup_logger()
            self.printl(f'pid: {os.getpid()}')
            self.running=False
            Camera = tisgrabber.TIS_CAM()
            camera_name=[camidi for camidi in Camera.GetDevices() if camidi.decode()==self.camera_id]
            if len(camera_name)==0:
                raise ValueError(f'Unkown camera: {camera_name}, {Camera.GetDevices() }')

            Camera.open(camera_name[0].decode())
            Camera.SetPropertySwitch("Strobe","Enable",0)
            Camera.SetPropertySwitch("Strobe","Polarity",1)
            Camera.SetPropertyMapString("Strobe","Mode","exposure")  # exposure,constant or fixed duration
            Camera.SetPropertyValue("Strobe","Delay",0)
            
            
            Camera.SetPropertySwitch("Trigger","Enable",0)
            Camera.SetVideoFormat("Y800 (320x240)")
        
            Camera.SetFrameRate(self.frame_rate)
            Camera.SetPropertyAbsoluteValue("Exposure","Value", self.exposure)   #50fps 640x480
            Camera.SetContinuousMode(0)
            
            if self.digital_line is not None:
                digital_output = PyDAQmx.Task()
                digital_output.CreateDOChan(self.digital_line,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
            fps='30'
            import skvideo.io
            if self.filename!=None:
                self.video_writer=skvideo.io.FFmpegWriter(self.filename, inputdict={'-r':fps}, outputdict={'-r':fps})
            
            frame_queue = queue.Queue()
            
            self.Userdata.camera = Camera
            self.Userdata.frame_queue = frame_queue
            Callbackfunc = tisgrabber.TIS_GrabberDLL.FRAMEREADYCALLBACK(self.FrameReadyCallback)
            Camera.SetFrameReadyCallback(Callbackfunc, self.Userdata)
            
            if self.show:
                Camera.StartLive(1)
            else:
                Camera.StartLive(0)
                
            Camera.SetPropertySwitch("Strobe","Enable",1)
            
            while True:
                if frame_queue.empty():
                    time.sleep(1e-4)
                    continue
                frame = frame_queue.get(timeout = 0.1)
                
                if hasattr(self, 'video_writer') and self.digital_line is not None:
                    digital_output.WriteDigitalLines(1,True,1.0,DAQmxConstants.DAQmx_Val_GroupByChannel,numpy.array([1], dtype=numpy.uint8),None,None)
                if hasattr(self, 'video_writer'):
                    if len(frame.shape)==2:
                        frame=numpy.rollaxis(numpy.array([frame]*3),0,3).copy()
                    self.video_writer.writeFrame(frame)
                #Digital pulse indicates video save time
                if hasattr(self, 'video_writer') and self.digital_line is not None:
                    digital_output.WriteDigitalLines(1,True,1.0,DAQmxConstants.DAQmx_Val_GroupByChannel,numpy.array([0], dtype=numpy.uint8),None,None)
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd=='stop':
                        Camera.SetPropertySwitch("Strobe","Enable",0)
                        Camera.StopLive()
                        self.printl('Stop camera')
                        break
                    elif cmd[0]=='save':
                        self.video_writer=skvideo.io.FFmpegWriter(cmd[1], inputdict={'-r':fps}, outputdict={'-r':fps})
                    elif cmd=='stop_saving':
                        self.printl('Close video file')
                        self.video_writer.close()
                        del self.video_writer
                        self.queues['response'].put('save done')
                if self.queues['data'].empty() and frame is not None:#Send frame when queue empty (previous frame was taken
                    self.queues['data'].put(frame)
                    
            if hasattr(self, 'video_writer'):
                self.printl('Close video file')
                self.video_writer.close()
            if self.digital_line is not None:
                digital_output.ClearTask()
            self.printl('Leaving process')
        except:
            import traceback
            self.printl(traceback.format_exc())
        
class WebCamera(instrument.InstrumentProcess):
    def __init__(self,camera_id,logfile,digital_line,filename=None):
        self.filename=filename
        self.camera_id=camera_id
        self.digital_line=digital_line
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self,self.queues,logfile)
        self.control=multiprocessing.Queue()
        self.data=multiprocessing.Queue()
        print(self.logfile)
        
    def stop(self):
        self.queues['command'].put('stop')
        
    def read(self):
        if not self.queues['data'].empty():
            return self.queues['data'].get()
            
    def run(self):
        try:
            self.setup_logger()
            self.printl(f'pid: {os.getpid()}')
            self.running=False
            if self.digital_line is not None:
                digital_output = PyDAQmx.Task()
                digital_output.CreateDOChan(self.digital_line,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
            fps='30'
            import skvideo.io
            if self.filename!=None:
                self.video_writer=skvideo.io.FFmpegWriter(self.filename, inputdict={'-r':fps}, outputdict={'-r':fps})
            frame_prev=None
            Camera = cv2.VideoCapture(self.camera_id)
            self.printl(Camera)
            while True:
                r, fr=Camera.read()
                if fr is None:
                    continue
                frame=fr.copy()
                if frame_prev is not None and numpy.array_equal(frame_prev, frame):#No new frame in buffer
                    continue
                frame_prev=frame
                if self.digital_line is not None:
                    digital_output.WriteDigitalLines(1,True,1.0,DAQmxConstants.DAQmx_Val_GroupByChannel,numpy.array([1], dtype=numpy.uint8),None,None)
                if hasattr(self, 'video_writer'):
                    if len(frame.shape)==2:
                        frame=numpy.rollaxis(numpy.array([fr]*3),0,3).copy()
                    self.video_writer.writeFrame(frame)
                #Digital pulse indicates video save time
                if self.digital_line is not None:
                    digital_output.WriteDigitalLines(1,True,1.0,DAQmxConstants.DAQmx_Val_GroupByChannel,numpy.array([0], dtype=numpy.uint8),None,None)
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd=='stop':
                        Camera.release()
                        break
                if self.queues['data'].empty() and frame is not None:#Send frame when queue empty (previous frame was taken
                    self.queues['data'].put(frame)
                
                time.sleep(1e-3)
            if hasattr(self,  'video_writer'):
                self.video_writer.close()
            if self.digital_line is not None:
                digital_output.ClearTask()
        except:
            import traceback
            self.printl(traceback.format_exc())

        
class TestCamera(unittest.TestCase):
    def setUp(self):
        self.folder=r'f:\Scientific Camera Interfaces\SDK\Python Compact Scientific Camera Toolkit\dlls\64_lib'
        
    @unittest.skip('')
    def test_1_thorlabs_camera(self):        
        tc=ThorlabsCamera(self.folder)
        tc.set(exposure=100000)
        tc.start_()
        for i in range(20):
            frame=tc.get_frame()
        tc.stop()
        tc.close()
        del tc
        self.assertTrue(hasattr(frame, 'dtype'))
        
    @unittest.skip('')
    def test_2_adjust_parameters(self):
        tc=ThorlabsCamera(self.folder, nbit=16)
        tc.set(gain=1)
        tc.set(roi=(1000,1000,1500,1500))
        tc.start_()
        exp1=100000
        exp2=50000
        tc.set(exposure=exp1)
        for i in range(20):
            frame=tc.get_frame()
        self.assertAlmostEqual(exp1,tc.camera.frame_time_us,-3)
        tc.set(exposure=exp2)
        for i in range(20):
            frame=tc.get_frame()
        self.assertAlmostEqual(exp2,tc.camera.frame_time_us,-3)
        tc.set(gain=100)
        frame2=tc.get_frame()
        self.assertGreater(frame2.mean(),frame.mean())#Would pass once lens is mounted
        tc.stop()
        tc.close()
        del tc
        self.assertEqual(frame.shape,(504,504))
      
    @unittest.skip('')
    def test_3_thorlab_camera_process(self):
        logfile=r'f:\tmp\log_camera_{0}.txt'.format(time.time())
        tp=ThorlabsCameraProcess(self.folder,logfile,roi=(0,0,1004,1004))
        tp.start()
        exposure_time=30e-3
        tp.set(exposure=int(exposure_time*1e6))
        tp.set(gain=1)
#        tp.queues['command'].put(('set','exposure',int(exposure_time*1e6)))
#        tp.queues['command'].put(('set','gain',1))
        tp.start_()
        timestamps=[]
        t0=time.time()
        while True:
            frame=tp.read()
            if frame is not None:
                timestamps.append(time.time()-t0)
            if len(timestamps)>100:
                break
        tp.stop()
        tp.terminate() 
        self.assertTrue(hasattr(frame,'dtype'))
        numpy.testing.assert_almost_equal(numpy.diff(timestamps),exposure_time,3)
        self.assertTrue(os.path.exists(logfile))
        self.assertGreater(os.path.getsize(logfile),0)
    
    @unittest.skip('')      
    def test_4_imaging_source_camera(self):
        fn=r'c:\Data\a.mp4'
        cam=ISCamera('DMK 22BUC03 31710198',r'c:\Data\log\camlog.txt','Dev1/port0/line0', frame_rate=60, exposure=1/65, filename=fn)
        cam.start()
        for i in range(60):
            time.sleep(1.1)
        cam.stop()
        time.sleep(1)
        cam.terminate()
        
    @unittest.skip('') 
    def test_5_web_camera(self):
        cam=WebCamera(3,r'c:\Data\log\camlog.txt','Dev1/port0/line0', filename=None)
        cam.start()
        for i in range(60):
            time.sleep(0.1)
            fr=cam.read()
            if fr is not None:
                frame=fr
                from pylab import imshow, show
                imshow(frame)
                show()
                break
        cam.stop()
        time.sleep(1)
        cam.terminate()
        
    @unittest.skip('')       
    def test_6_strobe(self):
        fn=r'f:\a.mp4'
        from visexpman.engine.generic import fileop
        fileop.remove_if_exists(fn)
        import daq
        ai=daq.AnalogRead('Dev2/ai0:1',20,10000)
        cam=ISCamera('DMK 37BUX287 15120861',r'f:\camlog.txt',None, frame_rate=160, exposure=1/250, filename=fn)
        cam.start()
        for i in range(60):
            time.sleep(1.1)
        cam.stop()
        time.sleep(1)
        cam.terminate()
        time.sleep(30)
        data=ai.read()
        import skvideo.io
        from visexpman.engine.generic import signal
        videodata = skvideo.io.vread(fn)
        print(f'Recorded frames {videodata.shape[0]}, n pulses: {signal.trigger_indexes(data[0]).shape[0]/2}')
        print(f'D pulse: {signal.trigger_indexes(data[0]).shape[0]/2-videodata.shape[0]}')
        d=(signal.trigger_indexes(data[0])[-1]-signal.trigger_indexes(data[0])[0])/10e3
        print(f'Duration: {d},frame rate {videodata.shape[0]/d}')
        print(f'Pulse rate: {10e3/numpy.diff(signal.trigger_indexes(data[0])[::2]).mean()} Hz')
        from pylab import plot,show
        plot(data[0]);show()
        
#        import pdb
#       
    
    def test_7_strobe(self):
        fn=r'c:\Data\cam_test\a.mp4'
        from visexpman.engine.generic import fileop
        fileop.remove_if_exists(fn)
        import daq
        
        cam=ISCamera('DMK 37BUX287 15120861',r'c:\Data\cam_test\camlog.txt',None, frame_rate=60, exposure=1/250, filename=fn)
        cam.start()
        time.sleep(1.52) #ugy beallitani, hogy a mintavetelezes a hamis impulzusok után induljon
                        #biztos megoldas lenne a mintavetelezest a Camera.StartLive utan inditani, de hogy?
        ai=daq.AnalogRead('Dev5/ai0:1',30,10000) 
        for i in range(10):
            time.sleep(1.1)
        cam.stop()
        time.sleep(1)
        cam.terminate()
        time.sleep(2)
        data=ai.read()
        import skvideo.io
        from visexpman.engine.generic import signal
        videodata = skvideo.io.vread(fn)
        print(f'Recorded frames {videodata.shape[0]}, n pulses: {signal.trigger_indexes(data[0]).shape[0]/2}')
        print(f'D pulse: {signal.trigger_indexes(data[0]).shape[0]/2-videodata.shape[0]}')
        d=(signal.trigger_indexes(data[0])[-1]-signal.trigger_indexes(data[0])[0])/10e3
        print(f'Duration: {d},frame rate {videodata.shape[0]/d}')
        print(f'Pulse rate: {10e3/numpy.diff(signal.trigger_indexes(data[0])[::2]).mean()} Hz')
        from pylab import plot,show
        plot(data[0]);show()
            

if __name__ == '__main__':
    unittest.main()
