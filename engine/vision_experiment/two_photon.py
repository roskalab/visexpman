import os,time, numpy, hdf5io, traceback, multiprocessing, serial, unittest, copy
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
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes

def generate_waveform(image_width,  image_height,  resolution,  **kwargs):
    return_x_samps = utils.roundint(kwargs['x_flyback_time'] * kwargs['fsample'])
    
    line_length = utils.roundint(image_width * resolution) + return_x_samps # Number of samples for scanning a line
    return_y_samps = line_length* kwargs['y_flyback_lines']
    total_lines = utils.roundint(image_height * resolution)+kwargs['y_flyback_lines']
    
    # Calibrating control signal voltages
    x_min = -kwargs['um2voltage']*image_width + kwargs.get('x_offset', 0)
    x_max = kwargs['um2voltage']*image_width + kwargs.get('x_offset', 0)
    
    y_min = -kwargs['um2voltage']*image_width + kwargs.get('y_offset', 0)
    y_max = kwargs['um2voltage']*image_width + kwargs.get('y_offset', 0)
    
    # X signal
    ramp_up_x = numpy.linspace(x_min, x_max, num=line_length - return_x_samps)
    ramp_down_x = numpy.linspace(x_max, x_min, num=return_x_samps + 1)[1:-1] # Exclude extreme values (avoiding duplication during concatenation)
    waveform_x = numpy.concatenate((ramp_up_x,  ramp_down_x))
    waveform_x = numpy.tile(waveform_x, total_lines)

    # Linear Y signal
    ramp_up_y = numpy.linspace(y_min, y_max, num=waveform_x.shape[0] - return_y_samps)
    ramp_down_y = numpy.linspace(y_max, y_min, num=return_y_samps) # Exclude maximum value
    waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y))
    
    
    # Projector control
    phase = utils.roundint(kwargs.get('stim_phase', 0) * kwargs['fsample'])
    pulse_width = utils.roundint(kwargs.get('stim_pulse_width', 0) * kwargs['fsample'])
    ttl_voltage=kwargs.get('ttl_voltage', 3.3)
    projector_control =numpy.tile(numpy.concatenate((numpy.zeros(ramp_up_x.shape[0]+phase), numpy.full(pulse_width,  ttl_voltage),  numpy.zeros(ramp_down_x.shape[0]-phase-pulse_width ))), total_lines)
    
    frame_timing=numpy.zeros_like(projector_control)
    frame_timing[-utils.roundint(1e-3*kwargs['fsample']):]=ttl_voltage
    return waveform_x,  waveform_y, projector_control,  frame_timing

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
        
        self.queues = {'command': multiprocessing.Queue(), 
                            'response': multiprocessing.Queue(), 
                            'data': multiprocessing.Queue()}
        
        self.daq_process = daq_instrument.AnalogIOProcess('daq', self.queues, self.logger,
                                ai_channels = self.machine_config.DAQ_DEV_ID + "/ai4:5",
                                ao_channels= self.machine_config.DAQ_DEV_ID + "/ao0:3",
                                limits=None)
        self.daq_process.start()
        
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
        else:
            self.parameters=self.params.get_parameter_tree(return_dict=True)
    
    def save_context(self):
        context_stream=utils.object2array(self.parameters)
        numpy.save(self.context_filename,context_stream)

    
    def plot(self):
        from pylab import plot, grid, show
        i=0
        t=numpy.arange(self.waveform_x.shape[0]) / float(self.machine_config.AIO_SAMPLE_RATE) * 1e3
        y=[self.projector_control, self.waveform_x, self.waveform_y, self.frame_timing]
        x=[t]*len(y)
#        self.generate_waveform();self.plot()
        self.p=gui.Plot(None)
        self.p.setGeometry(100, 100, 500, 500)
        self.p.update_curves(x, y,colors=[(255, 128, 0),  (0, 255, 0),  (0, 0, 255),  (255, 0, 0)])
        self.p.show()
        
