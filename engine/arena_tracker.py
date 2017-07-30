try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
import cv2,logging,numpy,time,pyqtgraph
from visexpman.engine.generic import gui,introspect,utils
from visexpman.engine.analysis import behavioral_data
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
                            {'name': 'Threshold', 'type': 'int', 'value': 100}
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
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        self.setWindowTitle('Mouse Position Tracker')
        self.setGeometry(20,20,700,700)
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
        
        self.track_timer=QtCore.QTimer()
        self.track_timer.start(5*33)#ms
        self.connect(self.track_timer, QtCore.SIGNAL('timeout()'), self.update_track)
        
    def parameter_changed(self):
        self.parameters=self.cw.paramw.get_parameter_tree(return_dict=True)
        
    def init(self):
        dt=utils.timestamp2ymdhms(time.time(), filename=True)
        self.logfile='/tmp/log_{0}.txt'.format(dt)
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        w=640
        h=480
        self.camera = cv2.VideoCapture(0)#Initialize video capturing
        self.camera.set(3, w)#Set camera resolution
        self.camera.set(4, h)
        logging.info('Camera initialized')
        self.record=False
        
    def read_camera(self):
        ret, frame = self.camera.read()#Reading the raw frame from the camera
        if frame is None or not ret:
            return
        frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to rearrange the color channels
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        return frame_color_corrected
        
    def update_track(self):
        return
        if not hasattr(self.frame, 'dtype'):
            return
        coo=behavioral_data.extract_mouse_position(self.frame, self.parameters['Threshold'])
        if coo!=None and self.record:
            self.track.append(coo)
            for t in self.track:
                self.frame[t[0], t[1],1]=255
                self.frame[t[0], t[1],0]=0
                self.frame[t[0], t[1],2]=0
            self.cw.image.set_image(numpy.rot90(numpy.flipud(self.frame)))
            return
            if hasattr(self, 'roi'):
                self.cw.image.plot.removeItem(self.roi)
            self.roi = pyqtgraph.PolyLineROI(self.track, closed=False)
            self.roi.setPen((0, 255, 0, 255), width=3)
            self.cw.image.plot.addItem(self.roi)
        
    def update_camera_image(self):
        self.frame=self.read_camera()
        if hasattr(self.frame, 'dtype'):
            coo=behavioral_data.extract_mouse_position(self.frame, self.parameters['Threshold'])
            f=numpy.copy(self.frame)
            if coo!=None and self.record and numpy.nan != coo[0]:
                self.track.append(coo)
                for coo in self.track:
                    f[f.shape[0]-int(coo[1]), f.shape[1]-int(coo[0])]=numpy.array([0,255,0],dtype=f.dtype)

            self.cw.image.set_image(numpy.rot90(numpy.flipud(f)))
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
        
    def record_action(self):
        if self.record:
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
        self.camera.release()#Stop camera operation
        self.close()
        

        
if __name__ == '__main__':
    #introspect.kill_other_python_processes()
    gui = ArenaTracker()
