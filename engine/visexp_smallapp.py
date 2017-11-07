'''
This module implements small applications like flowmeter logger or serial port pulse generator.
'''
import time
import sys
import os
import os.path
import traceback
import pdb
import numpy

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
import hdf5io
from visexpman.engine.generic import utils,log,fileop,signal,introspect
from visexpman.engine.vision_experiment import configuration,gui
from visexpman.engine.generic import gui as gui_generic
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.hardware_interface import digital_io,flowmeter

class SmallApp(QtGui.QWidget):
    '''
    Small  application gui
    '''
    def __init__(self, user=None, config_class=None, enable_console=True):
        if hasattr(config_class, 'OS'):
            self.config=config_class
            config_class_name = config_class.__class__.__name__
        elif config_class is not None:
            self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
            config_class_name = config_class
        else:
            self.config=None
            config_class_name = self.__class__.__name__
        if self.config is not None:
            self.config.user = user
        if not hasattr(self.config, 'SMALLAPP') and self.config is not None:
            raise RuntimeError('No small application configuration is provided, check machine config')
        if hasattr(self.config, 'LOG_PATH'):
            self.log = log.Log('gui log', fileop.generate_filename(os.path.join(self.config.LOG_PATH, self.config.SMALLAPP['NAME'].replace(' ', '_') +'.txt')), local_saving = True)
        self.console_text = ''
        if self.config is not None and self.config.SMALLAPP.has_key('POLLER'):
            if hasattr(gui_pollers, self.config.SMALLAPP['POLLER']):
                self.poller =  getattr(gui_pollers, self.config.SMALLAPP['POLLER'])(self, self.config)
            else:
                self.poller =  getattr(self.config.SMALLAPP['POLLER_MODULE'], self.config.SMALLAPP['POLLER'])(self, self.config)
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('{2} - {0} - {1}' .format(user if user is not None else '',  config_class_name, self.config.SMALLAPP['NAME'] if self.config is not None else ''))
        if hasattr(self.config, 'SIZE'):
            self.resize(self.config.SIZE['col'], self.config.SIZE['row'])
        else:
            self.resize(800,600)
        if hasattr(self.config, 'GUI_POSITION'):
            self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        if enable_console:
            self.add_console()
        self.create_layout()
        self.connect_signals()
        self.show()
        if self.config is not None and self.config.SMALLAPP.has_key('POLLER'):
            if hasattr(self.poller,  'init_widgets'):
                self.poller.init_widgets()
            self.poller.start()
        
    def add_console(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        
    def create_gui(self):
        pass
        
    def create_layout(self):
        pass
        
    def connect_signals(self):
        pass
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        if hasattr(self.poller, mapped_signal_parameter):
            self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
            getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
        else:
            self.printc('{0} method does not exists'.format(mapped_signal_parameter))
        
    def printc(self, text, add_timestamp = True):
        if not isinstance(text, str):
            text = str(text)
        if add_timestamp:
            timestamp_string = utils.timestamp2hm(time.time()) + ' '
        else:
            timestamp_string = ''
        self.console_text  += timestamp_string + text + '\n'
        self.text_out.setPlainText(self.console_text)
        self.text_out.moveCursor(QtGui.QTextCursor.End)
        try:
            if hasattr(self, 'log'):
                self.log.info(text)
        except:
            print 'gui: logging error'

    def ask4confirmation(self, action2confirm):
        reply = QtGui.QMessageBox.question(self, 'Confirm following action', action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return False
        else:
            return True
            
    def ask4filename(self,title, directory, filter):
        filename = str(QtGui.QFileDialog.getOpenFileName(self, title, directory, filter))
        return filename
        
    def notify_user(self, title, message):
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)
    
    def closeEvent(self, e):
        e.accept()
        if hasattr(self, 'log'):
            self.log.copy()
        if self.config is not None and self.config.SMALLAPP.has_key('POLLER'):
            self.poller.abort = True
        time.sleep(1.0)
        sys.exit(0)
        
class FlowmeterLogger(SmallApp):
    def create_gui(self):
        self.flowmeter = gui.FlowmeterControl(self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.flowmeter, 0, 0, 1, 1)
        self.layout.addWidget(self.text_out, 1, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.flowmeter.reset_button, 'reset')
        self.connect_and_map_signal(self.flowmeter.start_button, 'start_measurement')
        self.connect_and_map_signal(self.flowmeter.stop_button, 'stop_measurement')
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)

    def update_status(self, status, value =  None):
        if value is None:
            self.flowmeter.status_label.setText('{0}'.format(status))
        else:
            self.flowmeter.status_label.setText('{0}, {1:2.2f} ul/min'.format(status, value))
            
