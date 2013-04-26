'''
http://qt-project.org/doc/qt-4.8/stylesheet-examples.html


Config parameters:
EXPERIMENT_DATA_PATH
MAT/HDF5



'''


import os.path
import numpy
import time

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import PyQt4.Qwt5 as Qwt

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui as guiv
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.generic import introspect
from visexpman.engine.generic import gui
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.generic import log
from visexpA.engine.datadisplay import imaged
from visexpA.engine.datadisplay.plot import Qt4Plot

STYLE = 'background-color:#303030;color:#D0D0D0;selection-color:#0000A0;selection-background-color:#808080;border-style:outset;border-width: 1px;border-color:#707070;padding:3px'
STYLE='background-color:#C0C0C0;'
#STYLE=''

class CalibrationScanningPattern(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, 'Calibration scanning pattern')
        
    def create_widgets(self):
        self.widgets = {'scanning_range' : gui.LabeledInput(self, 'Scanning range [um]'), 
                                    'repeats' : gui.LabeledInput(self, 'Repeats'), 'start': QtGui.QPushButton('Run',  self)}
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        for w in [self.widgets]:
            keys = w.keys()
            keys.sort()
            [self.layout.addWidget(w[k], 0, 2*keys.index(k), 1, 2) for k in keys]
        self.setLayout(self.layout)

class CalibrationWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.parameter_names = ['scanner_speed',  'scanner_acceleration_xy',  'SCANNER_RAMP_TIME',  'SCANNER_SETTING_TIME',  \
                                 'XMIRROR_OFFSET',  'YMIRROR_OFFSET', 'AO_SAMPLE_RATE', 'AI_SAMPLE_RATE','POSITION_TO_SCANNER_VOLTAGE',  'SCANNER_START_STOP_TIME']
        self.scanner_parameters = {}
        for p in self.parameter_names:
            self.scanner_parameters[p] = gui.LabeledInput(self, p.replace('_',  ' ').capitalize())
        self.calib_scan_pattern = CalibrationScanningPattern(self)
        self.plot = Qt4Plot()
        
#        self.plot.clear()
#        self.plot.setdata(numpy.arange(100), penwidth=1.5, color=Qt.Qt.black)
#        self.plot.setaxisscale([0, 100, -1000, 1000])

        self.plot.setMaximumWidth(600)
        self.plot.setMaximumHeight(250)
        self.plot.setMinimumHeight(250)
        self.fromfile = QtGui.QPushButton('Load',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        params_per_row = 2
        i = 0
        for p in self.parameter_names:
            self.layout.addWidget(self.scanner_parameters[p], i/params_per_row, 2*(i%params_per_row), 1, 2)
            i += 1
        self.layout.addWidget(self.calib_scan_pattern, i/params_per_row + 1, 0, 1, 2 * len(self.parameter_names))
        self.layout.addWidget(self.plot, i/params_per_row + 3, 0, 1, 2 * len(self.parameter_names))
        self.layout.addWidget(self.fromfile, i/params_per_row + 2, 0, 1, 1)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)


class ImageAnalysis(gui.GroupBox):
    def __init__(self, parent):
        gui.GroupBox.__init__(self, parent, '')
        
    def create_widgets(self):
        self.channel = gui.LabeledComboBox(self, 'Select channel')
        self.channel.input.addItems(QtCore.QStringList(['Top',  'Side']))
        self.function = gui.LabeledComboBox(self, 'Select function')
        self.function.input.addItems(QtCore.QStringList(['histogram',  'time series',  ]))
        self.histogram_range = gui.LabeledInput(self, 'Histogram min, max, gamma')
        
        self.plot = Qwt.QwtPlot(self)
        self.plot.setMaximumHeight(150)
        self.plot.setMaximumWidth(600)
        self.plot.clear()
        
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
        self.cell_name.input.setEditable(True)
        self.recording = gui.LabeledComboBox(self, 'Select recording')
        self.enable_recording = gui.LabeledCheckBox(self, 'Enable recording')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.cell_name, 0, 0, 1, 1)
        self.layout.addWidget(self.recording, 1, 0, 1, 1)
        self.layout.addWidget(self.enable_recording, 2, 0, 1, 1)
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
        for channel in self.config.PMTS.keys():
            setattr(self, channel + '_enable',  gui.LabeledCheckBox(self, channel.capitalize()))
            if self.config.PMTS[channel]['ENABLE']:
                getattr(getattr(getattr(self, channel + '_enable'), 'input'),  'setCheckState')(2)
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
        
        self.control_widget = ControlWidget(self)
        self.image = QtGui.QLabel()
        self.blank_image = 128*numpy.ones((400,  400,  3), dtype = numpy.uint8)
        self.image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
        self.image.setObjectName("image")
        self.image.mousePressEvent = self.getPos
        self.image.mouseReleaseEvent = self.getPos
        self.sa = QtGui.QScrollArea(self)
        self.sa.setWidget(self.image)
        self.sa.setWidgetResizable(False)
