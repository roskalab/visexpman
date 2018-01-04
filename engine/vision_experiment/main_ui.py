import copy
import time
import numpy
import os.path
import itertools
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph

from visexpman.engine.generic import stringop,utils,gui,signal,fileop,introspect,colors
from visexpman.engine.vision_experiment import gui_engine, experiment,experiment_data


class Advanced(QtGui.QWidget):
    def __init__(self,parent):
        self.parent=parent
        QtGui.QWidget.__init__(self,parent)
        self.fix=QtGui.QPushButton('Fix rois, reexport files' ,parent=self)
        self.test=QtGui.QPushButton('Test' ,parent=self)
        
        self.p=gui.TabbedPlots(self,['a','b'])
        self.p.setMinimumWidth(300)
        self.p.setMinimumHeight(300)
        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.fix, 0, 0)
        self.layout.addWidget(self.test, 1, 0)
        self.layout.addWidget(self.p, 2, 0)
        self.setLayout(self.layout)
        self.connect(self.fix, QtCore.SIGNAL('clicked()'), self.fix_clicked)
        self.connect(self.test, QtCore.SIGNAL('clicked()'), self.test_clicked)
        
        
    def fix_clicked(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder', self.parent.machine_config.EXPERIMENT_DATA_PATH))
        if os.path.exists(folder):
            self.parent.to_engine.put({'function': 'fix_files', 'args':[folder]})
            
    def check_files_clicked(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder', self.parent.machine_config.EXPERIMENT_DATA_PATH))
        if os.path.exists(folder):
            self.parent.to_engine.put({'function': 'check_files', 'args':[folder]})
            
    def check_stim_timing_clicked(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder', self.parent.machine_config.EXPERIMENT_DATA_PATH))
        if os.path.exists(folder):
            self.parent.to_engine.put({'function': 'check_stim_timing', 'args':[folder]})
            
    def test_clicked(self):
        raise RuntimeError('ok')

class CellBrowser(pyqtgraph.TreeWidget):
    def __init__(self,parent):
        self.parent=parent
        pyqtgraph.TreeWidget.__init__(self,parent)
        self.setColumnCount(1)
        self.setHeaderLabels(QtCore.QStringList(['']))
        self.setMaximumWidth(350)
        self.itemDoubleClicked.connect(self.item_selected)
        
    def populate(self, cells):
        self.blockSignals(True)
        self.clear()
        for i in range(len(cells)):
            cell=cells[i]
            cellname = '{0}_{1:0=3}'.format(cell['scan_region'], i)
            cellw=QtGui.QTreeWidgetItem([cellname])
            self.addTopLevelItem(cellw)
            for stimulus_name in cell.keys():
                if stimulus_name=='scan_region':
                    continue
                stimulus_level_widget = QtGui.QTreeWidgetItem([stimulus_name])
                cellw.addChild(stimulus_level_widget)
                for filename in cell[stimulus_name].keys():
                    file_level_widget = QtGui.QTreeWidgetItem([filename])
                    stimulus_level_widget.addChild(file_level_widget)
        self.blockSignals(False)
        
    def item_selected(self,par):
        path=self._get_path(par)
        self.parent.to_engine.put({'function': 'display_cell', 'args':[path]})
        
    def _get_path(self,par):
        p=par.parent()
        path=[str(par.text(0))]
        if p is None:
            return path
        while p is not None:
            path.append(str(p.text(0)))
            p=p.parent()
        path.reverse()
        return path
    
class StimulusTree(pyqtgraph.TreeWidget):
    def __init__(self,parent, root,subdirs):
        self.parent=parent
        self.subdirs=subdirs
        self.root=root
        pyqtgraph.TreeWidget.__init__(self,parent)
        self.setColumnCount(1)
        self.setHeaderLabels(QtCore.QStringList(['']))#, 'Date Modified']))
        self.setMaximumWidth(350)
        self.setMinimumHeight(400)
        self.populate()
        self.itemDoubleClicked.connect(self.stimulus_selected_for_open)
        self.itemClicked.connect(self.stimulus_selected)
        self.itemSelectionChanged.connect(self.get_selected_stimulus)
        #Local menu
        self.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)

    def open_menu(self, position):
        self.menu = QtGui.QMenu(self)
        stimulus_info_action = QtGui.QAction('Stimulus duration', self)
        stimulus_info_action.triggered.connect(self.stimulus_info_action)
        self.menu.addAction(stimulus_info_action)
        stimulus_par_action = QtGui.QAction('Stimulus parameters', self)
        stimulus_par_action.triggered.connect(self.stimulus_par_action)
        self.menu.addAction(stimulus_par_action)
        self.menu.exec_(self.viewport().mapToGlobal(position))
        
    def stimulus_info_action(self):
        duration=experiment.get_experiment_duration( self.classname, self.parent.machine_config, source=fileop.read_text_file(self.filename))
        self.parent.printc('{0} stimulus takes {1:0.0f} seconds'.format(self.classname, duration))

    def stimulus_par_action(self):
        parameters=experiment.read_stimulus_parameters(self.classname, self.filename, self.parent.machine_config)
        self.parent.printc('{0} parameters'.format(self.classname))
        for k, v in parameters.items():
            self.parent.printc('{0} = {1}'.format(k,v))
        
    def populate(self):
        subdirs=map(os.path.join,len(self.subdirs)*[self.root], self.subdirs)
        files = fileop.find_files_and_folders(self.root)[1]
        files = [f for f in files if os.path.splitext(f)[1] =='.py' and os.path.dirname(f) in subdirs]
        experiment_configs = []
        for f in files:
            try:
                confnames = experiment.parse_stimulation_file(f).keys()
                experiment_configs.extend(map(os.path.join, [f]*len(confnames), confnames))
            except:
                pass#Ignoring py files with error
        #Clear tree view
        self.blockSignals(True)
        self.clear()
        #Populate with files and stimulus classes
        branches = [list(e.replace(self.root, '')[1:].split(os.sep)) for e in experiment_configs]
        added_items = {}
        for branch in branches:
            for level in range(len(branch)):
                if not added_items.has_key(level):
                    added_items[level] = []
                widgets = [w for w in added_items[level] if str(w.text(0)) == branch[level]]
                if len(widgets)==0:
                    newwidget=QtGui.QTreeWidgetItem([branch[level]])
                    if level==0:
                        self.addTopLevelItem(newwidget)
                    else:
                        try:
                            upper_widget = [w for w in added_items[level-1] if str(w.text(0)) == branch[level-1]][0]
                        except:
                            import pdb
                            pdb.set_trace()
                        upper_widget.addChild(newwidget)
                    added_items[level].append(newwidget)
        self.blockSignals(False)
        
    def stimulus_selected_for_open(self,selected_widget):
        self.stimulus_selected(selected_widget, open=True)
            
    def stimulus_selected(self,selected_widget, open=False):
        if self._is_experiment_class(selected_widget):
            self.filename, self.classname = self.filename_from_widget(selected_widget)
            if open:
                self.parent.to_engine.put({'function': 'open_stimulus_file', 'args':[self.filename, self.classname]})
            
    def select_stimulus(self, filename_classname):
        '''
        Selects stimulus class in file/class tree and expands the tree
        '''
        filename_classname = filename_classname.replace(self.root, '').split(os.sep)[1:]
        widget_ref = None
        for tli in self.topLevelItems():
            if str(tli.text(0)) == filename_classname[0]:
                widget_ref = tli
                widget_ref.setExpanded(True)
                for level in range(1, len(filename_classname)):
                    child_found=False
                    for childi in range(widget_ref.childCount()):
                        if widget_ref.child(childi) is None:
                            continue
                        if widget_ref.child(childi).text(0) == filename_classname[level]:
                            widget_ref.setExpanded(True)
                            widget_ref = widget_ref.child(childi)
                            child_found=True
                    if not child_found:
                        return
        if widget_ref is not None:
            self.setItemSelected(widget_ref, True)
        
    def get_selected_stimulus(self):
        selected_widget = self.selectedItems()
        if len(selected_widget)==0:
            self._give_not_stimulus_selected_warning()
            return
        else:
            selected_widget = selected_widget[0]
            if self._is_experiment_class(selected_widget):
                filename, classname = self.filename_from_widget(selected_widget)
                self.setHeaderLabels(QtCore.QStringList([classname]))
                self.parent.to_engine.put({'data': filename+os.sep+classname, 'path': 'stimulusbrowser/Selected experiment class', 'name': 'Selected experiment class'})
        
    def _is_experiment_class(self, widget):
        return not(widget.parent() is None or str(widget.parent().text(0))[-3:] != '.py')
        
    def filename_from_widget(self, widget, give_warning=True):
        if not self._is_experiment_class(widget) and give_warning:
            self._give_not_stimulus_selected_warning()
            return
        next_in_chain = widget
        items = []
        while True:
            if next_in_chain is not None and hasattr(next_in_chain, 'text'):
                items.append(str(next_in_chain.text(0)))
                next_in_chain = next_in_chain.parent()
            else:
                break
        classname = str(widget.text(0))
        items.reverse()
        filename = os.path.join(self.root, os.sep.join(items[:-1]))
        return filename, classname
        
    def _give_not_stimulus_selected_warning(self):
        QtGui.QMessageBox.question(self, 'Warning', 'No stimulus class selected. Please select one', QtGui.QMessageBox.Ok)        
        
class RoiShift(gui.ArrowButtons):
    def __init__(self,parent):
        gui.ArrowButtons.__init__(self, 'Shift Rois', parent)
        
    def arrow_clicked(self, direction):
        h=0
        v=0
        if direction == 'left':
            h -= 1
        elif direction == 'right':
            h += 1
        elif direction == 'down':
            v -= 1
        elif direction == 'up':
            v += 1
        self.parent.parent.parent.to_engine.put({'function': 'roi_shift', 'args':[h,v]})
        
class Image(gui.Image):
    def __init__(self, parent, roi_diameter=2):
        gui.Image.__init__(self, parent, roi_diameter)
        self.setMaximumWidth(parent.machine_config.GUI['SIZE']['col']/2)
        self.setMaximumHeight(parent.machine_config.GUI['SIZE']['col']/2)
        self.plot.setLabels(left='um', bottom='um')
        self.connect(self, QtCore.SIGNAL('roi_mouse_selected'), parent.roi_mouse_selected)
        self.connect(self, QtCore.SIGNAL('wheel_double_click'), parent.add_roi_action)
            
class DataFileBrowser(gui.FileTree):
    def __init__(self,parent, root, extensions):
        gui.FileTree.__init__(self,parent, root, extensions)
        self.doubleClicked.connect(self.file_open)
        self.clicked.connect(self.file_selected)
        self.setToolTip('Double click on file to open')
        self.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
        self.setSortingEnabled(True)
        
    def convert_filename(self, filename):
        ext=os.path.splitext(filename)[1]
        file2open=filename
        if ext=='.mat':#If mat or _mat is selected, corresponding hdf5 is opened
            if '_mat.mat' in filename:
                file2open=experiment_data.add_mat_tag(filename)
            else:
                file2open=filename.replace('.mat', '.hdf5')
        return file2open
        
    def file_selected(self,index):
        self.selected_filename = gui.index2filename(index)
        
    def file_open(self,index):
        filename = gui.index2filename(index)
        if os.path.isdir(filename): return#Double click on folder is ignored
        ext = os.path.splitext(filename)[1]
        if ext  in  ['.hdf5', '.mat']:
            function = 'open_datafile'
            keep_rois=(self.parent.parent.analysis_helper.keep_rois.input.checkState()==2) if hasattr(self.parent.parent.analysis_helper, 'keep_rois') else False
            self.parent.parent.to_engine.put({'function': 'keep_rois', 'args':[keep_rois]})
            if hasattr(self.parent.parent.analysis_helper, 'keep_rois'):#Works only on retina platform
                self.parent.parent.analysis_helper.keep_rois.input.setCheckState(0) 
        else:
            raise NotImplementedError(filename)
        self.parent.parent.to_engine.put({'function': function, 'args':[self.convert_filename(filename)]})

    def open_menu(self, position):
        self.menu = QtGui.QMenu(self)
        delete_action = QtGui.QAction('Remove recording', self)
        delete_action.triggered.connect(self.delete_action)
        self.menu.addAction(delete_action)
        plot_action = QtGui.QAction('Plot  sync signals', self)
        plot_action.triggered.connect(self.plot_action)
        self.menu.addAction(plot_action)
        self.menu.exec_(self.viewport().mapToGlobal(position))
        
    def delete_action(self):
        if hasattr(self, 'selected_filename'):
            self.parent.parent.to_engine.put({'function': 'remove_recording', 'args':[self.convert_filename(self.selected_filename)]})
            
    def plot_action(self):
        if hasattr(self, 'selected_filename'):
            self.parent.parent.to_engine.put({'function': 'plot_sync', 'args':[self.convert_filename(self.selected_filename)]})
            
class AnalysisHelper(QtGui.QWidget):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        self.show_rois = gui.LabeledCheckBox(self, 'Show/hide rois')
        self.show_rois.input.setCheckState(2)
        if parent.parent.machine_config.PLATFORM=='elphys_retinal_ca':
            self.keep_rois = gui.LabeledCheckBox(self, 'Keep rois')
            self.keep_rois.setToolTip('Check this it before opening next file and rois will be kept as a reference set and will be used for the next file')
            self.show_repetitions = gui.LabeledCheckBox(self, 'Show Repetitions')
            self.show_repetitions.input.setCheckState(0)
            self.find_repetitions = QtGui.QPushButton('Find repetitions' ,parent=self)
            self.aggregate = QtGui.QPushButton('Aggregate cells' ,parent=self)
            self.show_trace_parameter_distribution = QtGui.QPushButton('Trace parameter distributions' ,parent=self)
            self.find_cells_scaled = gui.LabeledCheckBox(self, 'Find Cells Scaled')
            self.roi_adjust = RoiShift(self)
#        self.trace_parameters = QtGui.QLabel('', self)
#        self.trace_parameters.setFont(QtGui.QFont('Arial', 10))
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_rois,0,0,1,1)
        if parent.parent.machine_config.PLATFORM=='elphys_retinal_ca':
            self.layout.addWidget(self.keep_rois,1,0,1,1)
            self.layout.addWidget(self.roi_adjust,0,1,2,2)
#        self.layout.addWidget(self.trace_parameters,0,2,2,1)
            self.layout.addWidget(self.show_repetitions,0,3,1,1)
            self.layout.addWidget(self.find_repetitions,1,3,1,1)
            self.layout.addWidget(self.aggregate,2,3,1,1)
            self.layout.addWidget(self.show_trace_parameter_distribution,3,3,1,1)
            self.layout.addWidget(self.find_cells_scaled,3,0,1,1)
        self.setLayout(self.layout)
        self.setFixedHeight(140)
        self.setFixedWidth(530)
        if parent.parent.machine_config.PLATFORM=='elphys_retinal_ca':
            self.connect(self.find_repetitions, QtCore.SIGNAL('clicked()'), self.find_repetitions_clicked)
            self.connect(self.show_trace_parameter_distribution, QtCore.SIGNAL('clicked()'), self.show_trace_parameter_distribution_clicked)
            self.connect(self.aggregate, QtCore.SIGNAL('clicked()'), self.aggregate_clicked)
        
    def find_repetitions_clicked(self):
        self.parent.parent.to_engine.put({'function': 'find_repetitions', 'args':[]})
        
    def show_trace_parameter_distribution_clicked(self):
        self.parent.parent.to_engine.put({'function': 'display_trace_parameter_distribution', 'args':[]})
        
    def aggregate_clicked(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, 'Select folder', self.parent.parent.machine_config.EXPERIMENT_DATA_PATH))
        if os.path.exists(folder):
            self.parent.parent.to_engine.put({'function': 'aggregate', 'args':[folder]})

