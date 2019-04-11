import os,time
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore

from visexpman.engine.generic import gui,fileop
from visexpman.engine.vision_experiment import gui_engine, main_ui,experiment_data

class Camera(gui.VisexpmanMainWindow):
    def __init__(self, context):        
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.setWindowIcon(gui.get_icon('cam'))
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
        self.datafilebrowser = main_ui.DataFileBrowser(self.analysis, filebrowserroot, ['stim*.hdf5', 'eye*.hdf5',   'data*.hdf5', 'data*.mat','*.mp4'])
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.datafilebrowser, 'Data Files')
        self.main_tab.addTab(self.params, 'Settings')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self.load_all_parameters()
        self.show()
        self.main_tab.currentChanged.connect(self.tab_changed)
        
        self.update_image_timer=QtCore.QTimer()
        self.update_image_timer.start(1000/self.machine_config.DEFAULT_CAMERA_FRAME_RATE/3)#ms
        self.connect(self.update_image_timer, QtCore.SIGNAL('timeout()'), self.update_image)
        
        #Set size of widgets
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT*0.4)
        self.plot.setFixedWidth(self.machine_config.GUI_WIDTH*0.5)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()

    def _init_variables(self):
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
                {'name': 'Enable ROI cut', 'type': 'bool', 'value': False},
                {'name': 'ROI x1', 'type': 'int', 'value': 200},
                {'name': 'ROI y1', 'type': 'int', 'value': 200},
                {'name': 'ROI x2', 'type': 'int', 'value': 400},
                {'name': 'ROI y2', 'type': 'int', 'value': 400},
                {'name': 'Channel', 'type': 'int', 'value': 0},
                {'name': 'Show channel only', 'type': 'bool', 'value': False},
                    ]
        self.params_config.append(params)
        
    def record_action(self):
        self.to_engine.put({'function': 'record', 'args':[]})
        
    def stop_action(self):
        self.to_engine.put({'function': 'stop', 'args':[]})
            
    def convert_folder_action(self):
        #This is handled by main GUI process, delegating it to gui engine would make progress bar handling more complicated
        foldername=self.ask4foldername('Select hdf5 video file folder',  self.machine_config.EXPERIMENT_DATA_PATH)
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
    
    def update_image(self):
        pass
        
    def exit_action(self):
        self.close()
    
