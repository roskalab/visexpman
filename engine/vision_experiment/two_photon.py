from pylab import *
import os,time, numpy, hdf5io, traceback, multiprocessing, serial, unittest, copy
import itertools
import scipy,skimage, tables
try:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
    from visexpman.engine.hardware_interface import scanner_control,camera, stage_control
    from visexpman.engine.vision_experiment import gui_engine, main_ui,experiment_data
except:
    print('Import errors')
    


from visexpman.engine.generic import gui,fileop, signal, utils


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
        
        toolbar_buttons = ['start', 'stop', 'record', 'snap', 'zoom_in', 'zoom_out', 'open', 'save_image', 'z_stack',  'exit']
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
        #self.image.set_image(numpy.random.random((200, 200, 3)))
        self.image.plot.setLabels(bottom='um', left='um')
        
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
        
        self.background_process_timer=QtCore.QTimer()
        self.background_process_timer.start(1000)
        self.background_process_timer.timeout(self.background_process)
        
        self.queues = {'command': multiprocessing.Queue(), 
                            'response': multiprocessing.Queue(), 
                            'data': multiprocessing.Queue()}
        
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
    
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.z_stack_running=False
        
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
                    {'name': 'Scale', 'type': 'float', 'value': 1.0,},
                    {'name': 'Rotation', 'type': 'float', 'value': 0.0,  'siPrefix': False, 'suffix': ' degrees'},                    
                ]}, 
                 {'name': 'Z stack', 'type': 'group', 'expanded' : False, 'children': [
                    {'name': 'Start', 'type': 'int', 'value': 0,  'step': 1, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'End', 'type': 'int', 'value': 0,  'step' : 1, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Step', 'type': 'int', 'value': 1, 'limits': (1, 10), 'step': 1, 'siPrefix': True, 'suffix': 'um'}, 
                    {'name': 'Samples per depth', 'type': 'int', 'value': 1}
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
        if(self.z_stack_running):
            self.printc("Cannot change parameters while Z stacking is running.")
            return
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
        self.stage=stage_control.SutterStage(self.machine_config.STAGE_PORT,  self.machine_config.STAGE_BAUDRATE)
        self.stage_z=self.stage.z
        
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
        self.waveform=numpy.array([waveform_x,  waveform_y, projector_control, frame_timing])
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
        
    def snap_action(self, n):
        self.start_action()
        t0=time.time()
        frames=[]
        while True:
            twop_frame=self.aio.read()
            if twop_frame is not None:
                self.twop_frame=twop_frame
                frames.append(twop_frame)
            if len(frames)==n:
                break
            if (time.time()-t0>3):
                self.printc("No image acquired")
                break
            time.sleep(0.5)
        self.stop_action()
        return frames
        
    def record_action(self):
        try:
            params={'id': experiment_data.get_id(), 'outfolder': self.machine_config.EXPERIMENT_DATA_PATH}
            self.filename=experiment_data.get_recording_path(self.machine_config,params, '2p')
            self.prepare_2p()
            self.printc('2p recording started, saving data to {0}'.format(self.filename))
        except:
            self.printc(traceback.format_exc())
        return
    
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
        
    def read_image(self):
        ir_frame=self.camera.read()
        if ir_frame is not None:
            self.ir_frame=ir_frame
        twop_frame=self.aio.read()
        if twop_frame is not None:
            self.twop_frame=twop_frame
    
    def update_image(self):
        if not hasattr(self, 'twop_frame'):
            self.merged=self.ir_filtered
        else:
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
                    '2p_scale':self.settings['params/Resolution'],
                    '2p_reference_scale':self.machine_config.REFERENCE_2P_RESOLUTION
                    }
            self.kwargs=kwargs
            twop_filtered=numpy.zeros_like(self.twop_frame)
            twop_filtered[:,:,0]=top_filtered
            twop_filtered[:,:,1]=side_filtered
            
            self.twop_filtered=twop_filtered
            self.merged=merge_image(self.ir_filtered, twop_filtered, kwargs)
        self.image.set_image(self.merged)
        if (self.settings['params/Show Top'] or self.settings['params/Show Side']) and not self.settings['params/Show IR']:
            self.imscale=1/self.settings['params/Resolution']#Only 2p image is shown
        else:#IR is also shown
            self.imscale=1/(self.machine_config.REFERENCE_2P_RESOLUTION*self.settings['params/Infrared-2P overlay/Scale X'])
        self.image.set_scale(self.imscale)
    
    def stop_action(self, remote=None):
       
        if self.z_stack_running:
            self.finish_zstack()
        elif not self.twop_running:
            return
        else:
            self.aio.stop()
            self.twop_running=False
            self.printc('2p scanning stopped')
        self.statusbar.twop_status.setText('Ready')
        self.statusbar.twop_status.setStyleSheet('background:gray;')
        
    def restart_scan(self):
        self.stop_action()
        self.printc("Restart scan")
        self.record_action()
    
############## REFERENCE IMAGE ###################

    def open_action(self):
        '''
        Open a recording for display
        '''
        
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
        if self.settings['params/Z Stack/Start']<self.settings['params/Z Stack/End']:
            raise ValueError('Start position must be greater than end position')
        if self.settings['params/Z Stack/Step']<=0:
            raise ValueError('Step value shall be a positive number')
        params={'id': experiment_data.get_id(), 'outfolder': self.machine_config.EXPERIMENT_DATA_PATH}
        self.zstack_filename=experiment_data.get_recording_path(self.machine_config,params, 'zstack')
        s=self.settings['params/Z Stack/Start']
        e=self.settings['params/Z Stack/End']
        st=self.settings['params/Z Stack/Step']
        self.depths=numpy.linspace(s, e, int((s-e)/st+1))
        self.printc(f"Z stack in {', '.join(self.depths)},  saving to {self.zstack_filename}")
        self.depth_index=0
        self.z_stack_running=True
        
    def z_stack_runner(self):
        if self.z_stack_running:
            self.stage.z=self.depths[self.depth_index]
            self.printc(f"Set position to {self.stage.z}")
            data=self.snap_action(self.settings['params/Z Stack/Samples per depth'])
            if self.depth_index==0:
                self.zstackfile=tables.open_file(self.zstack_filename,'w')
                datacompressor = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
                datatype = tables.UInt16Atom(data.shape)
                self.zstack_data_handle=self.zstackfile.create_earray(self.zstackfile.root, 'zstackdata', datatype, (0,),filters=datacompressor)
            else:
                self.zstack_data_handle.append(data[None,:])
            self.depth_index+=1
            if len(self.depths)==self.depth_index:
                self.finish_zstack()
                
    def finish_zstack(self):
        self.printc(f"Finishing z stack")
        atom = tables.Atom.from_dtype(self.depths.dtype)
        depths = self.zstackfile.create_carray(self.zstackfile.root, 'depths', atom, self.depths.shape)
        depths[:] = self.depths
        #Save settings
        self.settings2attr(depths.attr)
        self.z_stack_running=False
        self.zstackfile.close()
        
    def settings2attr(self, ref):
        for k, v in self.settings.items():
            attrn=k.replace('/', '_').replace(' ', '_')
            setattr(ref, attrn, v)
        
    def background_process(self):
        self.socket_handler()
        self.z_stack_runner()
    
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
        
def merge_image(ir_image, twop_image, kwargs):
    """
    ir_image: float 0-1 range
    twop_image: float, 0-1 range, height x width x 2
    kwargs keys:
    Offset X, Y: in um, offset between 2p and Ir image center
    Scale: Ratio between pixel size in um of IR and 2p image at reference resolution
    2p_scale: two photon image scale in um/pixel
    2p_reference_scale: resolution which was used when Scale and Offset X, Y was calibrated
    """
    if (ir_image==0).all():
        merged=numpy.zeros((twop_image.shape[0],  twop_image.shape[1], 3))
        merged[:,:,:2]=twop_image
        return merged
    merged=numpy.zeros((ir_image.shape[0],  ir_image.shape[1], 3))
    #Calculate offset in pixels of IR image
    offset_x=int(kwargs['2p_reference_scale']*kwargs['Offset X']*kwargs['Scale'])
    offset_y=int(kwargs['2p_reference_scale']*kwargs['Offset Y']*kwargs['Scale'])
    #Scale 2p image to the resolution of IR image
    scale=kwargs['2p_reference_scale']*kwargs['Scale']/kwargs['2p_scale']
    twop_size=numpy.cast['int'](numpy.array(twop_image.shape[:2])*scale)
    twop_size=numpy.append(twop_size, 2)
    twop_resized=skimage.transform.resize(twop_image, twop_size)
    #Extend to IR image
    twop_extended=numpy.zeros((ir_image.shape[0],  ir_image.shape[1], 2))
    #Put twop_resized to the center of twop_extended
    default_offset=numpy.cast['int'](numpy.array(twop_extended.shape[:2])/2-numpy.array(twop_resized.shape[:2])/2)
    ir_size_bigger=numpy.array(ir_image.shape)>numpy.array(twop_resized.shape[:2])
    if all(ir_size_bigger):#2p image is smaller than IR
        twop_extended[default_offset[0]:default_offset[0]+twop_resized.shape[0], default_offset[1]:default_offset[1]+twop_resized.shape[1], :]=twop_resized
        cut_2p=False
    elif any(ir_size_bigger) and not all(ir_size_bigger):#Only one dimension of 2p is bigger than IR
        cut_2p=False
        if ir_size_bigger[0]:
            twop_extended[default_offset[0]:-default_offset[0], :, :]=twop_resized[:, -default_offset[1]:default_offset[1], :]
        elif ir_size_bigger[1]:
            twop_extended[:, default_offset[1]:-default_offset[1], :]=twop_resized[-default_offset[0]:default_offset[0], :, :]
    else:
        #At keast one dimension of 2p is bigger than IR
        twop_extended=twop_resized
        cut_2p=True
    #Rotate
    if kwargs['Rotation']!=0:
        twop_rotated=scipy.ndimage.rotate(twop_extended, kwargs['Rotation'], reshape=False)
    else:
        twop_rotated=twop_extended
    #Shift 2p
    twop_shifted=numpy.roll(twop_rotated,(offset_x,offset_y),axis=(0,1))
    #Handle edges: rotated image is rolled and returned pixels shall be eliminated
    if any(ir_size_bigger) and not all(ir_size_bigger):
        if offset_x>0:
            twop_shifted[:offset_x, :, :]=0
        elif offset_x<0:
            twop_shifted[offset_x:, :, :]=0
        if offset_y>0:
            twop_shifted[:, :offset_y, :]=0
        elif offset_y<0:
            twop_shifted[:, offset_y:, :]=0
    else:
        if twop_resized.shape[1]/2+offset_y> twop_extended.shape[1]/2:
            edge=int(twop_resized.shape[1]/2+offset_y-twop_extended.shape[1]/2)
            twop_shifted[:,:edge,:]=0
        if twop_resized.shape[1]/2+offset_y<0:
            edge=int(abs(twop_resized.shape[1]/2+offset_y))
            twop_shifted[:,-edge:,:]=0
        if twop_resized.shape[0]/2+offset_x> twop_extended.shape[0]/2:
            edge=int(twop_resized.shape[0]/2+offset_x- twop_extended.shape[0]/2)
            twop_shifted[:edge,:,:]=0
        if twop_resized.shape[0]/2+offset_x<0:
            edge=int(abs(twop_resized.shape[0]/2+offset_x))
            twop_shifted[-edge:,:,:]=0
    if cut_2p:
        merged[:, :, :2]=twop_shifted[-default_offset[0]:merged.shape[0]-default_offset[0],-default_offset[1]:merged.shape[1]-default_offset[1],:]*0.5
    else:
        merged[:, :, :2]=twop_shifted*0.5
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
    @unittest.skip('')
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
                'Scale':3.0, 
                'Rotation':3.0*0,
                '2p_scale':2,  
                '2p_reference_scale':2
                }
        out=merge_image(ir_image, twop_image, kwargs) 
        repeats=100
        im=[[numpy.random.random((512, 512)), numpy.random.random((100, 100, 2))] for i in range(repeats)]
        t0=time.time()
        for im1, im2 in im:
            out=merge_image(im1, im2, kwargs)
        print((time.time()-t0)/repeats*1e3)
    
    @unittest.skip('')    
    def test_2p_bigger_than_ir(self):
        from pylab import imshow,figure,show
        ir_image=numpy.random.random((512, 512))
        twop1=numpy.random.random((400, 600, 2))
        kwargs={
                'Offset X':55, 
                'Offset Y':-10, 
                'Scale':1.5, 
                'Rotation':-2.0,
                '2p_scale':1.5,  
                '2p_reference_scale':2
                }
        out1=merge_image(ir_image, twop1, kwargs) 
        out2=merge_image(ir_image, numpy.random.random((100, 100, 2)), kwargs) 
#        imshow(out1*0.5+out2*0.5);show()

    @unittest.skip('')    
    def test_ir_disabled(self):
        ir_image=numpy.zeros((512, 512))
        twop1=numpy.random.random((600, 600, 2))
        kwargs={
                'Offset X':55, 
                'Offset Y':-10, 
                'Scale':1.5, 
                'Rotation':-2.0,
                '2p_scale':1.5,  
                '2p_reference_scale':2
                }
        out1=merge_image(ir_image, twop1, kwargs) 
        self.assertEqual(out1.shape[:2],twop1.shape[:2])
        self.assertNotEqual(ir_image.shape[:2],twop1.shape[:2])
        
    def test_filter_image(self):
        filtered=filter_image(numpy.random.random((100, 100, 2)), 0.5, 0.7, '')
        self.assertEqual(filtered.min(), 0)
        self.assertEqual(filtered.max(), 1)
        
                
    def test_merge_image_full_parameter_space(self):
        ir_image_size=numpy.array([504, 504])
        ir_values=[0, 1]
        twop_ref_resolution=2
        twop_resolutions=[0.5, 1, 1.5,2, 2.5]
        ir2p_scales=[2.5, 0.5,1]
        rotations=[0, -2,1,2, 10]
        twop_sizes=[[50, 50],[70, 70],[100, 100],[300, 300],[50, 100],[100, 70],[300, 100],[100, 300],[600, 300],[300, 600]]
        offsets=[[0,0],[55,0],[-55,0],[0,55],[0,-55],[60,60], [5, 10]]
        for ir_value, ir2p_scale, twop_size, offset in itertools.product(ir_values, ir2p_scales, twop_sizes, offsets):
            ir_image=numpy.ones(ir_image_size, dtype=numpy.float)*ir_value
            ox, oy=offset
            kwargs={'Offset X': ox, 'Offset Y': oy, 'Scale':ir2p_scale, \
                                'Rotation':0, '2p_scale': 2.0, '2p_reference_scale': twop_ref_resolution}
            
            #Check if offset puts image (partly) off from ir image
            #Ir image resolution: twop_ref_resolution*ir2p_scale
            #Ir image size: ir_image_size/(twop_ref_resolution*ir2p_scale)
            ir_image_size_um=ir_image_size/(twop_ref_resolution*ir2p_scale)
            twop_off= any(numpy.array(twop_size)/2+abs(numpy.array(offset))>ir_image_size_um/2)            
            out_rot=[]
            for rotation in rotations:
                twop_resolution=1
                twop_image=0.5*numpy.ones((int(twop_size[0]*twop_resolution),  int(twop_size[1]*twop_resolution),2), dtype=numpy.float)
                kwargs_rot=copy.deepcopy(kwargs)
                kwargs_rot['2p_scale']=twop_resolution
                kwargs_rot['Rotation']=rotation
                try:
                    out_rot.append(merge_image(ir_image, twop_image, kwargs_rot))
                except:
                    pass
            if ir_value==0:
                self.assertTrue(all(out_rot[-1][:,:,:2]==twop_image))
                continue
            #compare rotations, check if center of all rotations have the same cente
            centers=numpy.array([[numpy.where(ii>0.51)[0].mean(), numpy.where(ii>0.51)[1].mean()] for ii in out_rot])
            if not twop_off:
                #All centers are the same
                numpy.testing.assert_almost_equal(numpy.diff(centers,axis=0),0,1)
            out_res=[]
            for twop_resolution in twop_resolutions:
                rotation=0
                twop_image=0.5*numpy.ones((int(twop_size[0]*twop_resolution),  int(twop_size[1]*twop_resolution),2), dtype=numpy.float)
                kwargs_res=copy.deepcopy(kwargs)
                kwargs_res['2p_scale']=twop_resolution
                kwargs_res['Rotation']=rotation
                out_res.append(merge_image(ir_image, twop_image, kwargs_res))
            #Compare resolutions, all images shall be the same
            for i in range(1,  len(out_res)):
                numpy.testing.assert_almost_equal(out_res[0], out_res[i])
            #Check if 2p channels are identical
            numpy.testing.assert_almost_equal(out_res[0][:,:,0],out_res[0][:,:,0])
            if not twop_off:
                #Check image size for out_res[2] where 2p resolution is 1.5 pixel /um
                x,y=numpy.where(out_res[-1][:,:,0]>0.51)
                size_pixel=numpy.array([x.max()-x.min(), y.max()-y.min()])
                expected_size=numpy.array(twop_size)/ir_image_size_um*ir_image_size
                numpy.testing.assert_almost_equal(size_pixel, expected_size, -0.1)
            #Check if shifted center has the 2p pixel values
            offset_pixel=numpy.cast['int']((ir_image_size_um/2+numpy.array(offset))*(twop_ref_resolution*ir2p_scale))
            max_center=ir_image_size_um/2
            twop_center=abs(numpy.array(offset))
            center_off=any(max_center<twop_center)
            if not center_off:
                center_pixel=out_res[-1][offset_pixel[0],offset_pixel[1],:]
                numpy.testing.assert_equal(numpy.array([0.75, 0.75, 0.5 ]), center_pixel)

            

if __name__=='__main__':
    unittest.main()
