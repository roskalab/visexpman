import os,time, numpy, hdf5io, traceback, multiprocessing, serial, unittest, copy
import scipy,skimage

import PyQt5.Qt as Qt
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

from visexpman.engine.generic import gui,fileop, signal, utils
from visexpman.engine.hardware_interface import daq,scanner_control,camera
from visexpman.engine.vision_experiment import gui_engine, main_ui,experiment_data

import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes

class TwoPhotonImaging(gui.VisexpmanMainWindow):
    
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        
        gui.VisexpmanMainWindow.__init__(self, context)
        self.setWindowIcon(gui.get_icon('main_ui'))
        self._init_variables()
        self._init_hardware()
        self.resize(self.machine_config.GUI_WIDTH, self.machine_config.GUI_HEIGHT)
        self._set_window_title()
        
        toolbar_buttons = ['start',  'snap', 'record', 'stop', 'zoom_in', 'zoom_out', 'open', 'save_image', 'z_stack',  'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        
        self.statusbar=self.statusBar()
        self.statusbar.info=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.info)
        self.statusbar.ircamera_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.ircamera_status)
        self.statusbar.twop_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.twop_status)
        
        self.debug = gui.Debug(self)
        
        
        self.image = gui.Image(self)
        
        self.main_tab = QtGui.QTabWidget(self)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab.addTab(self.params, 'Settings')
        
        self.video_player = QtGui.QWidget()
        self.saved_image = gui.Image(self)
        
#        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
#        self.slider.setFocusPolicy(QtCore.Qt.StrongFocus)
#        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
#        self.slider.setTickInterval(self.machine_config.IMAGE_DISPLAY_RATE)
#        self.slider.setSingleStep(1)
#        self.slider.setPageStep(self.machine_config.IMAGE_DISPLAY_RATE)
#        self.slider.setMinimum(0)
#        self.slider.setMaximum(0)
#        self.slider.valueChanged.connect(self.frame_select)
        
#        self.vplayout = QtGui.QHBoxLayout()
#        self.vplayout.addWidget(self.referenceimage)
#        self.vplayout.addWidget(self.lut)
        
