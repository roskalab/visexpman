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
from visexpman.engine.generic import utils,log,fileop,signal
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
            
            
class TileScanCorrection(SmallApp):
    def __init__(self):
        self.TILE_SIZE=512
        SmallApp.__init__(self,enable_console=False)
        self.setWindowTitle('Tile Scan Correction')
        self.select_stack_button = QtGui.QPushButton('Select stack', self)
        self.save_mip_button = QtGui.QPushButton('Save MIP', self)
        self.show_correction = gui_generic.LabeledCheckBox(self, 'Show correction')
        self.red = gui_generic.LabeledCheckBox(self, 'Red')
        self.green = gui_generic.LabeledCheckBox(self, 'Green')
        self.blue = gui_generic.LabeledCheckBox(self, 'Blue')
        self.red.input.setCheckState(2)
        self.blue.input.setCheckState(2)
        self.green.input.setCheckState(2)
        self.image=gui_generic.Image(self)
        n=11
        defaultx = ','.join(map(str,numpy.linspace(0.0, 1.0, n)))
        defaulty= ','.join(['1']*n)
        self.vcorrection=numpy.ones(self.TILE_SIZE)
        self.hcorrection=numpy.ones(self.TILE_SIZE)
        params = [
                    {'name': 'Horizontal', 'type': 'group', 'expanded' : True, 'children': [
                        {'name': 'x', 'type': 'str', 'value': defaultx },
                        {'name': 'y', 'type': 'str', 'value': defaulty },
                        ]},
                    {'name': 'Vertical', 'type': 'group', 'expanded' : True, 'children': [
                        {'name': 'x', 'type': 'str', 'value': defaultx },
                        {'name': 'y', 'type': 'str', 'value': defaulty },
                        ]},
                    {'name': 'Parameters', 'type': 'group', 'expanded' : True, 'children': [
                        {'name': 'Interpolation', 'type': 'list', 'values': ['quadratic', 'cubic', 'linear', 'nearest' ] },
                        ]},]
        from pyqtgraph.parametertree import Parameter, ParameterTree
        self.parameters_widget = ParameterTree(self, showHeader=False)
        self.parameters_widget.setMinimumWidth(200)
        self.parameters_widget.setMaximumWidth(500)
        self.parameters = Parameter.create(name='params', type='group', children=params)
        self.parameters_widget.setParameters(self.parameters, showTop=False)
        self.parameters.sigTreeStateChanged.connect(self.parameter_changed)    
        
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
        self.layout.addWidget(self.parameters_widget, 1, 5, 1, 1)
        self.layout.addWidget(self.select_stack_button, 0, 0, 1, 1)
        self.layout.addWidget(self.save_mip_button, 0, 1, 1, 1)
        self.layout.addWidget(self.show_correction, 0, 2, 1, 1)
        self.layout.addWidget(self.red, 0, 3, 1, 1)
        self.layout.addWidget(self.green, 0, 4, 1, 1)
        self.layout.addWidget(self.blue, 0, 5, 1, 1)
        self.layout.addWidget(self.hplot, 2, 0, 1, 3)
        self.layout.addWidget(self.vplot, 2, 3, 1, 3)
        self.setLayout(self.layout)
        self.connect(self.select_stack_button, QtCore.SIGNAL('clicked()'),  self.select_stack)
        self.connect(self.save_mip_button, QtCore.SIGNAL('clicked()'),  self.save_mip)
        self.connect(self.show_correction.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.red.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.green.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.connect(self.blue.input, QtCore.SIGNAL('stateChanged(int)'), self.display_image)
        self.select_stack_button.setFixedWidth(100)
        
    
        
    def select_stack(self):
        self.filename= self.ask4filename('Select folder', 'c:\\' if os.name=='nt' else '/tmp/Santiago', '*.tif')
        import tifffile
        self.tilescandata=tifffile.imread(self.filename)#[:3*512,:3*512,:]
        self.image.set_image(self.tilescandata,alpha=1.0)
        self.image.img.setLevels([0,255])
        self.image_correction()
        
    def image_correction(self):
        
        vcorr= numpy.tile(self.vcorrection,(self.tilescandata.shape[1], self.tilescandata.shape[0]/self.TILE_SIZE)).T
        hcorr=  numpy.tile(self.hcorrection,(self.tilescandata.shape[0],self.tilescandata.shape[1]/self.TILE_SIZE))
        
        vcorr= numpy.tile(self.vcorrection,(self.tilescandata.shape[0],self.tilescandata.shape[1]/self.TILE_SIZE))
        hcorr=  numpy.tile(self.hcorrection,(self.tilescandata.shape[1], self.tilescandata.shape[0]/self.TILE_SIZE)).T
        
        corr=hcorr*vcorr
        self.corrected=numpy.zeros_like(self.tilescandata,dtype=numpy.float)
        for i in range(3):
            self.corrected[:,:,i]=self.tilescandata[:,:,i]*corr
        
    def display_image(self):
        disp=numpy.copy(self.corrected if self.show_correction.input.checkState()==2 else self.tilescandata)
        if self.red.input.checkState()==0:
            disp[:,:,0]=0
        if self.green.input.checkState()==0:
            disp[:,:,1]=0
        if self.blue.input.checkState()==0:
            disp[:,:,2]=0
        self.image.set_image(disp,alpha=1.0)

    def save_mip(self):
        import tifffile
        tifffile.imsave(self.filename.replace('.tif','_corrected.tif'),numpy.cast['uint8'](255*signal.scale(self.corrected)))
        
        
    def parameter_changed(self, param, changes):
        values={}
        for direction in param.children():
            if str(direction.name()) =='Parameters': 
                interp=direction.children()[0].value()
                continue
            values[str(direction.name())]=dict([(v.name(),numpy.array(map(float,v.value().split(',')))) for v in direction.children()])
        self._update_curves(values,interp)
        
    def _update_curves(self,curve_parameters,interp):
        plotparams = {'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)}
        from scipy.interpolate import interp1d
        k=interp#'cubic'#linear, nearest, zero, slinear, quadratic, 
        #Horizontal
        self.hplot._clear_curves()
        c1 = self.hplot.plot.plot(pen=(0,0,0), **plotparams)
        c1.setData(curve_parameters['Horizontal']['x']*self.TILE_SIZE, curve_parameters['Horizontal']['y'])
        c2 = self.hplot.plot.plot(pen=(0,255,255))
        fh=interp1d(curve_parameters['Horizontal']['x']*self.TILE_SIZE, curve_parameters['Horizontal']['y'], kind=k)
        self.hcorrection=fh(numpy.arange(self.TILE_SIZE))
        c2.setData(numpy.arange(self.TILE_SIZE), self.hcorrection)
        self.hplot.curves=[c1,c2]
        
        if hasattr(self, 'tilescandata'):
            c3 = self.hplot.plot.plot(pen=(0,255,0))
            curve=self.tilescandata[:,:,1].mean(axis=1).reshape(self.tilescandata[:,:,0].shape[0]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            curve/=curve.max()
            c3.setData(numpy.arange(self.TILE_SIZE), curve)
            c4 = self.hplot.plot.plot(pen=(0,0,255))
            curve=self.tilescandata[:,:,2].mean(axis=1).reshape(self.tilescandata[:,:,2].shape[0]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            curve/=curve.max()
            c4.setData(numpy.arange(self.TILE_SIZE), curve)
            self.hplot.curves.append(c3)
            self.hplot.curves.append(c4)
        
        
        #vertical
        self.vplot._clear_curves()
        c1 = self.vplot.plot.plot(pen=(0,0,0), **plotparams)
        c1.setData(curve_parameters['Vertical']['x']*self.TILE_SIZE, curve_parameters['Vertical']['y'])
        c2 = self.vplot.plot.plot(pen=(0,255,255))
        fv=interp1d(curve_parameters['Vertical']['x']*self.TILE_SIZE, curve_parameters['Vertical']['y'], kind=k)
        self.vcorrection=fv(numpy.arange(self.TILE_SIZE))
        c2.setData(numpy.arange(self.TILE_SIZE), self.vcorrection)
        self.vplot.curves=[c1,c2]
        if hasattr(self, 'tilescandata'):
            c3 = self.vplot.plot.plot(pen=(0,255,0))
            curve=self.tilescandata[:,:,1].mean(axis=0).reshape(self.tilescandata[:,:,0].shape[1]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            curve/=curve.max()
            c3.setData(numpy.arange(self.TILE_SIZE), curve)
            c4 = self.vplot.plot.plot(pen=(0,0,255))
            curve=self.tilescandata[:,:,2].mean(axis=0).reshape(self.tilescandata[:,:,2].shape[1]/self.TILE_SIZE,self.TILE_SIZE).mean(axis=0)
            curve/=curve.max()
            c4.setData(numpy.arange(self.TILE_SIZE), curve)
            self.vplot.curves.append(c3)
            self.vplot.curves.append(c4)
        
        
        
        self.image_correction()
        self.display_image()
    
        
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

if __name__ == '__main__':
    run_gui()
