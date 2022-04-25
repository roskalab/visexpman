from pylab import *
import pyqtgraph
import os,time, numpy, hdf5io, traceback, multiprocessing, serial, unittest, copy
import itertools
import scipy,skimage, tables
import skimage.exposure
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
        self.setGeometry(self.machine_config.GUI_POSITION[0], self.machine_config.GUI_POSITION[1], self.machine_config.GUI_WIDTH, self.machine_config.GUI_HEIGHT)
        self._set_window_title()
        
        toolbar_buttons = ['start', 'stop', 'record', 'snap', 'select_data_folder', 'zoom_in', 'zoom_out', 'open', 'save_image', 'z_stack', 'read_z', 'set_origin', 'process','exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        
        self.statusbar=self.statusBar()
        self.statusbar.progressbar=QtGui.QProgressBar(self)
        self.statusbar.progressbar.setTextVisible(False)
        self.statusbar.addPermanentWidget(self.statusbar.progressbar)
        self.statusbar.info=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.info)
        self.statusbar.ircamera_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.ircamera_status)
        self.statusbar.twop_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.twop_status)
        
        self.debug = gui.Debug(self)
        
        self.main_tab = QtGui.QTabWidget(self)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab.addTab(self.params, 'Settings')
        
        self.video_player = QtGui.QWidget()
        self.saved_image = gui.Image(self)
        self.plot=gui.Plot(self)
        self.plot.plot.setLabels(left='PMT Voltage [V]')
        
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
        self.main_tab.addTab(self.plot, 'Traces')
        self.main_tab.setFixedWidth(self.machine_config.GUI_WIDTH*0.4)
        self.main_tab.setFixedHeight(self.machine_config.GUI_WIDTH*0.4)
        
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        
        self.main_tab.setMinimumHeight(self.machine_config.GUI_HEIGHT * 0.5)
        self.debug.setMaximumHeight(self.machine_config.GUI_HEIGHT * 0.3)
        
        self.create_image_widget(dock=True)
        
        self.saved_image.plot.setLabels(bottom='um', left='um')
        self.saved_image.setMinimumWidth(self.machine_config.GUI_WIDTH * 0.4)                
        self.saved_image.setMinimumHeight(self.machine_config.GUI_WIDTH * 0.4)                
        
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        if os.path.exists(self.context_filename):
            try:
                context_stream = numpy.load(self.context_filename)
                self.settings = utils.array2object(context_stream)
            except:#Context file was probably broken
                self.parameter_changed()
        else:
            self.parameter_changed()
        if self.settings['params/Live IR']:
            self.printc('Autostart IR camera')
            self.camera.start_()
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
        self.background_process_timer.timeout.connect(self.background_process)
        
        self.queues = {'command': multiprocessing.Queue(), 
                            'response': multiprocessing.Queue(), 
                            'data': multiprocessing.Queue()}
        
        self.printc(f'pid: {os.getpid()}')
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def create_image_widget(self, dock):
        self.image = gui.Image(self)
        self.image.setMinimumWidth(self.machine_config.GUI_WIDTH * 0.4)                
        self.image.setMinimumHeight(self.machine_config.GUI_WIDTH * 0.4)                
        #Shrink image inside widget a bit
        #self.image.set_image(numpy.random.random((200, 200, 3)))
        self.image.plot.setLabels(bottom='um', left='um')
        
        
        self.im_container = QtGui.QWidget()
        l = QtGui.QGridLayout()
        self.im_container.setLayout(l)
        l.setSpacing(0)
        self.histogram=pyqtgraph.HistogramLUTWidget()
        self.histogram.setImageItem(self.image.img)
        self.histogram.setMaximumWidth(100)
        self.histogram.item.setLevels(0, 1)
        l.addWidget(self.histogram, 0, 1)
        l.addWidget(self.image, 0, 0)
        if dock:
            self.imgdock=self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.im_container)
        
    
    def _init_variables(self):
        params=[]
        
        self.scanning = False
        self.z_stack_running=False
        self.frame_counter=0
        # 3D numpy arrays, format: (X, Y, CH)
        self.ir_frame = numpy.zeros((500,500))
        self.twop_frame = numpy.zeros((100,100,2))
        
        # 4D numpy arrays, format: (t, X, Y, CH)
        self.z_stack = None
        
        self.shortest_sample = 1.0 / self.machine_config.AO_SAMPLE_RATE
        
        image_filters=['', 'autoscale', 'gamma', 'mean', 'MIP', 'median',  'histogram equalization']
        file_formats=['.mat',  '.hdf5', '.tiff']
        
