import os,time, numpy, hdf5io, traceback, multiprocessing, serial
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore

from visexpman.engine.generic import gui,fileop, signal, utils, introspect
from visexpman.engine.hardware_interface import camera_interface, daq_instrument,digital_io,openephys
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
        if hasattr(self.machine_config, 'CAMERA_GUI_POS_X'):
            self.move(self.machine_config.CAMERA_GUI_POS_X, self.machine_config.CAMERA_GUI_POS_Y)
        self._set_window_title()
        toolbar_buttons = ['record', 'stop', 'convert_folder', 'exit']
            
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.statusbar=self.statusBar()
        self.statusbar.recording_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.recording_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        
        self.statusbar.trigger_status=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.trigger_status)
        self.statusbar.recording_status.setStyleSheet('background:gray;')

        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)        
        self.image = gui.Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        if hasattr(self.machine_config,'ENABLE_USER_FOLDER') and self.machine_config.ENABLE_USER_FOLDER:
            self.filebrowserroot= os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,self.machine_config.user)
        else:
            self.filebrowserroot= self.machine_config.EXPERIMENT_DATA_PATH
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab = QtGui.QTabWidget(self)
        if self.machine_config.PLATFORM=='behav':
            self.datafilebrowser = main_ui.DataFileBrowser(self, self.filebrowserroot, ['behav*.hdf5', 'stim*.hdf5', 'eye*.hdf5',   'data*.hdf5', 'data*.mat','*.mp4'])
            self.main_tab.addTab(self.datafilebrowser, 'Data Files')        
        self.main_tab.addTab(self.params, 'Settings')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self.show()
        
        self.update_image_timer=QtCore.QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        self.update_image_timer.start(1000/self.machine_config.DEFAULT_CAMERA_FRAME_RATE/3)#ms
            
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        if os.path.exists(self.context_filename):
            context_stream = numpy.load(self.context_filename)
            self.parameters=utils.array2object(context_stream)
        else:
            self.parameter_changed()
        self.load_all_parameters()
        port= self.machine_config.CAMERA_IO_PORT if hasattr(self.machine_config, 'CAMERA_IO_PORT') else None
        self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['params/Frame Rate'], self.parameters['params/Exposure time']*1e-3, port)
        self.camerahandler.start()
        self.trigger_detector_enabled=False
