'''
http://qt-project.org/doc/qt-4.8/stylesheet-examples.html


Config parameters:
EXPERIMENT_DATA_PATH
USE_DATE_SUBFOLDERS
MAT/HDF5



'''


import os.path
import numpy

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui as guiv
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.generic import gui
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.generic import log
from visexpA.engine.datadisplay import imaged
from visexpA.engine.datadisplay.plot import Qt4Plot

STYLE = 'background-color:#303030;color:#D0D0D0;selection-color:#0000A0;selection-background-color:#808080;border-style:outset;border-width: 1px;border-color:#707070;padding:3px'
STYLE='background-color:#C0C0C0;'
#STYLE=''

class ImageAnalysis(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, '')
        
    def create_widgets(self):
        self.channel = gui.LabeledComboBox(self, 'Select channel')
        self.channel.input.addItems(QtCore.QStringList(['Top',  'Side']))
        self.function = gui.LabeledComboBox(self, 'Select function')
        self.function.input.addItems(QtCore.QStringList(['histogram',  'time series',  ]))
        self.histogram_range = gui.LabeledInput(self, 'Histogram min, max, gamma')
        
        self.plot = Qt4Plot()
        self.plot.setMaximumHeight(150)
        self.plot.setMaximumWidth(600)
        self.plot.clear()
        self.plot.setdata(numpy.arange(100), penwidth=1.5, color=Qt.Qt.black)
        self.plot.setaxisscale([0, 100, -1000, 1000])
        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.channel, 0, 0, 1, 1)
        self.layout.addWidget(self.function, 0, 1, 1, 1)
        self.layout.addWidget(self.histogram_range, 0, 2, 1, 1)
        self.layout.addWidget(self.plot, 1, 0, 1, 3)
        self.setLayout(self.layout)


class MeasurementFiles(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, 'Measurement files')
        
    def create_widgets(self):
        self.cell_name = gui.LabeledComboBox(self, 'Cell name')
        self.recording = gui.LabeledComboBox(self, 'Select recording')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.cell_name, 0, 0, 1, 1)
        self.layout.addWidget(self.recording, 1, 0, 1, 1)
        self.setLayout(self.layout)

class ObjectiveControl(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, 'Objective control')
        
    def create_widgets(self):
        self.position = QtGui.QLabel('', self)
        self.position_name = gui.LabeledInput(self, 'Position name')
        self.add = QtGui.QPushButton('Add',  self)
        self.select_position = gui.LabeledComboBox(self, 'Select position')
        self.select_position.input.setEditable(True)
        self.move = QtGui.QPushButton('Move',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.position, 0, 0, 1, 1)
        self.layout.addWidget(self.position_name, 1, 0, 1, 2)
        self.layout.addWidget(self.add, 1, 2, 1, 1)
        self.layout.addWidget(self.select_position, 2, 0, 1, 2)
        self.layout.addWidget(self.move, 2, 2, 1, 1)
        
        self.setLayout(self.layout)

class BeamerControl(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, 'Beamer control')
        
    def create_widgets(self):
        self.test_beamer = gui.LabeledCheckBox(self, 'Test beamer')
        self.trigger_delay = gui.LabeledInput(self, 'Trigger delay [us]')
        self.trigger_pulse_width = gui.LabeledInput(self, 'Trigger pulse width [us]')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.test_beamer, 0, 0, 1, 1)
        self.layout.addWidget(self.trigger_delay, 1, 0, 1, 1)
        self.layout.addWidget(self.trigger_pulse_width, 2, 0, 1, 1)
        self.setLayout(self.layout)

class ScanParameters(gui.GroupBox):
    def __init__(self, parent,  name):
        gui.GroupBox.__init__(self, parent, name)
        
    def create_widgets(self):
        self.inputs = {}
        self.parameter_names = ['scan_area_size_xy',  'scan_area_center_xy',  'resolution']
        for p in self.parameter_names:
            self.inputs[p] = gui.LabeledInput(self, p.replace('_',  ' ') )
            
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        i = 0
        for p in self.parameter_names:
            self.layout.addWidget(self.inputs[p], 0, i, 1, 1)
            i+= 1
        self.setLayout(self.layout)
    