#        minmax_group=[{'name': 'Min', 'type': 'float', 'value': 0.0,},
#                                    {'name': 'Max', 'type': 'float', 'value': 1.0,}, 
#                                    {'name': 'Image filters', 'type': 'list', 'value': '',  'values': image_filters},]
                                    
        channels_group=[{'name': 'Top Image filters', 'type': 'list', 'value': '',  'values': image_filters}, 
                                {'name': 'Side Image filters', 'type': 'list', 'value': '',  'values': image_filters}, 
                                {'name': 'IR Image filters', 'type': 'list', 'value': '',  'values': image_filters}, 
                                ]
        
        self.params_config = [
                {'name': 'Name', 'type': 'str', 'value': ''},
                {'name': 'Resolution', 'type': 'float', 'value': 1.0, 'limits': (0.5, 8), 'step' : 0.1, 'siPrefix': False, 'suffix': ' pixel/um'},
                {'name': 'Scan Width', 'type': 'float', 'value': 100, 'limits': (30, 500), 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Scan Height', 'type': 'float', 'value': 100, 'limits': (30, 500), 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Averaging samples', 'type': 'float', 'value': 1, 'limits': (0, 1000),  'decimals': 6},
                {'name': 'Live IR', 'type': 'bool', 'value': False},
                {'name': 'IR Exposure', 'type': 'float', 'value': 50, 'limits': (1, 1000), 'siPrefix': True, 'suffix': 'ms',  'decimals': 6},
                {'name': 'IR Gain', 'type': 'float', 'value': 1, 'limits': (0, 1000),  'decimals': 6},
                {'name': 'IR Zoom', 'type': 'list', 'value': '1x', 'values': ['1x', '2x', '3x','6x']},
                {'name': 'Show Top', 'type': 'bool', 'value': True},
                {'name': 'Show Side', 'type': 'bool', 'value': True},
                {'name': 'Show IR', 'type': 'bool', 'value': True},
                {'name': 'Show Grid', 'type': 'bool', 'value': False},
                {'name': 'Live', 'type': 'group', 'expanded' : False, 'children': channels_group}, 
                {'name': 'Saved', 'type': 'group', 'expanded' : False, 'children': channels_group}, 
                {'name': 'Infrared-2P overlay', 'type': 'group',  'expanded' : False, 'children': [
                    {'name': 'Offset X', 'type': 'float', 'value': 0,  'siPrefix': False, 'suffix': ' um', 'decimals': 6},
                    {'name': 'Offset Y', 'type': 'float', 'value': 0,  'siPrefix': False, 'suffix': ' um', 'decimals': 6},
                    {'name': 'Scale', 'type': 'float', 'value': 1.0,},
                    {'name': 'Rotation', 'type': 'float', 'value': 0.0,  'siPrefix': False, 'suffix': ' degrees'},                    
                ]}, 
                 {'name': 'Z Stack', 'type': 'group', 'expanded' : False, 'children': [
                    {'name': 'Start', 'type': 'float', 'value': 0, 'siPrefix': False, 'suffix': 'usteps', 'decimals': 6},
                    {'name': 'End', 'type': 'float', 'value': 0,  'siPrefix': False, 'suffix': 'usteps', 'decimals': 6},
                    {'name': 'Step', 'type': 'float', 'value': 1, 'siPrefix': False, 'suffix': 'usteps', 'decimals': 6}, 
                    {'name': 'Samples per depth', 'type': 'int', 'value': 1},
                    {'name': 'File Format', 'type': 'list', 'value': '.hdf5',  'values': file_formats},
                ]}, 
                {'name': 'Advanced', 'type': 'group', 'expanded' : False, 'children': [
                    {'name': 'Enable Projector', 'type': 'bool', 'value': True},
                    {'name': 'Projector Control Pulse Width', 'type': 'float', 'value': 10*self.shortest_sample*1e6, 'step': self.shortest_sample*1e6, 'siPrefix': False, 'suffix': ' us'}, 
                    {'name': 'Projector Control Phase', 'type': 'float', 'value': 0, 'step': self.shortest_sample*1e6, 'siPrefix': False, 'suffix': ' us'},
                    {'name': 'X Return Time', 'type': 'float', 'value': 20,  'suffix': ' %'},
                    {'name': 'Y Return Time', 'type': 'float', 'value': 2,  'suffix': ' lines'},
                    {'name': 'File Format', 'type': 'list', 'value': '.hdf5',  'values': file_formats},
                    {'name': '2p Shift', 'type': 'int', 'value': 35,  'suffix': ' samples'},
                    {'name': 'Enable scanners', 'type': 'list', 'value': 'both',  'values': ['both', 'X', 'Y', 'None']},
                    {'name': 'X scanner voltage', 'type': 'float', 'value': 0,  'suffix': ' V'},
                    {'name': 'Y scanner voltage', 'type': 'float', 'value': 0,  'suffix': ' V'},
                ]}, 
                {'name': 'Time lapse', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Enable', 'type': 'bool', 'value': False},
                    {'name': 'Interval', 'type': 'float', 'value': 300,  'suffix': ' s','decimals': 6},
                    #{'name': 'N frames', 'type': 'float', 'value': 1},
                ]}, 
            ]
        self.params_config.extend(params)
        self.twop_running=False
        self.camera_running=False
        self.fkwargs={'gamma':1.5}
        self.update_image_enable=True
        self.image_update_in_progress=False
        self.data_folder=self.machine_config.EXPERIMENT_DATA_PATH
        self.nframes_recording_running=False
    
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
            elif newparams['params/IR Gain'] != self.settings['params/IR Gain']:
                self.camera.set(gain=int(newparams['params/IR Gain']))
                self.printc('Gain set to {0}'.format(newparams['params/IR Gain']))
            elif newparams['params/Time lapse/Enable'] != self.settings['params/Time lapse/Enable']:
                if newparams['params/Time lapse/Enable']:
                    if len(os.listdir(self.data_folder))>0:
                        QtGui.QMessageBox.question(self, 'Warning', f'{self.data_folder} is not empty! It is recommended to start saving timelapse to an empty folder!', QtGui.QMessageBox.Ok)
                    else:
                        QtGui.QMessageBox.question(self, 'Warning', 'Make sure that computer is rebooted before a long recording!', QtGui.QMessageBox.Ok)
                        
                    self.statusbar.twop_status.setText('2P time lapse')
                    self.last_scan=time.time()-self.settings['params/Time lapse/Interval']
                    self.statusbar.twop_status.setStyleSheet('background:red;')
                else:
                    self.statusbar.twop_status.setText('Ready')
                    self.statusbar.twop_status.setStyleSheet('background:gray;')
            #2p image size changed
            elif newparams['params/Scan Width']!=self.settings['params/Scan Width'] or\
                newparams['params/Scan Height']!=self.settings['params/Scan Height'] or\
                newparams['params/Resolution']!=self.settings['params/Resolution']:
                    self.printc("2p img settings changed")
            
                    
            #IR Zoom
            if 'params/IR Zoom' in self.settings and self.settings['params/IR Zoom']!=newparams['params/IR Zoom']:
                if newparams['params/IR Zoom']=='1x':
                    self.camera.set_fov(6,[0,0,2160,2160])
                elif newparams['params/IR Zoom']=='2x':
                    self.camera.set_fov(3,[1080-540,1080-540,1080+540,1080+540]) 
                elif newparams['params/IR Zoom']=='3x':
                    self.camera.set_fov(2,[1080-360,1080-360,1080+360,1080+360]) 
                elif newparams['params/IR Zoom']=='6x':
                    self.camera.set_fov(1,[1080-180,1080-180,1080+180,1080+180]) 
