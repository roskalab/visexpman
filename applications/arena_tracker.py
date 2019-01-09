try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
import cv2,logging,numpy,time,pyqtgraph, os, sys
from visexpman.engine.generic import gui,introspect,utils
from visexpman.engine.hardware_interface import camera_interface, digital_io
from visexpman.engine.analysis import behavioral_data
from visexpman.engine.vision_experiment import experiment_data
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
                            {'name': 'Frame rate', 'type': 'int', 'value': 30},
                            {'name': 'Threshold', 'type': 'int', 'value': 200},
                            {'name': 'Enable ROI cut', 'type': 'bool', 'value': True},
                            {'name': 'ROI x1', 'type': 'int', 'value': 200},
                            {'name': 'ROI y1', 'type': 'int', 'value': 200},
                            {'name': 'ROI x2', 'type': 'int', 'value': 400},
                            {'name': 'ROI y2', 'type': 'int', 'value': 400},
                            {'name': 'Channel', 'type': 'int', 'value': 0},
                            {'name': 'Show channel only', 'type': 'bool', 'value': False},
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
        self.init()
        self.datafolder='c:\\Data'
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
        
    def parameter_changed(self):
        self.parameters=self.cw.paramw.get_parameter_tree(return_dict=True)
        
    def init(self):
        dt=utils.timestamp2ymdhms(time.time(), filename=True)
        root='/tmp' if os.name!='nt' else 'x:\\behavioral2'
        self.logfile=os.path.join(root, 'log_{0}.txt'.format(dt))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        w=640
        h=480
        self.is_camera='--iscamera' in sys.argv
        if self.is_camera:
            self.camera=camera_interface.ImagingSourceCamera(self.parameters['Frame rate'])
            self.camera.start()
        else:
            self.camera = cv2.VideoCapture(2)#Initialize video capturing
            self.camera.set(3, w)#Set camera resolution
            self.camera.set(4, h)
        logging.info('Camera initialized')
        self.record=False
        self.dio=digital_io.DigitalIO('COM4')
        self.dio.set_pin(1, 0)
        
    def ttl_pulse(self):
        self.dio.set_pin(1, 1)
        time.sleep(1e-3)
        self.dio.set_pin(1, 0)
        
    def read_digital_input(self):
        return self.dio.hwhandler.getCTS()
        
    def recording_start_stop(self):
        if self.is_camera:
            di=self.read_digital_input()
            if self.record and not di:
                self.camera.datafile.create_array(self.camera.datafile.root, 'track', numpy.array(self.track))
                self.camera.close_file()
            elif not self.record and di:
                fn=os.path.join(self.datafolder, 'camera_{0}.hdf5'.format(experiment_data.get_id()))
                self.camera.set_filename(fn)
                self.track=[]
                logging.info('Saving video to {0}'.format(fn))
            self.record = di
        
    def read_camera(self):
        if self.is_camera:
            self.camera.frames=[]
            res=self.camera.save()
            self.ttl_pulse()
            if res:
                return self.camera.frames[-1]
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
            if self.parameters['Enable ROI cut']:
                self.frame=self.frame[self.parameters['ROI x1']:self.parameters['ROI x2'],self.parameters['ROI y1']:self.parameters['ROI y2']]
            coo=behavioral_data.extract_mouse_position(self.frame, self.parameters['Channel'], self.parameters['Threshold'])
            f=numpy.copy(self.frame)
            if coo!=None and not numpy.isnan(coo[0]) and self.record and numpy.nan != coo[0]:
                if self.parameters['Show channel only']:
                    for i in range(3):
                        if i!=self.parameters['Channel']:
                            f[:,:,i]=0
                self.track.append(coo)
                for coo in self.track:
                    f[int(coo[0]), int(coo[1])]=numpy.array([0,255,0],dtype=f.dtype)


        self.cw.image.set_image(numpy.rot90(numpy.flipud(f)))
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
        
    def record_action(self):
        if self.record:
            return
        if self.parameters['Enable trigger']:
            return
        self.record=True
        self.track=[]
        logging.info('Start tracking')
    
    def stop_action(self):
        if not self.record:
            return
        self.record=False
        logging.info('Tracking finished')
        
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