#        for s in :
#            
#            plot(t, s+i*10)
#            i+=1
#        grid(True)
#        show()
    
######### Two Photon ###########
    
    def generate_waveform(self):
        self.waveform_x,  self.waveform_y, self.projector_control,  self.frame_timing=generate_waveform(self.parameters['Image Width'],  
                                                                                            self.parameters['Image Height'],  
                                                                                            self.parameters['Resolution'],  
                                                                                            x_flyback_time=self.parameters['X Return Time'],  
                                                                                            y_flyback_lines=self.machine_config.Y_FLYBACK_LINES, 
                                                                                            fsample=self.machine_config.AIO_SAMPLE_RATE,  
                                                                                            um2voltage=self.machine_config.UM_TO_VOLTAGE,
                                                                                            stim_pulse_width=self.parameters['Projector Control Pulse Width'])
   
#        self.plot()

    def init_daq(self):
        self.res = self.daq_process.start_daq(ai_sample_rate = self.machine_config.AIO_SAMPLE_RATE,
                                                            ao_sample_rate = self.machine_config.AIO_SAMPLE_RATE,
                                                            ao_waveform = self.waveform, 
                                                            timeout = 30)

        self.shutter = PyDAQmx.Task()
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
            
    def stop_daq(self):
        self.shutter.WriteDigitalLines(
            1,
            True,
            1.0,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            numpy.array([int(0)], dtype=numpy.uint8),
            None,
            None)
        self.unread_data = self.daq_process.stop_daq()
#        self.read_daq()
#        self.analog_output.WaitUntilTaskDone(self.machine_config.DAQ_TIMEOUT)
#        self.analog_output.StopTask()
#        self.analog_input.StopTask()
    
    def record_action(self):
        if self.scanning:
            return
        self.generate_waveform()
        self.waveform=numpy.array([self.waveform_x, self.waveform_y, self.projector_control,  self.frame_timing])
#        self.waveform=self.waveform.flatten()
        #self.waveform=numpy.zeros_like(self.waveform)
        self.init_daq()        
        self.scanning = True
        sample_time=self.waveform.shape[1]/float(self.machine_config.AIO_SAMPLE_RATE)
        self.printc("Frame rate {0}".format(1/sample_time))
        self.scan_timer.start(int(sample_time*1000))
        self.statusbar.recording_status.setText('Recording')
        self.statusbar.recording_status.setStyleSheet('background:red;')
    
    def scan_frame(self):
        f=self.daq_process.read_ai()
        if hasattr(f,  'dtype'):
            self.frame = f
            self.printc(self.frame.shape)
        return
        fps_counter_start = time.time()
        
        data = numpy.empty((2 * self.sampsperchan,), dtype=numpy.float64) # Because 2 channel present
        read = PyDAQmx.int32()
        
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
        print 2
        # Scaling pixel data
        data -= min(data)
        data *= 255.0 / self.machine_config.BRIGHT_PIXEL_VOLTAGE # Instead of dividing by max(data) -> watherver, gui.Image automatically scales colours anyway in set_image function - check out!
        
        actual_width = utils.roundint(self.image_width * self.image_resolution)
        actual_height = utils.roundint(self.image_height * self.image_resolution)
        
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
        print 3
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
            try:
                self.image.set_image(self.mask_channel(self.frame))
            except:
                self.printc("img disp problem")
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
        self.stop_daq()
        
        self.scanning = False
        self.statusbar.recording_status.setText('Idle')
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        
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
        raise NotImplementedError('reccord_action and stop_action shall be called for every depth')
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
        self.daq_process.terminate()
        self.close()

class Test(unittest.TestCase):
    def test(self):
        generate_waveform(10,  10,  1,  x_flyback_time=200e-6,  y_flyback_lines=2, fsample=400000,  um2voltage=1e-2,  stim_pulse_width=100e-6)
        
if __name__=='__main__':
    unittest.main()