#        if hasattr(self.machine_config,  'TRIGGER_DETECTOR_PORT'):
#            self.ioboard=serial.Serial(self.machine_config.TRIGGER_DETECTOR_PORT, 1000000, timeout=0.001)
#            self.trigger_detector_enabled=False
#            self.start_trigger=False
#            self.stop_trigger=False
#        time.sleep(2)
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
#            self.ai=daq_instrument.AnalogIOProcess('daq', self.daqqueues, None, ai_channels=self.machine_config.SYNC_RECORDER_CHANNELS,limits=limits)
#            self.ai.start()
        
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT*0.4)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()

    def _init_variables(self):
        self.recording=False
        self.track=[]
        self.trigger_state='off'
        if self.machine_config.PLATFORM in ['2p', 'resonant', 'generic']:
            trigger_value = 'network' 
            params=[]
        elif self.machine_config.PLATFORM in ['behav']:
            trigger_value='TTL pulses'
            params=[
                {'name': 'Show track', 'type': 'bool', 'value': True}, 
                {'name': 'Threshold', 'type': 'int', 'value': 80},
                {'name': 'ROI size', 'type': 'int', 'value': 20},
                {'name': 'Show color LEDs', 'type': 'bool', 'value': False}, 
                ]
        else:
            trigger_value='manual'
            params=[]
        self.params_config = [
                {'name': 'Trigger', 'type': 'list', 'values': ['manual', 'network', 'TTL pulses'], 'value': trigger_value},
                {'name': 'Enable trigger', 'type': 'bool', 'value': False,   'readonly': self.machine_config.PLATFORM!='behav'}, 
                {'name': 'Frame Rate', 'type': 'float', 'value': 25, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Exposure time', 'type': 'float', 'value': 39, 'siPrefix': True, 'suffix': 'ms'},
                {'name': 'Enable ROI cut', 'type': 'bool', 'value': False},
                {'name': 'ROI x1', 'type': 'int', 'value': 200},
                {'name': 'ROI y1', 'type': 'int', 'value': 200},
                {'name': 'ROI x2', 'type': 'int', 'value': 400},
                {'name': 'ROI y2', 'type': 'int', 'value': 400},
                    ]
        self.params_config.extend(params)
        
    def save_context(self):
        context_stream=utils.object2array(self.parameters)
        numpy.save(self.context_filename,context_stream)
        
    def restart_camera(self):
        if hasattr(self, 'camerahandler'):
            self.printc('Restart camera')
            self.camerahandler.stop()
            self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['params/Frame Rate'], self.parameters['params/Exposure time']*1e-3,  None)
            self.camerahandler.start()
    
    def start_recording(self,  experiment_parameters=None):
        try:
            if self.recording:
                return
            if not introspect.is_process_running('open-ephys') and self.machine_config.ENABLE_OPENEPHYS_TRIGGER:
                QtGui.QMessageBox.question(None,'Warning', 'Open-ephys GUI is not running', QtGui.QMessageBox.Ok)
                return
            if 1000/self.parameters['params/Frame Rate']<self.parameters['params/Exposure time']:
                msg='Exposure time is too long for this frame rate!'
                self.printc(msg)
                QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return
            self.recording=True
            self.printc('Start video recording')
            self.statusbar.recording_status.setStyleSheet('background:yellow;')
            self.statusbar.recording_status.setText('Preparing')
            self.camerahandler.stop()
            if self.machine_config.ENABLE_SYNC=='camera':
                self.ai=daq_instrument.SimpleAnalogIn(self.machine_config.SYNC_RECORDER_CHANNELS, self.machine_config.SYNC_RECORDER_SAMPLE_RATE, self.machine_config.MAX_RECORDING_DURATION,  finite=False)
