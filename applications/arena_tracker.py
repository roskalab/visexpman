try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
qt_app = Qt.QApplication([])
import logging,numpy,time,pyqtgraph, os, sys,cv2, hdf5io
from visexpman.engine.generic import gui,introspect,utils, fileop, signal
from visexpman.engine.hardware_interface import camera_interface, digital_io, daq_instrument
from visexpman.engine.analysis import behavioral_data
from visexpman.engine.vision_experiment import experiment_data

TEST=not True

class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.setFixedHeight(550)
        self.image=gui.Image(self)
        self.image.setFixedWidth(640)
        self.image.setFixedHeight(480)
        self.params_config=[
                            {'name': 'Enable trigger', 'type': 'bool', 'value': False}, 
                            {'name': 'Show track', 'type': 'bool', 'value': True}, 
                            {'name': 'Threshold', 'type': 'int', 'value': 200},
                            {'name': 'Enable ROI cut', 'type': 'bool', 'value': False},
                            {'name': 'ROI x1', 'type': 'int', 'value': 200},
                            {'name': 'ROI y1', 'type': 'int', 'value': 200},
                            {'name': 'ROI x2', 'type': 'int', 'value': 400},
                            {'name': 'ROI y2', 'type': 'int', 'value': 400},
                            {'name': 'Channel', 'type': 'int', 'value': 0},
                            {'name': 'Show channel only', 'type': 'bool', 'value': False},
                            {'name': 'Override trigger', 'type': 'bool', 'value': False}, 
                    ]
        self.paramw = gui.ParameterTable(self, self.params_config)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.image, 'Camera')
        self.main_tab.addTab(self.paramw, 'Settings')
        self.main_tab.setFixedWidth(680)
        self.main_tab.setFixedHeight(500)
        self.main_tab.setTabPosition(self.main_tab.South)

