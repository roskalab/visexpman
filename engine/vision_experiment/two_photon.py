import os,time, numpy, hdf5io, traceback, multiprocessing, serial
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore

from visexpman.engine.generic import gui,fileop, signal, utils
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import gui_engine, main_ui,experiment_data

import PyDAQmx
from PyDAQmx import Task

class TwoPhotonImaging(gui.VisexpmanMainWindow):
    
    def __init__(self, context):        
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.setWindowIcon(gui.get_icon('behav'))
        self._init_variables()
        self.resize(self.machine_config.GUI_WIDTH, self.machine_config.GUI_HEIGHT)
        self._set_window_title()
        
        toolbar_buttons = ['record', 'stop', 'open_reference_image',  'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)        
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT*0.4)
        
        self.image = gui.Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        
        self.main_tab = QtGui.QTabWidget(self)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab.addTab(self.params, 'Settings')    
        
        self.referenceimage = gui.Image(self)
        self.main_tab.addTab(self.referenceimage, 'Reference Image')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        if os.path.exists(self.context_filename):
            context_stream = numpy.load(self.context_filename)
            self.parameters = utils.array2object(context_stream)
        else:
            self.parameter_changed()
        self.load_all_parameters()
        
        self.show()
        self.statusbar.recording_status.setText('Ready')
        
        self.update_image_timer=QtCore.QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        self.update_image_timer.start(1000.0 / self.machine_config.IMAGE_EXPECTED_FRAME_RATE)
        
        self.scan_timer=QtCore.QTimer()
        self.scan_timer.timeout.connect(self.scan_frame)
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
        
    def parameter_changed(self):
        newparams=self.params.get_parameter_tree(return_dict=True)
        
        # trying to keep projector control signal properties in a valid range ...
        if hasattr(self, 'parameters') and\
            (newparams['Image Width']!=self.parameters['Image Width'] or\
            newparams['Resolution']!=self.parameters['Resolution'] or\
            newparams['X Return Time']!=self.parameters['X Return Time']):
                self.params.params.param('Projector Control Phase').items.keys()[0].param.setLimits((-self.parameters['Image Width'] * self.parameters['Resolution'] / self.machine_config.AO_SAMPLE_RATE, self.parameters['X Return Time'] - 0.000001))
                self.params.params.param('Projector Control Pulse Width').items.keys()[0].param.setLimits((self.shortest_sample, self.parameters['Image Width'] * self.parameters['Resolution'] / self.machine_config.AO_SAMPLE_RATE))
        self.parameters=newparams
        
        if(self.scanning):
            self.restart_scan()
        
    def save_context(self):
        context_stream=utils.object2array(self.parameters)
        numpy.save(self.context_filename,context_stream)
        
    def update_image(self) :
        if(self.frame is not None):
            self.image.set_image(self.frame)
        
    
    def approximate(self, value):#RZ: I would rename it to roundint
        return int(round(value))
        
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.frame = None

        '''how to list available DAQ devices:
        buffer_size = 1024
        buffer = "\0" * buffer_size
        PyDAQmx.DAQmxGetSysDevNames(buffer, buffer_size)
        devlist += buffer.rstrip('\0').split(',') 
        print devlist
        '''
        
        self.shortest_sample = 1.0 / self.machine_config.AO_SAMPLE_RATE
        
        self.params_config = [
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 4), 'step' : 0.1, 'siPrefix': False, 'suffix': ' px/' + 'u' + 'm'},
                {'name': 'Image Width', 'type': 'int', 'value': 100, 'limits': (3, 300), 'step': 1, 'siPrefix': True, 'suffix': ' ' + 'u' + 'm'},
                {'name': 'Image Height', 'type': 'int', 'value': 100, 'limits': (3, 300), 'step': 1, 'siPrefix': True, 'suffix': ' ' + 'u' + 'm'},
                #{'name': 'Optical Correction', 'type': 'float', 'value': 1.0000, 'decimals': 5, 'step' : 0.0001, 'siPrefix': True}, #moved to machine config
                {'name': 'X Return Time', 'type': 'float', 'value': self.shortest_sample, 'step': 0.000001, 'limits': (self.shortest_sample,  0.1), 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': 0.000001, 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': self.shortest_sample, 'step': 0.000001, 'limits': (self.shortest_sample,  None), 'siPrefix': True, 'suffix': 's'}
            ]
        self.params_config.extend(params)
        
    def generate_waveform(self):
        line_length = self.approximate(self.image_width * self.image_resolution) + self.new_line
        total_lines = self.approximate(self.image_height * self.image_resolution)
        self.sampsperchan = line_length * total_lines + self.new_frame
        
        x_min = self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE
        x_max = self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE
        
        y_min = self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE
        y_max = self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE
        
        x_min *= self.machine_config.OPTICAL_CORRECTION * self.parameters['Image Width']
        y_min *= self.machine_config.OPTICAL_CORRECTION * self.parameters['Image Height']
        x_max *= self.machine_config.OPTICAL_CORRECTION * self.parameters['Image Width']
        y_max *= self.machine_config.OPTICAL_CORRECTION * self.parameters['Image Height']
        
        ramp_up_x = numpy.linspace(x_min, x_max, num=line_length - self.new_line)
        ramp_down_x = numpy.linspace(x_max, x_min, num=self.new_line)
        waveform_x = numpy.concatenate((ramp_up_x,  ramp_down_x))
        waveform_x = numpy.tile(waveform_x, total_lines)
        waveform_x = numpy.append(waveform_x, numpy.full(self.new_frame, x_min))

        ramp_up_y = numpy.linspace(y_min, y_max, num=total_lines)
        ramp_up_y = numpy.repeat(ramp_up_y, line_length)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.new_frame)
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        
        phase = self.approximate(self.parameters['Projector Control Phase'] * self.machine_config.AO_SAMPLE_RATE)
        pulse_width = self.approximate(self.parameters['Projector Control Pulse Width'] * self.machine_config.AO_SAMPLE_RATE)
        projector_control = numpy.zeros(line_length - self.new_line + phase)
        
        if(phase + pulse_width > self.new_line):
            pulse_width -= (self.new_line - phase)
            projector_control = numpy.append(projector_control,  numpy.ones(self.new_line - phase) * self.machine_config.PROJECTOR_CONTROL_PEAK)
            projector_control[:pulse_width] = numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK
        else:
            projector_control = numpy.append(projector_control,  numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK)
            projector_control = numpy.append(projector_control,  numpy.ones(self.new_line - phase - pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK)
        projector_control = numpy.tile(projector_control, total_lines)
        projector_control = numpy.append(projector_control, numpy.zeros(self.new_frame))
        
        hold_5ms = self.approximate(0.005 * self.machine_config.AO_SAMPLE_RATE)
        old_frame = numpy.zeros(self.sampsperchan - self.new_frame)
        
        if(hold_5ms > self.new_frame):
            hold_5ms -= self.new_frame
            old_frame[:hold_5ms] = numpy.ones(hold_5ms) * self.machine_config.FRAME_TIMING_PEAK
            begin_new_frame = numpy.ones(self.new_frame) * self.machine_config.FRAME_TIMING_PEAK
        else:
            begin_new_frame = numpy.zeros(self.new_frame)
            begin_new_frame[:hold_5ms] = numpy.ones(hold_5ms) * self.machine_config.FRAME_TIMING_PEAK  
            
        frame_timing = numpy.concatenate((old_frame,  begin_new_frame))
        
        if not (len(waveform_x) == len(waveform_y) == len(projector_control) == len(frame_timing)):
            self.printc("Error during waveform generation! Number of samples are different.")
        
        #RZ: igy plottolhato is
        self.waveform_x=waveform_x
        self.waveform_y=waveform_y
        self.projector_control=projector_control
        self.frame_timing=frame_timing
        self.waveform = numpy.concatenate((waveform_x,  waveform_y,  projector_control,  frame_timing))
        
    def plot(self):
        from pylab import plot, show
        i=0
        t=numpy.arange(self.waveform_y.shape[0])/float(self.machine_config.AO_SAMPLE_RATE)*1e3
        for s in [self.waveform_x, self.waveform_y, self.projector_control, self.frame_timing]:
            plot(s+i*10)
            i+=1
        show()
        
        
    def record_action(self):
        if(self.scanning):
            return
        self.scanning = True
        
        self.image_width = self.parameters['Image Width']
        self.image_height = self.parameters['Image Height']
        self.image_resolution = self.parameters['Resolution']
        self.new_line = self.approximate(self.parameters['X Return Time'] * self.machine_config.AO_SAMPLE_RATE)
        self.new_frame = self.new_line #or replace with expected number of samples for y return
        
        self.frame = numpy.empty((self.approximate(self.image_width * self.image_resolution), self.approximate(self.image_height * self.image_resolution), 3),  dtype = int)
        self.generate_waveform()

        self.analog_output = Task()
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao0",
            "pos_x",
            self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE,
            self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao1",
            "pos_y",
            self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE,
            self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        ''' IMPORTANT, but commented out while using test hardware
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao2",
            "projector_control",
            self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE,
            self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao3",
            "frame_timing",
            self.machine_config.HIGH_PEAK + self.machine_config.OFFSET_VOLTAGE,
            self.machine_config.LOW_PEAK + self.machine_config.OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)            
        '''
        self.analog_output.CfgSampClkTiming(
            "OnboardClock",
            self.machine_config.AO_SAMPLE_RATE,             
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps,
            self.sampsperchan)
        
        self.analog_input = Task()
        self.analog_input.CreateAIVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ai0:1",
            "sensor0,sensor1",
            PyDAQmx.DAQmx_Val_RSE,
            -5,
            5,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_input.CfgSampClkTiming(
            "OnboardClock",
            self.machine_config.AI_SAMPLE_RATE,
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps,
            self.approximate(self.image_width * self.image_resolution) * self.approximate(self.image_height * self.image_resolution))
        
        self.shutter = Task()
        self.shutter.CreateDOChan(
            self.machine_config.DAQ_DEV_ID + "/port0/line0",
            "shutter",
            PyDAQmx.DAQmx_Val_GroupByChannel)
        self.shutter.WriteDigitalLines(
            1,
            True,
            1.0,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            numpy.array([int(1)], dtype=numpy.uint8),
            None,
            None)
            
        self.analog_output.WriteAnalogF64(
            self.sampsperchan, 
            True,
            numpy.ceil(self.sampsperchan / self.machine_config.AO_SAMPLE_RATE) + 0.1,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            self.waveform,
            None,
            None)
        
        self.scan_timer.start(100.0)
        self.statusbar.recording_status.setText('Scanning...')

    def scan_frame(self):
        for i in range(0, self.approximate(self.image_width * self.image_resolution)):
            for j in range(0,  self.approximate(self.image_height * self.image_resolution)):
                self.frame[i, j, 0] = self.approximate(256.0 / self.image_width * self.image_resolution * i)
                self.frame[i, j, 1] = self.approximate(256.0 / self.image_height * self.image_resolution * j)
                self.frame[i, j, 2] = 0
        pass
        
        '''        self.analog_input.ReadAnalogF64(int(self.ai_data.shape[0]/self.n_ai_channels),
                                        self.timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        self.ai_data.shape[0],
                                        DAQmxTypes.byref(self.readb),
                                        None)
        self.ai_data = self.ai_data[:self.readb.value * self.n_ai_channels]
        self.ai_data = self.ai_data.flatten('F').reshape((self.n_ai_channels, self.readb.value)).transpose()
        if not self.finite:
            self.ai_frames.append(self.ai_data.copy())'''
        
        '''data = numpy.zeros((width*height*2,), dtype=numpy.float64)
        self.sensor.ReadAnalogF64(1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, data, 1, PyDAQmx.byref(read), None)    #will overflow
        self.frame = numpy.empty((width,  height, 3),  dtype = int)'''
        
    def stop_action(self):
        if(not self.scanning):
            return

        self.scan_timer.stop()

        self.shutter.WriteDigitalLines(
            1,
            True,
            1.0,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            numpy.array([int(0)], dtype=numpy.uint8),
            None,
            None)
        self.printc("Close shutter")#RZ: Hasonlo uzenetekkel lehet jelezni a user (es magunk fele is), hogy mi tortenik
        self.analog_input.StopTask()
        self.analog_output.StopTask()
        
        self.analog_input.ClearTask()
        self.analog_output.ClearTask()
        self.shutter.ClearTask()
        
        self.scanning = False        
        self.statusbar.recording_status.setText('Stopped.')
        
    def restart_scan(self):
        self.printc("Restart scan")
        self.stop_action()
        self.record_action()
        
    def open_reference_image_action(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5')
        print fname
        if (fname==''):
            return
        
        h=hdf5io.Hdf5io(str(fname))
        ref = numpy.empty((100,  120, 3),  dtype = int)
        
        #TODO: actual image loading & processing here
        
        h.close()
        
        self.referenceimage.set_image(ref)
        self.main_tab.setCurrentIndex(1)
        
    def exit_action(self):
        self.stop_action()
        self.save_context()
        self.close()
