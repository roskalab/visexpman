import os,time, numpy, hdf5io, traceback, multiprocessing, serial
import scipy

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
        
        toolbar_buttons = ['record', 'stop', 'open_reference_image', 'capture_frame', 'record_z_stack', 'save', 'exit']
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
        
        self.init_camera_udp()
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
    
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.z_stacking = False # We are using scan_frame for both scanning and recording z stack. This variable tells the function, what to do (instead of passing it as a parameter, because more function uses it).
        
        # 3D numpy arrays, format: (X, Y, CH)
        self.frame = None
        self.ir_image = None
        self.clipboard = None
        
        # 4D numpy arrays, format: (t, X, Y, CH)
        self.z_stack = None
        self.reference_video = None
        
        self.shortest_sample = 1.0 / self.machine_config.AIO_SAMPLE_RATE
        
        self.params_config = [
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 4), 'step' : 0.1, 'siPrefix': False, 'suffix': ' px/um'},
                {'name': 'Image Width', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Image Height', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'X Return Time', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  0.1), 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': self.shortest_sample, 'siPrefix': True, 'suffix': 's'},
                {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'limits': (self.shortest_sample,  None), 'siPrefix': True, 'suffix': 's'}, 
                #Maximum for Projector Control Pulse Width and limits for Projector Control Phase aren't set yet!
                
                {'name': 'Enable RED channel', 'type': 'bool', 'value': True},
                {'name': 'Enable GREEN channel', 'type': 'bool', 'value': True},
                {'name': 'Enable IR layer', 'type': 'bool', 'value': True},
                
                {'name': 'IR X Offset', 'type': 'int', 'value': 0, 'step': 0.1, 'siPrefix': False},
                {'name': 'IR Y Offset', 'type': 'int', 'value': 0, 'step': 0.1, 'siPrefix': False},
                {'name': 'IR X Scale', 'type': 'float', 'value': 1, 'min': 0.01, 'step': 0.01, 'siPrefix': False},
                {'name': 'IR Y Scale', 'type': 'float', 'value': 1, 'min': 0.01, 'step': 0.01, 'siPrefix': False},
                {'name': 'IR Rotation', 'type': 'int', 'value': 0, 'limits': (0, 359), 'step': 1, 'siPrefix': False, 'suffix': ' degrees'},
                
                {'name': 'Z Stack Min Depth', 'type': 'int', 'value': 150, 'limits': (0, 250), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Z Stack Max Depth', 'type': 'int', 'value': 300, 'limits': (250, 500), 'step' : 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Z Stack Step', 'type': 'int', 'value': 1, 'limits': (1, 10), 'step': 1, 'siPrefix': True, 'suffix': 'um'}                
            ]
        self.params_config.extend(params)
    
    def parameter_changed(self):
        
        if(self.z_stacking):
            self.printc("Cannot change parameters while Z stacking is in proggress.")
            return
            # Feature (bug): 'Changed' parameter still stays there
        
        newparams=self.params.get_parameter_tree(return_dict=True)
        
        if hasattr(self, 'parameters'):
            if(newparams['Image Width']!=self.parameters['Image Width'] or\
            newparams['Image Height']!=self.parameters['Image Height'] or\
            newparams['Resolution']!=self.parameters['Resolution'] or\
            newparams['X Return Time']!=self.parameters['X Return Time'] or\
            newparams['Projector Control Pulse Width']!=self.parameters['Projector Control Pulse Width']):
                period = newparams['Image Width'] * newparams['Resolution'] / self.machine_config.AIO_SAMPLE_RATE - self.shortest_sample
                self.params.params.param('Projector Control Phase').items.keys()[0].param.setLimits((-period, period - newparams['Projector Control Pulse Width']))
                self.params.params.param('Projector Control Pulse Width').items.keys()[0].param.setLimits((self.shortest_sample, period))
                self.parameters=newparams

                if(self.scanning):
                    self.restart_scan() # Only if new self.waveform needed for scanning (depending on the changed parameterrs)
            else:
                self.parameters=newparams
            
            # Apply changed channel mask on loaded reference video - if there's any
            if(self.reference_video is not None):                
                self.frame_select(self.slider.value())
    
    def save_context(self):
        context_stream=utils.object2array(self.parameters)
        numpy.save(self.context_filename,context_stream)
    
    def roundint(self, value):
        return int(round(value))
    
    def plot(self):
        from pylab import plot, grid, show
        i=0
        t=numpy.arange(self.sampsperchan) / float(self.machine_config.AIO_SAMPLE_RATE) * 1e3
        for s in [self.projector_control, self.waveform_x, self.waveform_y, self.frame_timing]:
            plot(t, s+i*10)
            i+=1
        grid(True)
        show()
    
