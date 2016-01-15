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
from visexpman.engine.generic import utils,signal
from visexpman.engine.generic import file as fileop
from visexpman.engine.generic import log
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.hardware_interface import digital_io,flowmeter
from visexpA.engine.datahandlers import hdf5io

class SmallApp(QtGui.QWidget):
    '''
    Small  application gui
    '''
    def __init__(self, user=None, config_class=None):
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
        if hasattr(self.config, 'GUI_SIZE'):
            self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        else:
            self.resize(800,600)
        if hasattr(self.config, 'GUI_POSITION'):
            self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
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
            timestamp_string = utils.time_stamp_to_hm(time.time()) + ' '
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
        filename = QtGui.QFileDialog.getOpenFileNames(self, title, directory, filter)
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
            s = digital_io.SerialPulse(self.config.SERIAL_PORT)
            for i in range(1):
                if pulse_width > 0:
                    s.pulse(pulse_width)
                else:
                    self.printc('Pulse width is too short')
                time.sleep(0.1)
            s.close()
        except:
            self.printc(traceback.format_exc())
    
class ReceptiveFieldPlotter(SmallApp):
    def __init__(self):
        SmallApp.__init__(self)
        
        self.image = gui.Image(self)
        self.plots = gui.Plots(self)
        if len(sys.argv)==3 and sys.argv[2]=='rec':
            self.plots.setMinimumWidth(2200)
            self.resize(2500,900)
            self.plots.setMinimumHeight(900)
        else:
            self.plots.setMinimumWidth(800)
            self.plots.setMaximumHeight(300)
            self.resize(1500,800)
            self.image.setMinimumWidth(500)
            self.image.setMinimumHeight(500)
#        self.plots.show()
        self.open_file_button = QtGui.QPushButton('Open file', self)
        self.update_plots_button = QtGui.QPushButton('Update plots', self)
        help='First roi: cell, second roi: background'
        self.help = QtGui.QLabel(help, self)
        self.text_out.setMaximumHeight(200)
        self.debug=gui.PythonConsole(self, self)
        self.debug.setFixedHeight(200)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.open_file_button, 0, 0, 1, 1)
        self.layout.addWidget(self.update_plots_button, 0, 1, 1, 1)
        self.layout.addWidget(self.help, 0, 2, 1, 7)
        self.layout.addWidget(self.plots, 1, 0, 1, 3)
        self.layout.addWidget(self.image, 1, 6, 1, 2)
        self.layout.addWidget(self.text_out, 2, 0, 1, 5)
        self.layout.addWidget(self.debug, 2, 6, 1, 5)
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
        if len(self.plots.plots)>0:
            try:
                map(self.plots.removeItem, self.plots.plots)
            except:
                pass
        self.filenames = self.ask4filename('Select data file', fileop.select_folder_exists(['/mnt/datafast/experiment_data', 'v:\\experiment_data', '/tmp', 'c:\\temp\\rec']), '*.hdf5')
        self.filenames = map(str, self.filenames)
        if len(self.filenames)==0:return
        self.filename = self.filenames[0]
        if not os.path.exists(self.filename):return
        if len([fn for fn in self.filenames if 'ReceptiveFieldExploreNew' not in fn])>0:
            #self.notify_user('Warning', 'This is not a receptive field stimulus. Single ROI mode')
            self.is_recfield_stim=False
        else:
            self.is_recfield_stim=True
        
        import copy
        hh=hdf5io.Hdf5io(self.filename,filelocking=False)
        self.rawdata =copy.deepcopy(hh.findvar('rawdata'))
        self.t = hh.findvar('sync_signal')['data_frame_start_ms']*1e-3
        #Read sync data
        import visexpA.engine.component_guesser as cg
        self.printc(cg.select_measurement(hh).split('\\')[-1])
        idnode=hh.findvar(cg.select_measurement(hh).split('.')[-1])
        from visexpA.engine.datahandlers.importers import load_configs
        self.machine_config, self.experiment_config = load_configs(hh)
        if not self.is_recfield_stim:
            self.synct=numpy.linspace(0, idnode['sync_data'].shape[0]/float(self.machine_config.DAQ_CONFIG[0]['SAMPLE_RATE']), idnode['sync_data'].shape[0])
            self.sync_data=idnode['sync_data'][:, 0]
            self.sync_visual_stim=idnode['sync_data'][:, 1]
            self.sync_l_stim=idnode['sync_data'][:, 2]
        if self.rawdata is None:
            self.notify_user('Warning', 'Not yet prcessed by Jobhandler')
            self.plots.setFixedWidth(1000)
            hh.close()
            return
        self.scale = copy.deepcopy(hh.findvar('image_scale')['row'][0])