class SLI2000FlowmeterLogger(SmallApp, flowmeter.SLI_2000Flowmeter):
    def __init__(self):
        SmallApp.__init__(self)
        self.timer=QtCore.QTimer()
        self.timer.start(100)
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.periodic)
        flowmeter.SLI_2000Flowmeter.__init__(self)
        
    def periodic(self):
        self.printc(self.get_flow_rate())
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.text_out, 1, 0, 1, 10)
        self.setLayout(self.layout)
        
    def __del__(self):
        self.close()
            
class SerialportPulseGenerator(SmallApp):
    def create_gui(self):
        self.pulse_width_label = QtGui.QLabel('Pulse width [ms]', self)
        self.pulse_width_combobox = QtGui.QComboBox(self)
        self.pulse_width_combobox.setEditable(True)
        self.generate_button = QtGui.QPushButton('Generate pulse',  self)
    
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.pulse_width_label, 0, 0, 1, 1)
        self.layout.addWidget(self.pulse_width_combobox, 0, 1, 1, 1)
        self.layout.addWidget(self.generate_button, 0, 2, 1, 1)
        self.layout.addWidget(self.text_out, 1, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.connect(self.generate_button, QtCore.SIGNAL('clicked()'), self.generate_pulse)
        
    def generate_pulse(self):
        pulse_width = str(self.pulse_width_combobox.currentText())
        try:
            pulse_width = float(pulse_width) / 1000.0 - self.config.PULSE_OVERHEAD
            if pulse_width > self.config.MAX_PULSE_WIDTH:
                self.printc('Pulse is too long')
                return
            if pulse_width + self.config.PULSE_OVERHEAD < self.config.MIN_PULSE_WIDTH:
                self.printc('This pulse might take longer than requested, hardware cannot generate shorter pulses than {0} ms'.format(int(1000*self.config.MIN_PULSE_WIDTH)))
        except:
            self.printc('Provide pulse width in numeric format')
            return
        try:
            s = digital_io.SerialPortDigitalIO(self.config)
            for i in range(1):
                if pulse_width > 0:
                    s.pulse(pulse_width)
                else:
                    self.printc('Pulse width is too short')
                time.sleep(0.1)
            s.close()
        except:
            self.printc(traceback.format_exc())
            
class BehavioralTester(SmallApp):
    def create_gui(self):
        self.open_valve_for_a_time = gui_generic.PushButtonWithParameter(self, 'Open valve', 'Open time [ms]')
        self.open_valve = QtGui.QPushButton('Open valve',  self)
        self.close_valve = QtGui.QPushButton('Close valve',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.open_valve_for_a_time, 0, 0, 1, 7)
        self.layout.addWidget(self.open_valve, 1, 0, 1, 1)
        self.layout.addWidget(self.close_valve, 1, 1, 1, 1)
        self.layout.addWidget(self.text_out, 2, 0, 1, 10)
        self.setLayout(self.layout)
        
    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.open_valve_for_a_time.button, 'open_valve_for_a_time')
        self.connect_and_map_signal(self.open_valve, 'open_valve')
        self.connect_and_map_signal(self.close_valve, 'close_valve')
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)

class ReceptiveFieldPlotter(SmallApp):
    def __init__(self):
        SmallApp.__init__(self)
        self.resize(1300,900)
        self.image = gui.Image(self)
        self.image.setFixedWidth(500)
        self.image.setFixedHeight(500)
        self.plots = gui.ReceptiveFieldPlots(self)
        self.sa = QtGui.QScrollArea()
        self.sa.setWidget(self.plots)
        self.sa.setMinimumHeight(1000)
        self.plots.setMinimumWidth(1800)
        self.plots.setMinimumHeight(1000)
        self.open_file_button = QtGui.QPushButton('Open file', self)
        self.update_plots_button = QtGui.QPushButton('Update plots', self)
        self.text_out.setMaximumHeight(300)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.open_file_button, 0, 0, 1, 1)
        self.layout.addWidget(self.update_plots_button, 0, 1, 1, 1)
        self.layout.addWidget(self.sa, 1, 0, 1, 5)
        self.layout.addWidget(self.image, 1, 6, 1, 4)
        self.layout.addWidget(self.text_out, 2, 0, 1, 10)
        self.setLayout(self.layout)
        self.connect(self.open_file_button, QtCore.SIGNAL('clicked()'),  self.open_file)
        self.connect(self.update_plots_button, QtCore.SIGNAL('clicked()'),  self.update_plots)
        
    def update_image(self,img,mask=None):
        self.display_image = numpy.zeros((img.shape[0], img.shape[1], 3))
        self.display_image[:,:,1]=img
        if mask is not None:
            self.display_image[:,:,2] = mask
        self.image.set_image(self.display_image)
        
    def open_file(self):
        self.filename = str(self.ask4filename('Select data file', fileop.select_folder_exists(['/mnt/databig/debug/recfield', 'v:\\experiment_data1', '/tmp', 'c:\\temp\\rec']), '*.hdf5'))
        if not os.path.exists(self.filename):return
        if 'ReceptiveFieldExploreNew' not in self.filename:
            self.notify_user('Warning', 'This stimulus is not supported')
            return
        from visexpman.engine.vision_experiment import experiment_data
        import copy
        hh=hdf5io.Hdf5io(self.filename,filelocking=False)
        self.rawdata =copy.deepcopy(hh.findvar('rawdata'))