######### Two Photon ###########
    
    def generate_waveform(self):
        line_length = self.roundint(self.image_width * self.image_resolution) + self.return_x_samps # Number of samples for scanning a line
        total_lines = self.roundint(self.image_height * self.image_resolution)
        
        self.sampsperchan = (line_length - 1) * total_lines + self.return_y_samps - 1
        self.printc("Samples per channel: " + str(self.sampsperchan)) # Total number of samples for scanning a single frame
        
        # Calibrating control signal voltages
        x_min = -self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        x_max = self.machine_config.UM_TO_VOLTAGE * self.image_width + self.machine_config.X_OFFSET_VOLTAGE
        
        y_min = -self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        y_max = self.machine_config.UM_TO_VOLTAGE * self.image_height + self.machine_config.Y_OFFSET_VOLTAGE
        
        # X signal
        ramp_up_x = numpy.linspace(x_min, x_max, num=line_length - self.return_x_samps)
        ramp_down_x = numpy.linspace(x_max, x_min, num=self.return_x_samps + 1)[1:-1] # Exclude extreme values (avoiding duplication during concatenation)
        waveform_x = numpy.concatenate((ramp_up_x,  ramp_down_x))
        waveform_x = numpy.tile(waveform_x, total_lines)
        waveform_x = numpy.append(waveform_x, numpy.full(self.return_y_samps, x_min))[:-1] # Wait for Y to return
        
        # Linear Y signal
        ramp_up_y = numpy.linspace(y_min, y_max, num=self.sampsperchan - self.return_y_samps + 1)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)[1:] # Exclude maximum value
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
        
        '''
        # Stepped Y signal - for future tests, probably
        ramp_up_y = numpy.linspace(y_min, y_max, num=total_lines)
        ramp_up_y = numpy.repeat(ramp_up_y, line_length - 1)
        ramp_down_y = numpy.linspace(y_max, y_min, num=self.return_y_samps)
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))[:-1]
        '''
        
        # Projector control
        phase = self.roundint(self.parameters['Projector Control Phase'] * self.machine_config.AIO_SAMPLE_RATE)
        pulse_width = self.roundint(self.parameters['Projector Control Pulse Width'] * self.machine_config.AIO_SAMPLE_RATE)
        
        # TODO: code below can be simplified using numpy.roll (although, that would be as much work for me as creating this...)
        initial_shift = numpy.zeros(line_length - self.return_x_samps + phase)
        single_period = numpy.full(pulse_width, self.machine_config.PROJECTOR_CONTROL_PEAK)
        single_period = numpy.append(single_period, numpy.zeros(line_length - pulse_width - 1))
        projector_control = numpy.tile(single_period, total_lines) # Expand to all lines
        projector_control = numpy.append(initial_shift, projector_control) # Offset the whole signal depending on phase
        projector_control = projector_control[:-line_length + pulse_width + 1] # Cut off overflowed section
        
        projector_control = numpy.append(projector_control, numpy.zeros(self.return_y_samps + self.return_x_samps - pulse_width - phase - 1))[:-1] # Wait for Y to return
        
        # Frame timing
        hold_time = self.roundint(self.machine_config.FRAME_TIMING_HOLD * self.machine_config.AIO_SAMPLE_RATE)
        old_frame = numpy.zeros(self.sampsperchan - self.return_y_samps) #Zeros while old frame being scanned
        
        if(hold_time > self.return_y_samps):
            # Hold time strectches into the next frame
            hold_time -= self.return_y_samps
            old_frame[:hold_time] = numpy.full(hold_time, self.machine_config.FRAME_TIMING_PEAK) # Extend hold till the end of the previous frame
            begin_new_frame = numpy.full(self.return_y_samps, self.machine_config.FRAME_TIMING_PEAK) # Add the remaining section to the begining of the next one
            self.printc("Generating long frame timing pulse")
        else:
            begin_new_frame = numpy.zeros(self.return_y_samps)
            begin_new_frame[:hold_time] = numpy.full(hold_time,  self.machine_config.FRAME_TIMING_PEAK) # Simply add the hold_time section to its place
            self.printc("Generating short frame timing pulse")
            
        frame_timing = numpy.concatenate((old_frame,  begin_new_frame)) # Assemble
        
        # Basic error detection (useful for debuggging!)
        if not (len(waveform_x) == len(waveform_y) == len(projector_control) == len(frame_timing) == self.sampsperchan):
            self.printc("Error during waveform generation! Number of samples are different.")
            self.printc("Waveform X: " + str(len(waveform_x)))
            self.printc("Waveform Y: " + str(len(waveform_y)))
            self.printc("Projector Control: " + str(len(projector_control)))
            self.printc("Frame Timing: " + str(len(frame_timing)))
        
        # Only needed for plot, to pass:    
        self.waveform_x = waveform_x
        self.waveform_y = waveform_y
        self.projector_control = projector_control
        self.frame_timing = frame_timing
        
        self.waveform = numpy.concatenate((waveform_x,  waveform_y,  projector_control,  frame_timing))[:-1] # Order: X, Y PC, FT
        #self.plot()
    
    def record_action(self):
        if(self.scanning):
            return
        
        self.image_width = self.parameters['Image Width']
        self.image_height = self.parameters['Image Height']
        self.image_resolution = self.parameters['Resolution']
        self.return_x_samps = self.roundint(self.parameters['X Return Time'] * self.machine_config.AIO_SAMPLE_RATE) # Including max and min values! (for more details see generate_waveform)
        self.return_y_samps = self.roundint(self.image_width * self.image_resolution) + self.return_x_samps # Will be equal to line_length in generate_waveform
        
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
            -5.0,
            5.0,
            PyDAQmx.DAQmx_Val_Volts,
            None)
        self.analog_input.CfgSampClkTiming(
            "OnboardClock",
            self.machine_config.AIO_SAMPLE_RATE,
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_FiniteSamps,
            self.sampsperchan)
        '''
        TODO: trying to synchronize - hardware does not support yet (i am not sure if this is the solution)
        '''
        self.analog_input.CfgDigEdgeStartTrig(
            "ao/StartTrigger",
            PyDAQmx.DAQmx_Val_Rising)
        
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
            numpy.ceil(self.sampsperchan / self.machine_config.AIO_SAMPLE_RATE),
            PyDAQmx.DAQmx_Val_GroupByChannel,
            self.waveform,
            None,
            None)
        
        self.frame = numpy.zeros((self.roundint(self.image_width * self.image_resolution), self.roundint(self.image_height * self.image_resolution), 3),  dtype = int)
        self.scan_frame() # After changing parameters, this way is no need to wait for timer to scan the new frame + z tack will get a preview image
        
        if(not self.z_stacking):
            self.scan_timer.start(30) # TODO: Adjust as needed!
            self.statusbar.recording_status.setText('Scanning...')
        
        self.scanning = True
    
    def scan_frame(self):
        
        fps_counter_start = time.time()
        
        data = numpy.empty((2 * self.sampsperchan,), dtype=numpy.float64) # Because 2 channel present
        read = PyDAQmx.int32()
        
        self.analog_input.StartTask()
        # TODO: ReadAnalogF64 consumes a lot of time! ( ~0.3s -> 5000 samps per sec 40*40px, 1 px/um -> resulting a maximum of 3 fps ! )
        # the remaining piece of code finishes in only 0.01s. Optimization is needed, if maximum 18 FPS for a 200x200px image is too low
        self.analog_input.ReadAnalogF64(
            self.sampsperchan,
            60.0, # Timeout
            PyDAQmx.DAQmx_Val_GroupByChannel,
            data,
            2 * self.sampsperchan,
            PyDAQmx.byref(read),
            None)
        self.analog_input.StopTask()
        
        # Scaling pixel data
        data -= min(data)
        data *= 255.0 / self.machine_config.BRIGHT_PIXEL_VOLTAGE # Instead of dividing by max(data) -> watherver, gui.Image automatically scales colours anyway in set_image function - check out!
        
        actual_width = self.roundint(self.image_width * self.image_resolution)
        actual_height = self.roundint(self.image_height * self.image_resolution)
        
        '''
        Optimized frame builder: (just a bit faster than the nested loops below)
        #TODO: Bug fix needed: in the following 3 lines there must be missing a +-1 >:(
        
        begin_of_return = numpy.arange(actual_width, self.sampsperchan, actual_width + self.return_x_samps)
        end_of_return = numpy.arange(actual_width + self.return_x_samps, self.sampsperchan + 1, actual_width + self.return_x_samps)
        boundaries = numpy.insert(end_of_return,  numpy.arange(len(begin_of_return)), begin_of_return)
        
        red_ch = numpy.array(numpy.split(data, boundaries)[::2][:-1])
        green_ch = numpy.array(numpy.split(numpy.split(data, [self.sampsperchan])[1], boundaries)[::2][:-1])
        blue_ch = numpy.zeros((actual_height , actual_width),  dtype=int)
        
        self.printc(red_ch.shape)
        self.printc(green_ch.shape)
        self.printc(blue_ch.shape)
        
        self.frame = numpy.swapaxes(numpy.dstack([red_ch,  green_ch,  blue_ch]), 0, 1)
        
        #self.printc(self.frame.shape)
        '''
        
        # Exclude measurements during return x and return y:
        samples_to_skip = actual_width + self.return_x_samps - 1

        for j in range(0, actual_height):
            for i in range(0, actual_width):
                self.frame[i, j, 0] = data[samples_to_skip * j + i] # Test: X feedback - red
                self.frame[i, j, 1] = data[self.sampsperchan + samples_to_skip * j + i] # Test: Y feedback - green
                self.frame[i, j, 2] = 0
        
        # TODO: Repeats are only needed if IR image resolution is more than 2P resolution.
        #self.frame = self.frame.repeat(10, 0).repeat(10, 1)
        
        self.get_ir_image()
        
        scale = numpy.array([[1.0 / self.parameters["IR X Scale"], 0], [0, 1.0 / self.parameters["IR Y Scale"]]])
        
        # In the future, scipy.ndimage.geometric_transform might be the best solution instead of these:
        self.ir_image = scipy.ndimage.zoom(self.ir_image, (self.parameters["IR X Scale"], self.parameters["IR Y Scale"]))
        self.ir_image = scipy.ndimage.rotate(self.ir_image, self.parameters["IR Rotation"])
        
        # Put IR on frame (with offset here!) moving overlapping pixels from ir into frame
        # Known issues: bounding box changes size depending on zoom and rotation, image anchor is the lower left corner, not the center of the current view
        self.frame[max(0, self.parameters["IR X Offset"]) : min(self.ir_image.shape[0] + self.parameters["IR X Offset"], self.frame.shape[0]),
            max(0, self.parameters["IR Y Offset"]) : min(self.ir_image.shape[1]  + self.parameters["IR Y Offset"], self.frame.shape[1]), 2] = \
            self.ir_image[max(0, -self.parameters["IR X Offset"]) : min(self.ir_image.shape[0], self.frame.shape[0] - self.parameters["IR X Offset"]),
            max(0, -self.parameters["IR Y Offset"]) : min(self.ir_image.shape[1], self.frame.shape[1] - self.parameters["IR Y Offset"])]
        
        if(self.z_stacking):
            self.z_stack.append(numpy.rollaxis(numpy.copy(self.frame), 2)) # Changing axis order to: ch, x, y
            self.statusbar.recording_status.setText("Recording Z stack, frame number: " + str(len(self.z_stack)))
        else:
            self.statusbar.recording_status.setText("Scanning... " + str(round(1.0/(time.time() - fps_counter_start), 2)) + " FPS")
        
        '''
        TODO: add binning (something like this) - when hardware can handle more then 5000 samps/sec
        def raw2frame(rawdata, binning_factor, boundaries, offset = 0):
            binned_pmt_data = binning_data(rawdata, binning_factor)
            if offset != 0:
                binned_pmt_data = numpy.roll(binned_pmt_data, -offset)
            return numpy.array((numpy.split(binned_pmt_data, boundaries)[1::2]))
    
        def binning_data(data, factor):
            #data: two dimensional pmt data : 1. dim: pmt signal, 2. dim: channel
            return numpy.reshape(data, (data.shape[0]/factor, factor, data.shape[1])).mean(1)
        '''
    
    # ZMQ socket handler (mostly adopted from camera.py)
    def socket_handler(self):
        if not self.socket_queues['2p']['fromsocket'].empty():
            command=self.socket_queues['2p']['fromsocket'].get()
            try:
                if 'function' in command:
                    getattr(self,  command['function'])(*command['args']) # Executes function with given args
            except:
                printc("Socket handler error!")
    
    # Change parameters remotely (for zmq use) takes python dictionary as parameter
    def change_params(self, param_set):
        if(self.z_stacking):
            self.socket_queues['2p']['tosocket'].put({'change_params': "Cannot change parameters while Z stacking is in proggress."})
            return
            
        for name in param_set:
            try:
                self.params.params.param(name).items.keys()[0].param.setValue(param_set[name])
            except Exception as e:
                self.socket_queues['2p']['tosocket'].put({'change_params': str(e)})
    
    # Applies channel mask to an image (which has all color channel!) and returns a copy of its modified version
    def mask_channel(self, source):
        canvas = numpy.copy(source)
        if not self.parameters["Enable RED channel"]:
            canvas[:, :, 0:1] = 0
        if not self.parameters["Enable GREEN channel"]:
            canvas[:, :, 1:2] = 0
        if not self.parameters["Enable IR layer"]:
            canvas[:, :, 2:3] = 0
        return canvas
    
    def update_image(self):
        if(self.frame is not None):
            self.image.set_image(self.mask_channel(self.frame))
        self.socket_handler()
    
    def stop_action(self, remote=None):
        if(not self.scanning):
            return
            
        if(self.z_stacking):
            if(remote==False):
                self.printc("Z stacking is in progress, cannot abort manually.")
            else:
                self.socket_queues['2p']['tosocket'].put({'stop_action': "Z stacking is in progress, cannot abort manually."})
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
        self.stop_action()
        self.printc("Restart scan")
        self.record_action()
    