class TraceParameterPlots(QtGui.QWidget):
    def __init__(self, distributions):
        QtGui.QWidget.__init__(self)
        self.setWindowIcon(gui.get_icon('main_ui'))
        self.distributions = distributions
        self.setWindowTitle('Parameter distributions')
        self.tab = QtGui.QTabWidget(self)
        self.plots = {}
        plot_modes = ['1 axis', '2 axis']
        parameter_names = [stringop.to_title(n) for n in distributions[distributions.keys()[0]].keys()]
        for n,m in itertools.product(plot_modes, parameter_names):
            self.plots[m+'@'+n]=gui.Plot(self)
        for k in self.plots.keys():
            self.tab.addTab(self.plots[k], k)
        self.tab.setTabPosition(self.tab.South)
        self.update_plots()
        self.setGeometry(50,50,1000,500)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.tab,0,0,3,4)
        self.setLayout(self.layout)
        
    def _plotname2distributionname(self,plotname):
        if self.distributions.has_key(plotname):
                ki=plotname
        else:
            ki = plotname.split('@')
            ki.reverse()
            ki = '@'.join(ki)
        return ki
        
    def update_plots(self):
        for k in self.plots.keys():
            naxis = int(k.split('@')[1].split(' ')[0])
            pname=stringop.to_variable_name(k.split('@')[0])
            stimnames = self.distributions.keys()
            if naxis==2:
                if len(stimnames)!=2:#When number of stimuli is not 2, this plotting is skipped
                    continue
                x=self.distributions[stimnames[0]][pname]
                y=self.distributions[stimnames[1]][pname]
                self.plots[k].update_curve(x, y, pen=None, plotparams = {'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)})
                self.plots[k].plot.setLabels(bottom=stimnames[0],left=stimnames[1])
            elif naxis==1:
                colors = [(0, 0, 255,150), (0, 255, 0,150), (255,0,0,100)]
                self.plots[k]._clear_curves()
                self.plots[k].plot.addLegend(size=(120,60))
                self.plots[k].curves=[]
                self.plots[k].plot.setLabels(bottom=pname)
                for i in range(len(stimnames)):
                    ncells = self.distributions[stimnames[i]][pname].shape[0]
                    nbins=ncells/5
                    values = numpy.array([v for v in self.distributions[stimnames[i]][pname] if not numpy.isnan(v)])
                    distr1, bins1=numpy.histogram(values,nbins)
                    self.distr1 = numpy.cast['float'](distr1)/float(distr1.sum())
                    self.bins1 = numpy.diff(bins1)[0]*0.5+bins1
                    plotparams={'stepMode': True, 'fillLevel' : 0, 'brush' : colors[i], 'name': stimnames[i]}
                    self.plots[k].curves.append(self.plots[k].plot.plot(**plotparams))
                    self.plots[k].curves[-1].setData(self.bins1,self.distr1)
        
    def rescale(self):
        plotname = self.plots.keys()[self.tab.currentIndex()]
        plot = self.plots[plotname]
        try:
            n = float(self.nstd.input.text())
        except:
            return
        x=self.distributions[self._plotname2distributionname(plotname)][0]
        y=self.distributions[self._plotname2distributionname(plotname)][1]
        axis2scale = str(self.axis2scale.input.currentText())
        if axis2scale == 'x' or axis2scale == 'both':
            mu,std = (x.mean(), n*x.std())
            plot.plot.setXRange(mu-std, mu+std)
        if axis2scale == 'y' or axis2scale == 'both':
            mu,std = (y.mean(), n*y.std())
            plot.plot.setYRange(mu-std, mu+std)

class MainUI(gui.VisexpmanMainWindow):
    def __init__(self, context):        
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.setWindowIcon(gui.get_icon('main_ui'))
        self._init_variables()
        self._start_engine(gui_engine.MainUIEngine(self.machine_config, self.logger, self.socket_queues))
        self.resize(self.machine_config.GUI['SIZE']['col'], self.machine_config.GUI['SIZE']['row'])
        self._set_window_title()
        #Set up toobar
        if self.machine_config.PLATFORM=='elphys_retinal_ca':
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'find_cells', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'reset_datafile', 'exit']
        elif self.machine_config.PLATFORM=='mc_mea':
            toolbar_buttons = ['start_experiment', 'stop', 'convert_stimulus_to_video', 'exit']
        elif self.machine_config.PLATFORM=='us_cortical':
            toolbar_buttons = ['start_experiment', 'start_batch', 'stop', 'refresh_stimulus_files', 'convert_stimulus_to_video', 'exit']
        elif self.machine_config.PLATFORM=='ao_cortical':
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'reset_datafile','exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.statusbar=self.statusBar()
        #Add dockable widgets
        self.debug = gui.Debug(self)
#        self.debug.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/3)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'ao_cortical']:
            self.image = Image(self,roi_diameter=self.machine_config.DEFAULT_ROI_SIZE_ON_GUI)
            #self.image.setFixedHeight(480)
            #self.image.setFixedWidth(480)
            self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
            self.adjust=gui.ImageAdjust(self)
            self.adjust.setFixedHeight(40)
            self.adjust.low.setValue(0)
            self.adjust.high.setValue(99)
            self._add_dockable_widget('Image adjust', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.adjust)
            self.plot = gui.Plot(self)
            self.plot.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/2)
            self.plot.setMaximumWidth(self.image.width())
            self.plot.plot.setLabels(bottom='sec')
            self._add_dockable_widget('Plot', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.plot)
        self.stimulusbrowser = StimulusTree(self, os.path.dirname(fileop.get_user_module_folder(self.machine_config)), ['common', self.machine_config.user] )
        if self.machine_config.PLATFORM in ['elphys_retinal_ca']:
            self.cellbrowser=CellBrowser(self)
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'ao_cortical', 'us_cortical']:
            self.analysis = QtGui.QWidget(self)
            self.analysis.parent=self
            filebrowserroot= os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,self.machine_config.user) if self.machine_config.PLATFORM=='ao_cortical' else self.machine_config.EXPERIMENT_DATA_PATH
            self.datafilebrowser = DataFileBrowser(self.analysis, filebrowserroot, ['data*.hdf5', 'data*.mat', '*.tif', '*.mp4', '*.zip'])
            self.analysis_helper = AnalysisHelper(self.analysis)
            self.analysis.layout = QtGui.QGridLayout()
            self.analysis.layout.addWidget(self.datafilebrowser, 0, 0)
            self.analysis.layout.addWidget(self.analysis_helper, 1, 0)
            self.analysis.setLayout(self.analysis.layout)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.setMaximumWidth(500)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.advanced=Advanced(self)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.stimulusbrowser, 'Stimulus Files')
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'ao_cortical', 'us_cortical']:
            self.main_tab.addTab(self.analysis, 'Analysis')
        if self.machine_config.PLATFORM in ['elphys_retinal_ca']:
            self.main_tab.addTab(self.cellbrowser, 'Cell Browser')
        if self.machine_config.PLATFORM in ['us_cortical']:
            self.eye_camera=gui.Image(self)
            self.main_tab.addTab(self.eye_camera, 'Eye camera')
        self.main_tab.addTab(self.params, 'Settings')
        self.main_tab.addTab(self.advanced, 'Advanced')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self.load_all_parameters()
        self.show()
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'ao_cortical']:
            self.connect(self.analysis_helper.show_rois.input, QtCore.SIGNAL('stateChanged(int)'), self.show_rois_changed)
            self.connect(self.adjust.high, QtCore.SIGNAL('sliderReleased()'),  self.adjust_contrast)
            self.connect(self.adjust.low, QtCore.SIGNAL('sliderReleased()'),  self.adjust_contrast)
            self.connect(self.adjust.fit_image, QtCore.SIGNAL('clicked()'),  self.fit_image)
        if self.machine_config.PLATFORM == 'elphys_retinal_ca' and hasattr(self.analysis_helper, 'show_repetitions'):
            self.connect(self.analysis_helper.show_repetitions.input, QtCore.SIGNAL('stateChanged(int)'), self.show_repetitions_changed)

        self.connect(self.main_tab, QtCore.SIGNAL('currentChanged(int)'),  self.tab_changed)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_network_status(self):
        self.to_engine.put({'function': 'check_network_status', 'args':[]})
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if msg.has_key('printc'):
                self.printc(msg['printc'])
            elif msg.has_key('send_image_data'):
                self.meanimage, self.image_scale, boundaries = msg['send_image_data']
                self.image.remove_all_rois()
                self.image.set_image(self.meanimage, color_channel = 1)
                self.image.set_scale(self.image_scale)
                h=self.image.width()*float(self.meanimage.shape[1])/float(self.meanimage.shape[0])
                if h<self.machine_config.GUI['SIZE']['row']*0.5: h=self.machine_config.GUI['SIZE']['row']*0.5
                if h>self.image.height() and self.isMaximized():#when maximized and actual height is smaller then image width
                    self.printc('WARNING: temporary user interface rescaling')
                    w=self.image.height()*float(self.meanimage.shape[0])/float(self.meanimage.shape[1])
                    self.image.setFixedWidth(w)
                    #self.image.setFixedHeight(self.image.height())
                else:
                    self.image.setFixedHeight(h)
                self.adjust_contrast()
                if hasattr(boundaries, 'shape'):
                    self.image.add_linear_region(boundaries)
            elif msg.has_key('image_title'):
                self.image.plot.setTitle(msg['image_title'])
            elif msg.has_key('show_suggested_rois'):
                self.image_w_rois = msg['show_suggested_rois']
                self.image.set_image(self.image_w_rois)
                self.adjust_contrast()
            elif msg.has_key('display_roi_rectangles'):
                self.image.remove_all_rois()
                [self.image.add_roi(r[0],r[1], r[2:], movable=False) for r in msg['display_roi_rectangles']]
                self.printc('Displaying {0} rois'.format(len(msg['display_roi_rectangles'])))
            elif msg.has_key('display_roi_curve'):
                timg, curve, index, tsync,options = msg['display_roi_curve']
                self.timg=timg
                self.curve=curve
                self.tsync=tsync
                #Highlight roi
                self.image.highlight_roi(index)
                if isinstance(timg, list) and isinstance(curve, list):
                    self.plot.update_curves(timg, curve,plot_average = options['plot_average'] if options.has_key('plot_average') else True, colors = options['colors'] if options.has_key('colors') else [])
                else:
                    #Update plot
                    self.plot.update_curve(timg, curve)
                self.plot.add_linear_region(list(tsync))
            elif msg.has_key('remove_roi_rectangle'):
                 self.image.remove_roi(*list(msg['remove_roi_rectangle']))
            elif msg.has_key('fix_roi'):
                for r in self.image.rois:
                    r.translatable=False
            elif msg.has_key('ask4confirmation'):
                reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                self.to_engine.put(reply == QtGui.QMessageBox.Yes)
            elif msg.has_key('notify'):
                QtGui.QMessageBox.question(self, msg['notify']['title'], msg['notify']['msg'], QtGui.QMessageBox.Ok)
            elif msg.has_key('reset_datafile'):
                self.image.remove_all_rois()
            elif msg.has_key('display_trace_parameters'):
                pass
