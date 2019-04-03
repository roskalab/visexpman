try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
qt_app = Qt.QApplication([])
import logging,numpy,time,pyqtgraph, os, sys,cv2,serial
from visexpman.engine.generic import gui,introspect,utils, fileop
from visexpman.engine.hardware_interface import camera_interface, digital_io
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
                            {'name': 'Enable trigger', 'type': 'bool', 'value': True}, 
                            {'name': 'Show track', 'type': 'bool', 'value': True}, 
                            {'name': 'Threshold', 'type': 'int', 'value': 200},
                            {'name': 'Enable ROI cut', 'type': 'bool', 'value': True},
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
        self.frame_rate=30
        self.init()
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        self.setWindowTitle('Mouse Position Tracker')
        self.setGeometry(50,50,700,700)
        self.debugw.setFixedHeight(150)
        self.debugw.setMaximumWidth(700)        
        self.maximized=False
        toolbar_buttons = ['record', 'stop', 'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.cw.image.img.setLevels([0,255])
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.cw.paramw.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.parameter_changed()
        self.cam_timer=QtCore.QTimer()
        self.cam_timer.start(33)#ms
        self.connect(self.cam_timer, QtCore.SIGNAL('timeout()'), self.update_camera_image)
        
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        
        
    def parameter_changed(self):
        self.parameters=self.cw.paramw.get_parameter_tree(return_dict=True)
        
    def init(self):
        dt=utils.timestamp2ymdhms(time.time(), filename=True)
        root='/tmp' if os.name!='nt' else 'x:\\behavioral2\\log'
        self.logfile=os.path.join(root, 'log_{0}.txt'.format(dt))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        w=640
        h=480
        self.is_camera='--iscamera' in sys.argv
        if self.is_camera:
            self.camera=camera_interface.ImagingSourceCamera(self.frame_rate)
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
        self.ioboard=serial.Serial('COM5', 1000000, timeout=1)
        self.trigger_detector_enabled=False
        time.sleep(2)
        self.disable_trigger()
        
    def enable_trigger(self):
        if not self.trigger_detector_enabled:
            self.ioboard.write('wait_trigger,1\r\n')
            logging.info(self.iobaord.read(100))
            self.trigger_detector_enabled=True
        
    def disable_trigger(self):
        self.ioboard.write('wait_trigger,0\r\n')
        logging.info(self.iobaord.read(100))    
        self.trigger_detector_enabled=False
        
    def istriggered(self):
        res= self.ioboard.inWaiting()==13
        if res:
            logging.info(self.ioboard.read(13))
        return res
        
    def ttl_pulse(self):
        self.dio.set_pin(1, 1)
        time.sleep(1e-3)
        self.dio.set_pin(1, 0)
        
    def read_digital_input(self):
        return self.dio.hwhandler.getCTS()
        
    def start_recording(self):
        fn=os.path.join(self.datafolder, 'camera_{0}.hdf5'.format(experiment_data.get_id()))
        self.camera.set_filename(fn)
        self.track=[]
        logging.info('Saving video to {0}'.format(fn))
        self.statusbar.recording_status.setStyleSheet('background:red;')
        self.statusbar.recording_status.setText('Camera recording')
        
    def stop_recording(self):
        logging.info('Stopped video recording')
        self.camera.datafile.create_array(self.camera.datafile.root, 'track', numpy.array(self.track))
        self.camera.close_file()
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        self.statusbar.recording_status.setText('')
        
    def recording_start_stop(self):
        #Trigger enabled only if no recording is ongoing and trigger is enabled in Settings
        if (not self.triggered_recording or not self.manual_recording) and self.parameters['Enable trigger']:
            self.enable_trigger()
        if self.is_camera and self.parameters['Enable trigger']:
            if not TEST:
                di=self.istriggered()
            else:
                di= self.parameters['Override trigger']
            if self.triggered_recording and not self.manual_recording and not di:#Stop recording
                self.stop_recording()
            elif not self.triggered_recording and not self.manual_recording and di:#Start recording
                self.start_recording()
            self.triggered_recording = di#controlled by digital input, it expects that during recording it is set to HIGH otherwise to LOW
        
    def read_camera(self):
        if self.is_camera:
            frame=self.camera.read(save=self.manual_recording or self.triggered_recording)
            self.ttl_pulse()
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
                if self.parameters['Show track']:
                    for coo in self.track:
                        if not numpy.isnan(coo[0]):
                            f[int(coo[0]), int(coo[1])]=numpy.array([0,255,0],dtype=f.dtype)
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
        self.ioboard.close()
        self.close()
        

        
if __name__ == '__main__':
    #introspect.kill_other_python_processes()
    gui = ArenaTracker()
