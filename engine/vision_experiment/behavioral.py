import os,sys,time,threading,Queue,tempfile
import numpy,scipy.io
import serial
import cv2
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import gui,utils,videofile
from visexpman.engine.hardware_interface import daq_instrument
#TODO: video colors
#TODO: reduce video save time
#TODO: Scale digital curves on plot correctly when speed has high negativ values

class Config(object):
    def __init__(self):
        self.AO_CHANNEL='Dev3/ao0'
        self.DIO_PORT = 'COM3'
        self.DATA_FOLDER = tempfile.gettempdir()
        self.VALVE_OPEN_TIME=400e-3
        self.STIMULUS_DURATION=1.0
        self.CURSOR_RESET_POSITION=0.0
        self.CURSOR_POSITION_UPDATE_PERIOD = 50e-3
        self.CAMERA_UPDATE_RATE=24
        self.CAMERA_FRAME_WIDTH=640/2
        self.CAMERA_FRAME_HEIGHT=480/2
        self.POWER_VOLTAGE_RANGE=[0,10]

        self.RUN_THRESHOLD=0.8
        self.MOVE_THRESHOLD=10#200
        self.PROTOCOL_STOP_REWARD={}
        self.PROTOCOL_STOP_REWARD['run time']=2
        self.PROTOCOL_STOP_REWARD['stop time']=2
        
        self.PROTOCOL_STIM_STOP_REWARD={}
        self.PROTOCOL_STIM_STOP_REWARD['run time']=2
        self.PROTOCOL_STIM_STOP_REWARD['stop time']=2
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time range']=10
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']=0.5
        self.PROTOCOL_STIM_STOP_REWARD['delay after run']=2
        
    def get_protocol_names(self):
        return [vn.replace('PROTOCOL_','') for vn in dir(self) if 'PROTOCOL_' in vn]
        