#        self.rawdata[50:70,40:70,:,0]=self.rawdata.mean()*2#TMP
#        idnode = hh.findvar('_'.join(os.path.split(self.filename)[1].replace('.hdf5','').split('_')[-3:]))
#        self.sfi = copy.deepcopy(idnode['stimulus_frame_info'])
#        self.sd = copy.deepcopy(idnode['sync_data'])
        
#        self.machine_config = utils.array2object(idnode['machine_config'])
#        self.sync_sample_rate = float(self.machine_config.DAQ_CONFIG[0]['SAMPLE_RATE'])
        #Calculate timing from sync signal
#        self.imaging_time = signal.trigger_indexes(self.sd[:,0])[::2]/self.sync_sample_rate
#        self.stimulus_time = signal.trigger_indexes(self.sd[:,1])[::2]/self.sync_sample_rate
        #Display meanimage
        self.overall_activity = self.rawdata.mean(axis=0).mean(axis=0)[:,0]
        self.meanimage = self.rawdata.mean(axis = 2)[:,:,0]
        self.image.setFixedWidth(400)
        self.image.setFixedHeight(int(400*float(self.meanimage.shape[1])/self.meanimage.shape[0]))
        self.update_image(self.meanimage)
        self.image.img.setScale(self.scale)
        #Find repetitions and positions
#        block_times, stimulus_parameter_times,block_info, self.organized_blocks = experiment_data.process_stimulus_frame_info(self.sfi, self.stimulus_time, self.imaging_time)
#        self.positions = [o[0]['sig'][2]['pos'] for o in self.organized_blocks]
#        self.colors = [o[0]['sig'][2]['color'] for o in self.organized_blocks]
#        self.boundaries = []
#        for o in self.organized_blocks:
#            self.boundaries.append([[r['start'], r['end']  ] for r in o])
        hh.close()
        self.printc('Files opened {0}'.format(', '.join([os.path.split(f)[1] for f in self.filenames])))
        
    def get_positions(self,filename):
        import copy
        from visexpman.engine.vision_experiment import experiment_data
        idnode = hdf5io.read_item(filename, '_'.join(os.path.split(filename)[1].replace('.hdf5','').split('_')[-3:]), filelocking=False)
        self.machine_config = utils.array2object(idnode['machine_config'])
        sd = copy.deepcopy(idnode['sync_data'])
        self.sync_sample_rate = float(self.machine_config.DAQ_CONFIG[0]['SAMPLE_RATE'])
        stimulus_time = signal.trigger_indexes(sd[:,1])[::2]/self.sync_sample_rate
        sfi = copy.deepcopy(idnode['stimulus_frame_info'])
        imaging_time = signal.trigger_indexes(sd[:,0])[::2]/self.sync_sample_rate
        block_times, stimulus_parameter_times,block_info, self.organized_blocks = experiment_data.process_stimulus_frame_info(sfi, stimulus_time, imaging_time)
        try:
            positions = [o[0]['sig'][2]['angle'] for o in self.organized_blocks]
            self.angles=True
        except:
            positions = [o[0]['sig'][2]['pos'] for o in self.organized_blocks]
            self.angles=False
        colors = [o[0]['sig'][2]['color'] for o in self.organized_blocks]
        boundaries = []
        for o in self.organized_blocks:
            boundaries.append([[r['start'], r['end']  ] for r in o])
        self.ontime = utils.array2object(idnode['experiment_config']).ON_TIME
        self.offtime = utils.array2object(idnode['experiment_config']).OFF_TIME
        return stimulus_time, imaging_time, positions, colors, boundaries
        
    def update_plots(self):
        if not hasattr(self,'filename'):
            self.notify_user('Warning', 'Open a file first')
            return
        #Generate plot data
        if not self.is_recfield_stim and len(self.image.rois)==1:
            if hasattr(self, 'p'):
                self.plots.removeItem(self.p) 
                del self.p
            filename = self.filenames[0]
            rawdata = hdf5io.read_item(filename, 'rawdata',filelocking=False)
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
            import copy
            masked = numpy.rollaxis(rawdata, 2, 0)[:,:,:,0]
            masked *= mask
            raw_trace=masked.mean(axis=1).mean(axis=1)
            self.update_image(self.meanimage,mask*self.meanimage.max()*0.7)
            self.p=self.plots.addPlot()
            self.p.plot(self.t[:raw_trace.shape[0]], raw_trace-raw_trace.min(), pen=(255, 0, 0))
            self.p.plot(self.synct, numpy.where(self.sync_visual_stim>1.6, 1, 0), pen=(0, 128, 0))
            if hasattr(self.experiment_config,  'FLASH_AMPLITUDE'):
                if self.experiment_config.FLASH_AMPLITUDE>0.1:
                    s=numpy.where(self.sync_l_stim>self.experiment_config.FLASH_AMPLITUDE, 1, 0)
                else:
                    s=self.sync_l_stim
                self.p.plot(self.synct, s, pen=(0, 0,  255))
            #self.p.plot(self.synct, self.sync_data, pen=(0, 128,  255))
            self.p.showGrid(True,True,1.0)
            
            