#                self.update_image()
#                self.image.plot.autoRange()
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
        #Clear time lapse enable
        values, paths, refs=self.params.get_parameter_tree()
        param_index=[i for i in range(len(paths)) if 'Enable' in paths[i] and 'Time lapse' in paths[i]][0]
        refs[param_index].setValue(False)
        
        context_stream=utils.object2array(self.settings)
        numpy.save(self.context_filename,context_stream)

    def _init_hardware(self):
        self.daq_logfile=self.logger.filename.replace('2p', '2p_daq')
        self.waveform_generator=scanner_control.ScannerWaveform(machine_config=self.machine_config)
        if self.machine_config.STAGE_IN_SCANNER_PROCESS:
            self.aio=scanner_control.SyncAnalogIORecorder(self.machine_config.AI_CHANNELS,
                                                                        self.machine_config.AO_CHANNELS,
                                                                        self.daq_logfile,
                                                                        timeout=self.machine_config.DAQ_TIMEOUT,
                                                                        ai_sample_rate=self.machine_config.AI_SAMPLE_RATE,
                                                                        ao_sample_rate=self.machine_config.AO_SAMPLE_RATE,
                                                                        shutter_port=self.machine_config.SHUTTER_PORT, 
                                                                        stage_port=self.machine_config.STAGE_PORT, 
                                                                        stage_baudrate=self.machine_config.STAGE_BAUDRATE)
        else:
            self.aio=scanner_control.SyncAnalogIORecorder(self.machine_config.AI_CHANNELS,
                                                                        self.machine_config.AO_CHANNELS,
                                                                        self.daq_logfile,
                                                                        timeout=self.machine_config.DAQ_TIMEOUT,
                                                                        ai_sample_rate=self.machine_config.AI_SAMPLE_RATE,
                                                                        ao_sample_rate=self.machine_config.AO_SAMPLE_RATE, 
                                                                        shutter_port=self.machine_config.SHUTTER_PORT)
        self.aio.start()
        self.cam_logfile=self.logger.filename.replace('2p', '2p_cam')
        self.camera=camera.ThorlabsCameraProcess(self.machine_config.THORLABS_CAMERA_DLL,
                                self.cam_logfile,
                                self.machine_config.IR_CAMERA_ROI)
        self.camera.start()
        if not self.machine_config.STAGE_IN_SCANNER_PROCESS:
            try:
                self.stage=stage_control.SutterStage(self.machine_config.STAGE_PORT,  self.machine_config.STAGE_BAUDRATE)
                self.stage_z=self.stage.z
            except OSError:
                print('No Stage')
        
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
        
    def plot_raw(self):
        if not self.aio.queues['raw'].empty():
            d=self.aio.queues['raw'].get()
            t=numpy.arange(d.shape[1])/self.machine_config.AI_SAMPLE_RATE
            y=[d[0],d[1]]
            x=[t,t]
            self.p=gui.Plot(None)
            self.p.setGeometry(100, 100, 500, 500)
            self.p.update_curves(x, y,colors=[(255, 128, 0),  (0, 255, 0),  (0, 0, 255),  (255, 0, 0)])
            self.p.show()
    