#        self.sa.ensureVisible(200, 200)
        self.sa.setFixedWidth(600)
        self.sa.setFixedHeight(600)
        
        self.image_analysis = ImageAnalysis(self)
        
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        
        self.status = QtGui.QLabel('', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.status, 0, 1, 1, 1)
        self.layout.addWidget(self.main_tab, 1, 1, 2, 1)
        self.layout.addWidget(self.control_widget, 0, 0, 2, 1)
        self.layout.addWidget(self.sa, 2, 0, 1, 1)
        self.layout.addWidget(self.image_analysis, 3, 0, 1, 1)
        self.layout.addWidget(self.text_out, 3, 1, 1, 1)
        
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
        self.resize(1280, 1024)
        self.poller = gui_pollers.CaImagingPoller(self)
        self.init_variables()
        self.connect_signals()
        self.poller.start()
        self.show()
        self.init_widget_content()
        self.poller.init_debug()
        self.poller.update_main_image()
        if qt_app is not None: qt_app.exec_()
        
    def create_widgets(self):
        self.central_widget = CentralWidget(self, self.config)
        self.setCentralWidget(self.central_widget) 
        
    def init_widget_content(self):
        if hasattr(self.poller,'widget_context_values'):
            for ref_string, value in self.poller.widget_context_values.items():
                try:
                    ref = introspect.string2objectreference(self,ref_string.replace('parent.',''))
                except:
                    continue
                if hasattr(ref,'setEditText'):
                    ref.setEditText(value)
                elif hasattr(ref,'setText'):
                    ref.setText(value)
        
    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect(self.central_widget.calibration_widget.fromfile, QtCore.SIGNAL('clicked()'),  self.fromfile)
        self.connect(self.central_widget.image_analysis.histogram_range.input, QtCore.SIGNAL('textEdited(QString)'), self.update_main_image)
        self.connect_and_map_signal(self.central_widget.control_widget.scan, 'scan')
        self.connect_and_map_signal(self.central_widget.control_widget.snap, 'snap')
        self.connect_and_map_signal(self.central_widget.calibration_widget.calib_scan_pattern.widgets['start'], 'calib')
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)
        
    def update_main_image(self, text):
        pass
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        if hasattr(self.poller, mapped_signal_parameter):
            self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
            getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
        else:
            self.printc('{0} method does not exists'.format(mapped_signal_parameter))
        
    def printc(self, text):
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += utils.time_stamp_to_hms(time.time()) + ' '  + text + '\n'
        self.update_console()
        
    def update_console(self):
        self.filtered_console_text = self.console_text
        self.central_widget.text_out.setPlainText(self.filtered_console_text)
        self.central_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        
    def init_variables(self):
        self.console_text = ''
        
    def show_image(self, image, scale=None, origin=None):