#                txt='\n'.join(['{0}: {1}'.format(stringop.to_title(k),'{0}'.format(v)[:4]) for k, v in msg['display_trace_parameters'].items()])
#                self.analysis_helper.trace_parameters.setText(txt)
            elif msg.has_key('display_trace_parameter_distributions'):
                self.tpp = TraceParameterPlots(msg['display_trace_parameter_distributions'])
                self.tpp.show()
            elif msg.has_key('display_cell_tree'):
                self.cellbrowser.populate(msg['display_cell_tree'])
            elif msg.has_key('update_network_status'):
                self.statusbar.showMessage(msg['update_network_status'])
            elif msg.has_key('highlight_multiple_rois'):
                self.image.highlight_roi(msg['highlight_multiple_rois'][0])
            elif msg.has_key('eye_camera_image'):
                self.eye_camera.set_image(msg['eye_camera_image'], color_channel = 1)
                h=self.eye_camera.width()*float(msg['eye_camera_image'].shape[1])/float(msg['eye_camera_image'].shape[0])
                if h<self.machine_config.GUI['SIZE']['row']*0.5: h=self.machine_config.GUI['SIZE']['row']*0.5
                self.eye_camera.setFixedHeight(h)
                self.eye_camera.plot.setTitle(time.time())
            elif msg.has_key('plot_sync'):
                x,y=msg['plot_sync']
                self.p=gui.Plot(None)
                pp=[]
                for i in range(len(x)):
                    c=colors.get_color(i)
                    c=(numpy.array(c)*255).tolist()
                    pp.append({'name': (str(i)), 'pen':c})
                self.p.update_curves(x,y,plotparams=pp)
                self.p.show()