######### Two Photon ###########
    def get_fps(self):
        waveform_x, waveform_y, projector_control, frame_timing, self.boundaries=\
                    self.waveform_generator.generate(int(self.settings['params/Scan Height']), \
                                                                    int(self.settings['params/Scan Width']),\
                                                                    self.settings['params/Resolution'],\
                                                                    self.settings['params/Advanced/X Return Time'],\
                                                                    self.settings['params/Advanced/Y Return Time'],\
                                                                    0,\
                                                                    self.settings['params/Advanced/Projector Control Phase']*1e-6,)
        fps=round(self.machine_config.AO_SAMPLE_RATE/waveform_x.shape[0],1)
        return fps


    def prepare_2p(self, nframes=None, zvalues=None):
        t0=time.time()
        print(0)
        if self.twop_running:
            return
        pulse_width=self.settings['params/Advanced/Projector Control Pulse Width']*1e-6 if self.settings['params/Advanced/Enable Projector'] else 0
        waveform_x, waveform_y, projector_control, frame_timing, self.boundaries=\
                    self.waveform_generator.generate(int(self.settings['params/Scan Height']), \
                                                                    int(self.settings['params/Scan Width']),\
                                                                    self.settings['params/Resolution'],\
                                                                    self.settings['params/Advanced/X Return Time'],\
                                                                    self.settings['params/Advanced/Y Return Time'],\
                                                                    pulse_width,\
                                                                    self.settings['params/Advanced/Projector Control Phase']*1e-6,)
        self.waveform_x_orig=waveform_x.copy()
        waveform_x, self.boundaries=self.waveform_generator.generate_smooth(int(self.settings['params/Scan Height']), \
                                                                                        int(self.settings['params/Scan Width']), \
                                                                                        self.settings['params/Resolution'],\
                                                                                        self.settings['params/Advanced/X Return Time'],\
                                                                                        self.settings['params/Advanced/Y Return Time'])
        if self.settings['params/Advanced/Enable scanners']=='X':
            waveform_y*=0
            waveform_y+=self.settings['params/Advanced/Y scanner voltage']
        elif self.settings['params/Advanced/Enable scanners']=='Y':
            waveform_x*=0
            waveform_x+=self.settings['params/Advanced/X scanner voltage']
        elif self.settings['params/Advanced/Enable scanners']=='None':
            waveform_x=waveform_x*0+self.settings['params/Advanced/X scanner voltage']
            waveform_y=waveform_y*0+self.settings['params/Advanced/Y scanner voltage']
            
        self.waveform=numpy.array([waveform_x, waveform_y, projector_control, frame_timing])
        self.dwell_time=(1000/self.machine_config.AI_SAMPLE_RATE)/numpy.diff(self.waveform[0, self.boundaries[0]:self.boundaries[1]]).mean()
        
        channels=list(map(int, [self.settings['params/Show Top'], self.settings['params/Show Side']]))
        if nframes==0 or nframes is None:
            nf=None
        else:
            nf=nframes+scanner_control.NFRAMES_SKIP_AT_SCANNING_START
        self.aio.start_(self.waveform,self.filename,{'boundaries': self.boundaries, 'channels':channels,'metadata': self.format_settings()},\
                        offset=self.settings['params/Advanced/2p Shift'], \
                        nframes=nf, zvalues=zvalues)
        self.twop_running=True
        
        if not self.settings['params/Time lapse/Enable']:
            self.statusbar.twop_status.setText('2P')
            self.statusbar.twop_status.setStyleSheet('background:red;')
        t1=time.time()
        print(1)
        fps=round(self.machine_config.AO_SAMPLE_RATE/self.waveform.shape[1],1)
        if not self.settings['params/Time lapse/Enable']:
            self.printc(f'2p frame rate {fps} Hz,  dwell time: {self.dwell_time} ms/V')
        frq_xscan=(utils.roundint(self.settings['params/Scan Height'] * self.settings['params/Resolution'])+self.settings['params/Advanced/Y Return Time'])*fps
        t2=time.time()
        print(2)
        if not self.settings['params/Time lapse/Enable']:
            self.printc(f'X scanner frequency: {frq_xscan} Hz')
        self.twop_fps=fps
        self.intensities=[]
        self.frame_counter=0
        t3=time.time()
        print(3)
        self.printc(f'Debug: {t3-t2},  {t2-t1},  {t1-t0}')
        
    def test(self):
        zvalues=numpy.concatenate((numpy.zeros(30), numpy.ones(30)*1000))
        self.record_action(zvalues=zvalues)
        
    def testzstep(self, step):
        if abs(step)>10000: return
        zvalues=numpy.concatenate((numpy.zeros(30), numpy.ones(30)*step))
        self.record_action(zvalues=zvalues)
        
    def calcztransient(self):
        h=tables.open_file(self.filename,'r')
        data=h.root.twopdata.read()[:-1, :, :, 0]
        zvalues=h.root.twopdata.attrs.zvalues
        from pylab import plot, show
        img=data.std(axis=1).std(axis=1)
        img=img/img.max()
        t=numpy.arange(img.shape[0])/self.twop_fps
        h.close()
        plot(t, zvalues/zvalues.max());plot(t, img);show()
        
    def timelapse_handler(self):
        try:
            if self.settings['params/Time lapse/Enable']:
                now=time.time()
                if not hasattr(self,  'last_scan'):
                    self.last_scan=now-self.settings['params/Time lapse/Interval']#Ensure that z stack is triggered at the very beginning of the timelapse
                dt=now-self.last_scan
                if not hasattr(self,'dtct'):
                    self.dtct=0
                if self.dtct%100==0:
                    self.printc(f'Time left since last z stack trigger: {round(dt)} s')
                self.dtct+=1
                if dt>3600 and self.twop_running:
                    self.printc(f'2p timeout {dt}, {self.twop_running}')
                    self.stop_action()
                self.parameter_changed()
                if (dt==0 or dt>self.settings['params/Time lapse/Interval']) and not self.twop_running:
                    import psutil
                    self.printc(f'Debug: {psutil.virtual_memory().percent}% memory usage')
                    self.z_stack_action()
                    self.last_scan=now
                    self.parameter_changed()
        except:
            self.printc('Error happened during time lapse:', popup_error=False)
            self.printc(traceback.format_exc(), popup_error=False)
            #Try to stop imaging
            self.stop_action()
                
    
    def start_action(self, nframes=None):
        try:
            if self.twop_running:
                self.stop_action()
            self.filename=None
            self.prepare_2p(nframes=nframes)
            self.printc('2p scanning started')
            self.intensities=[]
            if nframes is not None:
                self.nframes_recording_running=True
        except:
            self.printc(traceback.format_exc())
        
    def snap_action(self, dummy,nframes=scanner_control.NFRAMES_SKIP_AT_SCANNING_START+1):
        self.start_action(nframes=nframes)
        t0=time.time()
        frames=[]
        while True:
            twop_frame=self.aio.read()
            QtCore.QCoreApplication.instance().processEvents()
            if twop_frame is not None:
                self.twop_frame=twop_frame
                frames.append(twop_frame)
            if len(frames)==nframes:
                break
            if (time.time()-t0>5):
                self.printc("No image acquired")
                break
            time.sleep(0.5)
        self.stop_action(snapshot=True)
        return numpy.array(frames)
        
    def record_action(self, nframes=None, zvalues=None):
        try:
            tag='2p_'+self.settings['params/Name']
            if self.twop_running:
                self.stop_action()
            params={'id': experiment_data.get_id(), 'outfolder': self.machine_config.EXPERIMENT_DATA_PATH}
            self.filename=experiment_data.get_recording_path(self.machine_config,params, prefix=tag)
            self.filename=os.path.join(self.data_folder, os.path.basename(self.filename))
            if self.filename is  None:
                raise ValueError()
            self.prepare_2p(nframes=nframes, zvalues=zvalues)
            self.printc('2p recording started, saving data to {0}'.format(self.filename))
        except:
            self.printc(traceback.format_exc())
        return
        
    def read_last_recording(self):
        import hdf5io
        self.rdata=hdf5io.read_item(self.filename, 'twopdata')
        self.rdata=self.rdata/6553.5
        self.rdata=self.rdata[:, :, :, 1]
        
    
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
        t0=time.time()
        try:
            now=time.time()
            ir_frame=self.camera.read()
            if ir_frame is not None:
                if hasattr(self, 'tirlast'):
                    self.irframerate=1/(now-self.tirlast)
                self.ir_frame=ir_frame
                self.ir_frame=numpy.fliplr(self.ir_frame)
                self.tirlast=now
            twop_frame=self.aio.read()
            rawimage=self.aio.read_rawimage()
            if rawimage is not None:
                rawimage=numpy.rot90(rawimage)
                self.rawimage=rawimage
                index=[]
                if self.settings['params/Show Top']:
                    index.append(0)
                if self.settings['params/Show Side']:
                    index.append(1)
                if len(index)==0 or len(index)==2:
                    index=[1]
                index=numpy.array(index)
                self.rawimage=self.rawimage[:, :, index]
                if len(self.image.rois)==0:
                    intensity=self.rawimage.mean()
                else:
                    sx=utils.roundint(self.image.rois[0].x()/self.imscale)
                    sy=utils.roundint(self.image.rois[0].y()/self.imscale)
                    ex=sx+utils.roundint(self.image.rois[0].size().x()/self.imscale)
                    ey=sy+utils.roundint(self.image.rois[0].size().y()/self.imscale)
                    self.co=self.rawimage[sx:ex, sy:ey]
                    print(self.rawimage[sx:ex, sy:ey].shape)
                    intensity=self.rawimage[sx:ex, sy:ey].mean()
                    
                self.intensities.append(intensity)
                
#            print(twop_frame)
            if twop_frame is not None:
                twop_frame=numpy.rot90(twop_frame)
                self.twop_frame=twop_frame
                self.frame_counter+=1
        except:
            if not hasattr(self, 'read_image_error_shown'):
                self.printc(traceback.format_exc())
                self.read_image_error_shown=True
        dt=time.time()-t0
        if not hasattr(self, 'ridt'):
            self.ridt=[]
        self.ridt.append(dt)
        self.ridt=self.ridt[-10:]
        
    def calculate_actual_zoom(self):
        fov=self.image.plot.viewRange()
        self.merged.shape
        self.imscale
        actual_zoom=self.imscale*numpy.array(self.merged.shape[:2])/numpy.diff(numpy.array(self.image.plot.viewRange()),axis=1)[:,0]
