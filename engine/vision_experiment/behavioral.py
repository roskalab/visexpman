import os,sys,time,threading,Queue,tempfile,random,shutil,multiprocessing,copy
import numpy,scipy.io
import serial
from PIL import Image
import cv2
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import gui,utils,videofile
from visexpman.engine.hardware_interface import daq_instrument
#TODO: test stim channel info in mat file
#TODO: check video frame rate 
#TODO: trace labels

class Config(object):
    '''
    This configuration class is for storing all the parameters
    '''
    def __init__(self):
        self.STIM_CHANNELS=['Dev1/ao0','Dev1/ao1']#Physical channels of usb-daq device
        self.DIO_PORT = 'COM4' if os.name=='nt' else '/dev/ttyUSB1'#serial port which controls the valve
        self.DATA_FOLDER = 'c:\\temp' if os.name == 'nt' else tempfile.gettempdir()#Default data folder
        self.VALVE_OPEN_TIME=10e-3
        self.STIMULUS_DURATION=1.0
        self.CURSOR_RESET_POSITION=0.0#Reset position of the cursor, 0.01 means that the reet positions will be 0.01*screen_width and 0.99*screen_width
        self.CURSOR_POSITION_UPDATE_PERIOD = 50e-3#second, The period time for calling the cursor handler. Cursor position is sampled and speed is calculated when curor handler is called
        self.CAMERA_UPDATE_RATE=16#Hz, Frame rate of camera. This value will be used for the output video file too
        self.CAMERA_FRAME_WIDTH=640/2
        self.CAMERA_FRAME_HEIGHT=480/2
        self.POWER_VOLTAGE_RANGE=[0,10]#The minimum and maximum accepted values for controlling the stimulus
        self.RUN_DIRECTION=1#Polarity of speed signal

        self.RUN_THRESHOLD=0.5#The speed at 50% of the time when mouse is expected to run shall be above MOVE_THRESHOLD
        #7 cm: 803-5,988-21,1072-75,1172-270,1341-293,1338-466: 7 cm = 930 pixel -> 1 pixel = 0.0075214899713467055
        self.PIXEL2SPEED=0.0075214899713467055
        self.MOVE_THRESHOLD=1#Above this speed the mouse is considered to be moving
        #Protocol specific parameters
        self.PROTOCOL_STOP_REWARD={}
        self.PROTOCOL_STOP_REWARD['run time']=5#sec
        self.PROTOCOL_STOP_REWARD['stop time']=0.3#sec
        
        self.PROTOCOL_STIM_STOP_REWARD={}
        self.PROTOCOL_STIM_STOP_REWARD['run time']=2#sec
        self.PROTOCOL_STIM_STOP_REWARD['stop time']=2#sec
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time range']=10#sec
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']=0.5#sec
        self.PROTOCOL_STIM_STOP_REWARD['delay after run']=2#sec
        
        self.PROTOCOL_KEEP_RUNNING_REWARD={}
        self.PROTOCOL_KEEP_RUNNING_REWARD['run time']=15.0
        
    def get_protocol_names(self):
        return [vn.replace('PROTOCOL_','') for vn in dir(self) if 'PROTOCOL_' in vn]
        
class FrameSaver(multiprocessing.Process):
    '''
    This process saves the images transmitted through the input queue. 
    It is running on a different processor core from the main thread to ensure higher video recording framerate.
    '''
    def __init__(self,queue):
        multiprocessing.Process.__init__(self)
        self.queue=queue
        
    def run(self):
        while True:
            if not self.queue.empty():
                msg=self.queue.get()
                if msg=='terminate':#If message contains this string, stop the process
                    break
                else:
                    frame,filename=msg#A message shall contain the frame and the filename where the frame is to be saved
                    Image.fromarray(frame).save(filename)#Saving the image
            else:
                time.sleep(1e-3)#Ensuring that this process does not consume all the time of the processor where it is running
                
