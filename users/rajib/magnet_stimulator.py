import os,numpy,threading,Queue,time,scipy,tifffile,scipy.io
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    pass
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from visexpman.engine.generic import gui,fileop
from visexpman.engine.hardware_interface import daq_instrument

class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        
        self.plotw=gui.Plot(self)#Plot widget initialization
        self.plotw.setFixedHeight(450)
        self.plotw.plot.setLabels(bottom='time [s]')#Adding labels to the plot
        self.settings = gui.ParameterTable(self, self._get_params_config())
        self.settings.setMinimumWidth(300)
        self.settings.setFixedHeight(450)
        self.select_folder = QtGui.QPushButton('Data Save Folder', parent=self)
        self.selected_folder = QtGui.QLabel(fileop.select_folder_exists(['d:\\', '/tmp','c:\\temp']), self)#Displays the data folder
        
        self.l = QtGui.QGridLayout()#Organize the above created widgets into a layout
        self.l.addWidget(self.plotw, 0, 0, 1, 5)
        self.l.addWidget(self.settings, 0, 5, 1, 3)
        self.l.addWidget(self.select_folder, 1, 1, 1, 1)
        self.l.addWidget(self.selected_folder, 1, 2, 1, 1)
        self.setLayout(self.l)

    def _get_params_config(self):
        pc =  [
                {'name': 'Recording Name', 'type': 'str', 'value': ''},
                {'name': 'Sample Rate', 'type': 'float', 'value': 1000, 'suffix':' Hz'},
                {'name': 'Switch Control Voltage', 'type': 'float', 'value': 5.0, 'suffix':' V'},
                {'name': 'Pre Trigger Wait Time', 'type': 'float', 'value': 2.0, 'suffix':' s'},
                {'name': 'Post Trigger Wait Time', 'type': 'float', 'value': 0.0, 'suffix':' s'},
                {'name': 'Stimulus', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Voltage', 'type': 'float', 'value': 12.0, 'suffix':' V'},
                    {'name': 'On Time', 'type': 'float', 'value': 1.0, 'suffix':' s'},
                    {'name': 'Period Time', 'type': 'float', 'value': 3.0, 'suffix':' s'},
                    {'name': 'Repeats', 'type': 'int', 'value': 2},
                    {'name': 'Current Limit', 'type': 'float', 'value': 1.5, 'suffix':' A'},
                    ]},
                {'name': 'Voltage/Current Lookup Tables', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Voltage In', 'type': 'str', 'value': '0,0.92,1.55,2.81,5', },
                    {'name': 'Voltage Out', 'type': 'str', 'value': '0,5,10,20,32.2', },
                    {'name': 'Current In', 'type': 'str', 'value': '0,0.5,1,1.5,3', },
                    {'name': 'Current Out', 'type': 'str', 'value': '0,0.5,2.6,4.6,11.1', },
                    ]},
                    ]
        return pc
        
class DigitalOut(threading.Thread):
    def __init__(self, switch_times):
        threading.Thread.__init__(self)
        self.switch_times=switch_times
        
    def run(self):
        daq_instrument.set_digital_line('Dev1/port0/line0',0)
        state=True
        for st in self.switch_times[:-1]:
            time.sleep(st)
            daq_instrument.set_digital_line('Dev1/port0/line0',int(state))
            state=not state
        time.sleep(self.switch_times[-1])
        daq_instrument.set_digital_line('Dev1/port0/line0',0)
        