#            for pp in self.plots.plots:
#                pp.setYRange(min(plotrangemin), max(plotrangemax))
            self.printc('Plots are updated')
            
            
            return
        if len(self.image.rois)==0:
            raw_trace = self.overall_activity
            self.notify_user('Warning', 'No roi selected,overall activity is plotted')
        elif len(self.image.rois)==2:
            aggregated_data = []
            t0=time.time()
            for filename in self.filenames:
                rawdata = hdf5io.read_item(filename, 'rawdata',filelocking=False)
                stimulus_time, imaging_time, positions, colors, boundaries = self.get_positions(filename)
                for i in range(2):
                    roipos = self.image.rois[i].pos()
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
                    import copy
                    masked = numpy.rollaxis(rawdata, 2, 0)[:,:,:,0]
                    masked *= mask
    #            raw_trace =numpy.cast['float'](masked)
                    if i==0:
                        raw_trace=masked.mean(axis=1).mean(axis=1)
                        self.update_image(self.meanimage,mask*self.meanimage.max()*0.7)
                    elif i==1:
                        background=masked.mean(axis=1).mean(axis=1)
                raw_trace -=background
                aggregated_data.append([raw_trace, stimulus_time, imaging_time, positions, colors, boundaries])
        else:
            self.notify_user('Warning', 'Exactly two rois should be placed: 1. cell, 2. bakcground')
            return
        self.positions = aggregated_data[0][3]
        nrows = len(set([p['row'] for p in self.positions]))
        ncols = len(set([p['col'] for p in self.positions]))
        col_start = min(set([p['col'] for p in self.positions]))
        row_start = min(set([p['row'] for p in self.positions]))
        if self.angles:
            row_vals=list(set(numpy.array(self.positions)['row']))
            row_vals.sort()
            col_vals=list(set(numpy.array(self.positions)['col']))
            col_vals.sort()
            grid_size = utils.rc((numpy.diff(row_vals)[0],numpy.diff(col_vals)[0]))
        else:
            grid_size = self.organized_blocks[0][0]['sig'][2]['size']
        traces = []
        for r in range(nrows):
            traces1 = []
            for r in range(ncols):
                traces1.append({})
            traces.append(traces1)
        plotrangemax=[]
        plotrangemin=[]
        for ad in aggregated_data:
            raw_trace, stimulus_time, imaging_time, positions, colors, boundaries = ad
            for i in range(len(positions)):
                p=positions[i]
                plot_color = tuple([0, 0, int(128*colors[i])])
                r=int(round((positions[i]['row']-row_start)/grid_size['row']))
                c=int(round((positions[i]['col']-col_start)/grid_size['col']))
                scx=self.machine_config.SCREEN_CENTER['col']
                scy=self.machine_config.SCREEN_CENTER['row']
    #            traces[r][c]['title'] = 'x={0}, y={1}, utils.cr(({2},{3}))'.format(int(p['col']-scx), int(p['row']-scy), int(p['col']-scx), int(p['row']-scy))
                traces[r][c]['title'] = 'cr(({0},{1}))'.format(int(p['col']-scx), int(p['row']-scy))
                if not traces[r][c].has_key('trace'):
                    traces[r][c]['trace'] = []
                for rep in range(len(boundaries[i])):
                    boundary=boundaries[i][rep]
                    y=raw_trace[boundary[0]:boundary[1]]
                    x=imaging_time[boundary[0]:boundary[1]]
                    x-=x[0]
                    baseline = y[numpy.where(x<0.5*self.offtime)[0]].mean()
                    y/=baseline
                    t = {'x':  x, 'y':y, 'color': plot_color}
                    plotrangemax.append(max(y))
                    plotrangemin.append(min(y))
                    traces[r][c]['trace'].append(t)