class FileSaver(multiprocessing.Process):
    '''
    This process saves the images transmitted through the input queue. 
    It is running on a different processor core from the main thread to ensure higher video recording framerate.
    '''
    def __init__(self,queue):
        multiprocessing.Process.__init__(self)
        self.queue=queue
        
    def run(self):
        while True:
            if not self.queue.empty():
                msg=self.queue.get()
                if msg=='terminate':#If message contains this string, stop the process
                    break
                else:
                    filename, data2save, frame_folder, fps=msg
                    self.save(filename, data2save, frame_folder, fps)
            else:
                time.sleep(1e-3)#Ensuring that this process does not consume all the time of the processor where it is running
                
    def save(self, filename, data2save, frame_folder, fps):
        scipy.io.savemat(filename, data2save,oned_as='row', do_compression=True)
        vfilename=filename.replace('.mat','.mp4')
        #frames saved to a temporary folder are used for generating an mpeg4 video file.
        videofile.images2mpeg4(frame_folder, vfilename,fps)
        shutil.rmtree(frame_folder)
        
class HardwareHandler(threading.Thread):
    '''
    Runs parallel with the main thread. Via queues it receives commands to open/close the valve or generate a stimulus
    '''
    def __init__(self,command,response,config):
        self.command=command
        self.response=response#Via queue the actual state of the stim and valve is signalled for the main thread
        self.config=config
        threading.Thread.__init__(self)
        
    def run(self):
        s=serial.Serial(self.config.DIO_PORT)#Opening the serial port
        s.setBreak(0)#Bringing the orange wire to a known state
        s.setRTS(1)#Same for the green one
        while True:
            if not self.command.empty():
                cmd=self.command.get()
                if cmd[0]=='terminate':#Terminate the command loop and stop thread
                    break
                elif cmd[0] == 'stimulate':
                    daq_instrument.set_voltage(cmd[2],cmd[1])#cmd[2] contains the physical channel name of the usb daq device, cmd[1] is the voltage
                    time.sleep(self.config.STIMULUS_DURATION)#Wait while the duration of the stimulus is over
                    daq_instrument.set_voltage(cmd[2],0)#Set the analog output to 0V
                    self.response.put('stim ready')#Signal the main thread that the stimulus is ready
                elif cmd[0] == 'reward':
                    s.setBreak(1)#Set the orange wire to 0 V which opens the valve (it has double inverted logic)
                    time.sleep(self.config.VALVE_OPEN_TIME)
                    s.setBreak(0)#Close the valve
                    self.response.put('reward ready')#signalling the main thread that delivering the reward is done
                elif cmd[0] == 'open_valve':
                    s.setBreak(1)#Opening the valve for debug purposes
                elif cmd[0] == 'close_valve':
                    s.setBreak(0)#Close tha valve 
            else:
                time.sleep(10e-3)
                
        s.setBreak(0)#Bring the orange and green wires to a safe state
        s.setRTS(1)
        s.close()#Close the serial port

HELP='''Start experiment: Ctrl+a
Stop experiment: Ctrl+s
Select next protocol: Space'''