class ArenaTracker(gui.SimpleAppWindow):
    def __init__(self):
        self.datafolder='c:\\Data'
        self.FRAME_RATE=30
        self.FSAMPLE_AI=2000
        self.MAX_RECORDING_DURATION=600#10 minutes
        self.init()
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        self.setWindowTitle('Mouse Position Tracker')
        self.setGeometry(50,50,700,700)
        self.debugw.setFixedHeight(150)
        self.debugw.setMaximumWidth(700)        
        self.maximized=False
        toolbar_buttons = ['record', 'stop', 'convert_folder', 'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.cw.image.img.setLevels([0,255])
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.cw.paramw.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.parameter_changed()
        self.cam_timer=QtCore.QTimer()
        self.cam_timer.start(1000/self.FRAME_RATE/2)#ms
        self.connect(self.cam_timer, QtCore.SIGNAL('timeout()'), self.update_camera_image)
        
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        
        
    def parameter_changed(self):
        self.parameters=self.cw.paramw.get_parameter_tree(return_dict=True)
        
    def init(self):
        dt=utils.timestamp2ymdhms(time.time(), filename=True)
        root='/tmp' if os.name!='nt' else 'c:\\Data\\log'#'x:\\behavioral2\\log'
        self.logfile=os.path.join(root, 'log_{0}.txt'.format(dt))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        w=640
        h=480
        self.is_camera='--iscamera' in sys.argv
        if self.is_camera:
            self.camera=camera_interface.ImagingSourceCamera(self.FRAME_RATE)
            self.camera.start()
        else:
            self.camera = cv2.VideoCapture(2)#Initialize video capturing
            self.camera.set(3, w)#Set camera resolution
            self.camera.set(4, h)
        logging.info('Camera initialized')
        self.triggered_recording=False
        self.manual_recording=False
        self.dio=digital_io.DigitalIO('usb-uart', 'COM3')
        self.dio.set_pin(1, 0)
        
    def ttl_pulse(self):
        self.dio.set_pin(1, 1)
        time.sleep(1e-3)
        self.dio.set_pin(1, 0)
        
    def read_digital_input(self):
        return self.dio.hwhandler.getCTS()
        
    def start_recording(self):
        self.fn=os.path.join(self.datafolder, 'camera_{0}.hdf5'.format(experiment_data.get_id()))
        #self.camera.set_filename(fn)
        self.track=[]
        self.frames=[]
        self.statusbar.recording_status.setStyleSheet('background:red;')
        self.statusbar.recording_status.setText('Camera recording')
        self.frame_counter=0
        self.t0=time.time()
        self.ai=daq_instrument.SimpleAnalogIn('Dev1/ai0:1',  self.FSAMPLE_AI, self.MAX_RECORDING_DURATION,  finite=False )
        
    def stop_recording(self):
        logging.info('Stopped video recording, recorded {0} frames'.format(self.frame_counter))
        h=hdf5io.Hdf5io(self.fn)
        h.track=numpy.array(self.track)
        h.ic_frames=numpy.array(self.frames)
        self.sync=self.ai.finish()
        h.sync=self.sync
        h.config=introspect.cap_attributes2dict(self)
        h.parameters=self.parameters
        h.save(['track', 'ic_frames',  'sync',  'config', 'parameters'])
        h.close()
        logging.info('Saved video to {0}'.format(self.fn))
        camera_fps=1.0/numpy.diff(signal.trigger_indexes(self.sync[:,1])/float(self.FSAMPLE_AI))[1::2]
        logging.info('Camera frame rate mean: {0:0.1f}, std {1:0.1f}'.format(camera_fps.mean(),  camera_fps.std()))
#        self.camera.datafile.create_array(self.camera.datafile.root, 'track', numpy.array(self.track))
#        self.camera.close_file()
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        self.statusbar.recording_status.setText('')
        
    def recording_start_stop(self):
        if self.is_camera and self.parameters['Enable trigger']:
            if not TEST:
                di=False# in [self.read_digital_input() for i in range(20000)]
            else:
                di= self.parameters['Override trigger']
            if self.triggered_recording and not self.manual_recording and not di:#Stop recording
                self.stop_recording()
            elif not self.triggered_recording and not self.manual_recording and di:#Start recording
                self.start_recording()
            self.triggered_recording = di#controlled by digital input, it expects that during recording it is set to HIGH otherwise to LOW
        
    def read_camera(self):
        if self.is_camera:
            frame=self.camera.read(save=False)#self.manual_recording or self.triggered_recording)
            if (self.triggered_recording or self.manual_recording) and hasattr(frame, 'dtype'):
                self.ttl_pulse()
                self.frame_counter+=1
                self.frames.append(frame)
            if hasattr(frame,  'dtype'):
                f=numpy.rollaxis(numpy.array([frame]*3), 0, 3)
                return f
        else:
            ret, frame = self.camera.read()#Reading the raw frame from the camera
            if frame is None or not ret:
                return
            frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to rearrange the color channels
            frame_color_corrected[:,:,0]=frame[:,:,2]
            frame_color_corrected[:,:,1]=frame[:,:,1]
            frame_color_corrected[:,:,2]=frame[:,:,0]
            return frame_color_corrected
        
    def update_camera_image(self):
        self.frame=self.read_camera()
        self.recording_start_stop()
        if hasattr(self.frame, 'dtype'):
#            self.cw.image.set_image(numpy.rot90(numpy.fliplr(self.frame)))
#            return
            self.vframe=self.frame
            if self.parameters['Enable ROI cut']:
                self.frame=self.frame[self.parameters['ROI x1']:self.parameters['ROI x2'],self.parameters['ROI y1']:self.parameters['ROI y2']]
            coo=behavioral_data.extract_mouse_position(self.frame, self.parameters['Channel'], self.parameters['Threshold'])
            f=numpy.copy(self.frame)
            if self.triggered_recording or self.manual_recording:
                self.track.append(coo)
            if coo!=None and not numpy.isnan(coo[0]) and (self.triggered_recording or self.manual_recording) and numpy.nan != coo[0]:
                if self.parameters['Show channel only']:
                    for i in range(3):
                        if i!=self.parameters['Channel']:
                            f[:,:,i]=0
                #self.track.append(coo)
                if self.parameters['Show track']:
                    for coo in self.track:
                        if not numpy.isnan(coo[0]):
                            f[int(coo[0]), int(coo[1])]=numpy.array([0,255,0],dtype=f.dtype)
            if not hasattr(self, "frame_counter") or ((self.triggered_recording or self.manual_recording) and self.frame_counter%4==0):
                self.cw.image.set_image(numpy.rot90(numpy.flipud(f)))
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
        
    def record_action(self):
        #Manually start saving frames to file
        if not self.parameters['Enable trigger']  and not self.manual_recording:
            self.start_recording()
            self.manual_recording=True
    
    def stop_action(self):
        if self.manual_recording or self.triggered_recording:
            self.stop_recording()
            self.triggered_recording=False
            self.manual_recording=False
            ual_recording=False
            
    def convert_folder_action(self):
        foldername=self.ask4foldername('Select hdf5 video file folder',  self.datafolder)
        files=fileop.listdir(foldername)
        p=gui.Progressbar(100, 'Conversion progress',  autoclose=True)
        p.show()
        logging.info('Conversion started')
        for f in files:
            if not os.path.isdir(f) and os.path.splitext(f)[1]=='.hdf5' and not os.path.exists(os.path.splitext(f)[0]+'.mat'):
                print f
                experiment_data.hdf52mat(f)
                prog=int((files.index(f)+1)/float(len(files))*100)
                p.update(prog)
                print prog
                time.sleep(100e-3)
        logging.info('{0} folder complete'.format(foldername))
        
    def exit_action(self):
        if self.is_camera:
            self.camera.stop()
            self.camera.close()
        else:
            self.camera.release()#Stop camera operation
        self.dio.close()
        self.close()
        

        
if __name__ == '__main__':
    #introspect.kill_other_python_processes()
    gui = ArenaTracker()