############## REFERENCE IMAGE ###################
    
    def open_reference_image_action(self, remote=None):
        
        if(remote==False):
            fname = str(QtGui.QFileDialog.getOpenFileName(self, 'Open Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5'))
        else:
            fname = remote
        
        if (fname=='' or not os.path.exists(fname)):
            return
        
        self.printc("Loading: " + fname)
        
        h=hdf5io.Hdf5io(fname)
        h.load('preview')
        h.load('imaging_data')
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        
        self.referenceimage.set_image(h.preview) # Does not apply channel mask for preview!
        self.main_tab.setCurrentIndex(1)
        
        if(hasattr(h, 'imaging_data')):
            # Loading had been optimized a LOT, now it is reasonably fast
            self.reference_video = numpy.moveaxis(h.imaging_data, 1, 3) # Change shape from (t, ch, x, y) -> (t, x, y, ch)
            self.slider.setMaximum(h.imaging_data.shape[0] - 1)
        else:
            self.reference_video = None
        
        h.close()
        
        self.statusbar.recording_status.setText('Loaded: ' + fname)
        self.printc("Imaging data loaded successfully")        
    
    def frame_select(self, position): # Using slider
        canvas = self.mask_channel(self.reference_video[position])
        self.referenceimage.set_image(canvas)
        self.clipboard = numpy.copy(canvas)
    
    def capture_frame_action(self):
        if(self.frame is None):
            return
        self.reference_video = None
        self.clipboard = self.mask_channel(self.frame.copy())
        self.referenceimage.set_image(self.clipboard)
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        self.main_tab.setCurrentIndex(1)
    
    def save_action(self, remote=None):
        #NOTE!: this function is only capable of saving captured frames, you cannot saves videos, only z stack
        
        if(self.clipboard is None):
            if(remote==False):
                self.printc("There's no image data to save. Record and capture it first!")
            else:
                self.socket_queues['2p']['tosocket'].put({'save_action': "There's no image data to save. Record and capture it first!"})
            return
        
        if(remote==False):
            fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Save Reference Image', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5'))
        else:
            fname = remote
        
        if (fname==''):
            return
        
        hdf5io.save_item(fname, 'preview', self.clipboard, overwrite=True)
        self.printc("Saving " + fname + " completed")
    

