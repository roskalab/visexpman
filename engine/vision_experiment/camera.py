import os,time, numpy, hdf5io, traceback, multiprocessing
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore

from visexpman.engine.generic import gui,fileop, signal
from visexpman.engine.hardware_interface import camera_interface, daq_instrument
from visexpman.engine.vision_experiment import gui_engine, main_ui,experiment_data
from visexpman.engine.analysis import behavioral_data

class Camera(gui.VisexpmanMainWindow):
    def __init__(self, context):        
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.setWindowIcon(gui.get_icon('behav'))
        self._init_variables()
        self.resize(self.machine_config.GUI_WIDTH, self.machine_config.GUI_HEIGHT)
        if hasattr(self.machine_config, 'GUI_POS_X'):
            self.move(self.machine_config.GUI_POS_X, self.machine_config.GUI_POS_Y)
        self._set_window_title()
        toolbar_buttons = ['record', 'stop', 'convert_folder', 'exit']
            
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')

        #Add dockable widgets
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)        
        self.image = gui.Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        filebrowserroot= os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,self.machine_config.user) if self.machine_config.PLATFORM in ['2p', 'ao_cortical','resonant'] else self.machine_config.EXPERIMENT_DATA_PATH
        self.datafilebrowser = main_ui.DataFileBrowser(self, filebrowserroot, ['behav*.hdf5', 'stim*.hdf5', 'eye*.hdf5',   'data*.hdf5', 'data*.mat','*.mp4'])
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.datafilebrowser, 'Data Files')
        self.main_tab.addTab(self.params, 'Settings')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self.show()
        
        self.update_image_timer=QtCore.QTimer()
        self.update_image_timer.start(1000/self.machine_config.DEFAULT_CAMERA_FRAME_RATE/3)#ms
        self.connect(self.update_image_timer, QtCore.SIGNAL('timeout()'), self.update_image)
        self.parameter_changed()
        self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['Frame Rate'], self.parameters['Exposure time']*1e-3, self.machine_config.CAMERA_IO_PORT)
        self.camerahandler.start()
        
#        if self.machine_config.ENABLE_SYNC=='camera':
#            self.daqqueues = {'command': multiprocessing.Queue(), 
#                                'response': multiprocessing.Queue(), 
#                                'data': multiprocessing.Queue()}
#            limits = {}
#            limits['min_ao_voltage'] = -5.0
#            limits['max_ao_voltage'] = 5.0
#            limits['min_ai_voltage'] = -5.0
#            limits['max_ai_voltage'] = 5.0
#            limits['timeout'] = self.machine_config.DAQ_TIMEOUT
#            self.sync_recorder=daq_instrument.AnalogIOProcess('daq', self.daqqueues, None, ai_channels=self.machine_config.SYNC_RECORDER_CHANNELS,limits=limits)
#            self.sync_recorder.start()
        
        #Set size of widgets
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT*0.4)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()

    def _init_variables(self):
        self.recording=False
        self.track=[]
        if self.machine_config.PLATFORM in ['2p', 'resonant']:
            trigger_value = 'network' 
            params=[]
        elif self.machine_config.PLATFORM in ['behav']:
            trigger_value='ttl pulses'
            params=[
                {'name': 'Show track', 'type': 'bool', 'value': True}, 
                {'name': 'Threshold', 'type': 'int', 'value': 200},
                ]
        else:
            trigger_value='manual'
            params=[]
        self.params_config = [
                {'name': 'Trigger', 'type': 'list', 'values': ['manual', 'network', 'ttl pulses'], 'value': trigger_value},
                {'name': 'Enable trigger', 'type': 'bool', 'value': False}, 
                {'name': 'Frame Rate', 'type': 'float', 'value': 30, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Exposure time', 'type': 'float', 'value': 20, 'siPrefix': True, 'suffix': 'ms'},
                {'name': 'Enable ROI cut', 'type': 'bool', 'value': False},
                {'name': 'ROI x1', 'type': 'int', 'value': 200},
                {'name': 'ROI y1', 'type': 'int', 'value': 200},
                {'name': 'ROI x2', 'type': 'int', 'value': 400},
                {'name': 'ROI y2', 'type': 'int', 'value': 400},
                {'name': 'Channel', 'type': 'int', 'value': 0},
                {'name': 'Show channel only', 'type': 'bool', 'value': False},
                    ]
        self.params_config.extend(params)
        
    def start_recording(self):
        try:
            if self.recording:
                return
            self.recording=True
            self.printc('Start video recording')
            self.statusbar.recording_status.setStyleSheet('background:yellow;')
            self.statusbar.recording_status.setText('Preparing')
            self.camerahandler.stop()
            if self.machine_config.ENABLE_SYNC=='camera':
                self.ai=daq_instrument.SimpleAnalogIn(self.machine_config.SYNC_RECORDER_CHANNELS, self.machine_config.SYNC_RECORDER_SAMPLE_RATE, self.machine_config.MAX_RECORDING_DURATION,  finite=False)
#                d=self.sync_recorder.read_ai()#Empty ai buffer
#                self.sync_recorder.start_daq(ai_sample_rate = self.machine_config.SYNC_RECORDER_SAMPLE_RATE,
#                                ai_record_time=self.machine_config.SYNC_RECORDING_BUFFER_TIME, timeout = 10) 
                msg='Camera&Sync recording'
            else:
                msg='Camera recording'
            self.fn=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, '{1}_{0}.hdf5'.format(experiment_data.get_id(),  self.machine_config.FILENAME_TAG))
            self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['Frame Rate'], self.parameters['Exposure time']*1e-3,  self.machine_config.CAMERA_IO_PORT,  filename=self.fn)
            self.camerahandler.start()
            self.tstart=time.time()
            self.statusbar.recording_status.setStyleSheet('background:red;')
            self.statusbar.recording_status.setText(msg)
            self.track=[]
        except:
            self.printc(traceback.format_exc())
        
    def stop_recording(self):
        try:
            if not self.recording:
                return
            self.printc('Stop video recording')
            self.statusbar.recording_status.setStyleSheet('background:yellow;')
            self.statusbar.recording_status.setText('Busy')
            self.camerahandler.stop()
            if hasattr(self,  'ai'):
                self.sync=self.ai.finish()