#        self.rawdata[50:70,40:70,:,0]=self.rawdata.mean()*2#TMP
        idnode = hh.findvar('_'.join(os.path.split(self.filename)[1].replace('.hdf5','').split('_')[-3:]))
        self.sfi = copy.deepcopy(idnode['stimulus_frame_info'])
        self.sd = copy.deepcopy(idnode['sync_data'])
        self.scale = copy.deepcopy(hh.findvar('image_scale')['row'][0])
        self.machine_config = utils.array2object(idnode['machine_config'])
        self.sync_sample_rate = float(self.machine_config.DAQ_CONFIG[0]['SAMPLE_RATE'])
        #Calculate timing from sync signal
        self.imaging_time = signal.trigger_indexes(self.sd[:,0])[::2]/self.sync_sample_rate
        self.stimulus_time = signal.trigger_indexes(self.sd[:,1])[::2]/self.sync_sample_rate
        #Display meanimage
        self.overall_activity = self.rawdata.mean(axis=0).mean(axis=0)[:,0]
        self.meanimage = self.rawdata.mean(axis = 2)[:,:,0]
        self.update_image(self.meanimage)
        self.image.img.setScale(self.scale)
        #Find repetitions and positions
        block_times, stimulus_parameter_times,block_info, self.organized_blocks = experiment_data.process_stimulus_frame_info(self.sfi, self.stimulus_time, self.imaging_time)
        self.positions = [o[0]['sig'][2]['pos'] for o in self.organized_blocks]
        self.colors = [o[0]['sig'][2]['color'] for o in self.organized_blocks]
        self.boundaries = []
        for o in self.organized_blocks:
            self.boundaries.append([[r['start'], r['end']  ] for r in o])
        hh.close()
        self.printc('File opened {0}'.format(self.filename))
        
    def update_plots(self):
        if not hasattr(self,'filename'):
            self.notify_user('Warning', 'Open a file first')
            return
        #Generate plot data
        if len(self.image.rois)==0:
            raw_trace = self.overall_activity
            self.notify_user('Warning', 'No roi selected,overall activity is plotted')
        elif len(self.image.rois)==1:
            roipos = self.image.rois[0].pos()
            roiposx=int(roipos.x()/self.scale)
            roiposy=int(roipos.y()/self.scale)
            roisize = int(self.image.rois[0].size().x()/self.scale)
            mask=numpy.zeros_like(self.meanimage, numpy.uint16)
            m=numpy.zeros_like(mask)
            m[roiposx:roiposx+roisize,roiposy:roiposy+roisize]=1
            coo=numpy.nonzero(m)
            rsq=(0.5*roisize)**2
            for cx,cy in zip(coo[0],coo[1]):
                if (roiposx+0.5*roisize-cx)**2+(roiposy+0.5*roisize-cy)**2<rsq:
                    mask[cx,cy]=1
            masked = numpy.rollaxis(self.rawdata, 2, 0)[:,:,:,0]
            masked *= mask
            raw_trace =numpy.cast['float'](masked).mean(axis=1).mean(axis=1)
            self.update_image(self.meanimage,mask*self.meanimage.max()*0.7)
        else:
            self.notify_user('Warning', 'More than one roi cannot be handled')
            return
        nrows = len(set([p['row'] for p in self.positions]))
        ncols = len(set([p['col'] for p in self.positions]))
        col_start = min(set([p['col'] for p in self.positions]))
        row_start = min(set([p['row'] for p in self.positions]))
        grid_size = self.organized_blocks[0][0]['sig'][2]['size']['row']
        traces = []
        for r in range(nrows):
            traces1 = []
            for r in range(ncols):
                traces1.append({})
            traces.append(traces1)
        plotrangemax=[]
        plotrangemin=[]
        for i in range(len(self.positions)):
            p=self.positions[i]
            plot_color = tuple([int(255*self.colors[i]), 0,0])
            r=int(round((self.positions[i]['row']-row_start)/grid_size))
            c=int(round((self.positions[i]['col']-col_start)/grid_size))
            scx=self.machine_config.SCREEN_CENTER['col']
            scy=self.machine_config.SCREEN_CENTER['row']
            traces[r][c]['title'] = 'x={0}, y={1}, utils.cr(({2},{3}))'.format(int(p['col']-scx), int(p['row']-scy), int(p['col']-scx), int(p['row']-scy))
            if not traces[r][c].has_key('trace'):
                traces[r][c]['trace'] = []
            boundaries = self.boundaries[i]
            for rep in range(len(boundaries)):
                boundary=boundaries[rep]
                y=raw_trace[boundary[0]:boundary[1]]
                x=self.imaging_time[boundary[0]:boundary[1]]
                x-=x[0]
                t = {'x':  x, 'y':y, 'color': plot_color}
                plotrangemax.append(max(y))
                plotrangemin.append(min(y))
                traces[r][c]['trace'].append(t)
        self.plots.set_plot_num(nrows,ncols)
        self.plots.addplots(traces)
        for pp in self.plots.plots:
            pp.setYRange(min(plotrangemin), max(plotrangemax))
        self.printc('Plots are updated')
        
