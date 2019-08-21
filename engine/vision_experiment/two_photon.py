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
        
        toolbar_buttons = ['record', 'stop', 'open_reference_image', 'capture_frame', 'save',  'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT * 0.4)
        
        self.image = gui.Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        
        self.main_tab = QtGui.QTabWidget(self)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab.addTab(self.params, 'Settings')
        
        self.video_player = QtGui.QWidget()
        self.referenceimage = gui.Image(self)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.slider.setTickInterval(self.machine_config.IMAGE_EXPECTED_FRAME_RATE)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(self.machine_config.IMAGE_EXPECTED_FRAME_RATE)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.frame_select)
        
        self.vplayout = QtGui.QVBoxLayout()
        self.vplayout.addWidget(self.referenceimage)
        self.vplayout.addWidget(self.slider)
        
        self.video_player.setLayout(self.vplayout)
        self.main_tab.addTab(self.video_player, 'Reference Image')
        
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
        
        if hasattr(self, 'parameters') and\
            (newparams['Image Width']!=self.parameters['Image Width'] or\
            newparams['Image Height']!=self.parameters['Image Height'] or\
            newparams['Resolution']!=self.parameters['Resolution'] or\
            newparams['X Return Time']!=self.parameters['X Return Time'] or\
            newparams['Projector Control Pulse Width']!=self.parameters['Projector Control Pulse Width']):
                period = newparams['Image Width'] * newparams['Resolution'] / self.machine_config.AIO_SAMPLE_RATE - self.shortest_sample
                self.params.params.param('Projector Control Phase').items.keys()[0].param.setLimits((-period, period - newparams['Projector Control Pulse Width']))
                self.params.params.param('Projector Control Pulse Width').items.keys()[0].param.setLimits((self.shortest_sample, period))
        self.parameters=newparams
        
        if(self.scanning):
            self.restart_scan()
        
    def save_context(self):
        context_stream=utils.object2array(self.parameters)
        numpy.save(self.context_filename,context_stream)
        
    def update_image(self):
        if(self.frame is not None):
            self.image.set_image(self.frame)
        
    def roundint(self, value):
        return int(round(value))
        
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.frame = None
        self.clipboard = None
        
        self.shortest_sample = 1.0 / self.machine_config.AIO_SAMPLE_RATE
        
        self.params_config = [
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 4), 'step' : 0.1, 'siPrefix': False, 'suffix': ' px/um'},
                {'name': 'Image Width', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Image Height', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'X Return Time', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  0.1), 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': self.shortest_sample, 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  None), 'siPrefix': True, 'suffix': 's'}
                #Maximum for Projector Control Pulse Width and limits for Projector Control Phase aren't set yet!
            ]
        self.params_config.extend(params)
        
    def generate_waveform(self):
        line_length = self.roundint(self.image_width * self.image_resolution) + self.return_x_samps #Number of samples for scanning a line
        total_lines = self.roundint(self.image_height * self.image_resolution)
        
        self.sampsperchan = (line_length - 1) * total_lines + self.return_y_samps
        self.printc("Samples per channel: " + str(self.sampsperchan)) #Total number of samples for scanning a single frame
        
        x_min = -self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        x_max = self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        
        y_min = -self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        y_max = self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        
        # X signal
        ramp_up_x = numpy.linspace(x_min, x_max, num=line_length - self.return_x_samps)
        ramp_down_x = numpy.linspace(x_max, x_min, num=self.return_x_samps + 1)[1:-1] #Exclude extreme values (avoiding duplication during concatenation)
        waveform_x = numpy.concatenate((ramp_up_x,  ramp_down_x))
        waveform_x = numpy.tile(waveform_x, total_lines)
        waveform_x = numpy.append(waveform_x, numpy.full(self.return_y_samps, x_min)) #Wait for Y to return
        
        # Linear Y signal
        ramp_up_y = numpy.linspace(y_min, y_max, num=self.sampsperchan - self.return_y_samps + 1)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)[1:] #Exclude maximum value
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        
        '''
        # Stepped Y signal - for future tests
        ramp_up_y = numpy.linspace(y_min, y_max, num=total_lines)
        ramp_up_y = numpy.repeat(ramp_up_y, line_length - 1)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        '''
        
        # Projector control
        phase = self.roundint(self.parameters['Projector Control Phase'] * self.machine_config.AIO_SAMPLE_RATE)
        pulse_width = self.roundint(self.parameters['Projector Control Pulse Width'] * self.machine_config.AIO_SAMPLE_RATE)
        
        initial_shift = numpy.zeros(line_length - self.return_x_samps + phase)
        single_period = numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK
        single_period = numpy.append(single_period, numpy.zeros(line_length - pulse_width - 1))
        projector_control = numpy.tile(single_period, total_lines) #Expand to all lines
        projector_control = numpy.append(initial_shift, projector_control) #Offset the whole signal depending on phase
        projector_control = projector_control[:-line_length + pulse_width + 1] #Cut off overflowed section
        
        projector_control = numpy.append(projector_control, numpy.zeros(self.return_y_samps + self.return_x_samps - pulse_width - phase - 1)) #Wait for Y to return
        
        # Frame timing
        hold_time = self.roundint(self.machine_config.FRAME_TIMING_HOLD * self.machine_config.AIO_SAMPLE_RATE)
        old_frame = numpy.zeros(self.sampsperchan - self.return_y_samps) #Zeros while old frame being scanned
        
        if(hold_time > self.return_y_samps):
            #Hold time strectches into the next frame
            hold_time -= self.return_y_samps
            old_frame[:hold_time] = numpy.ones(hold_time) * self.machine_config.FRAME_TIMING_PEAK #Hold from previous frame
            begin_new_frame = numpy.ones(self.return_y_samps) * self.machine_config.FRAME_TIMING_PEAK
            self.printc("Generating long frame timing pulse")
        else:
            begin_new_frame = numpy.zeros(self.return_y_samps)
            begin_new_frame[:hold_time] = numpy.ones(hold_time) * self.machine_config.FRAME_TIMING_PEAK
            self.printc("Generating short frame timing pulse")
            
        frame_timing = numpy.concatenate((old_frame,  begin_new_frame))
        
        # Basic error detection
        if not (len(waveform_x) == len(waveform_y) == len(projector_control) == len(frame_timing) == self.sampsperchan):
            self.printc("Error during waveform generation! Number of samples are different.")
            self.printc("Waveform X: " + str(len(waveform_x)))
            self.printc("Waveform Y: " + str(len(waveform_y)))
            self.printc("Projector Control: " + str(len(projector_control)))
            self.printc("Frame Timing: " + str(len(frame_timing)))
        
        self.waveform_x=waveform_x
        self.waveform_y=waveform_y
        self.projector_control=projector_control
        self.frame_timing=frame_timing
        self.waveform = numpy.concatenate((waveform_x,  waveform_y,  projector_control,  frame_timing)) #Order: X, Y PC, FT
        #self.plot()
        
    def plot(self):
        from pylab import plot, grid, show
        i=0
        t=numpy.arange(self.sampsperchan) / float(self.machine_config.AIO_SAMPLE_RATE) * 1e3
        for s in [self.projector_control, self.waveform_x, self.waveform_y, self.frame_timing]:
            plot(t, s+i*10)
            i+=1
        grid(True)
        show()
        
    def record_action(self):
        if(self.scanning):
            return
        self.scanning = True
        
        self.image_width = self.parameters['Image Width']
        self.image_height = self.parameters['Image Height']
        self.image_resolution = self.parameters['Resolution']
        self.return_x_samps = self.roundint(self.parameters['X Return Time'] * self.machine_config.AIO_SAMPLE_RATE) #Including max and min values!
        self.return_y_samps = self.roundint(self.image_width * self.image_resolution) + self.return_x_samps #=line_length from generate_waveform
        
        self.frame = numpy.zeros((self.roundint(self.image_width * self.image_resolution), self.roundint(self.image_height * self.image_resolution), 3),  dtype = int)
        self.generate_waveform()

        self.analog_output = Task()
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao0",
            "pos_x",
            -self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE,
            self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao1",
            "pos_y",
            -self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE,
            self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        ''' TODO: IMPORTANT, but commented out while using test hardware
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao2",
            "projector_control",
            -self.machine_config.PROJECTOR_CONTROL_PEAK,
            self.machine_config.PROJECTOR_CONTROL_PEAK,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_output.CreateAOVoltageChan(
            self.machine_config.DAQ_DEV_ID + "/ao3",
            "frame_timing",
            -self.machine_config.FRAME_TIMING_PEAK,
            self.machine_config.FRAME_TIMING_PEAK,
            PyDAQmx.DAQmx_Val_Volts,
            None)            
        '''
        self.analog_output.CfgSampClkTiming(
            "OnboardClock",
            self.machine_config.AIO_SAMPLE_RATE,
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
            self.machine_config.AIO_SAMPLE_RATE,
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_FiniteSamps,
            self.sampsperchan)
        '''
        TODO: trying to synchronize - hardware does not support yet
        self.analog_input.CfgDigEdgeStartTrig(
            "ao/StartTrigger",
            PyDAQmx.DAQmx_Val_Rising)
        '''
        
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
        self.printc('Open shutter')
            
        self.analog_output.WriteAnalogF64(
            self.sampsperchan,
            True,
            numpy.ceil(self.sampsperchan / self.machine_config.AIO_SAMPLE_RATE) + 0.1,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            self.waveform,
            None,
            None)
        
        self.scan_timer.start(50.0)
        self.statusbar.recording_status.setText('Scanning...')
        
    def scan_frame(self):
        
        data = numpy.empty((2 * self.sampsperchan,), dtype=numpy.float64)
        read = PyDAQmx.int32()
        
        self.analog_input.StartTask()
        self.analog_input.ReadAnalogF64(
            self.sampsperchan,
            10.0,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            data,
            2 * self.sampsperchan,
            PyDAQmx.byref(read),
            None)
        self.analog_input.StopTask()
        
        #Scaling pixel data
        data -= min(data)
        data *= 255.0 / max(data)
        
        actual_width = self.roundint(self.image_width * self.image_resolution)
        actual_height = self.roundint(self.image_height * self.image_resolution)
        
        #Exclude measurements during return x and return y:
        samples_to_skip = actual_width + self.return_x_samps - 1
        
        for j in range(0, actual_height):
            for i in range(0, actual_width):
                self.frame[i, j, 0] = data[samples_to_skip * j + i] #Test: X feedback - red
                self.frame[i, j, 1] = data[self.sampsperchan + samples_to_skip * j + i] #Test: Y feedback - green
                self.frame[i, j, 2] = 0
       
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
        self.printc("Close shutter")
        self.analog_input.StopTask()
        self.analog_output.StopTask()
        
        self.analog_input.ClearTask()
        self.analog_output.ClearTask()
        self.shutter.ClearTask()
        
        self.scanning = False
        self.statusbar.recording_status.setText('Stopped')
        
    def restart_scan(self):
        self.printc("Restart scan")
        self.stop_action()
        self.record_action()
        
    def open_reference_image_action(self):
        
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5')
        if (str(fname)=='' or not os.path.exists(str(fname))):
            return
        self.printc("Loading " + str(fname))
        self.statusbar.recording_status.setText('Loading ' + str(fname))
        
        h=hdf5io.Hdf5io(str(fname))
        h.load('preview')
        h.load('imaging_data')
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        
        #Loading process takes very long, might be inconvenient waiting for it to complete - TODO: put it in background task (?)
        # current solution: save a preview image separately and load it first.
        self.referenceimage.set_image(h.preview)
        self.main_tab.setCurrentIndex(1)
        Qt.QApplication.processEvents() # update Gui (window freezed during the following nested loop)
        
        if(hasattr(h, 'imaging_data')):
            self.reference_video = numpy.empty((h.imaging_data.shape[0], h.imaging_data.shape[2], h.imaging_data.shape[3], 3),  dtype = int)
            
            #TODO: shorten this stuff (is there a python magic indexing method or something?)
            for n in range(0,  h.imaging_data.shape[0]):
                for i in range(0, h.imaging_data.shape[2]):
                    for j in range(0, h.imaging_data.shape[3]):
                        self.reference_video[n, i, j, 0] = h.imaging_data[n,  0,  i,  j]
                        self.reference_video[n, i, j, 1] = h.imaging_data[n,  1,  i,  j]
                        self.reference_video[n, i, j, 2] = 0
                    
            self.slider.setMaximum(h.imaging_data.shape[0] - 1)
        
        h.close()
        
        self.printc("Imaging data loaded successfully")
        if(self.scanning):
            self.statusbar.recording_status.setText("Scanning...")
        else:
            self.statusbar.recording_status.setText("Imaging data loaded successfully")
        
    def frame_select(self, position):
        self.referenceimage.set_image(self.reference_video[position])
        self.clipboard = self.reference_video[position]
        
    def capture_frame_action(self):
        if(self.frame is None):
            return
        self.reference_video = None
        self.clipboard = self.frame.copy()
        self.referenceimage.set_image(self.clipboard)
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        self.main_tab.setCurrentIndex(1)
    
    def save_action(self):
        #NOTE!: this function is only capable of saving captured frames
        
        if(self.clipboard is None):
            self.printc("There's no image data to save. Record and capture it first!")
            return
            
        fname = QtGui.QFileDialog.getSaveFileName(self, 'Save Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5')
        if (str(fname)==''):
            return
            
        hdf5io.save_item(str(fname), 'preview', self.clipboard, overwrite=True)
        self.printc("Saving " + str(fname) + " completed")
    
    def exit_action(self):
        self.stop_action()
        self.save_context()
        self.close()