#        if actual_zoom[0]!=actual_zoom[1]:
#            raise NotImplementedError()
        self.actual_zoom=actual_zoom[0]
        return actual_zoom[0]
        
    def read_2p_zoom_range(self):
        if len(self.image.rois)>0 and (self.settings['params/Show Top'] or self.settings['params/Show Side']) and not self.settings['params/Show IR']:
            self.image.rois[0].size()#TODO: how to handle non centered roi?
            self.image.rois[0].x()
            self.image.rois[0].y()#All these values are in um
            
    def popup_image_widget(self):
        '''
        If image widget's postion changes, its size is increased to the main GUI's size
        '''
        if not hasattr(self, 'default_img_pos'):
            self.default_img_pos=[self.imgdock.geometry().x(),  self.imgdock.geometry().y()]
            self.popup_state=False
        gref=[self.imgdock.geometry().x(), self.imgdock.geometry().y()]
        if gref[:2]!=self.default_img_pos and not self.popup_state:
            g=self.geometry()
            self.imgdock.setGeometry(g.x(), g.y()+100, g.width(), g.height()-100)
            self.popup_state=True
            self.printc('popup image widget')
        elif gref[:2]==self.default_img_pos and self.popup_state:
            self.popup_state=False
            
    
    def update_image(self):
        self.popup_image_widget()
        t0=time.time()
        if not self.update_image_enable:
            return
        try:
            if self.image_update_in_progress:
                return
            self.image_update_in_progress=True
            if self.frame_counter>20 and self.twop_running and (self.twop_frame.shape[0]!=self.settings['params/Scan Height']*self.settings['params/Resolution'] or self.twop_frame.shape[1]!=self.settings['params/Scan Width']*self.settings['params/Resolution']):
                #self.stop_action()
                h=self.settings['params/Scan Height']*self.settings['params/Resolution']
                w=self.settings['params/Scan Width']*self.settings['params/Resolution']
                self.printc(f'Incorrect scan window! {self.twop_frame.shape}, {h}, {w}')
                #QtGui.QMessageBox.question(self, 'Warning', 'Incorrect scan window!', QtGui.QMessageBox.Ok)
                #return
            if not hasattr(self, 'twop_frame'):
                self.merged=self.ir_filtered
            else:
                self.ir_filtered=filter_image(self.ir_frame,
                                                                self.settings['params/Live/IR Image filters'])*int(self.settings['params/Show IR'])
                                                                
                                                                
                top_filtered=filter_image(self.twop_frame[:,:,0],
                                                                self.settings['params/Live/Top Image filters'])*\
                                                                int(self.settings['params/Show Top'])

                side_filtered=filter_image(self.twop_frame[:,:,1], 
                                                                self.settings['params/Live/Side Image filters'])*\
                                                                int(self.settings['params/Show Side'])
                if self.settings['params/Averaging samples']>1:#TODO: implement this for both channels
                    if not hasattr(self, 'moving_average_buffer') or self.moving_average_buffer.shape[1:]!=top_filtered.shape or self.navg!=int(self.settings['params/Averaging samples']):
                        self.printc('Reset averaging buffer')
#                        self.printc(top_filtered.shape)
                        self.moving_average_buffer=numpy.zeros((int(self.settings['params/Averaging samples']), top_filtered.shape[0], top_filtered.shape[1]))
                        self.buffer_index=0
#                        self.printc(self.moving_average_buffer.shape)
                        self.navg=int(self.settings['params/Averaging samples'])
                    if self.settings['params/Show Top']:
                        self.moving_average_buffer[self.buffer_index%self.navg]=top_filtered
                        top_filtered=self.moving_average_buffer.mean(axis=0)
                    elif self.settings['params/Show Side']:
                        self.moving_average_buffer[self.buffer_index%self.navg]=side_filtered
                        side_filtered=self.moving_average_buffer.mean(axis=0)
                    
                    self.buffer_index+=1
                    
                        
                kwargs={
                        'Offset X':self.settings['params/Infrared-2P overlay/Offset X'], 
                        'Offset Y':self.settings['params/Infrared-2P overlay/Offset Y'], 
                        'Scale':self.settings['params/Infrared-2P overlay/Scale'], 
                        'Rotation':self.settings['params/Infrared-2P overlay/Rotation'], 
                        '2p_scale':self.settings['params/Resolution'],
                        '2p_reference_scale':self.machine_config.REFERENCE_2P_RESOLUTION
                        }
                t1=time.time()
                self.kwargs=kwargs
                twop_filtered=numpy.zeros_like(self.twop_frame)
                twop_filtered[:,:,0]=top_filtered
                twop_filtered[:,:,1]=side_filtered
                self.twop_filtered=twop_filtered
                t2=time.time()
                if (self.settings['params/Show Side'] or self.settings['params/Show Top']) and not self.settings['params/Show IR']:
                    #No merge when no ir channel is selected for display
                    tp=numpy.zeros((twop_filtered.shape[0],twop_filtered.shape[1],3))
                    tp[:,:,:2]=twop_filtered
                    self.merged=tp
                elif (not self.settings['params/Show Side'] and not self.settings['params/Show Top']) and self.settings['params/Show IR']:
                    self.merged=numpy.zeros((self.ir_filtered.shape[0],self.ir_filtered.shape[1],3))
                    self.merged[:,:,0]=self.ir_filtered
                    self.merged[:,:,1]=self.ir_filtered
                    self.merged[:,:,2]=self.ir_filtered
                else:
                    self.merged=merge_image(self.ir_filtered, twop_filtered, kwargs)
            t3=time.time()
            histogram_levels=self.histogram.item.getLevels()
            sg=self.settings['params/Show Grid']
            self.image.plot.showGrid(sg,sg,10.0)
            if self.settings['params/Show IR'] or self.settings['params/Show Side'] or self.settings['params/Show Top']:
                self.image.set_image(self.merged)#Swap x, y axis
            else:
                self.image.set_image(numpy.zeros_like(self.merged))
            #Disabled for eliminating flashes: self.histogram.item.setLevels(histogram_levels[0], histogram_levels[1])
            #self.frame_counter+=1
            #Disabled for eliminating flashes: self.image.img.setLevels([0.0,1.0])
            if self.twop_running:
                self.image.plot.setTitle(f'{self.twop_fps} fps, {self.dwell_time:.02f} ms/V dwell time')
            if not self.aio.queues['response'].empty():
                msg=self.aio.queues['response'].get()
                self.printc(f'message from daq: {msg}')
                if msg=='nframes recorded':
                    self.nframes_recording_running=False
                    self.last_recording_filename=copy.deepcopy(self.filename)
                    self.twop_running=False
                    if not self.z_stack_running and not self.settings['params/Time lapse/Enable']:
                        self.statusbar.twop_status.setText('Ready')
                        self.statusbar.twop_status.setStyleSheet('background:gray;')
                else:
                    self.printc(msg)
            if hasattr(self, 'intensities') and len(self.intensities)>0:
                self.plot.update_curve(numpy.arange(len(self.intensities)),numpy.array(self.intensities))
                self.plot.plot.setTitle(f'Warning: time scale is based on the rate of displayed images<br>{self.intensities[-1]:0.3f} V')
            t4=time.time()
            dt=1e3*numpy.array([t4-t3,t3-t2,t2-t1,t1-t0])
            if not hasattr(self, 'dt'):
                self.dt=[]
            self.dt.append(dt)
            self.dt=self.dt[-10:]
            if 0:
                t='Frame rate: '
                if hasattr(self,'irframerate'):
                    t+=f"IR: {int(self.irframerate)} Hz "
                if hasattr(self, 'twop_fps'):
                    t+=f"2P {self.twop_fps} Hz"
                self.image.plot.setTitle(t)
            #Set aspect ratio of image plot
            ar=self.merged.shape[0]/self.merged.shape[1]
            if ar>1:
                w=self.image.width()
                h=w/ar
            else:
                h=self.image.height()
                w=h*ar
            self.image.plot.setFixedHeight(h*0.9)
            self.image.plot.setFixedWidth(w*0.9)
            if (self.settings['params/Show Top'] or self.settings['params/Show Side']) and not self.settings['params/Show IR']:
                self.imscale=1/self.settings['params/Resolution']#Only 2p image is shown
            elif (not self.settings['params/Show Top'] and not self.settings['params/Show Side']) and self.settings['params/Show IR']:#Only IR is shown
                self.imscale=1/(self.machine_config.REFERENCE_2P_RESOLUTION*self.settings['params/Infrared-2P overlay/Scale']*int(self.settings['params/IR Zoom'][0]))
            else:#IR is also shown
                self.imscale=1/(self.machine_config.REFERENCE_2P_RESOLUTION*self.settings['params/Infrared-2P overlay/Scale'])
            if (self.settings['params/Show Top'] or self.settings['params/Show Side']) and self.settings['params/IR Zoom']!='1x':
                self.printc('Set IR Zoom to 1x or disable showing 2p channels')
            self.image.set_scale(self.imscale)
        except:
            if not hasattr(self, 'update_image_error_shown'):
                self.printc(traceback.format_exc())
                self.update_image_error_shown=True
        self.image_update_in_progress=False
