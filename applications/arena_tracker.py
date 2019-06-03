try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
qt_app = Qt.QApplication([])
import logging,numpy,time,pyqtgraph, os, sys,cv2, hdf5io, serial
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
        self.FSAMPLE_AI=5000
        self.MAX_RECORDING_DURATION=600#10 minutes
        self.init()
        gui.SimpleAppWindow.__init__(self)
        self.disable_trigger()
        
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
        self.cam_timer.start(1000/self.FRAME_RATE/3)#ms
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
        
        self.camera=camera_interface.ImagingSourceCamera(self.FRAME_RATE)
        self.camera.start()
        logging.info('Camera initialized')
        self.triggered_recording=False
        self.manual_recording=False
        self.dio=digital_io.DigitalIO('usb-uart', 'COM3')
        self.dio.set_pin(1, 0)
        self.ioboard=serial.Serial('COM5', 1000000, timeout=0.001)
        self.trigger_detector_enabled=False
        time.sleep(2)
        
    def enable_trigger(self):
        if not self.trigger_detector_enabled and self.ioboard.isOpen():
            self.ioboard.write('wait_trigger,1\r\n')
            logging.info(self.ioboard.read(100))
            self.trigger_detector_enabled=True
        
    def disable_trigger(self):
        if self.ioboard.isOpen():
            self.ioboard.write('wait_trigger,0\r\n')
            logging.info(self.ioboard.read(100))    
            self.trigger_detector_enabled=False
        
    def istriggered(self):
        if self.ioboard.isOpen():
            readout=self.ioboard.read(20)
            if len(readout):
                logging.info(readout)
        else:
            readout=''
        return 'Start trigger' in readout,  'Stop trigger' in readout
        
    def ttl_pulse(self):
        self.dio.set_pin(1, 1)
        time.sleep(3e-3)
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
        time.sleep(0.5)#Let ai start recording
        logging.info('Start camera recording')
        
    def stop_recording(self):
        time.sleep(1)#Wait to ensure that last pulses of nVista timing signal are recorded. We need to record the last pulses because the first ones are missing due to the delay of trigger detection.
        logging.info('Stopped video recording, recorded {0} frames'.format(self.frame_counter))
        self.statusbar.recording_status.setStyleSheet('background:yellow;')
        self.statusbar.recording_status.setText('Saving file')
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
        self.camera_timestamps=signal.trigger_indexes(self.sync[:,1])/float(self.FSAMPLE_AI)
        camera_fps=1.0/numpy.diff(self.camera_timestamps)[1::2]
        logging.info('Camera frame rate mean: {0:0.1f}, std {1:0.1f}'.format(camera_fps.mean(),  camera_fps.std()))
        logging.info('n frames: {0}, n pulses: {1}'.format(len(self.frames),  self.camera_timestamps.shape[0]/2))
#        self.camera.datafile.create_array(self.camera.datafile.root, 'track', numpy.array(self.track))
#        self.camera.close_file()
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        self.statusbar.recording_status.setText('')
        
    def recording_start_stop(self):
        #Trigger enabled only if no recording is ongoing and trigger is enabled in Settings
        if (not self.triggered_recording or not self.manual_recording) and self.parameters['Enable trigger']:
            self.enable_trigger()
        if self.parameters['Enable trigger']:
            start, stop=self.istriggered()
            if self.triggered_recording and not self.manual_recording and stop:#Stop recording
                self.stop_recording()
                self.triggered_recording=False
                self.trigger_detector_enabled=False
            elif not self.triggered_recording and not self.manual_recording and start:#Start recording
                self.start_recording()
                self.triggered_recording=True
        
    def read_camera(self):
        frame=self.camera.read(save=False)#self.manual_recording or self.triggered_recording)
        if (self.triggered_recording or self.manual_recording) and hasattr(frame, 'dtype'):
            self.ttl_pulse()
            self.frame_counter+=1
            self.frames.append(frame)
        if hasattr(frame,  'dtype'):
            f=numpy.rollaxis(numpy.array([frame]*3), 0, 3)
            return f
        
    def update_camera_image(self):
        self.frame=self.read_camera()
        if hasattr(self.frame, 'dtype'):
            self.recording_start_stop()
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
            if not hasattr(self, "frame_counter") or ((self.triggered_recording or self.manual_recording) and self.frame_counter%4==0) or (not self.triggered_recording or not self.manual_recording):
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
        self.camera.stop()
        self.camera.close()
        self.dio.close()
        if self.ioboard.isOpen():
            self.disable_trigger()
            self.ioboard.close()
        self.close()
        
if __name__ == '__main__':
    #introspect.kill_other_python_processes()
    gui = ArenaTracker()
