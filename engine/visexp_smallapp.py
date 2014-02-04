'''
This module implements small applications like flowmeter logger or serial port pulse generator.
'''
import time
import sys
import os
import os.path
import traceback

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import log
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.generic import gui as gui_generic
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.hardware_interface import digital_io

class SmallApp(QtGui.QWidget):
    '''
    Small  application gui
    '''
    def __init__(self, user, config_class):
        if hasattr(config_class, 'OS'):
            self.config=config_class
            config_class_name = config_class.__class__.__name__
        else:
            self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
            config_class_name = config_class
        self.config.user = user
        if not hasattr(self.config, 'SMALLAPP'):
            raise RuntimeError('No small application configuration is provided, check machine config')
        if hasattr(self.config, 'LOG_PATH'):
            self.log = log.Log('gui log', fileop.generate_filename(os.path.join(self.config.LOG_PATH, self.config.SMALLAPP['NAME'].replace(' ', '_') +'.txt')), local_saving = True)
        self.console_text = ''
        if self.config.SMALLAPP.has_key('POLLER'):
            if hasattr(gui_pollers, self.config.SMALLAPP['POLLER']):
                self.poller =  getattr(gui_pollers, self.config.SMALLAPP['POLLER'])(self, self.config)
            else:
                self.poller =  getattr(self.config.SMALLAPP['POLLER_MODULE'], self.config.SMALLAPP['POLLER'])(self, self.config)
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('{2} - {0} - {1}' .format(user,  config_class_name, self.config.SMALLAPP['NAME']))
        if hasattr(self.config, 'GUI_SIZE'):
            self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        if hasattr(self.config, 'GUI_POSITION'):
            self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        self.add_console()
        self.create_layout()
        self.connect_signals()
        self.show()
        if self.config.SMALLAPP.has_key('POLLER'):
            if hasattr(self.poller,  'init_widgets'):
                self.poller.init_widgets()
            self.poller.start()
        
    def add_console(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        
    def create_gui(self):
        pass
        
    def create_layout(self):
        pass
        
    def connect_signals(self):
        pass
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        if hasattr(self.poller, mapped_signal_parameter):
            self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
            getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
        else:
            self.printc('{0} method does not exists'.format(mapped_signal_parameter))
        
    def printc(self, text, add_timestamp = True):
        if not isinstance(text, str):
            text = str(text)
        if add_timestamp:
            timestamp_string = utils.time_stamp_to_hm(time.time()) + ' '
        else:
            timestamp_string = ''
        self.console_text  += timestamp_string + text + '\n'
        self.text_out.setPlainText(self.console_text)
        self.text_out.moveCursor(QtGui.QTextCursor.End)
        try:
            if hasattr(self, 'log'):
                self.log.info(text)
        except:
            print 'gui: logging error'
    
    def closeEvent(self, e):
        e.accept()
        if hasattr(self, 'log'):
            self.log.copy()
        if self.config.SMALLAPP.has_key('POLLER'):
            self.poller.abort = True
        time.sleep(1.0)
        sys.exit(0)
        
class FlowmeterLogger(SmallApp):
    def create_gui(self):
        self.flowmeter = gui.FlowmeterControl(self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.flowmeter, 0, 0, 1, 1)
        self.layout.addWidget(self.text_out, 1, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.flowmeter.reset_button, 'reset')
        self.connect_and_map_signal(self.flowmeter.start_button, 'start_measurement')
        self.connect_and_map_signal(self.flowmeter.stop_button, 'stop_measurement')
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)

    def update_status(self, status, value =  None):
        if value is None:
            self.flowmeter.status_label.setText('{0}'.format(status))
        else:
            self.flowmeter.status_label.setText('{0}, {1:2.2f} ul/min'.format(status, value))
            
            
class SerialportPulseGenerator(SmallApp):
    def create_gui(self):
        self.pulse_width_label = QtGui.QLabel('Pulse width [ms]', self)
        self.pulse_width_combobox = QtGui.QComboBox(self)
        self.pulse_width_combobox.setEditable(True)
        self.generate_button = QtGui.QPushButton('Generate pulse',  self)
    
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.pulse_width_label, 0, 0, 1, 1)
        self.layout.addWidget(self.pulse_width_combobox, 0, 1, 1, 1)
        self.layout.addWidget(self.generate_button, 0, 2, 1, 1)
        self.layout.addWidget(self.text_out, 1, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.connect(self.generate_button, QtCore.SIGNAL('clicked()'), self.generate_pulse)
        
    def generate_pulse(self):
        pulse_width = str(self.pulse_width_combobox.currentText())
        try:
            pulse_width = float(pulse_width) / 1000.0 - self.config.PULSE_OVERHEAD
            if pulse_width > self.config.MAX_PULSE_WIDTH:
                self.printc('Pulse is too long')
                return
            if pulse_width + self.config.PULSE_OVERHEAD < self.config.MIN_PULSE_WIDTH:
                self.printc('This pulse might take longer than requested, hardware cannot generate shorter pulses than {0} ms'.format(int(1000*self.config.MIN_PULSE_WIDTH)))
        except:
            self.printc('Provide pulse width in numeric format')
            return
        try:
            s = digital_io.SerialPortDigitalIO(self.config)
            for i in range(1):
                if pulse_width > 0:
                    s.pulse(pulse_width)
                else:
                    self.printc('Pulse width is too short')
                time.sleep(0.1)
            s.close()
        except:
            self.printc(traceback.format_exc())
            
class BehavioralTester(SmallApp):
    def create_gui(self):
        self.open_valve_for_a_time = gui_generic.PushButtonWithParameter(self, 'Open valve', 'Open time [ms]')
        self.open_valve = QtGui.QPushButton('Open valve',  self)
        self.close_valve = QtGui.QPushButton('Close valve',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.open_valve_for_a_time, 0, 0, 1, 7)
        self.layout.addWidget(self.open_valve, 1, 0, 1, 1)
        self.layout.addWidget(self.close_valve, 1, 1, 1, 1)
        self.layout.addWidget(self.text_out, 2, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.open_valve_for_a_time.button, 'open_valve_for_a_time')
        self.connect_and_map_signal(self.open_valve, 'open_valve')
        self.connect_and_map_signal(self.close_valve, 'close_valve')
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)

def run_gui():
    '''
    1. argument: username
    2.  machine config class
    3. small application class name
    Example: python visexp_smallapp.py peter MEASetup FlowmeterLogger
    '''
    if len(sys.argv) < 3:
        raise RuntimeError('The following commandline parameters are required: username machine_config and smallapp class name')
    app = Qt.QApplication(sys.argv)
    gui = getattr(sys.modules[__name__], sys.argv[3])(sys.argv[1], sys.argv[2])
    app.exec_()

if __name__ == '__main__':
    run_gui()