#        self.background_process()        
    
    def stop_action(self, remote=None, snapshot=False):
        try:
            if self.z_stack_running and not snapshot:
                self.finish_zstack()
            elif not self.twop_running:
                return
            else:
                self.aio.stop()
                self.twop_running=False
                self.printc('2p scanning stopped')
                if self.filename is not None:
                    if not os.path.exists(self.filename):
                        time.sleep(5)
                        if not os.path.exists(self.filename):
                            raise IOError(f'{self.filename} is not saved')
                    if not os.path.exists(fileop.replace_extension(self.filename,'.tiff')):
                        time.sleep(5)
                        if not os.path.exists(fileop.replace_extension(self.filename,'.tiff')):
                            raise IOError('tiff is not saved')
            if not self.settings['params/Time lapse/Enable']:
                self.statusbar.twop_status.setText('Ready')
                self.statusbar.twop_status.setStyleSheet('background:gray;')
        except:
            self.printc(traceback.format_exc(), popup_error=False)
        
    def restart_scan(self):
        self.stop_action()
        self.printc("Restart scan")
        self.record_action()
    
############## REFERENCE IMAGE ###################

    def open_action(self):
        '''
        Open a recording for display or a snapshot. Image is put on secondary image display
        '''
        raise NotImplementedError('Second image display')
        
    def save_image_action(self):
        '''
        Save current image to reference image widget
        '''
        self.saved_image.set_scale(self.imscale)
        self.saved_image.set_image(numpy.copy(self.merged))
        self.saved_image_i=numpy.copy(self.merged)
    
    def zoom_in_action(self):
        raise NotImplementedError('')
        
    def zoom_out_action(self):
        raise NotImplementedError('')
    
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
        if self.z_stack_running or self.twop_running:
            return
        try:
            if self.settings['params/Z Stack/Step']<=0:
                raise ValueError('Step value shall be a positive number')
            params={'id': experiment_data.get_id(), 'outfolder': self.machine_config.EXPERIMENT_DATA_PATH}
            name=self.settings['params/Name']
            self.zstack_filename=experiment_data.get_recording_path(self.machine_config,params, f'zstack_{name}')
            self.zstack_filename=os.path.join(self.data_folder, os.path.basename(self.zstack_filename))
            s=self.settings['params/Z Stack/Start']
            e=self.settings['params/Z Stack/End']
            st=self.settings['params/Z Stack/Step']
            self.depths=numpy.linspace(s, e, int(abs(s-e)/st+1))
            steptime=1 if st<1000 else st/1000
            steptime*=4
            self.stepsamples=int(numpy.ceil(self.get_fps()*steptime))
            self.printc(f"Z stack in {', '.join(map(str,self.depths))}, stepsamples: {self.stepsamples}")
            self.zvalues=numpy.repeat(self.depths, self.settings['params/Z Stack/Samples per depth']+self.stepsamples)
            self.record_action(zvalues=self.zvalues)
            return
            ext=self.settings['params/Z Stack/File Format']
            self.printc(f"Z stack in {', '.join(map(str,self.depths))}, saving to {fileop.replace_extension(self.zstack_filename,ext)}")
            self.depth_index=0
            self.z_stack_running=True
            self.z_stack_state='setz'
            self.printc(f"Open {self.zstack_filename}")
            self.zstackfile=tables.open_file(self.zstack_filename,'w')
            datacompressor = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
            h=int(self.settings['params/Resolution']*self.settings['params/Scan Height'])
            w=int(self.settings['params/Resolution']*self.settings['params/Scan Width'])
            datatype = tables.UInt16Atom((self.settings['params/Z Stack/Samples per depth'], h, w, 2))
            self.zstack_data_handle=self.zstackfile.create_earray(self.zstackfile.root, 'zstackdata', datatype, (0,),filters=datacompressor)
            self.tifffns=[]
        except:
            self.printc(traceback.format_exc())
        
    def z_stack_runner(self):#OBSOLETE?
        if self.z_stack_running:
            try:
                if self.z_stack_state=='setz':
                    if not self.twop_running:
                        self.stage.z=self.depths[self.depth_index]
                        time.sleep(2)
                        self.printc(f"Set position to {self.stage.z} ustep")
                        self.record_action(nframes=self.settings['params/Z Stack/Samples per depth'])
                        self.z_stack_state='wait'
                elif self.z_stack_state=='wait':
                    if not self.nframes_recording_running:
                        #Read frame
                        time.sleep(15)
                        fileop.wait4file_ready(self.filename, min_size=0.5e6)
                        h=tables.open_file(self.filename, 'r')
                        data=h.root.twopdata.read()[-self.settings['params/Z Stack/Samples per depth']:]
                        self.printc(data.shape)
                        self.zstack_data_handle.append(data[None, :])
                        h.close()
                        os.remove(self.filename)
                        import shutil
                        dsttiff=fileop.replace_extension(self.filename, f'_{self.depths[self.depth_index]}um.tiff')
                        self.tifffns.append(dsttiff)
                        shutil.move(fileop.replace_extension(self.filename, '.tiff'), dsttiff)
                        self.z_stack_state='setz'
                        self.depth_index+=1
                        if len(self.depths)==self.depth_index:
                            self.printc('All depths imaged')
                            self.finish_zstack()
            except:
                self.printc(traceback.format_exc(), popup_error=False)
                self.finish_zstack()

    def finish_zstack(self):
        atom = tables.Atom.from_dtype(self.depths.dtype)
        depths = self.zstackfile.create_carray(self.zstackfile.root, 'depths', atom, self.depths.shape)
        depths[:] = self.depths
        #Save settings
        self.settings2attr(self.zstackfile.root.depths.attrs)
        self.z_stack_running=False
        self.zstackfile.close()
        try:
            self.stage.z=self.depths[0]
        except:
            time.sleep(2)#Wait a bit until it reaches endposition and recovers
        self.printc(f'Stage set back to initial position to {self.stage.z} ustep')
        if self.settings['params/Z Stack/File Format']!='.hdf5':
            hdf5_convert(self.zstack_filename, self.settings['params/Z Stack/File Format'])
            #os.remove(self.zstack_filename)
        self.printc(f"Z stack finished, data saved to {self.zstack_filename}")
        
    def read_z_action(self):
        self.printc(f'z position: {self.aio.read_z()} ustep')
        
    def set_origin_action(self):
        reply = QtGui.QMessageBox.question(self, 'Confirm:', 'Set stage origin?', QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if not reply:
            return
        self.aio.set_origin()
        self.printc(f'z Origin set: {self.aio.read_z()} ustep')
        
    def format_settings(self):
        '''
        Change setting names to a format that can be handled by pytables: replace / and space to _
        '''
        settings_out={}
        for k, v in self.settings.items():
            settings_out[k.replace('/', '_').replace(' ', '_')]=v
        settings_out.update(self.machine_config.todict())
        if hasattr(self, 'stepsamples'):
            settings_out['stepsamples']=self.stepsamples
        return settings_out
        
    def settings2attr(self, ref):
        for k, v in self.format_settings().items():
            setattr(ref, k, v)
            
    def error_checker(self):
        if not hasattr(self, 'error_shown'):
            for f in [self.cam_logfile,self.daq_logfile]:
                t0=time.time()
                if os.path.exists(f):
                    maxsize=int(1e5)
                    if os.path.getsize(f)>maxsize:
                        fp=open(f, 'rt')
                        offset=int(os.path.getsize(f)-maxsize)
                        fp.seek(offset)
                        log=fp.read(maxsize)
                        fp.close()
                    else:
                        log=fileop.read_text_file(f)
                else:
                    log=''
                dt=time.time()-t0
                if dt>0.8:
                    self.printc('!!!! logfile read takes long')
                if 'ERROR' in log:
                    lines=log.split('\n')
                    index=[i for i in range(len(lines)) if 'ERROR' in lines[i]][0]
                    message='\n'.join(lines[index:])
                    self.stop_action()
                    self.printc(message)
                    QtGui.QMessageBox.question(self, 'Error', message, QtGui.QMessageBox.Ok)
                    self.error_shown=True
        
    def background_process(self):
        try:
            now=time.time()
            if not hasattr(self,  'bgp_tlast'):
                self.bgp_tlast=now
            dt=now-self.bgp_tlast
            if dt>5:
                self.bgp_tlast=now
            else:
                return
            print('00')
            self.socket_handler()
            self.z_stack_runner()   
            self.timelapse_handler()
            print(15)
            self.error_checker()
            print(16)
        except:
            if not hasattr(self, 'background_process_error_shown'):
                self.printc(traceback.format_exc())
                self.background_process_error_shown=True
                
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

    def select_data_folder_action(self):
        df= QtGui.QFileDialog.getExistingDirectory(self, 'Select data folder',  self.data_folder).replace('/','\\')
        self.printc(f'Selected data folder is {df}')
        if 'g:' in df.lower():
            raise IOError("Saving directly to Google drive not supported")
        else:
            self.data_folder=df
            
    def process_action(self):
        df= QtGui.QFileDialog.getExistingDirectory(self, 'Select folder to process. Make sure that folder contains only timelapse files from one recording!',  self.data_folder).replace('/','\\')
        if df.lower()[0]=='g':
            raise IOError('Files from Google drive are not processed')
        self.statusbar.twop_status.setText('Busy')
        self.statusbar.twop_status.setStyleSheet('background:yellow;')
        #Check  dimension of data in files, raise error if incorrect files found
        files=[f for f in fileop.listdir(df) if os.path.splitext(f)[1]=='.hdf5']
        self.printc(f'Checking {len(files)} files')
        self.statusbar.progressbar.setRange(0, len(files))
        self.shapes=[]
        for i in range(len(files)):
            try:
                h=tables.open_file(files[i], 'r')
                self.shapes.append(h.root.twopdata.read().shape)
                attributes_txt=[f'{an}={getattr(h.root.twopdata.attrs, an)}\r\n' for an in dir(h.root.twopdata.attrs)]
                h.close()
            except:
                import traceback
                self.printc(files[i])
                self.printc(traceback.format_exc())
            self.statusbar.progressbar.setValue(i+1)
            QtCore.QCoreApplication.instance().processEvents()
        if max([s[1:3] for s in self.shapes])!=min([s[1:3] for s in self.shapes]):
            raise ValueError('Not all files have the same scan windows')
        self.printc('Undistort images and remove transient images')
        self.zstacks=[]
        self.timelapse_timepoints=[]
        self.distorted_s=[]
        for i in range(len(files)):
            try:
                res=process_zstack(files[i])
                if res is None:
                    self.printc(f'Skip {files[i]},  already processed?,  TODO: handle already processed files')
                    continue
                else:
                    zstack, zvalues, distorted=res
                self.zstacks.append(zstack)
                self.distorted_s.append(distorted)
                ds=os.path.splitext(os.path.basename(files[i]))[0].split('_')[-1]
                self.timelapse_timepoints.append(utils.datestring2timestamp(ds[:-1],format="%Y%m%d%H%M%S"))
            except:
                import traceback
                self.printc(files[i])
                self.printc(traceback.format_exc())
            self.statusbar.progressbar.setValue(i+1)
            QtCore.QCoreApplication.instance().processEvents()
        self.timelapse_timepoints.sort()
        self.zstacks=numpy.array(self.zstacks)
        #Merge all files to one big datafile
        #Save self.timelapse_timepoints to file
        self.statusbar.progressbar.setValue(0)
        self.statusbar.progressbar.setVisible(False)
        import tifffile
        dtag='distorted' if any(self.distorted_s) else ''
        fn=os.path.join(df, os.path.basename(df)+f'_{dtag}_merged_timelapse.tiff')
        tifffile.imwrite(fn, self.zstacks, imagej=True)
        attributes_txt=''.join(attributes_txt)
        tstxt=','.join(list(map(str, self.timelapse_timepoints)))
        metadata=f'timestamps={tstxt}\r\n{attributes_txt}'
        fileop.write_text_file(fileop.replace_extension(fn, '.txt'), metadata)
        self.statusbar.twop_status.setText('Ready')
        self.statusbar.twop_status.setStyleSheet('background:gray;')
        self.printc('Done')

    def exit_action(self):
        self.stop_action()
        self.save_context()
        self._close_hardware()
        self.close()
        
def process_zstack(filename, max_pmt_voltage=8):
    #Undistort images based on scanner position signal
    frames, distorted_frames, distorted=scanner_control.pmt2undistorted_image(filename, fcut=10e3)
    frames=frames[1:]#Ignore first frame
    #remove transient frames
    h=tables.open_file(filename, 'a')
    if hasattr(h.root,'zstack'):
        print('Z stack already calculated')
        return
    transient_indexes=numpy.nonzero(numpy.diff(h.root.twopdata.attrs.zvalues))[0]
    transient_indexes=numpy.insert(transient_indexes,0,0)
    valid_start_indexes=transient_indexes+h.root.twopdata.attrs.stepsamples
    valid_end_indexes=valid_start_indexes+h.root.twopdata.attrs.params_Z_Stack_Samples_per_depth
    zstack=numpy.zeros((valid_start_indexes.shape[0], h.root.twopdata.attrs.params_Z_Stack_Samples_per_depth, frames.shape[1], frames.shape[2]))
    for stepi in range(valid_start_indexes.shape[0]):
        zstack[stepi]=frames[valid_start_indexes[stepi]:valid_end_indexes[stepi]]
    zvalues=numpy.array(list(set(h.root.twopdata.attrs.zvalues)))
    if zvalues.shape[0]!=zstack.shape[0]:
        raise ValueError('invalid number of z depths')
    filters = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
    atom = tables.Float32Atom()
    zstackh = h.create_carray(h.root, 'zstack', atom, zstack.shape,filters=filters)
    zstackh[:, :, :, :]=zstack
    setattr(zstackh.attrs, 'zvalues', zvalues)
    h.close()
    #Scale to uint16
    if zstack.max()<20:
        zstack=zstack+1
        zstack=numpy.clip(zstack, 0, max_pmt_voltage)
        zstack=numpy.cast['uint16'](zstack/max_pmt_voltage*(2**16-1))
    else:
        zstack=numpy.cast['uint16'](zstack)
    return zstack, zvalues, distorted
        
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
    two_p_sw_gain=kwargs.get('2p gain', 0.3)
    if cut_2p:
        merged[:, :, :2]=twop_shifted[-default_offset[0]:merged.shape[0]-default_offset[0],-default_offset[1]:merged.shape[1]-default_offset[1],:]*0.2
    else:
        merged[:, :, :2]=twop_shifted*two_p_sw_gain
    two_p_sw_gain_conj=1-two_p_sw_gain
    merged[:, :, :]+=numpy.stack((ir_image,)*3,axis=-1)*numpy.array([two_p_sw_gain_conj, two_p_sw_gain_conj, two_p_sw_gain_conj])
    return merged
    
def filter_image(image, filter, gamma=0.25):
    if image.dtype==numpy.uint16:
        image_=image/(2**12-1)
    else:
        image_=image
    #Scale input image to min_,max_ range
    scaled=image_#(numpy.clip(image_, min_, max_)-min_)/(max_-min_)
    if filter=='':
        filtered=scaled
    elif filter=='histogram equalization':
        filtered=skimage.exposure.equalize_hist(scaled)
    elif filter=='autoscale':
        filtered=(scaled-scaled.min())/(scaled.max()-scaled.min())
    elif filter=='gamma':
        filtered=skimage.exposure.adjust_gamma((scaled-scaled.min())/(scaled.max()-scaled.min()), gamma)
    else:
        raise NotImplementedError('')
    return filtered
    
def hdf5_convert(fn,format):
    fh=tables.open_file(fn,'r')
    import tifffile
    if 'zstackdata' in dir(fh.root):
        data=fh.root.zstackdata.read()
        metadata=f'depths={fh.root.depths.read()}\n'
        metadata2={'depths':fh.root.depths.read()}
        for vn in dir(fh.root.depths.attrs):
            if vn[0].isalpha() and vn[0].islower():
                value=getattr(fh.root.depths.attrs,vn)
                metadata+=f"{vn}={value}\n"
                metadata2[vn]=value
                
        #Reshape data
        if format=='.tiff':
            dataout=numpy.zeros((data.shape[0]*data.shape[1],data.shape[2],data.shape[3],3),dtype=numpy.uint16)
            ct=0
            for d in range(data.shape[0]):
                for r in range(data.shape[1]):
                    dataout[ct,:,:,:2]=data[d,r]
                    ct+=1
            tifffile.imwrite(fn.replace('.hdf5', '.tiff'),dataout)
            fileop.write_text_file(fn.replace('.hdf5','.txt'),metadata)
        elif format=='.mat':
            dataout={'zstack':data,'metadata': metadata2}
            import scipy.io
            scipy.io.savemat(fileop.replace_extension(fn,format), dataout,long_field_names=True)
    elif 'twopdata' in dir(fh.root):
        raise NotImplementedError('')
    fh.close()
    
class Test(unittest.TestCase):
    def test_hdf52tiff(self):
        files=[r'f:\Data\zstack_202006021643399.hdf5',r'f:\Data\2p_202005211441530.hdf5']
        for f in files:
            hdf5_convert(f,'.tiff')
    
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
        ct=0
        for ir_value, ir2p_scale, twop_size, offset in itertools.product(ir_values, ir2p_scales, twop_sizes, offsets):
            print((ct,numpy.prod(list(map(len, [ir_values, ir2p_scales, twop_sizes, offsets])))))
            ct+=1
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
                
    def test_process_zstack(self):
        process_zstack('D:\\Data\\convert\\2p_BEAD_TEST_202202282054006.hdf5')

            

if __name__=='__main__':
    mytest = unittest.TestSuite()
    mytest.addTest(Test('test_process_zstack'))
    unittest.TextTestRunner(verbosity=2).run(mytest)
