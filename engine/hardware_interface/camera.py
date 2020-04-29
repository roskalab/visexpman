import os,unittest,multiprocessing,time,pdb,numpy
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
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
        
class ThorlabsCameraProcess(ThorlabsCamera, instrument.InstrumentProcess):
    def __init__(self,dll_path,logfile,roi=None):
        self.roi=roi
        self.dll_path=dll_path
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self,self.queues,logfile)
        self.control=multiprocessing.Queue()
        self.data=multiprocessing.Queue()
        
    def run(self):
        self.setup_logger()
        self.running=False
        ThorlabsCamera.__init__(self, dll_path=self.dll_path,nbit=16)
        if self.roi is not None:
            self.set(roi=self.roi)
        while True:
            try:
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd=='start':
                        self.start_()
                        self.running=True
                    elif cmd=='stop':
                        self.stop()
                        self.running=False
                    elif cmd=='terminate':
                        self.close()
                        break
                    elif cmd[0]=='set':
                        kwarg={cmd[1]:cmd[2]}
                        self.set(**kwarg)
                if self.running:
                    frame=self.get_frame()
                    if self.queues['data'].empty() and frame is not None:#Send frame when queue empty (previous frame was taken
                        self.queues['data'].put(frame)
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
      
    def test_3_thorlab_camera_process(self):
        logfile=r'f:\tmp\log_camera_{0}.txt'.format(time.time())
        tp=ThorlabsCameraProcess(self.folder,logfile,roi=(0,0,1004,1004))
        tp.start()
        exposure_time=30e-3
        tp.queues['command'].put(('set','exposure',int(exposure_time*1e6)))
        tp.queues['command'].put(('set','gain',1))
        tp.queues['command'].put('start')
        timestamps=[]
        t0=time.time()
        while True:
            if not tp.queues['data'].empty():
                frame=tp.queues['data'].get()
                timestamps.append(time.time()-t0)
            if len(timestamps)>100:
                break
        
        tp.queues['command'].put('stop')
        tp.terminate() 
        self.assertTrue(hasattr(frame,'dtype'))
        numpy.testing.assert_almost_equal(numpy.diff(timestamps),exposure_time,3)
        self.assertTrue(os.path.exists(logfile))
        self.assertGreater(os.path.getsize(logfile),0)

if __name__ == '__main__':
    unittest.main()