#                res=self.sync_recorder.stop_daq()
#                try:
#                    self.sync, n=res
#                except:
#                    raise RuntimeError("daq data cannot be read: {0}".format(res))
#                concatenated=self.sync[0]
#                for i in range(self.sync.shape[0]-1):
#                    concatenated=numpy.concatenate((concatenated,  self.sync[i+1]))
#                self.sync=concatenated
                hdf5io.save_item(self.fn,  'sync',  self.sync)
                hdf5io.save_item(self.fn,  'parameters',  self.parameters)
                hdf5io.save_item(self.fn,  'machine_config',  self.machine_config.todict())
                self.fps_values, fpsmean,  fpsstd=signal.calculate_frame_rate(self.sync[:, self.machine_config.TBEHAV_SYNC_INDEX], self.machine_config.SYNC_RECORDER_SAMPLE_RATE, threshold=2.5)
                self.printc('Measured frame rate is {0:.2f} Hz, std: {1:.2f}, recorded {2} frames'.format(fpsmean, fpsstd,  self.fps_values.shape[0]+1))
            self.printc('Saved to {0}'.format(self.fn))
            self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['Frame Rate'], self.parameters['Exposure time']*1e-3,  self.machine_config.CAMERA_IO_PORT)
            self.camerahandler.start()        
            self.statusbar.recording_status.setStyleSheet('background:gray;')
            self.statusbar.recording_status.setText('Ready')
            self.recording=False
        except:
            self.printc(traceback.format_exc())
        
    def parameter_changed(self):
        self.parameters=self.params.get_parameter_tree(return_dict=True)
        
    def record_action(self):
        self.start_recording()
        
    def stop_action(self):
        self.stop_recording()
            
    def convert_folder_action(self):
        #This is handled by main GUI process, delegating it to gui engine would make progress bar handling more complicated        
        try:
            foldername = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select hdf5 video file folder', self.machine_config.EXPERIMENT_DATA_PATH))
            if os.name=='nt':
                foldername=foldername.replace('/','\\')
            files=fileop.listdir(foldername)
            p=gui.Progressbar(100, 'Conversion progress',  autoclose=True)
            p.show()
            self.printc('Conversion started')
            for f in files:
                if not os.path.isdir(f) and os.path.splitext(f)[1]=='.hdf5' and not os.path.exists(os.path.splitext(f)[0]+'.mat'):
                    print f
                    experiment_data.hdf52mat(f)
                    prog=int((files.index(f)+1)/float(len(files))*100)
                    p.update(prog)
                    print prog
                    time.sleep(100e-3)
            self.printc('{0} folder complete'.format(foldername))
        except:
            self.printc(traceback.format_exc())
    
    def update_image(self):
        try:
            if not self.camerahandler.display_frame.empty():
                frame=self.camerahandler.display_frame.get()
                if self.parameters['Enable ROI cut']:
                    frame=frame[self.parameters['ROI x1']:self.parameters['ROI x2'],self.parameters['ROI y1']:self.parameters['ROI y2']]
                f=numpy.copy(frame)
                if 'Channel' in self.parameters:
                    coo=behavioral_data.extract_mouse_position(frame, self.parameters['Channel'], self.parameters['Threshold'])
                    self.track.append(coo)
                    if coo!=None and not numpy.isnan(coo[0]) and self.recording and numpy.nan != coo[0]:
                        if self.parameters['Show channel only']:
                            for i in range(3):
                                if i!=self.parameters['Channel']:
                                    f[:,:,i]=0
                        if self.parameters['Show track']:
                            for coo in self.track:
                                if not numpy.isnan(coo[0]):
                                    f[int(coo[0]), int(coo[1])]=numpy.array([0,255,0],dtype=f.dtype)
                self.image.set_image(numpy.rot90(numpy.flipud(f)))
                if self.recording:
                    dt=time.time()-self.tstart
                    self.image.plot.setTitle('{0} s'.format(int(dt)))
                    
        except:
            self.printc(traceback.format_exc())
        
    def exit_action(self):
        self.camerahandler.stop()
#        if hasattr(self, 'sync_recorder'):
#            self.sync_recorder.queues['command'].put('terminate')
#            self.sync_recorder.join()
        self.close()
    