class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.image=gui.Image(self)#Create image widget
        self.image.setFixedWidth(450)#Setting its width
        ar=float(parent.config.CAMERA_FRAME_WIDTH)/parent.config.CAMERA_FRAME_HEIGHT
        self.image.setFixedHeight(450/ar)#Setting image widget height while keeping the aspect ratio of camera resolution
        
        self.plotw=gui.Plot(self)#Plot widget initialization
        self.plotw.setFixedHeight(250)
        self.plotw.plot.setLabels(left='speed [cm/s]', bottom='time [s]')#Adding labels to the plot
        #self.plotw.plot.addLegend(size=(120,60))
        
        self.setToolTip(HELP)
        self.select_protocol=gui.LabeledComboBox(self,'Select protocol', parent.config.get_protocol_names())#With this combobox the stimulus protocol can be selected
        self.select_folder = QtGui.QPushButton('Data Save Folder', parent=self)#Clicking this button the data save folder can be selected
        self.selected_folder = QtGui.QLabel(parent.config.DATA_FOLDER, self)#Displays the data folder
        
        self.stim_power = gui.LabeledInput(self, 'Stimulus Intensity [V]')#The voltages controlling the stimulus devices can be set here
        self.stim_power.input.setText('1,1')#The default value is 1 V for both channels
        self.stim_power.input.setFixedWidth(40)
        
        self.open_valve=gui.LabeledCheckBox(self,'Open Valve')#This checkbox is for controlling the valve manually
        self.open_valve.setToolTip('When checked, the valve is open')
        self.save_data=gui.LabeledCheckBox(self,'Save Data')#Checking this checkbox enables saving the video and the speed signal of a session
        self.save_data.input.setCheckState(2)
        
        self.start = QtGui.QPushButton('Start', parent=self)#Start recording/experiment session
        self.start.setMaximumWidth(100)
        self.stop = QtGui.QPushButton('Stop', parent=self)#Stop recording/experiment session
        self.stop.setMaximumWidth(100)
        
        self.enable_periodic_data_save=gui.LabeledCheckBox(self,'Enable Periodic Save')
        self.enable_periodic_data_save.input.setCheckState(2)
        self.save_period = gui.LabeledInput(self, 'Data Save Period [s]')
        self.save_period.input.setText('60')
        self.save_period.input.setFixedWidth(40)
        
        self.l = QtGui.QGridLayout()#Organize the above created widgets into a layout
        self.l.addWidget(self.image, 0, 0, 5, 2)
        self.l.addWidget(self.plotw, 0, 2, 1, 5)
        self.l.addWidget(self.select_protocol, 1, 2, 1, 2)
        self.l.addWidget(self.stim_power, 2, 5, 1, 1)
        self.l.addWidget(self.enable_periodic_data_save, 3, 4, 1, 1)
        self.l.addWidget(self.save_period, 3, 5, 1, 1)
        self.l.addWidget(self.select_folder, 1, 4, 1, 1)
        self.l.addWidget(self.selected_folder, 1, 5, 1, 1)
        self.l.addWidget(self.open_valve, 1, 6, 1, 1)
        self.l.addWidget(self.save_data, 2, 4, 1, 1)
        self.l.addWidget(self.start, 2, 2, 1, 1)
        self.l.addWidget(self.stop, 2, 3, 1, 1)
        self.setLayout(self.l)