#                d=self.ai.read_ai()#Empty ai buffer
#                self.ai.start_daq(ai_sample_rate = self.machine_config.SYNC_RECORDER_SAMPLE_RATE,
#                                ai_record_time=self.machine_config.SYNC_RECORDING_BUFFER_TIME, timeout = 10) 
                msg='Camera&Sync recording'
            else:
                msg='Camera recording'
            if hasattr(experiment_parameters, 'keys') and 'eyecamfilename' in experiment_parameters:
                self.fn=experiment_parameters['eyecamfilename']
            else:
                if not self.machine_config.ENABLE_USER_FOLDER:
                    outfolder=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, utils.timestamp2ymd(time.time(), separator=''))
                else:
                    outfolder=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, self.machine_config.user, utils.timestamp2ymd(time.time(), separator=''))
                if not os.path.exists(outfolder):
                    os.makedirs(outfolder)
                self.fn=experiment_data.get_recording_path(self.machine_config, {'outfolder': outfolder,  'id': experiment_data.get_id()},prefix = self.machine_config.CAMFILENAME_TAG,extension='.mp4')
            if self.machine_config.ENABLE_OPENEPHYS_TRIGGER:
                if not openephys.start_recording():
                    self.printc('Openephyc cannot be triggered, is it started?')
                else:
                    self.printc('Start Openephys')
                time.sleep(self.machine_config.OPENEPHYS_PRETRIGGER_TIME)
                #Check if openephys related file has appeared
                latest_file=fileop.find_latest(self.machine_config.OPENEPHYS_DATA_PATH)
                self.openephys_datafolder=os.path.join(self.machine_config.OPENEPHYS_DATA_PATH,latest_file.replace(self.machine_config.OPENEPHYS_DATA_PATH,'').split(os.sep)[1])
                latest_file_age=fileop.file_age(latest_file)
                if latest_file_age>self.machine_config.OPENEPHYS_PRETRIGGER_TIME:
                    openephys.stop_recording()
                    self.recording=False
                    msg='Openephys GUI does not save file to {0}, recording terminated'.format(self.machine_config.OPENEPHYS_DATA_PATH)
                    self.printc(msg)
                    QtGui.QMessageBox.question(self, "Warning", msg, QtGui.QMessageBox.Ok)
                    self.statusbar.recording_status.setStyleSheet('background:gray;')
                    self.statusbar.recording_status.setText('Ready')
                    
            self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['params/Frame Rate'], self.parameters['params/Exposure time']*1e-3,  self.machine_config.CAMERA_IO_PORT,  filename=self.fn, watermark=True)
            self.camerahandler.start()
            import psutil
            p = psutil.Process(self.camerahandler.pid)
            p.nice(psutil.HIGH_PRIORITY_CLASS)
            self.tstart=time.time()
            self.statusbar.recording_status.setStyleSheet('background:red;')
            self.statusbar.recording_status.setText(msg)
            self.track=[]
        except:
            self.printc(traceback.format_exc())
            self.send({'trigger': 'cam error'})
            
    def stop_recording(self):
        try:
            if not self.recording:
                return
            t0=time.time()
            self.printc('Stop video recording, please wait...')
            self.statusbar.recording_status.setStyleSheet('background:yellow;')
            self.statusbar.recording_status.setText('Busy')
            QtCore.QCoreApplication.instance().processEvents()
            self.ts, log=self.camerahandler.stop()
            hdf5_out=self.fn if self.fn[-4]=='hdf5' else fileop.replace_extension(self.fn,'.hdf5')
            hdf5io.save_item(hdf5_out, 'timestamps', self.ts)
            if hasattr(self.machine_config, 'MINISCOPE_DATA_PATH'):
                miniscope_datafolder=self.find_miniscope_data()
                if os.path.exists(miniscope_datafolder):
                    import copy
                    parameters=copy.deepcopy(self.parameters)
                    parameters['miniscope data']=miniscope_datafolder
                    hdf5io.save_item(hdf5_out, 'parameters', parameters)
            else:
                hdf5io.save_item(hdf5_out, 'parameters', self.parameters)
            self.printc('\n'.join(log))
            if hasattr(self,  'ai'):
                self.sync=self.ai.finish()