############## Z-STACK ###################
    
    def record_z_stack_action(self, remote=None):
        
        if(self.scanning):
            self.stop_action()
        
        self.z_stacking = True
        self.z_stack = []
        
        self.record_action() # Without statring scan_timer! (self.z_stacking = True) scan_frame is being called 'manually' check out the for loop below!
        preview = numpy.copy(self.frame) # Preview image (self.frame) available right after record_action()
        
        for i in range(self.parameters["Z Stack Min Depth"],  self.parameters["Z Stack Max Depth"],  self.parameters["Z Stack Step"]):
            self.set_depth(i)
            Qt.QApplication.processEvents() # Update gui
            self.scan_frame()
        
        self.z_stacking = False
        self.stop_action()
        
        stack = numpy.stack(self.z_stack, axis=0) # Dimensions : time, ch, x, y
        
        if(remote==False):
            fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Save Recorded Z Stack (' + str(len(self.z_stack)) + ' frames)', self.machine_config.EXPERIMENT_DATA_PATH, '*.hdf5'))
        else:
            fname = remote
        
        if (fname==''):
            return
        
        hdf5io.save_item(fname, 'imaging_data', stack, overwrite=True)
        hdf5io.save_item(fname, 'preview', preview)
        self.printc("Saving " + fname + " completed")
        self.statusbar.recording_status.setText("Z Stack Recorded: " + fname)
        
    
    def set_depth(self, depth):
        #TODO: implement in stage_control device specific protocol
        pass
        
    def init_camera_udp(self):
        import socket
        self.camera_udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.camera_udp.bind(("127.0.0.1", 8880))
    
    def get_ir_image(self):
        data, addr = self.camera_udp.recvfrom(16009)
        if 0:
            #Demo: 4 blue rectangles
            self.ir_image = numpy.full((400, 300), 80, dtype=int)
            self.ir_image[180:220, :] = 0
            self.ir_image[:, 130:170] = 0
            #self.ir_image = numpy.random.randint(0, 75, size=(400, 300))
            #done :)
        else:
            self.ir_image = numpy.zeros((800, 600))
            pixels=data[6:-3]
            data=data[0].decode()
            if data[:5]=='start' and data[-3:]=='end':
                frame_count=ord(data[5])
                for i in range(20):#Every packet contains 20 lines
                    line_index=frame_count*20+i
                    self.ir_image[:, line_index]=pixels[i*self.ir_image.shape[0]: (i+1)*self.ir_image.shape[0]]
    
    def exit_action(self):
        self.stop_action()
        self.save_context()
        self.close()