class Behavioral(gui.SimpleAppWindow):
    '''
    Main application class and main thread of the behavioral control software.
    '''
    def init_gui(self):
        self.config=Config()#The Config class is created which holds the configuration values
        self.setWindowTitle('Behavioral Experiment Control')
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.cw.setMinimumHeight(500)#Adjusting its geometry
        self.cw.setMinimumWidth(1100)
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.debugw.setMinimumWidth(800)#Setting the sizes of the debug widget. The debug widget is created by gui.SimpleAppWindow class which is 
        self.debugw.setMinimumHeight(250)#the superclass of Behavioral. The debug widget displays the logfile and provides a python console
        self.setMinimumWidth(1200)#Setting the minimum size of the main user interface
        self.setMinimumHeight(750)
        self.camera_reader = QtCore.QTimer()#Timer for periodically reading out the camera
        self.camera_reader.timeout.connect(self.read_camera)#Assigning the function which reads out the camera to this timer
        self.camera_reader.start(int(1000./self.config.CAMERA_UPDATE_RATE))#Setting the update rate of the timer
        self.camera = cv2.VideoCapture(0)#Initialize video capturing
        self.camera.set(3, self.config.CAMERA_FRAME_WIDTH)#Set camera resolution
        self.camera.set(4, self.config.CAMERA_FRAME_HEIGHT)
        #Assign the keyboard hortcuts to functions, more details check the value of HELP variable
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+a'), self), QtCore.SIGNAL('activated()'), self.start_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self), QtCore.SIGNAL('activated()'), self.stop_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Space'), self), QtCore.SIGNAL('activated()'), self.next_protocol)
        #Assigning the folder selection button to the function which pops up the dialog box
        self.connect(self.cw.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder)
        #When the open valve checkbox is toggled, the toggle_value function is called
        self.connect(self.cw.open_valve.input, QtCore.SIGNAL('stateChanged(int)'),  self.toggle_valve)
        #Assigning start and stop buttons with the corresponding functions
        self.connect(self.cw.start, QtCore.SIGNAL('clicked()'), self.start_experiment)
        self.connect(self.cw.stop, QtCore.SIGNAL('clicked()'), self.stop_experiment)
        self.output_folder = self.config.DATA_FOLDER
        self.cursor_t = QtCore.QTimer()#Timer for periodically checking mouse cursor position
        self.cursor_t.timeout.connect(self.cursor_handler)#Assign it to cursor_handler function
        self.cursor_t.start(int(1000.*self.config.CURSOR_POSITION_UPDATE_PERIOD))#Start timer with the right period time
        self.screen_width = self.qt_app.desktop().screenGeometry().width()#Read the screens's size. This will be used for resetting cursor position
        self.screen_height = self.qt_app.desktop().screenGeometry().height()
        self.screen_left=int(self.screen_width*self.config.CURSOR_RESET_POSITION)#When the cursor is left from this position it is set to the right side
        self.screen_right=int((1-self.config.CURSOR_RESET_POSITION)*self.screen_width)-1#When the cursor is right from this position it is set to the left side
        nparams=5#time, position, speed, reward, stim
        self.empty=numpy.empty((nparams,0))#Empty array for resetting other arrays
        self.hwcommand=Queue.Queue()#creating queue for controlling and reading the hardware handler thread
        self.hwresponse=Queue.Queue()
        self.hwh=HardwareHandler(self.hwcommand,self.hwresponse, self.config)#Initialize hardware handler thread (controls valve and stimulus)
        self.hwh.start()#Starting the thread
        self.framequeue=multiprocessing.Queue()#Queue for sending video frames for the frame saver
        self.framesaver=FrameSaver(self.framequeue)#Create frame saver process
        self.framesaver.start()#Start the process
        self.video_counter=0
        self.frame_counter=0
        self.filesaver_q=multiprocessing.Queue()
        self.filesaver=FileSaver(self.filesaver_q)
        self.filesaver.start()
        #Initialize state variables:
        self.stim_state=0#0 when no stimulus is presented, 1 when LED1 and 2 when LED2 is on
        self.valve_state=False#True when valve is open
        self.running=False#True when session is running
        
    def toggle_valve(self,state):
        '''
        Opens/closes the valve depending on the state of the checkbox
        '''
        if state==2:
            self.hwcommand.put(['open_valve'])#Sending the "open_valve" command via the command queue to the hardware handler thread
        elif state == 0:
            self.hwcommand.put(['close_valve'])
        
    def read_camera(self):
        '''
        Reads the camera periiodically, displays the image and sends it to the frame saver process when a session is running
        '''
        ret, frame = self.camera.read()#Reading the raw frame from the camera
        if frame is None:
            return
        frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to rearrange the color channels
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        
        if hasattr(frame_color_corrected, 'shape'):
            self.cw.image.set_image(numpy.rot90(frame_color_corrected,3),alpha=1.0)#Setting the image with correct colors on the user interface. A 90 degree rotation is necessary
            if self.running:#If the experiment is running...
                self.frame_times.append(time.time())#... the time of image acquisition is saved
                #self.frames.append(frame_color_corrected)#Saving the frame to the memory (might not be necessary)
                if self.cw.save_data.input.checkState()==2:#If the data save checkbox is checked...
                    #... The image and the filename of the image file is sent via a queue to the frame saver. The images are saved to a temporary folder
                    self.framequeue.put([copy.deepcopy(frame_color_corrected), os.path.join(self.frame_folder, 'f{0:0=5}.png'.format(self.frame_counter))])
                    self.frame_counter+=1
            
    def _get_new_frame_folder(self):
        self.frame_folder=os.path.join(tempfile.gettempdir(), 'vf_{0}_{1}'.format(self.video_counter,time.time()))#Create temporary folder for video frames
        self.video_counter+=1
        if os.path.exists(self.frame_folder):#If already exists, delete it with its content
            shutil.rmtree(self.frame_folder)
        os.mkdir(self.frame_folder)
            
    def start_experiment(self):
        if self.running: return#Do nothing when already running
        self.running=True
        self.checkdata=numpy.copy(self.empty)#checkdata contains the speed values for checking whether the mouse reached run for x seconds or stop for y seconds condition
        self.data=numpy.copy(self.empty)#self.data stores the all the speed, valve state, stimulus state data
        self.frame_times=[]
        self.save_period=float(self.cw.save_period.input.text())
        self.enable_periodic_data_save=self.cw.enable_periodic_data_save.input.checkState()==2
        self.recording_start_time=time.time()
        self.last_save_time=time.time()
        self.data_index=0
        self.frame_counter=0
        self.log('start experiment')
        self._get_new_frame_folder()
        #Protocol specific
        self.run_complete=False
        self.stimulus_fired=False
        self.stop_complete=False
        self.generate_run_time()#Generate the randomized expected runtime for start stop stim protocol
        self.last_reward = 0
        
    def check_recording_save(self):
        if not self.enable_periodic_data_save:return
        now=time.time()
        #Restart is enabled if last reward was within a second or it was a long time ago (20 sec).
        dt=now-self.last_reward
        if now-self.last_save_time>self.save_period:# and ((dt<2.0 and dt>0.5) or dt>20):
            self.save_data()
            self._get_new_frame_folder()
            self.last_save_time=now
            self.frame_counter=0
            if self.data[0,-1]-self.data[0,0]>2*60:
                index=numpy.where(self.data[0]>self.data[0,-1]-60.0)[0].min()
                self.data=self.data[:,index:]
            self.data_index=self.data.shape[1]
            
            #self.stop_experiment()
            #self.start_experiment()
            
        
    def stop_experiment(self):
        if not self.running: return
        self.running=False
        self.log('stop experiment')
        if self.cw.save_data.input.checkState()==2:#If save data checked...
            self.save_data() #... Save all the speeed, valve state, timing, stimulus state and video data to file
        
    def next_protocol(self):
        '''
        When space is pressed, the actual item in the protocol selector combobox is changed
        '''
        if self.running: return#If space is accidentially pressed during experiment, do not change protocol
        next_index = self.cw.select_protocol.input.currentIndex()+1
        if next_index == self.cw.select_protocol.input.count():
            next_index = 0
        self.cw.select_protocol.input.setCurrentIndex(next_index)
        
    def cursor_handler(self):
        '''
        Cursor handler, reads mouse cursor position, calculates speed and calls protocol specific logic
        '''
        if not self.running:
            return
        self.check_recording_save()
        self.cursor_position = QtGui.QCursor.pos().x()#Reading the mouse position (x)
        self.now=time.time()#Save the current time for timestamping later the data
        reset_position=None
        jump=0
        if self.cursor_position<=self.screen_left:#If cursor position is left from the left edge...
            reset_position = self.screen_right# ... set the reset position to the other side
            jump=self.screen_width#this is for  eliminating the effect of the position resetting at the speed calculation
        if self.cursor_position>=self.screen_right:
            reset_position = self.screen_left
            jump=-self.screen_width
        if reset_position is not None:#If reet_position is valid...
            QtGui.QCursor.setPos(reset_position,int(self.screen_height*0.5))#...Setting the cursor to reset position
        if self.data.shape[1]>0:
            ds=self.cursor_position-self.data[1, -1]#movement of x position since the last call of cursor handler
            self.cursor_position+=jump#correct cursor position with jump
            #calculate speed using the pixel2speed conversion factor and the time elapsed since the last call of cursor handler
            speed=self.config.RUN_DIRECTION*ds/(self.now-self.data[0,-1])*self.config.PIXEL2SPEED
        else:
            speed=0#At the first call of cursor handler the previous cursor position is not known
        #collect all the data to one array: time, cursor position, speed, valve state, stimulus state
        newdata=numpy.array([[self.now, self.cursor_position,speed,int(self.valve_state),int(self.stim_state)]]).T
        self.data = numpy.append(self.data, newdata,axis=1)#Append it to data
        self.checkdata = numpy.append(self.checkdata, newdata,axis=1)#Append newdata to the checkdata where the protocol handlers will look for srun/stop events
        t=self.data[0]-self.data[0,0]#Relative time values for the x axis of the plot
        #Plot speed, valve state and stimulus state on the user interface
        self.cw.plotw.update_curves([t,t,t], [self.data[2],self.data[3]*self.data[2].max(),self.data[4]*self.data[2].max()], colors=[(0,0,0),(0,255,0),(0,0,255)])
        self.cw.plotw.plot.setXRange(min(t), max(t))#Set the x range of plot
        #Call the protocol handler which value is taken from protocol selection combox
        getattr(self, str(self.cw.select_protocol.input.currentText()).lower())()
        #Check stim and valve states:
        if not self.hwresponse.empty():
            resp=self.hwresponse.get()#If there is a stim ready message...
            if resp=='stim ready':
                self.stim_state=0#...set the stim_state to 0
            elif resp == 'reward ready':#Same for valve state
                self.valve_state=False
        
    def stop_reward(self):
        '''
        Stop reward protocol handler
        '''
        #If time recorded into checkdata is bigger than run time and stop time ...
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
            t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
            #Calculate index for last runtime +stoptime duration
            t0index=numpy.where(t>t.max()-(self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']))[0].min()
            #Calculate index for last stoptime duration
            index=numpy.where(t>t.max()-self.config.PROTOCOL_STOP_REWARD['stop time'])[0].min()
            run_speed=speed[t0index:index]#using these indexes, take out running part ...
            stop_speed=speed[index:]#...and the stop part
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]#Decide wheather at the run part was the speed above thershold
            stop=stop_speed.sum()==0#All elements of the stop part shall be below threshold
            if run and stop:#If both conditions are met ...
                self.reward()#... give reward and...
                self.checkdata=numpy.copy(self.empty)#Reset checkdata
    
    def stim_stop_reward(self):
        '''
        Stim top protocol handler
        '''
        #Run the protocol handler is checkdata has at least self.actual_runtime duration
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.actual_runtime:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speeds above threshold are marked with 1s
            t=self.checkdata[0]-self.checkdata[0,0]
            index=numpy.where(t>t.max()-self.actual_runtime)[0].min()#calculate index of last actual_runtime duration
            run_speed=speed[index:]#cut this section out of speed vector
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]#decide if the mouse was really running
            if run and not self.run_complete:#If mouse was really running and we consider the run part uncompleted...
                self.run_complete=True#... then mark this with completed. This is necessary for firing the stimulus only once and detect if the mouse stops running afterwards
            if self.run_complete:
                if not self.stimulus_fired:#If stimulus not yet fired but run part is completed by mouse...
                    self.mouse_run_complete=self.now
                    self.stimulate()#... present stimulus
                    self.stimulus_fired=True
                else:#If stimulus was fired, ...
                    index=numpy.where(t>t.max()-self.config.PROTOCOL_STIM_STOP_REWARD['stop time'])[0].min()#... we look back for the last "stop time" duration
                    stop_speed=speed[index:]#Cut out this part from the speed vector
                    self.stop_complete = stop_speed.sum()==0#Check if the mouse was really stopped
                    if self.now-self.mouse_run_complete>self.config.PROTOCOL_STIM_STOP_REWARD['delay after run']+self.config.PROTOCOL_STIM_STOP_REWARD['stop time'] and not self.stop_complete:
                        #TImeout, start from the beginning if time elapsed since the run complete event is bigger than "delay after run" and "stop time" (expected time to stay stopped"
                        self.log('no reward')
                        self.run_complete=False#Reset all the state variables
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
                        self.generate_run_time()#generate a new randomized runtime 
                    elif self.stop_complete:
                        self.reward()#If mouse stopped afterthe run complete for a certain amount of time, reward is given
                        self.run_complete=False#Reset state variables
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
                        self.generate_run_time()#generate a new randomized runtime 
                        
    def keep_running_reward(self):
        '''
        If mouse is running for at least 10 seconds and the last reward was given 10 sec ago
        '''
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time']:
            t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
            t0index=numpy.where(t>t.max()-self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time'])[0].min()
            ismoving=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)[t0index:]
            run=ismoving.sum()>self.config.RUN_THRESHOLD*ismoving.shape[0]#Decide wheather at the run part was the speed above thershold
            if run and self.checkdata[0,-1]-self.last_reward>=self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time']:
                self.reward()#... give reward and...
                self.checkdata=numpy.copy(self.empty)#Reset checkdata
                        
    def generate_run_time(self):
        '''
        Stim stop protocol expected runtime has a random part that needs to be recalculated
        
        The random part is between 0...'stimulus time range' and has its values are generated in 'stimulus time resolution' steps
        The random part i added to the "run time"
        '''
        random_time=self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']*int(random.random()*self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time range']/self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution'])
        self.actual_runtime = self.config.PROTOCOL_STIM_STOP_REWARD['run time']+random_time
        
    def stimulate(self):
        try:
            power=map(float, str(self.cw.stim_power.input.text()).split(','))#read power intensity values from user interface
        except:
            import traceback
            self.log(traceback.format_exc())
        if self.config.POWER_VOLTAGE_RANGE[0]>power[0] and self.config.POWER_VOLTAGE_RANGE[1]<power[0]\
            or self.config.POWER_VOLTAGE_RANGE[0]>power[1] and self.config.POWER_VOLTAGE_RANGE[1]<power[1]:
            #Check if the provided value falls into the expected range, otherwise give warning
            self.log('stimulus intensity shall be within this range: {0}'.format(self.config.POWER_VOLTAGE_RANGE))
            power=[0,0]
        channel = random.choice(range(2))#Make a random choice from the two stimulus channels
        self.hwcommand.put(['stimulate', power[channel], self.config.STIM_CHANNELS[channel]])#Send command to hardware handler to generate stimulation
        self.stim_state=channel+1#Stim state is 0 when no stimulus is shown, otherwise the id of the stimulus channel
        self.log('stim at channel {0}'.format(self.stim_state))
        
    def reward(self):
        self.hwcommand.put(['reward'])#hardware handler is notified to generate reward 
        self.valve_state=True
        self.log('reward')
        self.last_reward=time.time()
        
    def save_data(self):
        '''
        Save all the recorded data to a mat file and generate a video file from the captured frames
        '''
        #Filename containts the protocol name and the date
        filename=os.path.join(self.output_folder, '{1}_{0}.mat'.format(utils.timestamp2ymdhms(time.time()).replace(':', '-').replace(' ', '_'),str(self.cw.select_protocol.input.currentText()).lower()))
        #Aggregating the data to be saved
        data2save={}
        data2save['time']=self.data[0,self.data_index:]
        data2save['position']=self.data[1,self.data_index:]
        data2save['speed']=self.data[2,self.data_index:]
        data2save['reward']=self.data[3,self.data_index:]
        data2save['stim']=self.data[4,self.data_index:]
        #configuration values are also saved
        data2save['config']=[(vn, getattr(self.config,vn)) for vn in dir(self.config) if vn.isupper()]
        data2save['frametime']=self.frame_times[self.data_index:]
        self.log('Video capture frame rate was {0}'.format(1/numpy.diff(self.frame_times).mean()))
        self.log('Saving data to {0}, saving video to {1}'.format(filename,filename.replace('.mat','.mp4')))
        self.filesaver_q.put((filename, data2save, self.frame_folder,  self.config.CAMERA_UPDATE_RATE))
        
    def select_folder(self):
        #Pop up a dialog asking the user for folder selection
        self.output_folder=self.ask4foldername('Select output folder', self.output_folder)
        self.cw.selected_folder.setText(self.output_folder)

    def closeEvent(self, e):
        #When the user interface is closed the following procedure is preformed
        self.camera.release()#Stop camera operation
        self.hwcommand.put(['terminate'])#Terminate hardware handler thread
        e.accept()
        self.hwh.join()#Wait till thread ends
        self.framequeue.put('terminate')#Terminate frame saver process and ...
        self.framesaver.join()#Wait until it terminates
        self.filesaver_q.put('terminate')
        self.filesaver.join()
            
if __name__ == '__main__':
    gui = Behavioral()
