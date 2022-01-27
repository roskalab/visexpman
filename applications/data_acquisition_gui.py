from visexpman import gui
import PyQt5.QtCore as QtCore

class DaqGui(gui.SimpleGuiWindow):
    def init_gui(self):#This will be called upon initialization
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
        
    def set_status(self,state, color):
        self.statusbar.status_msg.setStyleSheet(f'background:{color};')
        self.statusbar.status_msg.setText(state)
        QtCore.QCoreApplication.instance().processEvents()
        
    def parameter_changed(self):
        setting_values=self.params.get_parameter_tree(return_dict=True)#Grab all values from Settings tab and organize to a dictionary
        self.log(setting_values)#Display setting values on log widget and also save to logfile
        
    def start_action(self):
        pass
        
    def stop_action(self):
        pass
        
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
