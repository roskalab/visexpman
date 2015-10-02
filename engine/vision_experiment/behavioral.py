import sys
import time
import numpy
import cv2
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import gui

class Config(object):
    def __init__(self):
        self.DATA_FOLDER = '/mnt/tmp'
        self.VALVE_OPEN_TIME=400e-3
        self.CURSOR_RESET_POSITION=0.01
        self.CURSOR_POSITION_UPDATE_PERIOD = 10e-3
        self.CAMERA_UPDATE_RATE=10
        self.CAMERA_FRAME_WIDTH=640
        self.CAMERA_FRAME_HEIGHT=480
        
        self.MOVE_THRESHOLD=200
        self.PROTOCOL_STOP_REWARD={}
        self.PROTOCOL_STOP_REWARD['run time']=2
        self.PROTOCOL_STOP_REWARD['stop time']=2
        
        self.PROTOCOL_STIM_STOP_REWARD={}
        self.PROTOCOL_STIM_STOP_REWARD['run time']=2
        self.PROTOCOL_STIM_STOP_REWARD['stop time']=2
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time range']=10
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']=0.5
        
    def get_protocol_names(self):
        return [vn.replace('PROTOCOL_','') for vn in dir(self) if 'PROTOCOL_' in vn]
        

HELP='''Start experiment: Ctrl+a
Stop experiment: Ctrl+s
Select next protocol: Space'''

class CWidget(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.image=gui.Image(self)
        self.image.setFixedWidth(500)
        ar=float(parent.config.CAMERA_FRAME_WIDTH)/parent.config.CAMERA_FRAME_HEIGHT
        self.image.setFixedHeight(500/ar)
        
        self.plotw=gui.Plot(self)
        self.plotw.setFixedHeight(250)
        self.help=QtGui.QLabel(HELP,self)
        self.select_protocol=gui.LabeledComboBox(self,'Select protocol', parent.config.get_protocol_names())
        
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.image, 0, 0, 2, 2)
        self.l.addWidget(self.plotw, 0, 2, 1, 3)
        self.l.addWidget(self.select_protocol, 1, 2, 1, 1)
        self.l.addWidget(self.help, 1, 3, 1, 1)
        self.setLayout(self.l)

class Behavioral(gui.SimpleAppWindow):
    def init_gui(self):
        self.config=Config()
        self.setWindowTitle('Behavioral Experiment Control')
        self.cw=CWidget(self)
        self.cw.setMinimumHeight(500)
        self.cw.setMinimumWidth(1100)
        self.setCentralWidget(self.cw)
        self.debugw.setMinimumWidth(800)
        self.debugw.setMinimumHeight(300)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)
        self.camera_reader = QtCore.QTimer()
        self.camera_reader.timeout.connect(self.read_camera)
        self.camera_reader.start(int(1000./self.config.CAMERA_UPDATE_RATE))
        self.camera = cv2.VideoCapture(0)
        self.camera.set(3, self.config.CAMERA_FRAME_WIDTH)
        self.camera.set(4, self.config.CAMERA_FRAME_HEIGHT)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+a'), self), QtCore.SIGNAL('activated()'), self.start_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self), QtCore.SIGNAL('activated()'), self.stop_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Space'), self), QtCore.SIGNAL('activated()'), self.next_protocol)
        self.cursor_t = QtCore.QTimer()
        self.cursor_t.timeout.connect(self.cursor_handler)
        self.cursor_t.start(int(1000.*self.config.CURSOR_POSITION_UPDATE_PERIOD))
        screen_width = self.qt_app.desktop().screenGeometry().width()
        self.screen_height = self.qt_app.desktop().screenGeometry().height()
        self.screen_left=int(screen_width*self.config.CURSOR_RESET_POSITION)
        self.screen_right=int((1-self.config.CURSOR_RESET_POSITION)*screen_width)
        self.running=False
        
    def read_camera(self):
        ret, frame = self.camera.read()
        if hasattr(frame, 'shape'):
            self.cw.image.set_image(numpy.rot90(frame,3),alpha=1.0)
            
    def start_experiment(self):
        if self.running: return
        self.running=True
        nparams=2
        self.data=numpy.empty((nparams,0))
        self.log('start')
        
    def stop_experiment(self):
        if not self.running: return
        self.running=False
        self.log('stop')
        
    def next_protocol(self):
        next_index = self.cw.select_protocol.input.currentIndex()+1
        if next_index == self.cw.select_protocol.input.count():
            next_index = 0
        self.cw.select_protocol.input.setCurrentIndex(next_index)
        
    def cursor_handler(self):
        if not self.running:
            return
        self.cursor_position = QtGui.QCursor.pos().x()
        reset_position=None
        if self.screen_left>self.cursor_position:
            reset_position = self.screen_right
        if self.screen_right<self.cursor_position:
            reset_position = self.screen_left
        if reset_position is not None:
            QtGui.QCursor.setPos(reset_position,int(self.screen_height*0.5))
        self.data = numpy.append(self.data, numpy.array([[time.time(), self.cursor_position]]).T,axis=1)
        d=self.data
        self.cw.plotw.update_curve(d[0]-d[0,0], d[1], pen=(0,0,0), plotparams = {})
        
    def closeEvent(self, e):
        self.camera.release()
        e.accept()
        
    
if __name__ == '__main__':
    gui = Behavioral()
