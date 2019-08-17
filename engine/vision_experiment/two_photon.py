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
            newparams['Resolution']!=self.parameters['Resolution'] or\
            newparams['X Return Time']!=self.parameters['X Return Time'] or\
            newparams['Projector Control Pulse Width']!=self.parameters['Projector Control Pulse Width']):
                period = newparams['Image Width'] * newparams['Resolution'] / self.machine_config.AO_SAMPLE_RATE - self.shortest_sample
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
            self.image.set_image(numpy.rot90(self.frame, 3))
            #Note: image data is only rotated before display!
    
    def roundint(self, value):
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
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 4), 'step' : 0.1, 'siPrefix': False, 'suffix': ' px/um'},
                {'name': 'Image Width', 'type': 'int', 'value': 100, 'limits': (10, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Image Height', 'type': 'int', 'value': 100, 'limits': (10, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'X Return Time', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  0.1), 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': self.shortest_sample, 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  None), 'siPrefix': True, 'suffix': 's'}
                #Maximum for Projector Control Pulse Width and limits for Projector Control Phase aren't set yet!
            ]
        self.params_config.extend(params)
        
    def generate_waveform(self):
        line_length = self.roundint(self.image_width * self.image_resolution) + self.return_x_samps
        total_lines = self.roundint(self.image_height * self.image_resolution)
        
        self.return_y_samps = line_length
        self.AO_sampsperchan = (line_length - 1) * total_lines + self.return_y_samps
        self.printc(self.AO_sampsperchan)
        
        x_min = -self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        x_max = self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        
        y_min = -self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        y_max = self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        
        # X signal
        ramp_up_x = numpy.linspace(x_min, x_max, num=line_length - self.return_x_samps)
        ramp_down_x = numpy.linspace(x_max, x_min, num=self.return_x_samps + 1)[1:-1]
        waveform_x = numpy.concatenate((ramp_up_x,  ramp_down_x))
        waveform_x = numpy.tile(waveform_x, total_lines)
        waveform_x = numpy.append(waveform_x, numpy.full(self.return_y_samps, x_min)) # wait for Y to return        
        
        # Linear Y signal
        ramp_up_y = numpy.linspace(y_min, y_max, num=self.AO_sampsperchan - self.return_y_samps + 1)      
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)[1:]
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        
        '''
        # Stepped Y signal
        ramp_up_y = numpy.linspace(y_min, y_max, num=total_lines)
        ramp_up_y = numpy.repeat(ramp_up_y, line_length - 1)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        ''' 
        
        # Projector control
        phase = self.roundint(self.parameters['Projector Control Phase'] * self.machine_config.AO_SAMPLE_RATE)
        pulse_width = self.roundint(self.parameters['Projector Control Pulse Width'] * self.machine_config.AO_SAMPLE_RATE)
        
        initial_shift = numpy.zeros(line_length - self.return_x_samps + phase)
        single_period = numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK
        single_period = numpy.append(single_period, numpy.zeros(line_length - pulse_width - 1))
        projector_control = numpy.tile(single_period, total_lines)
        projector_control = numpy.append(initial_shift, projector_control)
        projector_control = projector_control[:-line_length + pulse_width + 1]
        
        projector_control = numpy.append(projector_control, numpy.zeros(self.return_y_samps + self.return_x_samps - pulse_width - phase - 1))
        
        '''
        projector_control = numpy.zeros(line_length - self.return_x_samps - 1 + phase)
        
        if(phase + pulse_width > self.return_x_samps):
            pulse_width -= (self.return_x_samps - phase)
            projector_control = numpy.append(projector_control,  numpy.ones(self.return_x_samps - phase) * self.machine_config.PROJECTOR_CONTROL_PEAK)
            projector_control[:pulse_width] = numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK
            self.printc("Generating long projector control pulse")
        else:
            projector_control = numpy.append(projector_control,  numpy.ones(pulse_width) * self.machine_config.PROJECTOR_CONTROL_PEAK)
            projector_control = numpy.append(projector_control,  numpy.zeros(self.return_x_samps - phase - pulse_width))
            self.printc("Generating short projector control pulse")
        projector_control = numpy.tile(projector_control, total_lines)        
        projector_control = numpy.append(projector_control, numpy.zeros(self.return_y_samps))
        '''
        
        #Frame timing
        hold_time = self.roundint(self.machine_config.FRAME_TIMING_HOLD * self.machine_config.AO_SAMPLE_RATE)
        old_frame = numpy.zeros(self.AO_sampsperchan - self.return_y_samps)
        
        if(hold_time > self.return_y_samps):
            hold_time -= self.return_y_samps
            old_frame[:hold_time] = numpy.ones(hold_time) * self.machine_config.FRAME_TIMING_PEAK
            begin_new_frame = numpy.ones(self.return_y_samps) * self.machine_config.FRAME_TIMING_PEAK
            self.printc("Generating long frame timing pulse")
        else:
            begin_new_frame = numpy.zeros(self.return_y_samps)
            begin_new_frame[:hold_time] = numpy.ones(hold_time) * self.machine_config.FRAME_TIMING_PEAK  
            self.printc("Generating short frame timing pulse")
            
        frame_timing = numpy.concatenate((old_frame,  begin_new_frame))
        
        if not (len(waveform_x) == len(waveform_y) == len(projector_control) == len(frame_timing)):
            self.printc("Error during waveform generation! Number of samples are different.")
            self.printc(len(waveform_x))
            self.printc(len(waveform_y))
            self.printc(len(projector_control))
            self.printc(len(frame_timing))
        
        self.waveform_x=waveform_x
        self.waveform_y=waveform_y
        self.projector_control=projector_control
        self.frame_timing=frame_timing
        self.waveform = numpy.concatenate((projector_control,  frame_timing,  waveform_x,  waveform_y)) # order: x y pc ft
        #self.plot()
        
    def plot(self):
        from pylab import plot, grid, show
        i=0
        t=numpy.arange(self.waveform_y.shape[0]) / float(self.machine_config.AO_SAMPLE_RATE) * 1e3
        for s in [self.projector_control, self.waveform_x, self.waveform_y, self.frame_timing]:
            #plot(s+i*10) # WP: added t <- arrays were plot by their default indexes (number of samples) and not by msecs
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
        self.return_x_samps = self.roundint(self.parameters['X Return Time'] * self.machine_config.AO_SAMPLE_RATE) # including max and min values too! needed to remove later
        self.return_y_samps = self.return_x_samps #will be overwritten
        
        self.frame = numpy.empty((self.roundint(self.image_width * self.image_resolution), self.roundint(self.image_height * self.image_resolution), 3),  dtype = int)
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
        ''' IMPORTANT, but commented out while using test hardware
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
            self.machine_config.AO_SAMPLE_RATE,             
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps,
            self.AO_sampsperchan)
        
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
            # configure ai for single samples yet
            #PyDAQmx.DAQmx_Val_ContSamps,
            PyDAQmx.DAQmx_Val_FiniteSamps,
            self.roundint(self.image_width * self.image_resolution) * self.roundint(self.image_height * self.image_resolution))
        '''
        Trying to synchronize - hardware does not support
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
            self.AO_sampsperchan, 
            True,
            numpy.ceil(self.AO_sampsperchan / self.machine_config.AO_SAMPLE_RATE) + 0.1,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            self.waveform,
            None,
            None)
        
        self.scan_timer.start(50.0)
        self.iteration = False
        self.statusbar.recording_status.setText('Scanning...')

    def scan_frame(self):
        
        self.iteration = not self.iteration
        self.analog_input.StartTask()
        nsamples = self.roundint(self.image_width * self.image_resolution) * self.roundint(self.image_height * self.image_resolution)
        data = numpy.zeros((2 * nsamples,), dtype=numpy.float64)
        read = PyDAQmx.int32()
        self.analog_input.ReadAnalogF64(nsamples, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,  data,  2 * nsamples, PyDAQmx.byref(read),  None)
        self.analog_input.StopTask()
        
        data += min(data)
        data *= self.roundint(256.0 / max(data))
        
        for j in range(0, self.roundint(self.image_height * self.image_resolution)):
            for i in range(0,  self.roundint(self.image_width * self.image_resolution)):
                self.frame[i, j, 0] = data[self.roundint(self.image_width * self.image_resolution) * i + j] # X
                self.frame[i, j, 1] = data[nsamples - 1 + self.roundint(self.image_width * self.image_resolution)* i + j] # Y
                self.frame[i, j, 2] = 0
        
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
        
        
        '''
        # Save demo:
        #TODO: dynamic memory access, or allocate space that big enough for the imaging data
        imaging_data = numpy.ndarray(shape=(20, 3, self.roundint(self.image_width * self.image_resolution), self.roundint(self.image_height * self.image_resolution)), dtype=int)
        demo_frame = numpy.empty((3, imaging_data.shape[2], imaging_data.shape[3]),  dtype = int)
        
        for i in range(0, self.roundint(self.image_width * self.image_resolution)):
            for j in range(0,  self.roundint(self.image_height * self.image_resolution)):
                demo_frame[0, i, j] = self.roundint(256.0 / self.image_width * self.image_resolution * i)
                demo_frame[1, i, j] = self.roundint(256.0 / self.image_width * self.image_resolution * j)
                demo_frame[2, i, j] = 0
        
        for n in range(0,  20):
            imaging_data[n] = demo_frame
        hdf5io.save_item("C:\Data\\test.hdf5", 'imaging_data', imaging_data, overwrite=True)
        
        demo_frame[2] = demo_frame[1]
        hdf5io.save_item("C:\Data\\test.hdf5", 'preview', numpy.moveaxis(demo_frame, 0,  -1))
        '''
        
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
        self.statusbar.recording_status.setText('Stopped.')
        
    def restart_scan(self):
        self.printc("Restart scan")
        self.stop_action()
        self.record_action()
        
    def open_reference_image_action(self):
        
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5')
        if (str(fname)=='' or not os.path.exists(str(fname))):
            return
        self.printc("Loading " + str(fname))
        
        h=hdf5io.Hdf5io(str(fname)) 
        h.load('preview')
        h.load('imaging_data')
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        
        #loading process takes very long, might be inconvenient waiting for it to complete - TODO: put it in background task (?)
        # current solution: save a preview image separately and load it first.
        self.referenceimage.set_image(h.preview)
        self.main_tab.setCurrentIndex(1)
        Qt.QApplication.processEvents()  # update Gui (window freezed during the following nested loop)
        
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
        
    def frame_select(self, position):
        self.referenceimage.set_image(numpy.rot90(self.reference_video[position], 3))
        #Note: image data is only rotated before display!
        
    def exit_action(self):
        self.stop_action()
        self.save_context()
        self.close()
