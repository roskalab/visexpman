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
        
    def parameter_changed(self):
        setting_values=self.params.get_parameter_tree(return_dict=True)#Grab all values from Settings tab and organize to a dictionary
        self.log(setting_values)#Display setting values on log widget and also save to logfile
        
if __name__=='__main__':
    gui=DaqGui(logfolder=r'c:\tmp')