class RoiScanParameters(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self,  parent, 'Roi scan parameters')
        
    def create_widgets(self):
        self.upper_button_names = ['add_roi',  'remove_last_roi']
        self.upper_buttons = {}
        for b in self.upper_button_names :
            self.upper_buttons[b] = QtGui.QPushButton(b.replace('_',  ' ').capitalize(),  self)
        self.roi_resolution = gui.LabeledInput(self, 'ROI resolution' )
        self.roilist = QtGui.QComboBox(self)
        self.scan_parameters = ScanParameters(self, '')
        self.scan_parameters.setFixedWidth(450)
        self.scan_parameters.setFixedHeight(75)
            
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        i = 0
        for b in self.upper_button_names:
            self.layout.addWidget(self.upper_buttons[b], 0, i, 1, 1)
            i+= 1
        self.layout.addWidget(self.roi_resolution, 0, len(self.upper_button_names), 1, 1)
        self.roi_resolution.input.setFixedWidth(40)
        self.layout.addWidget(self.roilist, 1, 0, 1, 2)
        self.layout.addWidget(self.scan_parameters, 2, 0, 1, 4)
        self.setLayout(self.layout)
    
class ExperimentControlGroupBox(gui.GroupBox):
    
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, 'Experiment control')

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
        self.layout.addWidget(self.experiment_name, 0, 0, 1, 4)
        self.layout.addWidget(self.start_experiment_button, 1, 0, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 1, 2)
        self.layout.addWidget(self.experiment_progress, 2, 0, 1, 4)
        self.setLayout(self.layout)
        
class ControlWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        
    def create_widgets(self):
        self.channels = ['top', 'side']
        self.layout = QtGui.QGridLayout()
        self.scan = QtGui.QPushButton('Scan',  self)
        self.layout.addWidget(self.scan, 0, 0)
        self.snap = QtGui.QPushButton('Snap',  self)
        self.layout.addWidget(self.snap, 0, 1)
        self.scan_mode = QtGui.QComboBox(self)
        self.layout.addWidget(self.scan_mode, 0, 2)
        self.scan_mode.addItems(QtCore.QStringList(['background',  'roi']))
        self.draw_mode = gui.LabeledComboBox(self, 'Select tool')
        self.layout.addWidget(self.draw_mode, 1, 0,  1, 2)
        self.draw_mode.input.addItems(QtCore.QStringList(['draw rectangle',  'draw line',  'select point',  'zoom in',  'zoom out']))
        self.filters = {}
        line = 0
        for channel in self.channels:
            setattr(self, channel + '_enable',  gui.LabeledCheckBox(self, channel.capitalize()))
            self.layout.addWidget(getattr(self, channel + '_enable'), line, 3)
            for i in range(2):
                self.filters[channel+str(i)] = QtGui.QComboBox(self)
                self.layout.addWidget(self.filters[channel+str(i)], line, 4+i)
            line += 1
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)
        
class MainWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.experiment_control_groupbox.setFixedWidth(250)
        self.experiment_control_groupbox.setFixedHeight(150)
        self.measurement_files = MeasurementFiles(self)
        self.measurement_files.setFixedWidth(250)
        self.measurement_files.setFixedHeight(150)
        self.objective_control = ObjectiveControl(self)
        self.objective_control.setFixedWidth(250)
        self.objective_control.setFixedHeight(150)
        self.beamer_control = BeamerControl(self)
        self.beamer_control.setFixedWidth(250)
        self.beamer_control.setFixedHeight(150)
        self.background_scan_parameters = ScanParameters(self, 'Background')
        self.background_scan_parameters.setFixedWidth(500)
        self.background_scan_parameters.setFixedHeight(75)
        self.roi_scan_parameters = RoiScanParameters(self)
        self.roi_scan_parameters.setFixedWidth(500)
        self.roi_scan_parameters.setFixedHeight(200)
        

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 1, 1)
        self.layout.addWidget(self.measurement_files, 0, 1, 1, 1)
        self.layout.addWidget(self.objective_control, 1, 0, 1, 1)
        self.layout.addWidget(self.beamer_control, 1, 1, 1, 1)
        self.layout.addWidget(self.background_scan_parameters, 2, 0, 1, 2)
        self.layout.addWidget(self.roi_scan_parameters, 3, 0, 1, 2)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)

class CalibrationWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.parameter_names = ['scanner_speed_xy',  'scanner_acceleration_xy',  'scanner_settling_time_xy', 'analog_output_sampling_rate', 'analog_input_sampling_rate']
        self.scanner_parameters = {}
        for p in self.parameter_names:
            self.scanner_parameters[p] = gui.LabeledInput(self, p.replace('_',  ' ').capitalize())
        self.plot = Qt4Plot()
        self.plot.setMaximumWidth(500)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        params_per_row = 2
        i = 0
        for p in self.parameter_names:
            self.layout.addWidget(self.scanner_parameters[p], i/params_per_row, 2*(i%params_per_row), 1, 2)
            i += 1
        self.layout.addWidget(self.plot, i/params_per_row + 1, 0, 1, 2 * len(self.parameter_names))
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)


class CentralWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.main_widget = MainWidget(self)
        self.calibration_widget = CalibrationWidget(self)
        self.animal_parameters_widget = guiv.AnimalParametersWidget(self)
        self.zstack_widget = guiv.ZstackWidget(self)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Ca imaging')
        self.main_tab.addTab(self.zstack_widget, 'Z stack')
        self.main_tab.addTab(self.animal_parameters_widget, 'Animal parameters')
        self.main_tab.addTab(self.calibration_widget, 'Calibration')
        self.main_tab.setCurrentIndex(0)
        
        self.control = ControlWidget(self)
        self.image = QtGui.QLabel()
        self.blank_image = 128*numpy.ones((400,  400,  3), dtype = numpy.uint8)
        self.image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
        self.image.setObjectName("image")
        self.image.mousePressEvent = self.getPos
        self.image.mouseReleaseEvent = self.getPos
        self.sa = QtGui.QScrollArea(self)
        self.sa.setWidget(self.image)
        self.sa.setWidgetResizable(False)
        self.sa.ensureVisible(200, 200)
        self.sa.setFixedWidth(600)
        self.sa.setFixedHeight(600)
        
        self.image_analysis = ImageAnalysis(self)
        
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.main_tab, 0, 1, 2, 1)
        self.layout.addWidget(self.control, 0, 0, 1, 1)
        self.layout.addWidget(self.sa, 1, 0, 1, 1)
        self.layout.addWidget(self.image_analysis, 2, 0, 1, 1)
        self.layout.addWidget(self.text_out, 2, 1, 1, 1)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)
        
    def getPos(self , event):
        x = event.pos().x()
        y = event.pos().y() 
        print x, y

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
        if STYLE != '':
            self.setStyleSheet(STYLE)
        self.create_widgets()
        self.resize(1280,  1024)
        self.poller = gui_pollers.CaImagingPoller(self)
        self.init_variables()
        self.poller.start()
        self.show()
        
        if qt_app is not None: qt_app.exec_()
        
    def create_widgets(self):
        self.central_widget = CentralWidget(self, self.config)
        self.setCentralWidget(self.central_widget) 
        
    def connect_signals(self):
        pass
        
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.update_console()
        
    def update_console(self):
        self.filtered_console_text = self.console_text
        self.central_widget.text_out.setPlainText(self.filtered_console_text)
        self.central_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        
    def init_variables(self):
        self.console_text = ''
        
    def closeEvent(self, e):
        self.printc('Please wait till gui closes')
        e.accept()
        self.poller.abort = True
        self.poller.wait()
    
if __name__ == '__main__':
    CaImagingGui('zoltan', 'CaImagingTestConfig')