#                self.pb = Progressbar(10)
#                self.pb.show()
            
                
    def _init_variables(self):
        if hasattr(self.machine_config,'FILTERWHEEL'):
            fw1=self.machine_config.FILTERWHEEL[0]['filters'].keys()
            fw1.sort()
            fw2=[] if len(self.machine_config.FILTERWHEEL)==1 else self.machine_config.FILTERWHEEL[1]['filters'].keys()
            fw2.sort()
        else:
            fw1=[]
            fw2=[]
            
        self.params_config = [
                {'name': 'Experiment', 'type': 'group', 'expanded' : self.machine_config.PLATFORM=='mc_mea', 'children': [#'expanded' : True
                    {'name': 'Name', 'type': 'str', 'value': ''},
                    ]},
                {'name': 'Stimulus', 'type': 'group', 'expanded' : self.machine_config.PLATFORM in ['mc_mea', 'ao_cortical'], 'children': [#'expanded' : True                    
                    {'name': 'Grey Level', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': '%'},
                    {'name': 'Bullseye On', 'type': 'bool', 'value': False},
                    {'name': 'Bullseye Size', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Bullseye Shape', 'type': 'list', 'values': ['bullseye', 'spot', 'L', 'square'], 'value': 'bullseye', 'readonly': self.machine_config.PLATFORM=='mc_mea'},
                    {'name': 'Stimulus Center X', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Stimulus Center Y', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                    ]},
                    ]
        if len(fw1)>0:
            self.params_config[1]['children'].append({'name': 'Filterwheel 1', 'type': 'list', 'values': fw1, 'value': ''})
        if len(fw2)>0:
            self.params_config[1]['children'].append({'name': 'Filterwheel 2', 'type': 'list', 'values': fw2, 'value': ''})            
        if self.machine_config.PLATFORM in ['elphys_retinal_ca']:
            self.params_config[1]['children'].extend([{'name': 'Projector On', 'type': 'bool', 'value': False, },])
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'ao_cortical']:
            self.params_config.extend([
                                                  {'name': 'Analysis', 'type': 'group', 'expanded' : True, 'children': [
                            {'name': 'Baseline Lenght', 'type': 'float', 'value': 1.0, 'siPrefix': True, 'suffix': 's'},
                            {'name': 'Background Threshold', 'type': 'float', 'value': 10, 'siPrefix': True, 'suffix': '%'},
                            {'name': 'Cell Detection', 'type': 'group', 'expanded' : False, 'children': [
                                {'name': 'Minimum Cell Radius', 'type': 'float', 'value': 2.0, 'siPrefix': True, 'suffix': 'um'},
                                {'name': 'Maximum Cell Radius', 'type': 'float', 'value': 3.0, 'siPrefix': True, 'suffix': 'um'},
                                {'name': 'Sigma', 'type': 'float', 'value': 1.0},
                                {'name': 'Threshold Factor', 'type': 'float', 'value': 1.0}
                                ]
                            },
                            {'name': 'Save File Format', 'type': 'list', 'values': ['mat', 'tif', 'mp4'], 'value': 'mat'},
                            {'name': 'Manual Roi', 'type': 'list', 'values': ['rectangle', 'cell shape'], 'value': 'rectangle'},
                            {'name': '3d to 2d Image Function', 'type': 'list', 'values': ['mean', 'mip'], 'value': 'mean'},
                            ]
                            }])
        if 'santiago' in self.machine_config.__class__.__name__.lower():
            from visexpman.users.santiago import bouton_analysis
            self.params_config[-1]['children'].append(bouton_analysis.settings)
            self.params_config[-1]['children'][0]['readonly']=True#Disable baseline lenght and threshold
            self.params_config[-1]['children'][1]['readonly']=True#Disable baseline lenght and threshold
        if self.machine_config.PLATFORM in ['elphys_retinal_ca']:                    
                self.params_config.extend([
                            {'name': 'Electrophysiology', 'type': 'group', 'expanded' : False, 'children': [
                                {'name': 'Electrophysiology Channel', 'type': 'list', 'values': ['None', 'CH1', 'CH2'], 'value': 'None'},
                                {'name': 'Electrophysiology Sampling Rate', 'type': 'list', 'value': 10e3,  'values': [10e3, 1e3]},
                            ]},  ]               
                        )
        if self.machine_config.PLATFORM=='mc_mea':
            self.params_config[0]['children'].extend([
                {'name': 'Bandpass filter', 'type': 'str', 'value': ''},
                {'name': 'ND filter', 'type': 'str', 'value': ''},
                {'name': 'Comment', 'type': 'str', 'value': ''},
            ])
        if self.machine_config.PLATFORM=='us_cortical':
            self.params_config.append(
            {'name': 'Ultrasound', 'type': 'group', 'expanded' : True, 'children': [#'expanded' : True
                    {'name': 'Protocol', 'type': 'list', 'values': self.machine_config.ULTRASOUND_PROTOCOLS},
                    {'name': 'Number of Trials', 'type': 'int', 'value': 1},
                    {'name': 'Motor Positions', 'type': 'str', 'value': ''},
                    ]},
            )
            self.params_config[0]['expanded']=True
            self.params_config[0]['children'].append({'name': 'Enable Eye Camera', 'type': 'bool', 'value': False})
                        

    ############# Actions #############
    def start_experiment_action(self):
        self.to_engine.put({'function': 'start_experiment', 'args':[]})
        
    def start_batch_action(self):
        self.to_engine.put({'function': 'start_batch', 'args':[]})
        
    def stop_action(self):
        self.to_engine.put({'function': 'stop_experiment', 'args':[]})
        
    def refresh_stimulus_files_action(self):
        self.stimulusbrowser.populate()
        self.printc('Stimulus files and classes are refreshed.')
        
    def find_cells_action(self):
        if self.analysis_helper.find_cells_scaled.input.checkState()==2:
            pixel_range=[self.adjust.low.value(),self.adjust.high.value()]
        else:
            pixel_range=None
        self.to_engine.put({'function': 'find_cells', 'args':[pixel_range]})
        
    def previous_roi_action(self):
        self.to_engine.put({'function': 'previous_roi', 'args':[]})

    def next_roi_action(self):
        self.to_engine.put({'function': 'next_roi', 'args':[]})
        
    def delete_roi_action(self):
        self.to_engine.put({'function': 'delete_roi', 'args':[]})
        
    def add_roi_action(self):
        '''
        Adds (all) manually placed roi(s)
        '''
        if self.machine_config.PLATFORM=='ao_cortical':
            QtGui.QMessageBox.question(self, 'Warning', 'Adding manual ROIs to AO data is not supported', QtGui.QMessageBox.Ok)
            return
        movable_rois = [r for r in self.image.rois if r.translatable]#Rois manually placed
        if len(movable_rois)>0 and 0:
            self.printc('Only one manually placed roi can be added!')
            return
        elif len(movable_rois)==0:
            self.printc('Put roi first on image!')
            return
        for roi in movable_rois:
            rectangle = [roi.x(), roi.y(),  roi.size().x(),  roi.size().y()]
            if self.machine_config.PLATFORM=='elphys_retinal_ca' and self.analysis_helper.find_cells_scaled.input.checkState()==2:
                pixel_range=[self.adjust.low.value(),self.adjust.high.value()]
            else:
                pixel_range=None
            self.to_engine.put({'function': 'add_manual_roi', 'args':[rectangle,pixel_range]})
            
    def save_rois_action(self):
        '''Also exports to mat file'''
        self.to_engine.put({'function': 'save_rois_and_export', 'args':[]})
        
    def reset_datafile_action(self):
        self.to_engine.put({'function': 'reset_datafile', 'args':[]})

    def convert_stimulus_to_video_action(self):
        self.to_engine.put({'function': 'convert_stimulus_to_video', 'args':[]})
        
    def exit_action(self):
        if hasattr(self, 'tpp'):
            self.tpp.close()
        self.send_all_parameters2engine()
        self._stop_engine()
        self.close()
    
    ############# Events #############
    def show_rois_changed(self,state):
        if hasattr(self, 'image_w_rois'):
            im = numpy.copy(self.image_w_rois)
            im[:,:,2] *= state==2
            self.image.set_image(im)
            self.adjust_contrast()
            
    def show_repetitions_changed(self,state):
        self.to_engine.put({'data': state==2, 'path': 'analysis_helper/show_repetitions/input', 'name': 'show_repetitions'})
        self.to_engine.put({'function': 'display_roi_curve', 'args':[]})
        
    def roi_mouse_selected(self,x,y,multiple_select):
        self.to_engine.put({'function': 'roi_mouse_selected', 'args':[x,y,multiple_select]})
    
    def parameter_changed(self, param, changes):
        self.send_widget_status()
        for change in changes:
            #find out tree
            ref = copy.deepcopy(change[0])
            tree = []
            while True:
                if hasattr(ref, 'name') and callable(getattr(ref, 'name')):
                    tree.append(getattr(ref, 'name')())
                    ref = copy.deepcopy(ref.parent())
                else:
                    break
            tree.reverse()
            self.to_engine.put({'data': change[2], 'path': '/'.join(tree), 'name': change[0].name()})
            
    def tab_changed(self,currentIndex):
        self.to_engine.put({'data': currentIndex, 'path': 'main_tab', 'name': 'Main Tab'})
        
    def adjust_contrast(self):#TODO: self.adjust widget shall be integrated into image widget
        if hasattr(self.image, 'rawimage'):
            image_range = self.image.rawimage.max()-self.image.rawimage.min()
            low = self.image.rawimage.min() + float(self.adjust.low.value())/100*image_range
            high = self.image.rawimage.min() + float(self.adjust.high.value())/100*image_range
            self.image.img.setLevels([low,high])
            
    def fit_image(self):
        if self.machine_config.PLATFORM in ['ao_cortical']:
            fitrange=[self.image_scale*48,self.image_scale*self.meanimage.shape[1]]#TODO: take this constant from datafile
            self.image.plot.setXRange(0,fitrange[0])
            self.image.plot.setYRange(0,fitrange[1])
            
    def send_widget_status(self):
        if hasattr(self, 'tpp'):
            self.to_engine.put({'function': 'update_widget_status', 'args': [{'tpp':self.tpp.isVisible()}]})
    
    
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'main_ui', log_sources = ['engine'])
    
    context['logger'].start()
    m = MainUI(context=context)
    visexpman.engine.stop_application(context)