#        self.video_player.setLayout(self.vplayout)
        self.main_tab.addTab(self.saved_image, 'Saved Image')
        
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        
        self.main_tab.setMinimumHeight(self.machine_config.GUI_HEIGHT * 0.5)
        self.debug.setMaximumHeight(self.machine_config.GUI_HEIGHT * 0.3)
        self.image.setMinimumWidth(self.machine_config.GUI_WIDTH * 0.4)                
        self.image.setMinimumHeight(self.machine_config.GUI_WIDTH * 0.4)                
        self.image.set_image(numpy.random.random((200, 200, 3)))
        
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        
        
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        if os.path.exists(self.context_filename):
            try:
                context_stream = numpy.load(self.context_filename)
                self.settings = utils.array2object(context_stream)
            except:#Context file was probab
                self.parameter_changed()
        else:
            self.parameter_changed()
        self.load_all_parameters()
        self.show()
        self.statusbar.twop_status.setText('Ready')
        self.statusbar.ircamera_status.setText('Ready')
        
        self.update_image_timer=QtCore.QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        self.update_image_timer.start(1000.0 / self.machine_config.IMAGE_DISPLAY_RATE)
        
        self.read_image_timer=QtCore.QTimer()
        self.read_image_timer.start(1000.0 / self.machine_config.IMAGE_DISPLAY_RATE)
        self.read_image_timer.timeout.connect(self.read_image)
        
        self.queues = {'command': multiprocessing.Queue(), 
                            'response': multiprocessing.Queue(), 
                            'data': multiprocessing.Queue()}
        
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
    
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.z_stacking = False # We are using scan_frame for both scanning and recording z stack. This variable tells the function, what to do (instead of passing it as a parameter, because more function uses it).
        
        # 3D numpy arrays, format: (X, Y, CH)
        self.ir_frame = numpy.zeros((500,500))
        self.twop_frame = numpy.zeros((100,100,2))
        
        # 4D numpy arrays, format: (t, X, Y, CH)
        self.z_stack = None
        
        self.shortest_sample = 1.0 / self.machine_config.AO_SAMPLE_RATE
        
        image_filters=['', 'mean', 'MIP', 'median',  'histogram equalization']
        file_formats=['.mat',  '.hdf5', '.tiff']
        
        minmax_group=[{'name': 'Min', 'type': 'float', 'value': 0.0,},
                                    {'name': 'Max', 'type': 'float', 'value': 1.0,}, 
                                    {'name': 'Image filters', 'type': 'list', 'value': '',  'values': image_filters},]
                                    
        channels_group=[{'name': 'Top', 'type': 'group', 'expanded' : False, 'children': minmax_group}, 
                                    {'name': 'Side', 'type': 'group', 'expanded' : False, 'children': minmax_group},
                                    {'name': 'IR', 'type': 'group', 'expanded' : False, 'children': minmax_group}]
        
        self.params_config = [
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 4), 'step' : 0.1, 'siPrefix': False, 'suffix': ' pixel/um'},
                {'name': 'Scan Width', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Scan Height', 'type': 'int', 'value': 100, 'limits': (30, 300), 'step': 1, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Live IR', 'type': 'bool', 'value': True},
                {'name': 'IR Exposure', 'type': 'int', 'value': 50, 'limits': (1, 1000), 'step': 1, 'siPrefix': True, 'suffix': 'ms'},
                {'name': 'IR Gain', 'type': 'int', 'value': 1, 'limits': (0, 1000), 'step': 1},
                {'name': 'Show Top', 'type': 'bool', 'value': True},
                {'name': 'Show Side', 'type': 'bool', 'value': True},
                {'name': 'Show IR', 'type': 'bool', 'value': True},
                {'name': 'Live', 'type': 'group', 'expanded' : False, 'children': channels_group}, 
                {'name': 'Saved', 'type': 'group', 'expanded' : False, 'children': channels_group}, 
                {'name': 'Infrared-2P overlay', 'type': 'group',  'expanded' : False, 'children': [
                    {'name': 'Offset X', 'type': 'int', 'value': 0,  'siPrefix': False, 'suffix': ' um'},
                    {'name': 'Offset Y', 'type': 'int', 'value': 0,  'siPrefix': False, 'suffix': ' um'},
                    {'name': 'Scale X', 'type': 'float', 'value': 1.0,},
                    {'name': 'Scale Y', 'type': 'float', 'value': 1.0,},
                    {'name': 'Rotation', 'type': 'float', 'value': 0.0,  'siPrefix': False, 'suffix': ' degrees'},                    
                ]}, 
                 {'name': 'Z stack', 'type': 'group', 'expanded' : False, 'children': [
                    {'name': 'Start', 'type': 'int', 'value': 0,  'step': 1, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'End', 'type': 'int', 'value': 0,  'step' : 1, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Step', 'type': 'int', 'value': 1, 'limits': (1, 10), 'step': 1, 'siPrefix': True, 'suffix': 'um'}                
                ]}, 
                {'name': 'Advanced', 'type': 'group', 'expanded' : False, 'children': [
                    {'name': 'Enable Projector', 'type': 'bool', 'value': False},
                    {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': self.shortest_sample, 'step': self.shortest_sample, 'siPrefix': False, 'suffix': ' us'}, 
                    {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': self.shortest_sample, 'siPrefix': False, 'suffix': ' us'},
                    {'name': 'X Return Time', 'type': 'float', 'value': 20,  'suffix': ' %'},
                    {'name': 'Y Return Time', 'type': 'float', 'value': 2,  'suffix': ' lines'},
                    {'name': 'File format', 'type': 'list', 'value': '.hdf5',  'values': file_formats},
                ]}, 
            ]
        self.params_config.extend(params)
        self.twop_running=False
        self.camera_running=False
    
    def parameter_changed(self):
        
        if(self.z_stacking):
            self.printc("Cannot change parameters while Z stacking is in proggress.")
            return
            # Feature (bug): 'Changed' parameter still stays there
        newparams=self.params.get_parameter_tree(return_dict=True)
        
        if hasattr(self, 'settings'):
            if newparams['params/Live IR'] and not self.settings['params/Live IR']:
                self.camera.start_()
                self.printc('Start IR camera')
                self.statusbar.ircamera_status.setText('IR Live')
                self.statusbar.ircamera_status.setStyleSheet('background:orange;')
                self.camera_running=True
            elif not newparams['params/Live IR'] and self.settings['params/Live IR']:
                self.camera.stop()
                self.printc('Stop IR camera')
                self.statusbar.ircamera_status.setText('Ready')
                self.statusbar.ircamera_status.setStyleSheet('background:gray;')
                self.camera_running=False
            if newparams['params/IR Exposure'] != self.settings['params/IR Exposure']:
                self.camera.set(exposure=int(newparams['params/IR Exposure']*1000))
                self.printc('Exposure set to {0}'.format(newparams['params/IR Exposure']))
            if newparams['params/IR Gain'] != self.settings['params/IR Gain']:
                self.camera.set(gain=int(newparams['params/IR Gain']))
                self.printc('Gain set to {0}'.format(newparams['params/IR Gain']))
            
            
#            if(newparams['Image Width']!=self.settings['Image Width'] or\
#            newparams['Image Height']!=self.settings['Image Height'] or\
#            newparams['Resolution']!=self.settings['Resolution'] or\
#            newparams['X Return Time']!=self.settings['X Return Time'] or\
#            newparams['Projector Control Pulse Width']!=self.settings['Projector Control Pulse Width']):
#                period = newparams['Image Width'] * newparams['Resolution'] / self.machine_config.AO_SAMPLE_RATE - self.shortest_sample
#                self.params.params.param('Projector Control Phase').items.keys()[0].param.setLimits((-period, period - newparams['Projector Control Pulse Width']))
#                self.params.params.param('Projector Control Pulse Width').items.keys()[0].param.setLimits((self.shortest_sample, period))
#                self.settings=newparams
#
#                if(self.scanning):
#                    self.restart_scan() # Only if new self.waveform needed for scanning (depending on the changed parameterrs)
#                
            self.settings=newparams
        else:
            self.settings=self.params.get_parameter_tree(return_dict=True)
    
    def save_context(self):
        context_stream=utils.object2array(self.settings)
        numpy.save(self.context_filename,context_stream)

    def _init_hardware(self):
        logfile=self.logger.filename.replace('2p', '2p_daq')
        self.waveform_generator=scanner_control.ScannerWaveform(machine_config=self.machine_config)
        self.aio=scanner_control.SyncAnalogIORecorder(self.machine_config.AI_CHANNELS,
                                                                        self.machine_config.AO_CHANNELS,
                                                                        logfile,
                                                                        timeout=1,
                                                                        ai_sample_rate=self.machine_config.AI_SAMPLE_RATE,
                                                                        ao_sample_rate=self.machine_config.AO_SAMPLE_RATE,
                                                                        shutter_port=self.machine_config.SHUTTER_PORT,
                                                                        display_rate=self.machine_config.IMAGE_DISPLAY_RATE)
        self.aio.start()
        self.camera=camera.ThorlabsCameraProcess(self.machine_config.THORLABS_CAMERA_DLL,
                                self.logger.filename.replace('2p', '2p_cam'),
                                self.machine_config.IR_CAMERA_ROI)
        self.camera.start()
        
    def _close_hardware(self):
        self.aio.terminate()
        self.camera.terminate()
    
    def plot(self):
        from pylab import plot, grid, show
        i=0
        t=numpy.arange(self.waveform_x.shape[0]) / float(self.machine_config.AO_SAMPLE_RATE) * 1e3
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
    def prepare_2p(self):
        if self.twop_running:
            return
        pulse_width=self.settings['params/Advanced/Projector Control Pulse Width']*1e-6 if self.settings['params/Advanced/Enable Projector'] else 0
        waveform_x, waveform_y, projector_control, frame_timing, self.boundaries=\
                    self.waveform_generator.generate(self.settings['params/Scan Height'], \
                                                                    self.settings['params/Scan Height'],\
                                                                    self.settings['params/Resolution'],\
                                                                    self.settings['params/Advanced/X Return Time'],\
                                                                    self.settings['params/Advanced/Y Return Time'],\
                                                                    pulse_width,\
                                                                    self.settings['params/Advanced/Projector Control Phase']*1e-6,)
        self.waveform=numpy.array([waveform_x,  waveform_y])
        channels=list(map(int, [self.settings['params/Show Top'], self.settings['params/Show Side']]))
        self.aio.start_(self.waveform,self.filename,{'boundaries': self.boundaries, 'channels':channels})
        self.twop_running=True
        self.statusbar.twop_status.setText('2P Live')
        self.statusbar.twop_status.setStyleSheet('background:red;')
    
    def start_action(self):
        try:
            self.filename=None
            self.prepare_2p()
            self.printc('2p scanning started')
        except:
            self.printc(traceback.format_exc())
        
    def snap_action(self):
        pass
        
    def record_action(self):
        try:
            params={'id': experiment_data.get_id(), 'outfolder': self.machine_config.EXPERIMENT_DATA_PATH}
            self.filename=experiment_data.get_recording_path(self.machine_config,params, '2p')
            self.prepare_2p()
            self.printc('2p recording started, saving data to {0}'.format(self.filename))
        except:
            self.printc(traceback.format_exc())
        return
    
    def scan_frame(self):
        f=self.daq_process.read_ai()
        if hasattr(f,  'dtype'):
            self.frame = f
            if self.settings['Save']:
                self.file.add(f)
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
        print (2)
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
        
        scale = numpy.array([[1.0 / self.settings["IR X Scale"], 0], [0, 1.0 / self.settings["IR Y Scale"]]])
        
        # In the future, scipy.ndimage.geometric_transform might be the best solution instead of these:
        self.ir_image = scipy.ndimage.zoom(self.ir_image, (self.settings["IR X Scale"], self.settings["IR Y Scale"]))
        self.ir_image = scipy.ndimage.rotate(self.ir_image, self.settings["IR Rotation"])
        
        # Put IR on frame (with offset here!) moving overlapping pixels from ir into frame
        # Known issues: bounding box changes size depending on zoom and rotation, image anchor is the lower left corner, not the center of the current view
        self.frame[max(0, self.settings["IR X Offset"]) : min(self.ir_image.shape[0] + self.settings["IR X Offset"], self.frame.shape[0]),
            max(0, self.settings["IR Y Offset"]) : min(self.ir_image.shape[1]  + self.settings["IR Y Offset"], self.frame.shape[1]), 2] = \
            self.ir_image[max(0, -self.settings["IR X Offset"]) : min(self.ir_image.shape[0], self.frame.shape[0] - self.settings["IR X Offset"]),
            max(0, -self.settings["IR Y Offset"]) : min(self.ir_image.shape[1], self.frame.shape[1] - self.settings["IR Y Offset"])]
        
        if(self.z_stacking):
            self.z_stack.append(numpy.rollaxis(numpy.copy(self.frame), 2)) # Changing axis order to: ch, x, y
            self.statusbar.recording_status.setText("Recording Z stack, frame number: " + str(len(self.z_stack)))
        else:
            self.statusbar.recording_status.setText("Scanning... " + str(round(1.0/(time.time() - fps_counter_start), 2)) + " FPS")
        print (3)
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
                self.printc("Socket handler error!")
    
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
        if not self.settings["Show RED channel"]:
            canvas[:, :, 0] = 0
        if not self.settings["Show GREEN channel"]:
            canvas[:, :, 1] = 0
        if not self.settings["Show IR layer"]:
            canvas[:, :, 2] = 0
        return canvas
        
    def generate_image_to_display(self):
        '''
        From raw image data generates merged/scaled/etc image
        '''
        self.img=raw2frame(self.frame, self.binning_factor, self.boundaries, offset = 0)
        self.img2display=numpy.zeros((self.img.shape[0], self.img.shape[1], 3))
        self.img2display[:, :, :2]=self.img
        masked=self.mask_channel(self.img2display)
        masked=numpy.where(masked>self.machine_config.MAX_PMT_VOLTAGE, self.machine_config.MAX_PMT_VOLTAGE, masked)
        masked=numpy.where(masked<0.0, 0.0, masked)
        masked/=self.machine_config.MAX_PMT_VOLTAGE
        return masked
    
    
    
    def read_image(self):
        ir_frame=self.camera.read()
        if ir_frame is not None:
            self.ir_frame=ir_frame
        twop_frame=self.aio.read()
        if twop_frame is not None:
            self.twop_frame=twop_frame
    
    def update_image(self):
        self.ir_filtered=filter_image(self.ir_frame, self.settings['params/Live/IR/Min'], 
                                                        self.settings['params/Live/IR/Max'],
                                                        self.settings['params/Live/IR/Image filters'])*\
                                                        int(self.settings['params/Show IR'])
                                                        
        top_filtered=filter_image(self.twop_frame[:,:,0], self.settings['params/Live/Top/Min'], 
                                                        self.settings['params/Live/Top/Max'],
                                                        self.settings['params/Live/Top/Image filters'])*\
                                                        int(self.settings['params/Show Top'])

        side_filtered=filter_image(self.twop_frame[:,:,1], self.settings['params/Live/Side/Min'], 
                                                        self.settings['params/Live/Side/Max'],
                                                        self.settings['params/Live/Side/Image filters'])*\
                                                        int(self.settings['params/Show Side'])

        kwargs={
                'Offset X':self.settings['params/Infrared-2P overlay/Offset X'], 
                'Offset Y':self.settings['params/Infrared-2P overlay/Offset Y'], 
                'Scale X':self.settings['params/Infrared-2P overlay/Scale X'], 
                'Scale Y':self.settings['params/Infrared-2P overlay/Scale Y'], 
                'Rotation':self.settings['params/Infrared-2P overlay/Rotation'], 
                }
        self.kwargs=kwargs
        twop_filtered=numpy.zeros_like(self.twop_frame)
        twop_filtered[:,:,0]=top_filtered
        twop_filtered[:,:,1]=side_filtered
        self.merged=merge_image(self.ir_filtered, twop_filtered, **kwargs)
        self.image.set_image(self.merged)
    
    def stop_action(self, remote=None):
        if not self.twop_running:
            return
        self.aio.stop()
        self.twop_running=False
        self.printc('2p scanning stopped')
        self.statusbar.twop_status.setText('Ready')
        self.statusbar.twop_status.setStyleSheet('background:gray;')
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
        self.statusbar.info.setText('')
        
    def restart_scan(self):
        self.stop_action()
        self.printc("Restart scan")
        self.record_action()
    
############## REFERENCE IMAGE ###################

    def open_action(self):
        '''
        Open a recording for display
        ''', 
        
    def save_image_action(self):
        '''
        Save current image to reference image widget
        '''
    
    def zoom_in_action(self):
        pass
        
    def zoom_out_action(self):
        pass
    
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
    
    def z_stack_action(self, remote=None):
        raise NotImplementedError('reccord_action and stop_action shall be called for every depth')
        if(self.scanning):
            self.stop_action()
        
        self.z_stacking = True
        self.z_stack = []
        
        self.record_action() # Without statring scan_timer! (self.z_stacking = True) scan_frame is being called 'manually' check out the for loop below!
        preview = numpy.copy(self.frame) # Preview image (self.frame) available right after record_action()
        
        for i in range(self.settings["Z Stack Start"],  self.settings["Z Stack End"],  self.settings["Z Stack Step"]):
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
        self._close_hardware()
        self.close()
        
def merge_image(ir_image, twop_image, **kwargs):
    """
    ir_image: uint16, 2d
    twop_image: float, 0-1 range, height x width x 2
    """
    merged=numpy.zeros((ir_image.shape[0],  ir_image.shape[1], 3))
    #Scale 2p image
    twop_size=numpy.cast['int'](numpy.array(twop_image.shape[:2])*numpy.array([kwargs['Scale X'],kwargs['Scale Y']]))
    twop_size=numpy.append(twop_size, 2)
    twop_resized=skimage.transform.resize(twop_image, twop_size)
    #Extend to IR image
    twop_extended=numpy.zeros((ir_image.shape[0],  ir_image.shape[1], 2))
    twop_extended[:twop_resized.shape[0], :twop_resized.shape[1], :]=twop_resized
    #Shift 2p
    twop_shifted=numpy.zeros_like(twop_extended)
    end_x = twop_extended.shape[0] if kwargs['Offset X']==0 else -kwargs['Offset X']
    end_y = twop_extended.shape[1] if kwargs['Offset Y']==0 else -kwargs['Offset Y']
    twop_shifted[kwargs['Offset X']:, kwargs['Offset Y']:, :]=twop_extended[:end_x,:end_y:, :]
    #Rotate
    if kwargs['Rotation']!=0:
        twop_rotated=scipy.ndimage.rotate(twop_shifted, kwargs['Rotation'], reshape=False)
    else:
        twop_rotated=twop_shifted
    merged[:, :, :2]=twop_rotated*0.5
    merged[:, :, :]+=numpy.stack((ir_image,)*3,axis=-1)*numpy.array([0.5, 0.5, 0.5])
    return merged
    
def filter_image(image, min_, max_, filter):
    if image.dtype==numpy.uint16:
        image_=image/(2**12-1)
    else:
        image_=image
    #Scale input image to min_,max_ range
    scaled=(numpy.clip(image_, min_, max_)-min_)/(max_-min_)
    if filter=='':
        filtered=scaled
    else:
        raise NotImplementedError('')
    return filtered
    
class Test(unittest.TestCase):
    def test_image_merge(self):
        from pylab import plot, imshow, show
        ir_image=numpy.ones((1004, 1004), dtype=numpy.uint16)
        ir_image[300:700,100:800]=0
        twop_image=numpy.ones((200, 200, 2))*0.5
        twop_image[100:,:,0]=0
        twop_image[:100,:,1]=0
        kwargs={
                'Offset X':200, 
                'Offset Y':200, 
                'Scale X':3.0, 
                'Scale Y':3.0,  
                'Rotation':3.0*0,  
                }
        out=merge_image(ir_image, twop_image, **kwargs) 
        repeats=100
        im=[[numpy.random.random((512, 512)), numpy.random.random((100, 100, 2))] for i in range(repeats)]
        t0=time.time()
        for im1, im2 in im:
            out=merge_image(im1, im2, **kwargs)
        print((time.time()-t0)/repeats*1e3)
        
    def test_filter_image(self):
        filtered=filter_image(numpy.random.random((100, 100, 2)), 0.5, 0.7, '')
        self.assertEqual(filtered.min(), 0)
        self.assertEqual(filtered.max(), 1)
        
    def test_debug_merge(self):
        ir_image=numpy.ones((1004, 1004), dtype=numpy.uint16)*30000
        twop_image=numpy.load(r'f:\tmp\2p.npy')
        kwargs={
                'Offset X':100, 
                'Offset Y':200, 
                'Scale X':3.5, 
                'Scale Y':3.5,  
                'Rotation':3.0*0,  
                }
        out=merge_image(ir_image, twop_image, **kwargs) 
if __name__=='__main__':
    unittest.main()