class AfmCaImagingAnalyzer(SmallApp):
    def __init__(self):
        SmallApp.__init__(self)
        self.setWindowTitle('Ca Imaging Analyzer')
        self.resize(800,600)
        self.select_folder_button = QtGui.QPushButton('Select folder/Start analysis', self)
        self.select_folder_button.setFixedWidth(250)
        self.create_parameter_table()
        txt = \
            '''
            Preparation:
            1) Convert zvi files to tiff with Fiji/ImageJ. Make sure that the background is already removed
            2) Copy them to a folder
            Usage:
            3) Adjust parameters if necessary, however default parameters should work
            4) Press "Select folder/Start analysis" to select the folder where the datafiles are.
            5) After folder selection the analysis is initiated and takes approximately 100 seconds/file
                * It will search for cell like objects. Their activity will be extracted as roi curves
                * Error messages may appear on the DOS window
            Results:
            * The activity plot of the detected cells are saved to a cells_and_plots subfolder
            * The plots of the stimulated cells are copied to the data folder
            * The ROI area and ROI curve information is saved to a .mat file for each recording
            * The aggregated plots of the stimulated cells are saved to the aggregated_curves.mat.
            '''
        self.manual = QtGui.QLabel(txt, self)

        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.parameters_widget, 0, 0, 1, 1)
        self.layout.addWidget(self.manual, 0, 2, 1, 1)
        self.layout.addWidget(self.select_folder_button, 1, 0, 1, 1)
        self.layout.addWidget(self.text_out, 2, 0, 1, 1)
        self.setLayout(self.layout)
        self.connect(self.select_folder_button, QtCore.SIGNAL('clicked()'),  self.process_folder)
        
    def create_parameter_table(self):
        params = [
                    {'name': 'Export fileformat', 'type': 'list', 'value': 'eps', 'values': ['eps','png']},
                    {'name': 'Enable parallel processing', 'type': 'bool', 'value': False},
                    {'name': 'Frame rate', 'type': 'float', 'value': 1/0.64, 'siPrefix': True, 'suffix': 'Hz'},
                    {'name': 'Baseline time', 'type': 'float', 'value': 5, 'siPrefix': True, 'suffix': 's'},
                    {'name': 'Max cell diameter', 'type': 'float', 'value': 65.0,  'suffix': ' pixel'},
                    {'name': 'Cell detector gaussian filter\'s sigma', 'type': 'float', 'value': 0.2, },
                    {'name': 'Max offset from center', 'type': 'float', 'value': 100.0,  'suffix': ' pixel'},
                    {'name': 'df/f threshold', 'type': 'float', 'value': 0.2 }]
        from pyqtgraph.parametertree import Parameter, ParameterTree
        self.parameters_widget = ParameterTree(self, showHeader=False)
        self.parameters_widget.setFixedWidth(400)
        self.parameters = Parameter.create(name='params', type='group', children=params)
        self.parameters_widget.setParameters(self.parameters, showTop=False)
        
    def process_folder(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder', 'c:\\' if os.name=='nt' else '/' ))
        if os.path.exists(folder):
            parameters=dict([(n.name(), n.value()) for n in self.parameters.children()])
            from visexpman.users.rajib import ca_analysis
            msg='Processing {0}. Please wait'.format(folder)
            self.printc(msg)
            if 0:
                ca_analysis.process_folder(folder, baseline_duration=parameters['Baseline time'],
                                        export_fileformat = parameters['Export fileformat'],
                                        center_tolerance = parameters['Max offset from center'], 
                                        dfpf_threshold=parameters['df/f threshold'], 
                                        maxcellradius=parameters['Max cell diameter'],
                                        sigma=parameters['Cell detector gaussian filter\'s sigma'], 
                                        frame_rate=parameters['Frame rate'],
                                        ppenable = False and parameters['Enable parallel processing'])
            else:
                import subprocess
                if os.name=='nt':
                    folder=folder.replace('//','////')
                cmd='''python -c "from visexpman.users.rajib import ca_analysis;ca_analysis.process_folder('{0}', baseline_duration={1},export_fileformat = '{2}',center_tolerance = {3}, dfpf_threshold={4}, maxcellradius={5},sigma={6}, frame_rate= {7},ppenable = {8})"
                                        '''.format(folder,parameters['Baseline time'],parameters['Export fileformat'], parameters['Max offset from center'],
                                            parameters['df/f threshold'], parameters['Max cell diameter'], parameters['Cell detector gaussian filter\'s sigma'],
                                            parameters['Frame rate'],parameters['Enable parallel processing']
                                        )
                subprocess.call(cmd,shell=True)
            self.printc('Processing finished')
            
from pyqtgraph.parametertree import Parameter, ParameterTree
#TODO: NEXT: better low resolution image: reduce runtime, rotate image
class TileScanCorrection(SmallApp):
    def __init__(self):
        self.TILE_SIZE=512
        self.RESCALE=4
        SmallApp.__init__(self,enable_console=False)
        self.setWindowTitle('Tile Scan Correction')
        self.open_file_button = QtGui.QPushButton('Open', self)
        self.save_button = QtGui.QPushButton('Save', self)
        self.tif2tif_button = QtGui.QPushButton('Tif 2 Tif', self)
        self.tif2tif_button.setToolTip('''
        Tif files in selected folder will be read and saved back to tif. Opening saved back tif files takes less time
        ''')
        self.view=QtGui.QComboBox(self)
        self.low_resolution = gui_generic.LabeledCheckBox(self, 'Low resolution')
        self.low_resolution.input.setCheckState(2)
        self.show_correction = gui_generic.LabeledCheckBox(self, 'Show correction')
        self.red = gui_generic.LabeledCheckBox(self, 'Red')
        self.green = gui_generic.LabeledCheckBox(self, 'Green')
        self.blue = gui_generic.LabeledCheckBox(self, 'Blue')
        self.red.input.setCheckState(2)
        self.blue.input.setCheckState(2)
        self.green.input.setCheckState(2)
        self.image=gui_generic.Image(self)
        self.image.img.setLevels([0,255])
        self.npoints = gui_generic.LabeledComboBox(self, 'Number of points', map(str,[3,5,7,10,15]))
        self.npoints.input.setCurrentIndex(2)
        
        self.vcorrection=numpy.ones((3,self.TILE_SIZE))
        self.vcorrection_lr=numpy.ones((3,self.TILE_SIZE/self.RESCALE))
        self.hcorrection=numpy.ones((3,self.TILE_SIZE))
        self.hcorrection_lr=numpy.ones((3,self.TILE_SIZE/self.RESCALE))
        self.hprofile=numpy.ones((3,self.TILE_SIZE))
        self.vprofile=numpy.ones((3,self.TILE_SIZE))
        self.color_channels = [False,False,False]
        self.parameters_widget = ParameterTree(self, showHeader=False)
        self.parameters_widget.setMinimumWidth(200)
        self.parameters_widget.setMaximumWidth(500)
        self.update_parameter_tree()
            
        self.hplot=gui_generic.Plot(self)
        self.vplot=gui_generic.Plot(self)
        self.vplot.setMinimumWidth(300)
        self.hplot.setMinimumWidth(300)
        self.vplot.setFixedHeight(200)
        self.hplot.setFixedHeight(200)
        self.hplot.plot.setTitle('Horizontal correction')
        self.vplot.plot.setTitle('Vertical correction')
        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.image, 1, 0, 1, 5)
        self.layout.addWidget(self.parameters_widget, 1, 5, 1, 3)
        self.layout.addWidget(self.open_file_button, 0, 0, 1, 1)
        self.layout.addWidget(self.save_button, 0, 1, 1, 1)
        self.layout.addWidget(self.low_resolution, 0, 2, 1, 1)
        self.layout.addWidget(self.show_correction, 0, 3, 1, 1)
        self.layout.addWidget(self.red, 0, 4, 1, 1)
        self.layout.addWidget(self.green, 0, 5, 1, 1)
        self.layout.addWidget(self.blue, 0, 6, 1, 1)
        self.layout.addWidget(self.npoints, 0, 7, 1, 1)
        self.layout.addWidget(self.tif2tif_button, 0, 8, 1, 1)
        self.layout.addWidget(self.hplot, 2, 0, 1, 3)
        self.layout.addWidget(self.vplot, 2, 3, 1, 3)
        self.setLayout(self.layout)
        self.connect(self.open_file_button, QtCore.SIGNAL('clicked()'),  self.open_file)
        self.connect(self.save_button, QtCore.SIGNAL('clicked()'),  self.save)
        self.connect(self.show_correction.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.low_resolution.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.red.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.green.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.blue.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.npoints.input, QtCore.SIGNAL('currentIndexChanged(int)'), self.update_parameter_tree)
        self.connect(self.tif2tif_button, QtCore.SIGNAL('clicked()'), self.tif2tif)
        self.open_file_button.setFixedWidth(100)
        
    def _param_config(self,n):
        xval=numpy.linspace(0,1,n)
        xvalconfig=[{'name': '{0:0=2}'.format(i), 'type': 'float', 'value': xval[i]} for i in range(n)]
        yvalconfig=[{'name': '{0:0=2}'.format(i), 'type': 'float', 'value': 1.0, 'step': 0.01} for i in range(n)]
        x_group= {'name': 'X', 'type': 'group', 'expanded' : False, 'children': xvalconfig}
        hy_group= {'name': 'Horizontal Y', 'type': 'group', 'expanded' : True, 'children': yvalconfig}
        vy_group= {'name': 'Vertical Y', 'type': 'group', 'expanded' : True, 'children': yvalconfig}
        xy_group_template={'name': '', 'type': 'group', 'expanded' : True, 'children': [hy_group,vy_group]}
        import copy
        r=copy.deepcopy(xy_group_template)
        r['name']='Red'
        r['expanded'] = self.color_channels[0]
        g=copy.deepcopy(xy_group_template)
        g['name']='Green'
        g['expanded'] = self.color_channels[1]
        b=copy.deepcopy(xy_group_template)
        b['name']='Blue'
        b['expanded'] = self.color_channels[2]
        params = [x_group,r,g,b]
        return params
        
    def update_parameter_tree(self):
        self.parameters = Parameter.create(name='params', type='group', children=self._param_config(int(self.npoints.input.currentText())))
        self.parameters_widget.setParameters(self.parameters, showTop=False)
        self.parameters.sigTreeStateChanged.connect(self.parameter_changed)
        self.default_correction_curves()
        self.display_image()
        
    def default_correction_curves(self):
        '''
        tile profiles to default correction curves
        '''
        x=numpy.array([c.value() for c in [c for c in self.parameters.children() if c.name()=='X'][0].children()])
        indexes=x*self.TILE_SIZE
        indexes[-1]-=1
        hnew_values = numpy.round(self.hprofile[:,numpy.cast['int'](indexes)],2)
        vnew_values = numpy.round(self.vprofile[:,numpy.cast['int'](indexes)],2)
        colors=['Red','Green','Blue']
        self.parameters.blockSignals(True)
        for i in range(len(colors)):
            for d in [c for c in self.parameters.children() if c.name()==colors[i]][0].children():
                for v in d.children():
                    if 'Horizontal' in d.name():
                        v.setValue(hnew_values[i,int(v.name())])
                    elif 'Vertical' in d.name():
                        v.setValue(vnew_values[i,int(v.name())])
        self.parameters.blockSignals(False)
        self.points2correction_curves(x,hnew_values, vnew_values)
        self.update_plots(x,hnew_values,vnew_values)
            
    def update_plots(self,x,hcorrection, vcorrection):
        if hasattr(self, 'hplot') and hasattr(self, 'vplot'):
            colors=['Red','Green','Blue']
            curves = {'horizontal':[],'vertical':[]}
            self.hplot._clear_curves()
            self.vplot._clear_curves()
            self.hplot.curves = []
            self.vplot.curves = []
            plotparams = {'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)}
            for i in range(len(colors)):
                tracecolor=[0,0,0]
                tracecolor[i]=127
                plotparams['symbolBrush']=tuple(numpy.array(tracecolor)*2)
                c1 = self.hplot.plot.plot(pen=tracecolor, **plotparams)
                c1.setData(x,hcorrection[i])
                self.hplot.curves.append(c1)
                curves['horizontal'].append(hcorrection[i])
                c1 = self.vplot.plot.plot(pen=tracecolor, **plotparams)
                c1.setData(x,vcorrection[i])
                self.vplot.curves.append(c1)
                curves['vertical'].append(vcorrection[i])
            if hasattr(self, 'hprofile') and hasattr(self, 'vprofile'):
                x=numpy.arange(self.TILE_SIZE,dtype=numpy.float)/self.TILE_SIZE
                for i in range(len(colors)):
                    tracecolor=[0,0,0]
                    tracecolor[i]=255
                    c1 = self.hplot.plot.plot(pen=tracecolor)
                    c1.setData(x,self.hprofile[i])
                    self.hplot.curves.append(c1)
                    curves['horizontal'].append(self.hprofile[i])
                    c1 = self.vplot.plot.plot(pen=tracecolor)
                    c1.setData(x,self.vprofile[i])
                    self.vplot.curves.append(c1)
                    curves['vertical'].append(self.vprofile[i])
            y1=numpy.concatenate([c for c in curves['horizontal'] if c.sum() != 0])
            self.hplot.plot.setYRange(y1.min(), y1.max())
            y2=numpy.concatenate([c for c in curves['vertical'] if c.sum() != 0])
            self.vplot.plot.setYRange(y2.min(), y2.max())
            #This is necessary for unknown reason
            self.hplot.plot.setYRange(y1.min(), y1.max())
            self.vplot.plot.setYRange(y2.min(), y2.max())
        
    def open_file(self):
        '''
        1) Open file
        2) Create downsampled version of image
        3) Create trench corrected image which will be the input for correction
        4) Calculate tile profiles
        '''
        self.filename = self.ask4filename('Select tif file', 'c:\\' if os.name=='nt' else '/tmp/Santiago', '*.tif')
        if not os.path.exists(self.filename):
            return
        import tifffile
        self.tilescan=tifffile.imread(self.filename)
        if self.tilescan.shape[0]%self.TILE_SIZE!=0 or self.tilescan.shape[1]%self.TILE_SIZE!=0:
            self.notify_user('Warning', 'Size {1} of {0} is not the multiple of tile size ({2})'.format(self.filename,self.tilescan.shape, self.TILE_SIZE))
            return
        self.lowres=self.tilescan[0.5*self.RESCALE::self.RESCALE,0.5*self.RESCALE::self.RESCALE]#signal.downsample_2d_rgbarray(self.tilescan,self.RESCALE)
        self.color_channels = [numpy.nonzero(self.lowres[:,:,0])[0].shape[0]>0,numpy.nonzero(self.lowres[:,:,1])[0].shape[0]>0,numpy.nonzero(self.lowres[:,:,1])[0].shape[0]>0]
        self.trench_corrected=self.trench_correction(self.tilescan)
        self.trench_corrected_lowres=self.trench_correction(self.lowres)
        self.tile_profile(self.trench_corrected)
        self.default_correction_curves()
        self.image.plot.setTitle(self.filename)
        self.display_image()
        
    def trench_correction(self,image):
        corrected=numpy.cast['float'](numpy.copy(image))
        #Remove vertical trenches
        color=2
        for color in range(3):
            for i in range(1,corrected.shape[1]/512):
                start=i*512-1
                end=i*512+3
                corr=corrected[:,start:end,color]
                step=(corrected[:,end,color]-corrected[:,start,2])/(end-start-1)
                c=numpy.ones((corr.shape[0],2))
                c[:,1]*=2
                corr[:,1:3]=(c.T*step+corr[:,0]).T
                corrected[:,start:end,color]=corr
            #Remove horizontal trenches
            for i in range(1,corrected.shape[0]/512):
                start=i*512-1
                end=i*512+3
                corr=corrected[start:end,:,color]
                step=(corrected[end,:,color]-corrected[start,:,color])/(end-start-1)
                c=numpy.ones((2,corr.shape[1]))
                c[1]*=2
                corr[1:3]=c*step+corr[0]
                corrected[start:end,:,color]=corr
        corrected=numpy.where(corrected<0,0,corrected)
        return corrected
        
    def tile_profile(self,image):
        '''
        calculate average horizontal and vertical profiles
        '''
        self.hprofile=numpy.zeros((3,self.TILE_SIZE))
        self.vprofile=numpy.zeros((3,self.TILE_SIZE))
        for ci in range(3):
            p1=image[:,:,ci].mean(axis=1).reshape(image[:,:,0].shape[0]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            if p1.max()==0: continue
            self.hprofile[ci]=p1/p1.max()
            p2=image[:,:,ci].mean(axis=0).reshape(image[:,:,0].shape[1]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            if p2.max()==0: continue
            self.vprofile[ci]=p2/p2.max()
        
    def display_image(self):
        if not hasattr(self, 'trench_corrected'):
            return
        img = numpy.copy(self.trench_corrected_lowres if self.low_resolution.input.checkState()==2 else self.trench_corrected)
        if self.show_correction.input.checkState()==2:
            img=self.correct(self.trench_corrected)
        if self.red.input.checkState()==0:
            img[:,:,0]=0
        if self.green.input.checkState()==0:
            img[:,:,1]=0
        if self.blue.input.checkState()==0:
            img[:,:,2]=0
        self.image.set_image(numpy.fliplr(numpy.rollaxis(img,0,2)),alpha=1.0)
        
    def correct(self,image):
        '''
        Should work for both full resolution and low resolution
        '''
#        if self.low_resolution.input.checkState()==2:
#            vcorr=self.vcorrection_lr
#            hcorr=self.hcorrection_lr
#            size=self.TILE_SIZE/self.RESCALE
#        else:
        if 1:
            vcorr=self.vcorrection
            hcorr=self.hcorrection
            size=self.TILE_SIZE
        vcorr=numpy.where(vcorr==0.0, 1.0,vcorr)
        vcorr=1.0/vcorr
        hcorr=numpy.where(hcorr==0.0, 1.0,hcorr)
        hcorr=1.0/hcorr
        vcorr_img=numpy.zeros_like(image,dtype=numpy.float)
        hcorr_img=numpy.zeros_like(image,dtype=numpy.float)
#        for i in range(3):
#            if self.color_channels[i] and i==1:
#                vcorr_img[:,:,i] = numpy.tile(vcorr[i],(image.shape[0],image.shape[1]/size))
#                hcorr_img[:,:,i] = numpy.tile(hcorr[i],(image.shape[1], image.shape[0]/size)).T
        vcorr_img = numpy.tile(vcorr.T.flatten(),(image.shape[0], image.shape[1]/size)).reshape(image.shape[0],image.shape[1],3)
        hcorr_img = numpy.tile(hcorr.T, (image.shape[0]/size,image.shape[1])).reshape(image.shape[0],image.shape[1],3)
        out=image*hcorr_img*vcorr_img
        if self.low_resolution.input.checkState()==2:
#            out=signal.downsample_2d_rgbarray(out,self.RESCALE)
            out = out[0.5*self.RESCALE::self.RESCALE,0.5*self.RESCALE::self.RESCALE]
        return out
    
    def save(self):
        import tifffile
        fn=self.filename.replace('.tif','_corrected{0}.tif'.format('_lowres' if self.low_resolution.input.checkState()==2 else ''))
        tifffile.imsave(fn,numpy.cast['uint8'](255*signal.scale(self.correct(self.trench_corrected))))
        self.notify_user('Save done', 'Saved to {0}'.format(fn))
        
    def parameter_changed(self, param, changes):
        values={}
        x=numpy.array([v.value() for v in [c.children() for c in param.children() if c.name()=='X'][0]])
        colors=['Red','Green','Blue']
        hcorrection_points = numpy.zeros((3,x.shape[0]))
        vcorrection_points = numpy.zeros((3,x.shape[0]))
        for c in param.children():
            if c.name()=='X': continue
            h=numpy.array([v.value() for v in [t for t in c.children() if 'Horizontal' in t.name()][0].children()])
            v=numpy.array([v.value() for v in [t for t in c.children() if 'Vertical' in t.name()][0].children()])
            hcorrection_points[colors.index(c.name())]=h
            vcorrection_points[colors.index(c.name())]=v
        self.update_plots(x,hcorrection_points, vcorrection_points)
        self.points2correction_curves(x,hcorrection_points, vcorrection_points)
        self.display_image()
        
    def points2correction_curves(self,x,h,v):
        from scipy.interpolate import interp1d
        for i in range(3):
            #Horizontal
            fh=interp1d(x*self.TILE_SIZE, h[i], kind='linear')
            self.hcorrection[i]=fh(numpy.arange(self.TILE_SIZE))
            fhlr=interp1d(x*self.TILE_SIZE/self.RESCALE, h[i], kind='linear')
            self.hcorrection_lr[i]=fh(numpy.arange(self.TILE_SIZE/self.RESCALE))
            #Vertical
            fv=interp1d(x*self.TILE_SIZE, v[i], kind='linear')
            self.vcorrection[i]=fv(numpy.arange(self.TILE_SIZE))
            fvlr=interp1d(x*self.TILE_SIZE/self.RESCALE, v[i], kind='linear')
            self.vcorrection_lr[i]=fv(numpy.arange(self.TILE_SIZE/self.RESCALE))
            
    def tif2tif(self):
        self.folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder','c:\\' if os.name=='nt' else '/tmp/Santiago' ))
        if not os.path.exists(self.folder):
            return
        tiffiles=[f for f in fileop.find_files_and_folders(self.folder,  extension = 'tif')[1] if '_prep.tif' not in tf]
        import tifffile
        for tf in tiffiles:
            print tiffiles.index(tf)+1, len(tiffiles), tf
            data=tifffile.imread(tf)
            new_fn=tf.replace('.tif', '_prep.tif')
            tifffile.imsave(new_fn,data)
        self.notify_user('Tif file preparation is ready', '{0} files are converted'.format(len(tiffiles)))

def run_gui():
    '''
    1. argument: username
    2.  machine config class
    3. small application class name
    Example: python visexp_smallapp.py peter MEASetup FlowmeterLogger
    '''
    if len(sys.argv) < 4 and len(sys.argv) != 2:
        raise RuntimeError('The following commandline parameters are required: username machine_config and smallapp class name')
    app = Qt.QApplication(sys.argv)
    if len(sys.argv) ==4:
        gui = getattr(sys.modules[__name__], sys.argv[3])(sys.argv[1], sys.argv[2])
    else:
        gui = getattr(sys.modules[__name__], sys.argv[1])()
    app.exec_()

def rotate_images(root='.'):
    '''
    Prepares a folder of images for video stimulus by generating the rotation  of all images
    Input: image folder, output folder
    Output: checksum/hash of all folders
    '''
    from visexpman.engine.generic.gui import fileinput
    from visexpman.engine.generic.imageop import rotate_folder
    from visexpman.engine.generic.fileop import folder_signature
    image_folder=fileinput(title='Select image folder',root=root, mode='folder')
    output_folder=fileinput(title='Select output folder',root=root, mode='folder')
    if image_folder==output_folder:
        raise RuntimeError('rotated files cannot be put to image folder')
    for rot in range(0,360,90):
        subfolder=str(rot)
        print rot,image_folder, output_folder,os.path.join(output_folder,subfolder)
        rotate_folder(image_folder, os.path.join(output_folder,subfolder), rot)
    print 'Image files signature:', folder_signature(output_folder), 'Add this to stimulus file!'

if __name__ == '__main__':
    run_gui()