class HardwareHandler(threading.Thread):
    def __init__(self,command,response,config):
        self.command=command
        self.response=response
        self.config=config
        threading.Thread.__init__(self)
        
    def run(self):
        s=serial.Serial(self.config.DIO_PORT)
        s.setBreak(1)
        s.setRTS(1)
        while True:
            if not self.command.empty():
                cmd=self.command.get()
                if cmd[0]=='terminate':
                    break
                elif cmd[0] == 'stimulate':
                    daq_instrument.set_voltage(self.config.AO_CHANNEL,cmd[1])
                    #s.setRTS(0)
                    time.sleep(self.config.STIMULUS_DURATION)
                    daq_instrument.set_voltage(self.config.AO_CHANNEL,0)
                    #s.setRTS(1)
                    self.response.put('stim ready')
                elif cmd[0] == 'reward':
                    s.setBreak(0)
                    time.sleep(self.config.VALVE_OPEN_TIME)
                    s.setBreak(1)
                    self.response.put('reward ready')
            else:
                time.sleep(10e-3)
                
        s.setBreak(1)
        s.setRTS(1)
        s.close()

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
        self.select_folder = QtGui.QPushButton('Data Save Folder', parent=self)
        self.selected_folder = QtGui.QLabel('', self)
        
        self.stim_power = gui.LabeledInput(self, 'Stimulus Intensity [V]')
        self.stim_power.input.setText('1')
        self.stim_power.input.setFixedWidth(40)
        
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.image, 0, 0, 3, 2)
        self.l.addWidget(self.plotw, 0, 2, 1, 3)
        self.l.addWidget(self.select_protocol, 1, 2, 1, 1)
        self.l.addWidget(self.stim_power, 2, 2, 1, 1)
        self.l.addWidget(self.help, 1, 3, 1, 1)
        self.l.addWidget(self.select_folder, 1, 4, 1, 1)
        self.l.addWidget(self.selected_folder, 2, 4, 1, 1)
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
        #self.camera.set(15, 1)#CV_CAP_PROP_EXPOSURE
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+a'), self), QtCore.SIGNAL('activated()'), self.start_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self), QtCore.SIGNAL('activated()'), self.stop_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Space'), self), QtCore.SIGNAL('activated()'), self.next_protocol)
        self.connect(self.cw.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder)
        self.output_folder = self.config.DATA_FOLDER
        self.cw.selected_folder.setText(self.output_folder)
        self.cursor_t = QtCore.QTimer()
        self.cursor_t.timeout.connect(self.cursor_handler)
        self.cursor_t.start(int(1000.*self.config.CURSOR_POSITION_UPDATE_PERIOD))
        self.screen_width = self.qt_app.desktop().screenGeometry().width()
        self.screen_height = self.qt_app.desktop().screenGeometry().height()
        self.screen_left=int(self.screen_width*self.config.CURSOR_RESET_POSITION)
        self.screen_right=int((1-self.config.CURSOR_RESET_POSITION)*self.screen_width)-1
        self.running=False
        self.next_speed_correction=False#Obsolete
        nparams=5#time, position, speed, reward, stim
        self.empty=numpy.empty((nparams,0))
        self.hwcommand=Queue.Queue()
        self.hwresponse=Queue.Queue()
        self.hwh=HardwareHandler(self.hwcommand,self.hwresponse, self.config)
        self.hwh.start()
        self.stim_state=False
        self.valve_state=False
        
    def read_camera(self):
        ret, frame = self.camera.read()
        frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to do this
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        
        if hasattr(frame_color_corrected, 'shape'):
            self.cw.image.set_image(numpy.rot90(frame_color_corrected,3),alpha=1.0)
            if self.running:
                self.frame_times.append(time.time())
                self.frames.append(frame_color_corrected)
            
    def start_experiment(self):
        if self.running: return
        self.running=True
        self.checkdata=numpy.copy(self.empty)
        self.data=numpy.copy(self.empty)
        self.frame_times=[]
        self.frames=[]
        self.log('start experiment')
        
        #Protocol specific
        self.run_complete=False
        self.stimulus_fired=False
        self.stop_complete=False
        
    def stop_experiment(self):
        if not self.running: return
        self.running=False
        self.log('stop experiment')
        self.save_data()
        
    def next_protocol(self):
        if self.running: return
        next_index = self.cw.select_protocol.input.currentIndex()+1
        if next_index == self.cw.select_protocol.input.count():
            next_index = 0
        self.cw.select_protocol.input.setCurrentIndex(next_index)
        
    def cursor_handler(self):
        if not self.running:
            return
        self.cursor_position = QtGui.QCursor.pos().x()
        self.now=time.time()
        reset_position=None
        jump=0
        if self.cursor_position<=self.screen_left:
            reset_position = self.screen_right
            jump=self.screen_width
        if self.cursor_position>=self.screen_right:
            reset_position = self.screen_left
            jump=-self.screen_width
        if reset_position is not None:
            QtGui.QCursor.setPos(reset_position,int(self.screen_height*0.5))
        if self.data.shape[1]>0:
            ds=self.cursor_position-self.data[1, -1]
            self.cursor_position+=jump
            speed=ds/(self.now-self.data[0,-1])
            if abs(speed)>1000 and 0:
                self.log('!')
                self.context={'speed':speed, 'ds':ds,'data':self.data[1,-1], 'jump':jump, 'cursor_position':self.cursor_position}
                self.log(self.context)
        else:
            speed=0
        #Check stim and valve states:
        if not self.hwresponse.empty():
            resp=self.hwresponse.get()
            if resp=='stim ready':
                self.stim_state=False
            elif resp == 'reward ready':
                self.valve_state=False
        newdata=numpy.array([[self.now, self.cursor_position,speed,int(self.valve_state),int(self.stim_state)]]).T
        self.data = numpy.append(self.data, newdata,axis=1)
        self.checkdata = numpy.append(self.checkdata, newdata,axis=1)
        t=self.data[0]-self.data[0,0]
        self.cw.plotw.update_curves([t,t,t], [self.data[2],self.data[3]*self.data[2].max(),self.data[4]*self.data[2].max()], colors=[(0,0,0),(0,255,0),(0,0,255)])
        getattr(self, str(self.cw.select_protocol.input.currentText()).lower())()
        
    def stop_reward(self):
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)
            t=self.checkdata[0]-self.checkdata[0,0]
            t0index=numpy.where(t>t.max()-(self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']))[0].min()
            index=numpy.where(t>t.max()-self.config.PROTOCOL_STOP_REWARD['stop time'])[0].min()
            run_speed=speed[t0index:index]
            stop_speed=speed[index:]
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]
            stop=stop_speed.sum()==0
            if run and stop:
                self.reward()
                self.checkdata=numpy.copy(self.empty)
    
    def stim_stop_reward(self):
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_STIM_STOP_REWARD['run time']:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)
            t=self.checkdata[0]-self.checkdata[0,0]
            index=numpy.where(t>t.max()-self.config.PROTOCOL_STIM_STOP_REWARD['run time'])[0].min()
            run_speed=speed[index:]
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]
            if run and not self.run_complete:
                self.run_complete=True
            if self.run_complete:
                if not self.stimulus_fired:
                    self.mouse_run_complete=self.now
                    self.stimulate()
                    self.stimulus_fired=True
                else:
                    index=numpy.where(t>t.max()-self.config.PROTOCOL_STIM_STOP_REWARD['stop time'])[0].min()
                    stop_speed=speed[index:]
                    self.stop_complete = stop_speed.sum()==0
                    if self.now-self.mouse_run_complete>self.config.PROTOCOL_STIM_STOP_REWARD['delay after run']+self.config.PROTOCOL_STIM_STOP_REWARD['stop time'] and not self.stop_complete:
                        #TImeout, start from the beginning
                        self.log('no reward')
                        self.run_complete=False
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
                    elif self.stop_complete:
                        self.reward()
                        self.run_complete=False
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
        
    def stimulate(self):
        power=float(str(self.cw.stim_power.input.text()))
        if self.config.POWER_VOLTAGE_RANGE[0]>power and self.config.POWER_VOLTAGE_RANGE[1]<power:
            self.log('stimulus intensity shall be within this range: {0}'.format(self.config.POWER_VOLTAGE_RANGE))
            power=0
        self.hwcommand.put(['stimulate', power])
        self.stim_state=True
        self.log('stim')
        
    def reward(self):
        self.hwcommand.put(['reward'])
        self.valve_state=True
        self.log('reward')
        
    def save_data(self):
        filename=os.path.join(self.output_folder, '{1}_{0}.mat'.format(utils.timestamp2ymdhms(time.time()).replace(':', '-').replace(' ', '_'),str(self.cw.select_protocol.input.currentText()).lower()))
        data2save={}
        data2save['time']=self.data[0]
        data2save['position']=self.data[1]
        data2save['speed']=self.data[2]
        data2save['reward']=self.data[3]
        data2save['stim']=self.data[4]
        data2save['config']=[(vn, getattr(self.config,vn)) for vn in dir(self.config) if vn.isupper()]
        data2save['frametime']=self.frame_times
        self.log(1/numpy.diff(self.frame_times).mean())
        scipy.io.savemat(filename, data2save,oned_as='row')
        self.log('Data saved to {0}'.format(filename))
        vfilename=filename.replace('.mat','.mp4')
        videofile.array2mp4(numpy.array(self.frames), vfilename, self.config.CAMERA_UPDATE_RATE)
        self.log('Video saved to {0}'.format(vfilename))
        
    def select_folder(self):
        self.output_folder=self.ask4foldername('Select output folder', self.output_folder)
        self.cw.selected_folder.setText(self.output_folder)

    def closeEvent(self, e):
        self.camera.release()
        self.hwcommand.put(['terminate'])
        e.accept()
        self.hwh.join()
        
    
if __name__ == '__main__':
    gui = Behavioral()
