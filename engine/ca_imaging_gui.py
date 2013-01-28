import os.path

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.generic import log

class ExperimentControlGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment control', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        #Stimulation/experiment control related
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList([]))
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop',  self)
        self.experiment_progress = QtGui.QProgressBar(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_name, 0, 0, 1, 2)
        self.layout.addWidget(self.start_experiment_button, 0, 2, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 0, 4)
        self.layout.addWidget(self.experiment_progress, 3, 0, 1, 2)
        self.setLayout(self.layout)        

class MainWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
#        self.resize(100, 100)
        

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 2, 4)        
        self.setLayout(self.layout)


class CaImagingGui(Qt.QMainWindow):
    '''
    Main Qt GUI class of vision experiment manager gui.
    '''
    def __init__(self, user, config_class):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.config.user = user
        self.console_text = ''
        self.log = log.Log('caimaging log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'caimaging_log.txt')), local_saving = True)
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle('Calcium Imaging Experiment GUI - {0} - {1}' .format(user,  config_class))
        self.create_widgets()
        self.create_layout()
        self.show()
        
        if qt_app is not None: qt_app.exec_()
        
    def create_widgets(self):
        self.main_widget = MainWidget(self, self.config)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Main')
        self.main_tab.setCurrentIndex(0)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.main_tab, 0, 0, 1, 1)
        self.setLayout(self.layout)

if __name__ == '__main__':
    CaImagingGui('zoltan', 'CaImagingTestConfig')