#                res=self.ai.stop_daq()
#                try:
#                    self.sync, n=res
#                except:
#                    raise RuntimeError("daq data cannot be read: {0}".format(res))
#                concatenated=self.sync[0]
#                for i in range(self.sync.shape[0]-1):
#                    concatenated=numpy.concatenate((concatenated,  self.sync[i+1]))
#                self.sync=concatenated
                hdf5io.save_item(hdf5_out, 'sync', self.sync)
                hdf5io.save_item(hdf5_out, 'machine_config',  self.machine_config.todict())
                self.fps_values, fpsmean,  fpsstd=signal.calculate_frame_rate(self.sync[:, self.machine_config.TBEHAV_SYNC_INDEX], self.machine_config.SYNC_RECORDER_SAMPLE_RATE, threshold=2.5)
                self.printc('Measured frame rate is {0:.2f} Hz, std: {1:.2f} ms, recorded {2} frames'.format(fpsmean, 1000/fpsstd,  self.fps_values.shape[0]+1))
                self.check_camera_timing_signal()
                if self.trigger_state=='stopped':#check if nvista camera was also recording
                    self.check_nvista_camera_timing()
            else:
                self.printc('mean: {0} Hz,  std: {1} ms'.format(1/numpy.mean(numpy.diff(self.ts)), 1000*numpy.std(numpy.diff(self.ts))))
            self.printc('Saved to {0}'.format(self.fn))
            import skvideo.io
            videogen = skvideo.io.vreader(self.fn)
            fc=len([frame.shape for frame in videogen])
            self.printc('Recorded {0} frames'.format(fc))
            self.camerahandler=camera_interface.ImagingSourceCameraHandler(self.parameters['params/Frame Rate'], self.parameters['params/Exposure time']*1e-3,  None)
            self.camerahandler.start()
            self.statusbar.recording_status.setStyleSheet('background:gray;')
            self.statusbar.recording_status.setText('Ready')
            self.recording=False
            self.printc('Save time {0} s'.format(int(time.time()-t0)))
            if hasattr(self, 'fps_values') and self.fps_values.shape[0]<10:
                self.printc('Recording too short, file removed')
                os.remove(hdf5_out)
            if self.machine_config.ENABLE_OPENEPHYS_TRIGGER:
                time.sleep(self.machine_config.OPENEPHYS_PRETRIGGER_TIME)
                self.printc('Stop Openephys')
                openephys.stop_recording()
                zipfile=os.path.join(os.path.dirname(hdf5_out), fileop.replace_extension(os.path.basename(hdf5_out), '.zip'))
                self.printc('Check recorded data,please wait...')
                QtCore.QCoreApplication.instance().processEvents()
                self.frequency, self.frequency_std, self.video_frame_indexes, self.sync_data=openephys.check_data(self.openephys_datafolder)
                hdf5io.save_item(hdf5_out, 'video_frame_indexes', self.video_frame_indexes)
                self.printc('Move openephys data to {0}'.format(zipfile))
                fileop.move2zip(self.openephys_datafolder,zipfile)
            if self.machine_config.EXPERIMENT_FILE_FORMAT=='mat':
                experiment_data.hdf52mat(hdf5_out,  scale_sync=True)
                try:
                    time.sleep(1)
                    os.remove(hdf5_out)
                except:
                    time.sleep(5)
                    os.remove(hdf5_out)
            if self.machine_config.ENABLE_OPENEPHYS_TRIGGER:
                self.printc(f"Expected frame rate: {self.parameters['params/Frame Rate']} Hz,  measured: {self.frequency} Hz, std: {self.frequency_std}")
                if self.video_frame_indexes[0]<10e3*self.machine_config.OPENEPHYS_PRETRIGGER_TIME:
                    QtGui.QMessageBox.question(None,'Warning', 'Beginning of sync signal is corrupt', QtGui.QMessageBox.Ok)
                if len(self.video_frame_indexes)!=fc:
                    raise ValueError(f'Recorded number of frames ({fc}) and timestamps ({len(self.video_frame_indexes)}) do not match')
                
        except:
            e=traceback.format_exc()
            self.printc(e)
            if hasattr(self,  'send'):
                self.send({'trigger': 'cam error'})
            
    def check_camera_timing_signal(self):
        timestamps=signal.trigger_indexes(self.sync[:,self.machine_config.TBEHAV_SYNC_INDEX])/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        length=self.sync.shape[0]/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        two_frame_time=self.parameters['params/Exposure time']*1e-3*2
        if timestamps[0]<two_frame_time or timestamps[-1]>length-two_frame_time:
            msg='Beginning or end of camra timing signal may not be recorder properly!'
            self.printc(msg)
            QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok)
            
    def check_nvista_camera_timing(self):
        timestamps=signal.trigger_indexes(self.sync[:,self.machine_config.TNVISTA_SYNC_INDEX])/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        fps=1/numpy.diff(timestamps[::2])
        self.printc('nVista camera frame rate: {0:.1f} Hz, std: {1:.1f} Hz'.format(fps.mean(), fps.std()))
        if fps.mean()>60 or fps.mean()<4:
            self.printc('Invalid nVIsta camera frame rate: {0}'.format(fps.mean()))
            
    def check_video(self):
        import hdf5io
        self.fframes=hdf5io.read_item(self.fn,  'frames')
        self.ct=[]
        for f in self.fframes:
            ct=f[0, 0, 0]*256+f[0, 1, 0]
            self.ct.append(ct)
        if (numpy.diff(self.ct)!=1).any():
            raise RuntimeError(numpy.diff(self.ct))
            
        
    def parameter_changed(self):
        newparams=self.params.get_parameter_tree(return_dict=True)
        if hasattr(self,  'parameters') and (newparams['params/Frame Rate']!=self.parameters['params/Frame Rate'] or newparams['params/Exposure time']!=self.parameters['params/Exposure time']):
            self.restart_camera()
        self.parameters=newparams
        
    def record_action(self):
        self.start_recording()
        
    def stop_action(self):
        self.stop_recording()
            
    def convert_folder_action(self):
        #This is handled by main GUI process, delegating it to gui engine would make progress bar handling more complicated        
        try:
            if self.recording: return
            foldername = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select hdf5 video file folder', self.filebrowserroot))
            if foldername=='': return
            if os.name=='nt':
                foldername=foldername.replace('/','\\')
            files=fileop.listdir(foldername)
            p=gui.Progressbar(100, 'Conversion progress',  autoclose=True)
            p.show()
            self.printc('Conversion started')
            self.statusbar.recording_status.setStyleSheet('background:yellow;')
            self.statusbar.recording_status.setText('Processing')
            QtCore.QCoreApplication.instance().processEvents()
            dst=os.path.join(self.machine_config.BACKUP_PATH, os.path.basename(foldername))
            if not os.path.exists(dst):
                os.mkdir(dst)
            time.sleep(0.5)
            for f in files:
                if not os.path.isdir(f) and os.path.splitext(f)[1]=='.hdf5' and not os.path.exists(fileop.replace_extension(experiment_data.add_mat_tag(f), '.mat')):
                    print(f)
                    try:
                        self.convert_file(f)
                        #Copy files
                        import shutil
                        shutil.copy(f,dst)
                        shutil.copy(fileop.replace_extension(experiment_data.add_mat_tag(f), '.mat'),dst)
                        self.printc('Copied to {0}'.format(dst))
                    except:
                        self.printc(traceback.format_exc(), popup_error=False)
                    prog=int((files.index(f)+1)/float(len(files))*100)
                    p.update(prog)
                    QtCore.QCoreApplication.instance().processEvents()
                    time.sleep(100e-3)
            self.printc('{0} folder complete'.format(foldername))
        except:
            self.printc(traceback.format_exc())
        self.statusbar.recording_status.setStyleSheet('background:gray;')
        self.statusbar.recording_status.setText('Ready')
    
    
    def convert_file(self, filename):
        h=hdf5io.Hdf5io(filename)
        h.load('machine_config')
        h.load('parameters')
        h.load('sync')
        #Make parameters and machine config compatible with matlab's hdf5io
        p={}
        for k, v in h.parameters.items():
            if isinstance(v, bool):
                v=int(v)
            p[k.replace(' ', '_').lower()]=v
        for k, v in h.machine_config.items():
            if isinstance(v, bool):
                h.machine_config[k]=int(v)
        h.parameters=p
        h.head_direction=[]
        h.led_positions=[]
        h.head_position=[]
        ct=0
        h.frame_indexes=[]
        h.tnvista=signal.trigger_indexes(h.sync[:,self.machine_config.TNVISTA_SYNC_INDEX])[::2]/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        h.tbehav=signal.trigger_indexes(h.sync[:,self.machine_config.TBEHAV_SYNC_INDEX])[::2]/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        nframes=h.h5f.root.frames.shape[0]
        chunksize=1000
        nchunks=nframes/chunksize
        if nchunks==0:
            nchunks=1
        p=gui.Progressbar(100, 'Processing status',  autoclose=True)
        p.move(200, 100)
        p.show()
        for chunki in range(nchunks):
            frames=h.h5f.root.frames.read(chunki*chunksize,  (chunki+1)*chunksize)
            self.printc((frames[0, 0, :2, 0]*numpy.array([256,1])).sum())#Just to see if frames are loaded in the right order
            prog=100*chunki/nchunks
            p.update(prog)
            QtCore.QCoreApplication.instance().processEvents()
            for f in frames:
                try:
                    result, position, self.red_angle, red, green, blue, debug=behavioral_data.mouse_head_direction(f, roi_size=self.parameters['params/ROI size'], threshold=self.parameters['params/Threshold'],  saturation_threshold=0.6, value_threshold=0.4)
                    print((result, position, self.red_angle, red, green, blue))
                    if result:
                        h.head_direction.append(self.red_angle)
                        h.led_positions.append([red, green, blue])
                        h.head_position.append(position)
                        h.frame_indexes.append(ct)
                    ct+=1
                except:
                    self.printc(traceback.format_exc(), popup_error=False)
                    ct+=1
                    continue
        h.save(['head_direction',  'led_positions',  'head_position',  'frame_indexes',  'tnvista', 'tbehav', 'machine_config',  'parameters'])
        h.close()
        experiment_data.hdf52mat(filename,  scale_sync=True, exclude=['frames'])
    
    def update_image(self):
        try:
            if not self.camerahandler.log.empty():
                self.printc(self.camerahandler.log.get())
            if not self.camerahandler.display_frame.empty():
                frame=self.camerahandler.display_frame.get()
                self.frame=frame
                if self.parameters['params/Enable ROI cut']:
                    frame=frame[self.parameters['ROI x1']:self.parameters['ROI x2'],self.parameters['ROI y1']:self.parameters['ROI y2']]
                f=numpy.copy(frame)
                self.f=f
                if self.machine_config.PLATFORM=='behav':
                    if self.recording or self.parameters.get('params/Show color LEDs', False):
                        try:
                            result, self.position, self.red_angle, self.red, self.green, self.blue, debug=behavioral_data.mouse_head_direction(f, roi_size=self.parameters['params/ROI size'], threshold=self.parameters['params/Threshold'],  saturation_threshold=0.6, value_threshold=0.4)
                        except:
                            self.printc('Tracking problem')
                            numpy.save('c:\\Data\\log\\{0}.npy'.format(time.time()),  f)
                            self.logger.info(traceback.format_exc())
                            
                        if self.recording:
                            self.track.append(self.position)
                        if self.parameters.get('params/Show color LEDs', False):
                            f[int(self.red[0]), int(self.red[1])]=numpy.array([255, 255,0],dtype=f.dtype)
                            f[int(self.green[0]), int(self.green[1])]=numpy.array([255,255,0],dtype=f.dtype)
                            f[int(self.blue[0]), int(self.blue[1])]=numpy.array([255,255, 0],dtype=f.dtype)
                            #f[int(self.position[0]), int(self.position[1])]=numpy.array([255,255, 255],dtype=f.dtype)
                    if self.parameters.get('params/Show track', False):
                        for p in self.track:
                            try:
                                if numpy.isnan(p[0]):
                                    continue  
                                f[int(p[0]), int(p[1])]=numpy.array([255,255,255],dtype=f.dtype)
                            except:
                                self.printc('Track display problem')
                                numpy.save('c:\\Data\\log\\{0}.npy'.format(time.time()),  numpy.array(p))
                                self.logger.info(traceback.format_exc())
                    
                self.image.set_image(numpy.rot90(numpy.flipud(f)))
                if self.recording:
                    dt=time.time()-self.tstart
                    title='{0} s'.format(int(dt))
                    if hasattr(self,  'red_angle'):
                        title+='/head direction: {0:0.1f}'.format(self.red_angle)
                    self.image.plot.setTitle(title)
                if hasattr(self.machine_config,  'TRIGGER_DETECTOR_PORT'):
                    self.trigger_handler()
                self.socket_handler()
        except:
            self.printc(traceback.format_exc())
        
    def exit_action(self):
        self.save_context()
        self.camerahandler.stop()