class MagnetStimulator(gui.SimpleAppWindow):
    def init_gui(self):
        icon_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'icons')
        self.toolbar = gui.ToolBar(self, ['start_experiment', 'stop','exit'], icon_folder = icon_folder)
        self.toolbar.setToolTip('''
        Connections:
            AI0: arduino p13
            AI1: p0.0
            AO0: orange wire, voltage control
            AO1: green wire, current limit control
        Usage:
            1. Make sure that power supply mode is set to Remote Ctrl (switch is on the rear)
            2. Adjust stimulus parameters
            3. Press Start Experiment button
            4. Start imaging, make sure that imaging starts within Pre trigger wait time
            
        ''')
        self.addToolBar(self.toolbar)
        self.setWindowTitle('Magnet Stimulator')
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.debugw.setMinimumWidth(1000)#Setting the sizes of the debug widget. The debug widget is created by gui.SimpleAppWindow class which is 
        self.debugw.setMinimumHeight(250)#the superclass of Behavioral. The debug widget displays the logfile and provides a python console
        self.cw.settings.params.sigTreeStateChanged.connect(self.settings_changed)
        self.settings_changed()
        self.connect(self.cw.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder)
        self.data_folder=fileop.select_folder_exists(['d:\\', '/tmp', 'c:\\temp'])
        self.stim_ended_timer = QtCore.QTimer()
        self.stim_ended_timer.timeout.connect(self.stim_finished)
        self.running=False
        
    def select_folder(self):
        #Pop up a dialog asking the user for folder selection
        self.data_folder=self.ask4foldername('Select output folder', self.data_folder)
        self.cw.selected_folder.setText(self.data_folder)
        
    def generate_waveform(self):
        self.clut=scipy.interpolate.interp1d(map(float,self.setting_values['Current Out'].split(',')), 
                                            map(float,self.setting_values['Current In'].split(',')), 
                                            bounds_error  = False, fill_value  = 0.0)
        self.vlut=scipy.interpolate.interp1d(map(float,self.setting_values['Voltage Out'].split(',')), 
                                            map(float,self.setting_values['Voltage In'].split(',')), 
                                            bounds_error  = False, fill_value  = 0.0)
        pre=numpy.zeros(self.setting_values['Pre Trigger Wait Time']*self.setting_values['Sample Rate'])
        post=numpy.zeros(self.setting_values['Post Trigger Wait Time']*self.setting_values['Sample Rate'])
        offsamples=self.setting_values['Sample Rate']*(self.setting_values['Period Time']-self.setting_values['On Time'])
        onsamples=self.setting_values['Sample Rate']*self.setting_values['On Time']
        self.switch_times=[self.setting_values['Pre Trigger Wait Time']]
        self.switch_times.extend([self.setting_values['On Time'],self.setting_values['Period Time']-self.setting_values['On Time']]*self.setting_values['Repeats'])
        self.switch_times[-1]+=self.setting_values['Post Trigger Wait Time']
        self.switch=self.setting_values['Switch Control Voltage']*numpy.concatenate((pre,numpy.tile(numpy.concatenate((numpy.ones(onsamples),numpy.zeros(offsamples))), self.setting_values['Repeats']),post))
        if self.switch.shape[0]>0:
            self.t=numpy.linspace(0,self.switch.shape[0]/float(self.setting_values['Sample Rate']),self.switch.shape[0])            
            self.cw.plotw.update_curves([self.t],[self.switch], colors=[(0,0,0)])
            self.cw.plotw.plot.setXRange(min(self.t), max(self.t))
            self.cw.plotw.plot.setTitle('Stimulus Waveform ({0:.2f} s)'.format(self.t.max()))
        
    def settings_changed(self):
        self.setting_values = self.cw.settings.get_parameter_tree(True)
        self.generate_waveform()
        
    def start_experiment_action(self):
        if self.running:
            self.log('Already running')
            return
        daq_instrument.set_voltage('Dev1/ao0',float(self.vlut(self.setting_values['Voltage'])))
        daq_instrument.set_voltage('Dev1/ao1',float(self.clut(self.setting_values['Current Limit'])))
        time.sleep(0.1)#Wait till power supply is set
        self.expected_duration=sum(self.switch_times)
        self.ai=daq_instrument.SimpleAnalogIn('Dev1/ai0:1',self.setting_values['Sample Rate'], self.expected_duration+2,timeout=20)
        self.do=DigitalOut(self.switch_times)
        self.do.start()
        self.running=True
        self.stim_ended_timer.start(int(1000.*self.expected_duration))
        self.log('Starting stimulation, expected duration is {0:.1f} s'.format(self.expected_duration))
        self.pb=gui.Progressbar(self.expected_duration, 'Stimulus', autoclose = True, timer=True)
        self.pb.show()
        
    def stim_finished(self):
        self.sync_data=self.ai.finish()
        del self.ai
        self.stim_ended_timer.stop()
        daq_instrument.set_voltage('Dev1/ao0',0.0)
        daq_instrument.set_voltage('Dev1/ao1',0.0)
        self.do.join()
        self.running=False
        self.pb.close()
        self.log('Stimulation and recording finished')
        t=numpy.linspace(0,self.sync_data.shape[0]/self.setting_values['Sample Rate'],self.sync_data.shape[0])
        self.cw.plotw.update_curves(self.sync_data.shape[1]*[t],[self.sync_data[:,i] for i in range(self.sync_data.shape[1])], colors=[(0,255,0),(0,0,255)])
        self.save2file()
        
    def save2file(self):
        dirs=[f for f in fileop.listdir_fullpath(self.data_folder) if os.path.isdir(f)]
        latest_folder=dirs[numpy.array([os.path.getctime(d) for d in dirs ]).argmax()]
        tifffiles=[f for f in fileop.listdir_fullpath(latest_folder) if 'tif' in os.path.basename(f)]
        tifffiles.sort()
        mat={}
        mat['rawdata']=numpy.array([tifffile.imread(f) for f in tifffiles])
        mat['sync']=self.sync_data
        mat['parameters']=dict([(k.replace(' ','_'), v) for k,v in self.setting_values.items()])
        outfn=os.path.join(self.data_folder, 'data_{0}_{1}.mat'.format(self.setting_values['Recording Name'],int(time.time())))
        scipy.io.savemat(outfn, mat, oned_as='column',do_compression=True)
        self.log('Data saved to {0}'.format(outfn))
        
    
    def stop_action(self):
        self.notify_user('WARNING','Not implemented')
        
    def exit_action(self):
        self.close()

if __name__ == '__main__':
    gui = MagnetStimulator()