#                #calculate average
#                y = numpy.array([t['y'] for t in traces[r][c]['trace']]).mean(axis=0)
#                x = traces[r][c]['trace'][0]['x']
#                t = {'x':  x, 'y':y, 'color': (255, 0, 0)}
#                traces[r][c]['trace'].append(t)
#                traces[r][c]['response_size'] = y[numpy.where(numpy.logical_and(x>self.offtime*0.5, x<self.offtime*0.5+self.ontime))[0]].mean()
#                response_sizes.append(traces[r][c]['response_size'])
#        for i in range(len(traces)):
#            for j in range(len(traces[i])):
#                traces[i][j]['response_size_scaled'] = (traces[i][j]['response_size'] - min(response_sizes))/(max(response_sizes)-min(response_sizes))
        response_sizes = []
        for r in range(len(traces)):
            for c in range(len(traces[r])):
                #Calculate mean of repetitions
                l = min([t['y'].shape[0] for t in traces[r][c]['trace']])
                y=numpy.array([t['y'][:l] for t in traces[r][c]['trace']]).mean(axis=0)
                x= traces[r][c]['trace'][0]['x'][:l]
                t = {'x':  x, 'y':y, 'color': (255, 0, 0)}
                traces[r][c]['trace'].append(t)
                traces[r][c]['response_size'] = y[numpy.where(numpy.logical_and(x>self.offtime*0.5, x<self.offtime*0.5+self.ontime))[0]].mean()
                response_sizes.append(traces[r][c]['response_size'])
        for r in range(len(traces)):
            for c in range(len(traces[r])):
                traces[r][c]['response_size_scaled'] = (traces[r][c]['response_size'] - min(response_sizes))/(max(response_sizes)-min(response_sizes))
        self.plots.set_plot_num(nrows,ncols)
        self.plots.addplots(traces)
        for pp in self.plots.plots:
            pp.setYRange(min(plotrangemin), max(plotrangemax))
        self.printc('Plots are updated')
        

def run_gui():
    '''
    1. argument: username
    2.  machine config class
    3. small application class name
    Example: python visexp_smallapp.py peter MEASetup FlowmeterLogger
    '''
#    if len(sys.argv) < 4 and len(sys.argv) != 2:
#        raise RuntimeError('The following commandline parameters are required: username machine_config and smallapp class name')
    app = Qt.QApplication(sys.argv)
    if len(sys.argv) ==4:
        gui = getattr(sys.modules[__name__], sys.argv[3])(sys.argv[1], sys.argv[2])
    else:
        gui = getattr(sys.modules[__name__], sys.argv[1])()
    app.exec_()

if __name__ == '__main__':
    run_gui()