#        import Image
#        Image.fromarray(image).save('c:\\temp\\im.bmp')
        self.central_widget.image.setPixmap(imaged.array_to_qpixmap(image))#, utils.rc((600, 600))))
        
    def plot_histogram(self, x, hist, lut):
        self.central_widget.image_analysis.plot.clear()
        self.central_widget.image_analysis.plot.histogram = Qwt.QwtPlotCurve('H')
        self.central_widget.image_analysis.plot.histogram.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        self.central_widget.image_analysis.plot.histogram.attach(self.central_widget.image_analysis.plot)
        pen1 = Qt.QPen(Qt.Qt.red)
        pen1.setWidth(1)
        self.central_widget.image_analysis.plot.histogram.setPen(pen1)
        self.central_widget.image_analysis.plot.histogram.setData(x, hist)
        if lut is not None:
            self.central_widget.image_analysis.plot.lut = Qwt.QwtPlotCurve('LUT')
            self.central_widget.image_analysis.plot.lut.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
            self.central_widget.image_analysis.plot.lut.attach(self.central_widget.image_analysis.plot)
            pen2 = Qt.QPen(Qt.Qt.black)
            pen2.setWidth(1.5)
            self.central_widget.image_analysis.plot.lut.setPen(pen2)
            self.central_widget.image_analysis.plot.lut.setData(x, lut)
        self.central_widget.calibration_widget.plot.replot()

    def plot_calibdata(self):
        calibdata = self.poller.queues['data'].get()
        self.central_widget.calibration_widget.plot.setdata(calibdata['pmt'][:, 0], penwidth=1.5, color=Qt.Qt.black)
        if calibdata['pmt'].shape[1] ==2:
            self.central_widget.calibration_widget.plot.adddata(calibdata['pmt'][:, 1],color=Qt.Qt.black, penwidth=1.5)
        self.central_widget.calibration_widget.plot.adddata(calibdata['waveform'][:, 0],color=Qt.Qt.green, penwidth=1.5)
        self.central_widget.calibration_widget.plot.adddata(calibdata['waveform'][:, 1],color=Qt.Qt.red, penwidth=1.5)
        self.central_widget.calibration_widget.plot.adddata(calibdata['mask'],color=Qt.Qt.blue, penwidth=1.5)
        self.central_widget.calibration_widget.plot.replot()
        if calibdata['parameters'].has_key('POSITION_TO_SCANNER_VOLTAGE'):
            pos2voltage = calibdata['parameters']['POSITION_TO_SCANNER_VOLTAGE']
        else:
            pos2voltage = self.config.POSITION_TO_SCANNER_VOLTAGE
        overshoot = ((calibdata['waveform'][:,0].max() - calibdata['waveform'][:,0].min()) - calibdata['parameters']['scanning_range']*pos2voltage)/pos2voltage
        line_rate = 1.0/(calibdata['waveform'][:, 0].shape[0]/(calibdata['parameters']['AO_SAMPLE_RATE']*calibdata['parameters']['repeats']*4))
        self.printc(
                    'Accel max: {0:.3e} um/s2,  max speed {1:.3e} um/s, overshoot {2:2.3f} um, line rate: {3:3.1f} Hz, scan time efficiency {4:2.1f} %'
                    .format(calibdata['accel_speed']['accel_x'].max(), calibdata['accel_speed']['speed_x'].max(),  overshoot, line_rate,  100.0*calibdata['mask'].sum()/calibdata['mask'].shape[0]))
        try:
            for axis in calibdata['profile_parameters'].keys():
                for dir in calibdata['profile_parameters'][axis].keys():
                    self.printc('{0}, {1}, sigma {2}, delay {3}'
                                    .format(axis, dir, numpy.round(calibdata['profile_parameters'][axis][dir]['sigma'], 4), numpy.round(calibdata['profile_parameters'][axis][dir]['delay'], 4)))
            self.show_image(calibdata['line_profiles'])
        except:
            pass

    def fromfile(self):
        from visexpA.engine.datahandlers import hdf5io
        p = os.path.join(self.config.EXPERIMENT_DATA_PATH,  'calib.hdf5')
        p = '/mnt/databig/software_test/ref_data/scanner_calib/calib_repeats.hdf5'
        calibdata = hdf5io.read_item(p, 'calibdata', filelocking=False)
        from visexpman.engine.hardware_interface import scanner_control
        calibdata['profile_parameters'], calibdata['line_profiles'] = scanner_control.process_calibdata(calibdata['pmt'], calibdata['mask'], calibdata['parameters'])
        self.poller.queues['data'].put(calibdata)
        self.plot_calibdata()
        
    def update_scan_run_status(self, status):
        '''
        Scan button color and text is updated according to current status of scanning process. During preparation and datasaving button is disabled
        '''
        if status == 'prepare':
            self.central_widget.control_widget.scan.setText('Preparing')
            self.central_widget.control_widget.scan.setStyleSheet('background-color:#FF8000;')
        elif status == 'started':
            self.central_widget.control_widget.scan.setText('Stop')
            self.central_widget.control_widget.scan.setStyleSheet('background-color:#E00000;')
            self.central_widget.control_widget.scan.setDisabled(False)
            self.poller.scan_run = True
        elif status == 'saving':
            self.central_widget.control_widget.scan.setText('Saving')
            self.central_widget.control_widget.scan.setStyleSheet('background-color:#FF8000;')
        elif status == 'ready':
            self.central_widget.control_widget.scan.setText('Scan')
            self.central_widget.control_widget.scan.setStyleSheet('background-color:#C0C0C0;')
            self.poller.scan_run = False
        
    def closeEvent(self, e):
        self.printc('Please wait till gui closes')
        e.accept()
        self.poller.abort = True
        self.poller.wait()
    
if __name__ == '__main__':
    CaImagingGui('zoltan', 'CaImagingTestConfig')