#        if hasattr(self,  'ioboard'):
#            self.ioboard.close()
#        if hasattr(self, 'ai'):
#            self.ai.queues['command'].put('terminate')
#            self.ai.join()
        self.close()
        
    def socket_handler(self):
        if not self.socket_queues['cam']['fromsocket'].empty():
            command=self.socket_queues['cam']['fromsocket'].get()
            try:
                if 'function' in command:
                    getattr(self,  command['function'])(*command['args'])
            except:
                self.socket_queues['cam']['tosocket'].put({'trigger': 'cam error'})
        
    def trigger_handler(self):
        if self.trigger_state=='off':
            if self.parameters['params/Trigger']=='TTL pulses' and self.parameters['params/Enable trigger']:
                self.enable_trigger()
                self.trigger_state='waiting'
                self.printc('New trigger status: '+self.trigger_state)
        elif self.trigger_state=='waiting':
            readout=self.trigger_detector.detect()
            if readout !='none':
                self.printc(readout)
            if readout=='on':
                if self.parameters['params/Enable trigger'] and not self.recording:
                    self.trigger_state='started'
                    self.printc('New trigger status: '+self.trigger_state)
                    self.start_recording()
                else:
                    self.disable_trigger()
                    self.enable_trigger()
            elif self.parameters['params/Trigger']!='TTL pulses' or not self.parameters['params/Enable trigger'] :
                self.disable_trigger()
                self.trigger_state='off'
        elif self.trigger_state=='started':
            readout=self.trigger_detector.detect()
            if readout !='none':
                self.printc(readout)
            if readout == 'off' and self.recording:
                self.trigger_state='stopped'
                self.printc('New trigger status: '+self.trigger_state)
                self.stop_recording()
            elif not self.recording:#manually stopped
                self.trigger_state='stopped'
                self.printc(self.trigger_state)
        elif self.trigger_state=='stopped':
            self.disable_trigger()
            self.enable_trigger()
            self.trigger_state='waiting'
            self.printc('New trigger status: '+self.trigger_state)
        if self.trigger_state=='off':
            color='grey'
        elif self.trigger_state=='waiting':
            color='yellow'
        elif self.trigger_state=='started':
            color='red'
        elif self.trigger_state=='stopped':
            color='orange'
        self.statusbar.trigger_status.setStyleSheet('background:{0};'.format(color))
        self.statusbar.trigger_status.setText('trigger status: {0}'.format(self.trigger_state))
    
    def enable_trigger(self):
        if not self.trigger_detector_enabled:
            self.trigger_detector=digital_io.TriggerDetector(self.machine_config.TRIGGER_DETECTOR_PORT,self.machine_config.TRIGGER_TIMEOUT)
#            self.ioboard.write('wait_trigger,1\r\n')
#            self.printc(self.ioboard.read(100))
            self.trigger_detector_enabled=True
        
    def disable_trigger(self):
        if self.trigger_detector_enabled:
#            self.ioboard.write('wait_trigger,0\r\n')
#            self.printc(self.ioboard.read(100))    
            self.trigger_detector.close()
            self.trigger_detector_enabled=False

    def find_miniscope_data(self):
        time_struct = time.localtime(time.time())
        d='{2:0=2}_{1:0=2}_{0:0=4}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday)
        folder=os.path.join(self.machine_config.MINISCOPE_DATA_PATH, d)
        #Latest folder:
        fns = [fn for fn in fileop.listdir_fullpath(folder) if os.path.isdir(fn)]
        if len(fns) == 0:
            return
        fns_dates = map(os.path.getmtime, fns)
        latest_file_index = fns_dates.index(max(fns_dates))
        return fns[latest_file_index]
        
