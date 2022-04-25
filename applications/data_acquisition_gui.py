from visexpman import gui
from visexpman import daq
import PyQt5.QtCore as QtCore

class DaqGui(gui.SimpleGuiWindow):
    def init_gui(self):#This will be called upon initialization
        import os
        import PyQt5.QtGui as QtGui
        iconfn=os.path.join(os.sep.join(__file__.split(os.sep)[:-2]),'data','icons','main_ui.png')
        #Set an application icon
        self.setWindowIcon(QtGui.QIcon(iconfn))
        #Icon shows up on taskbar
        gui.set_win_icon()
        #Set name of main window
        self.setWindowTitle('Data Acquisition GUI')
    
        self.plot=gui.Plot(self)
        self.plot.setMinimumHeight(500)
        self.plot.setMinimumWidth(500)
        self.add_dockwidget(self.plot, 'Recorded Signals', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea)
        params_config = [
                {'name': 'Recording Name', 'type': 'str', 'value': ''},
                {'name': 'Sampling Rate', 'type': 'float', 'value': 1000.0,  'suffix': ' Hz', 'decimals':6},
                {'name': 'Recording Duration', 'type': 'float', 'value': 10.0,  'suffix': ' s', 'decimals':6},
                ]
        self.params = gui.ParameterTable(self, params_config)
        self.params.setMinimumWidth(300)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)#Function called when any setting modified by the user
        self.add_dockwidget(self.params, 'Settings', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea)
        
        toolbar_buttons=['start', 'stop', 'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        
        import PyQt5.QtGui as QtGui
        self.statusbar=self.statusBar()
        self.statusbar.msg=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.msg)
        self.statusbar.status_msg=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.status_msg)
        self.set_status('Idle','gray')
        self.shortcut_start = QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self)
        self.shortcut_start.activated.connect(self.start_action)
        self.parameter_changed()        
        
    def set_status(self,state, color):
        self.statusbar.status_msg.setStyleSheet(f'background:{color};')
        self.statusbar.status_msg.setText(state)
        QtCore.QCoreApplication.instance().processEvents()
        
    def parameter_changed(self):
        self.setting_values=self.params.get_parameter_tree(return_dict=True)#Grab all values from Settings tab and organize to a dictionary
        self.log(self.setting_values)#Display setting values on log widget and also save to logfile
        
    def start_action(self):
        duration=self.setting_values['params/Recording Duration']#Take recording duration from Settings
        fsample=self.setting_values['params/Sampling Rate']
        self.ai=daq.AnalogRead('Dev2/ai1:2', duration, fsample)
        self.timer=QtCore.QTimer()
        self.timer.singleShot(int(duration*1000), self.finish_recording)
        self.log('Recording started')#Notify user about the beginning of recording data
        import numpy
        waveform=numpy.zeros((1,int(duration*fsample)))
        waveform[0]=numpy.sin(2*numpy.pi*numpy.arange(waveform.shape[1])/waveform.shape[1])
        self.ao,d=daq.set_waveform_start('Dev2/ao1',waveform,fsample)
        self.set_status('recording','red')
        
    def stop_action(self):
        pass
        
    def finish_recording(self):
        data=self.ai.read()#Read acquired data
        self.plot_traces(data,['AI1', 'AI2'],fsample=self.setting_values['params/Sampling Rate'])
        self.plot.plot.setTitle(self.setting_values['params/Recording Name'])#Copy recording name to plot's title
        self.log('Recording ended')
        daq.set_waveform_finish(self.ao, 1)
        self.set_status('saving','yellow')
        self.save_data(data)
        self.set_status('Idle','gray')
        
    def save_data(self,data):
        import os
        import tables
        from visexpman.engine.vision_experiment.experiment_data import get_id
        if not self.ask4confirmation('Do you want to save data?'):
            return
        name=self.setting_values['params/Recording Name']
        fn=os.path.join(r'c:\tmp', f'data_{name}_{get_id()}.h5')#Generate a filename with unique id
        fh=tables.open_file(fn,'w')
        #Use zlib for data compression, compression level 5 is optimal
        datacompressor = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
        #Initialize array
        datatype=tables.Float32Atom(data.shape)
        data_handle=fh.create_earray(fh.root, 'data', datatype, (0,),filters=datacompressor)
        #Add data
        data_handle.append(data[None,:])
        #Save recording parameters as attributes
        setattr(fh.root.data.attrs,'sample_rate',self.setting_values['params/Sampling Rate'])
        fh.close()
        self.notify('Information', f'Data is saved to {fn}')
        
        
        
    def exit_action(self):
        self.close()
        
    def plot_traces(self, sig,channel_names,fsample):
        import numpy
        x=[numpy.arange(sig.shape[1])/fsample]*sig.shape[0]
        y=[sig[i] for i in range(sig.shape[0])]
        from visexpman import colors
        pp=[{'name': (str(channel_names[i])), 'pen':(numpy.array(colors.get_color(i))*255).tolist()} for i in range(len(x))]
        self.plot.update_curves(x, y, plotparams=pp)
        
if __name__=='__main__':
    gui=DaqGui(logfolder=r'c:\tmp')
