import copy
import time
import numpy
import os.path
import itertools
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
import pyqtgraph

from visexpman.engine.generic import stringop,utils,gui,signal,fileop,introspect,colors
from visexpman.engine.vision_experiment import gui_engine, experiment,experiment_data


class SelectPlotSignals(QtGui.QWidget):
    def __init__(self,parent):
        self.parent=parent
        QtGui.QWidget.__init__(self,parent)
        if hasattr(self.parent.machine_config, 'CHANNEL_NAMES'):
            self.left=[]
            self.right=[]
            self.layout = QtGui.QGridLayout()
            row=0
            for channel_name in self.parent.machine_config.CHANNEL_NAMES:
                self.left.append(gui.LabeledCheckBox(self, channel_name))
                self.layout.addWidget(self.left[-1], row, 0)
                self.right.append(gui.LabeledCheckBox(self, channel_name))
                self.layout.addWidget(self.right[-1], row, 1)
                self.right[-1].input.setChecked(2)
                self.left[-1].input.setChecked(2)
                self.right[-1].input.stateChanged.connect(self.update_selection)
                self.left[-1].input.stateChanged.connect(self.update_selection)
                row+=1
            self.setLayout(self.layout)
            self.update_selection()
            
    def update_selection(self):
        enable={'left': [], 'right': []}
        for i in range(len(self.parent.machine_config.CHANNEL_NAMES)):
            enable['left'].append(self.left[i].input.checkState()==2)
            enable['right'].append(self.right[i].input.checkState()==2)
        self.parent.to_engine.put({'function': 'enable_plot_signals', 'args':[enable]})

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
        self.fix.clicked.connect(self.fix_clicked)
        self.test.clicked.connect(self.test_clicked)
        
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
        if hasattr(QtCore, 'QStringList'):
            self.setHeaderLabels(QtCore.QStringList(['']))
        else:
            self.setHeaderLabels([''])
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
        self.setHeaderLabels([''])#, 'Date Modified']))
        self.populate()
        self.itemDoubleClicked.connect(self.stimulus_selected_for_open)
        self.itemClicked.connect(self.stimulus_selected)
        self.itemSelectionChanged.connect(self.get_selected_stimulus)
        #Local menu
        self.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)

    def open_menu(self, position):
        self.menu = QtGui.QMenu(self)
        stimulus_info_action = QtGui.QAction('Stimulus info', self)
        stimulus_info_action.triggered.connect(self.stimulus_info_action)
        self.menu.addAction(stimulus_info_action)
        stimulus_par_action = QtGui.QAction('Stimulus parameters', self)
        stimulus_par_action.triggered.connect(self.stimulus_par_action)
        self.menu.addAction(stimulus_par_action)
        self.menu.exec_(self.viewport().mapToGlobal(position))
        
    def stimulus_info_action(self):
        try:
            bases=experiment.read_stimulus_base_classes(self.classname, self.filename, self.parent.machine_config)
            self.parent.printc('Base classes: {0}'.format(' -> '.join(bases)))
            duration=experiment.get_experiment_duration(self.classname, self.parent.machine_config, source=fileop.read_text_file(self.filename))
            self.parent.printc('Duration: {0:0.0f} seconds'.format(duration))
            parameters=experiment.read_stimulus_parameters(self.classname, self.filename, self.parent.machine_config)
            self.parent.printc('Stimulus hash: {0}'.format(experiment.stimulus_parameters_hash(parameters)))
        except:
            import traceback
            self.parent.printc(traceback.format_exc())

    def stimulus_par_action(self):
        parameters=experiment.read_stimulus_parameters(self.classname, self.filename, self.parent.machine_config)
        self.parent.printc('{0} parameters'.format(self.classname))
        for k, v in parameters.items():
            self.parent.printc('{0} = {1}'.format(k,v))
            
    def roots(self,item):
        roots=[str(item.text(0))]
        while True:
            item=item.parent()
            if hasattr(item, 'text'):
                roots.append(str(item.text(0)))
            else:
                break
        return roots[::-1]
        
    def populate(self):
        subdirs=[s for s in map(os.path.join,len(self.subdirs)*[self.root], self.subdirs)]
        files = fileop.find_files_and_folders(self.root)[1]
        files = [f for f in files if os.path.splitext(f)[1] =='.py' and os.path.dirname(f) in subdirs]
        experiment_configs = []
        for f in files:
            try:
                confnames = experiment.parse_stimulation_file(f).keys()
                experiment_configs.extend([i for i in map(os.path.join, [f]*len(confnames), confnames)])
            except:
                pass#Ignoring py files with error
        #Clear tree view
        self.blockSignals(True)
        self.clear()
        if hasattr(self.parent.machine_config, 'STIMULUS_VIEW_FILTER'):
            experiment_configs=[ec for ec in experiment_configs if len([kw for kw in self.parent.machine_config.STIMULUS_VIEW_FILTER if kw in os.path.basename(ec)])>0]
        #Populate with files and stimulus classes
        branches = [list(e.replace(self.root, '')[1:].split(os.sep)) for e in experiment_configs]
        nlevels=[len(b) for b in branches]
        if not all(nlevels):
            raise ValueError('All branches shall have the same depth')
        nlevels=0 if len(nlevels)==0 else nlevels[0]
        tree_items=[]
        for level in range(nlevels):
            for i in [b[:level+1] for b in branches]:
                if i not in tree_items:
                    tree_items.append(i)
        tree_items.sort()
        added_items=[]
        for tree_item in tree_items:
            roots=[self.roots(w) for w in added_items]
            newwidget=QtGui.QTreeWidgetItem([tree_item[-1]])
            if len(tree_item)==1:
                self.addTopLevelItem(newwidget)
            else:
                ref=[added_items[i] for i in range(len(roots)) if roots[i]==tree_item[:-1]]
                if len(ref)==1:
                    ref[0].addChild(newwidget)
                else:
                    raise
            added_items.append(newwidget)
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
            if hasattr(self,  'setItemSelected'):
                self.setItemSelected(widget_ref, True)
            else:
                widget_ref.setSelected(True)
        
    def get_selected_stimulus(self):
        selected_widget = self.selectedItems()
        if len(selected_widget)==0:
            self._give_not_stimulus_selected_warning()
            return
        else:
            selected_widget = selected_widget[0]
            if self._is_experiment_class(selected_widget):
                filename, classname = self.filename_from_widget(selected_widget)
                if hasattr(QtCore, 'QStringList'):
                    self.setHeaderLabels(QtCore.QStringList([classname]))
                else:
                    self.setHeaderLabels([classname])
                self.parent.to_engine.put({'data': filename+os.sep+classname, 'path': 'stimulusbrowser/Selected experiment class', 'name': 'Selected experiment class'})
                return filename, classname
        
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
        self.plot.setLabels(left='um', bottom='um')
        try:
            self.connect(self, QtCore.SIGNAL('roi_mouse_selected'), parent.roi_mouse_selected)
            self.connect(self, QtCore.SIGNAL('wheel_double_click'), parent.add_roi_action)
        except:
            print('Cannot connect roi_mouse_selected and add_roi_action')
            
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
        if os.path.splitext(self.selected_filename )[1]!='.hdf5':#Find corresponding hdf5 file
            idn=os.path.splitext(os.path.basename(self.selected_filename))[0].split('_')[-1]
            hdf5fn=[f for f in fileop.listdir(os.path.dirname(self.selected_filename)) if idn in os.path.basename(f) and os.path.splitext(f)[1]=='.hdf5']
            if len(hdf5fn)==1:
                self.selected_filename=hdf5fn[0]
        print(self.selected_filename)

        
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
        plot_action = QtGui.QAction('Plot recorded signals', self)
        plot_action.triggered.connect(self.plot_action)
        self.menu.addAction(plot_action)
        add_comment_action=QtGui.QAction('Comment', self)
        add_comment_action.triggered.connect(self.add_comment_action)
        self.menu.addAction(add_comment_action)
        self.menu.exec_(self.viewport().mapToGlobal(position))
        
    def delete_action(self):
        if hasattr(self, 'selected_filename'):
            self.parent.parent.to_engine.put({'function': 'remove_recording', 'args':[self.convert_filename(self.selected_filename)]})
            
    def plot_action(self):
        if hasattr(self, 'selected_filename'):
            self.parent.parent.to_engine.put({'function': 'plot_sync', 'args':[self.convert_filename(self.selected_filename)]})
            
    def add_comment_action(self):
        if hasattr(self, 'selected_filename'):
            self.parent.parent.to_engine.put({'function': 'add_comment', 'args':[self.convert_filename(self.selected_filename)]})        
            
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
        self.resize(self.machine_config.GUI_WIDTH, self.machine_config.GUI_HEIGHT)
        if hasattr(self.machine_config, 'GUI_POS_X'):
            self.move(self.machine_config.GUI_POS_X, self.machine_config.GUI_POS_Y)
        self._set_window_title()
        #Set up toobar
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'retinal']:
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'find_cells', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'reset_datafile', 'exit']
        elif self.machine_config.PLATFORM=='mc_mea':
            toolbar_buttons = ['start_experiment', 'stop', 'exit']
        elif self.machine_config.PLATFORM=='us_cortical':
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'convert_stimulus_to_video', 'exit']
        elif self.machine_config.PLATFORM in ['ao_cortical', '2p', 'resonant']:
            toolbar_buttons = ['start_experiment', 'stop', 'select_data_folder',  'connect', 'refresh_stimulus_files', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'reset_datafile','exit']
        elif self.machine_config.PLATFORM =='behav':
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'exit']
        elif self.machine_config.PLATFORM =='elphys':
            toolbar_buttons = ['start_experiment', 'stop', 'exit']
        elif self.machine_config.PLATFORM =='erg':
            toolbar_buttons = ['start_experiment', 'stop', 'exit']
        elif self.machine_config.PLATFORM =='generic':
            toolbar_buttons = ['start_experiment', 'stop', 'refresh_stimulus_files', 'exit']
        if self.machine_config.ENABLE_BATCH_EXPERIMENT:
            toolbar_buttons.insert(1,'start_batch_experiment')
            
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.statusbar=self.statusBar()
        self.statusbar.status=QtGui.QLabel('Idle', self)
        self.statusbar.addPermanentWidget(self.statusbar.status)
        self.statusbar.status.setStyleSheet('background:gray;')
        #Add dockable widgets
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'retinal', 'ao_cortical', '2p']:
            self.image = Image(self,roi_diameter=self.machine_config.DEFAULT_ROI_SIZE_ON_GUI)
            self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
            self.adjust=gui.ImageAdjust(self)
            self.adjust.setFixedHeight(40)
            self.adjust.low.setValue(0)
            self.adjust.high.setValue(99)
            self._add_dockable_widget('Image adjust', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.adjust)
        if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'retinal', 'ao_cortical',  "elphys", 'erg', '2p', 'resonant']:
            self.plot = gui.Plot(self)
            self.plot.plot.setLabels(bottom='sec')
            d=QtCore.Qt.BottomDockWidgetArea if hasattr(self,  "image") else QtCore.Qt.RightDockWidgetArea
            self._add_dockable_widget('Plot', d, d, self.plot)
        subfolders=['common', self.machine_config.user] 
        if hasattr(self.machine_config,  'SECONDARY_USER'):#Stimuli of this user are loaded into stimulus tree
            subfolders.append(self.machine_config.SECONDARY_USER)
        self.stimulusbrowser = StimulusTree(self, os.path.dirname(fileop.get_user_module_folder(self.machine_config)), subfolders)
        if self.machine_config.PLATFORM in ['retinal']:
            self.cellbrowser=CellBrowser(self)
        if self.machine_config.PLATFORM in ['elphys', 'retinal',  'ao_cortical', 'us_cortical', 'resonant',  'behav', '2p', 'mc_mea', 'erg','generic']:
            self.analysis = QtGui.QWidget(self)
            self.analysis.parent=self
            #filebrowserroot= os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,self.machine_config.user) if self.machine_config.PLATFORM in ['ao_cortical','resonant'] else self.machine_config.EXPERIMENT_DATA_PATH
            filebrowserroot=self.engine.dataroot
            if not os.path.exists(filebrowserroot):
                filebrowserroot=self.machine_config.EXPERIMENT_DATA_PATH
            self.datafilebrowser = DataFileBrowser(self.analysis, filebrowserroot, ['stim*.hdf5', 'sync*.hdf5', 'eye*.hdf5',   'data*.hdf5', 'data*.mat', '*.tif', '*.tiff', '*.avi', '*.mp4', '*.zip', '*.mesc', '*.mcd'])
            self.analysis_helper = AnalysisHelper(self.analysis)
            self.analysis.layout = QtGui.QGridLayout()
            self.data_folder_w = QtGui.QLabel('', self)
            self.analysis.layout.addWidget(self.data_folder_w, 0, 0)
            self.analysis.layout.addWidget(self.datafilebrowser, 1, 0)
            self.analysis.layout.addWidget(self.analysis_helper, 2, 0)
            self.analysis.setLayout(self.analysis.layout)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.stimulusbrowser, 'Stimulus Files')
        if self.machine_config.PLATFORM in ['elphys', 'retinal', 'ao_cortical', 'us_cortical', 'resonant',  'behav', '2p', 'mc_mea', 'erg', 'generic']:
            self.main_tab.addTab(self.analysis, 'Data')
        if self.machine_config.PLATFORM in ['retinal']:
            self.main_tab.addTab(self.cellbrowser, 'Cell Browser')
        self.main_tab.addTab(self.params, 'Settings')
#        if self.machine_config.PLATFORM in ["elphys"]:
#            self.electrical_stimulus=QtGui.QWidget(self)
#            self.main_tab.addTab(self.electrical_stimulus, 'Electrical Stimulus')
        if self.machine_config.PLATFORM in ["erg"]:
            self.plot2 = gui.Plot(self)
            self.main_tab.addTab(self.plot2, 'Sensor signals')
        if self.machine_config.PLATFORM in ['tbd']:
            self.advanced=Advanced(self)
            self.main_tab.addTab(self.advanced, 'Advanced')
        if hasattr(self.machine_config, 'WIDGET'):
            import importlib
            m=importlib.import_module('.'.join(self.machine_config.WIDGET.split('.')[:-1]))
            self.w=getattr(m, self.machine_config.WIDGET.split('.')[-1])(self)
            self.main_tab.addTab(self.w, self.w.__class__.__name__)
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self.load_all_parameters()
        self.show()
        if self.machine_config.PLATFORM in ['retinal', 'ao_cortical', '2p']:
            self.analysis_helper.show_rois.input.stateChanged.connect(self.show_rois_changed)
            self.adjust.high.sliderReleased.connect(self.adjust_contrast)
            self.adjust.low.sliderReleased.connect(self.adjust_contrast)
            self.adjust.fit_image.clicked.connect(self.fit_image)
        if self.machine_config.PLATFORM == 'retinal' and hasattr(self.analysis_helper, 'show_repetitions'):
            self.connect(self.analysis_helper.show_repetitions.input, QtCore.SIGNAL('stateChanged(int)'), self.show_repetitions_changed)
        self.main_tab.currentChanged.connect(self.tab_changed)
        #Set size of widgets
        self.debug.setFixedHeight(self.machine_config.GUI_HEIGHT*0.35)
        self.main_tab.setMinimumHeight(self.machine_config.GUI_HEIGHT*0.4)
        if hasattr(self, 'plot'):
            self.plot.setFixedWidth(self.machine_config.GUI_WIDTH*0.5)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_network_status(self):
        self.to_engine.put({'function': 'check_network_status', 'args':[]})
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if 'printc' in msg:
                self.printc(msg['printc'])
            elif 'send_image_data' in msg:
                self.meanimage, self.image_scale, boundaries = msg['send_image_data']
                self.image.remove_all_rois()
                self.image.set_image(self.meanimage, color_channel = 1)
                self.image.set_scale(self.image_scale)
                h=self.image.width()*float(self.meanimage.shape[1])/float(self.meanimage.shape[0])
                if h<self.machine_config.GUI_HEIGHT*0.5: h=self.machine_config.GUI_HEIGHT*0.5
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
            elif 'image_title' in msg:
                self.image.plot.setTitle(msg['image_title'])
            elif 'plot_title' in msg:
                self.plot.plot.setTitle(msg['plot_title'])
            elif 'plot2_title' in msg:
                self.plot2.plot.setTitle(msg['plot2_title'])
            elif 'show_suggested_rois' in msg:
                self.image_w_rois = msg['show_suggested_rois']
                self.image.set_image(self.image_w_rois)
                self.adjust_contrast()
            elif 'display_roi_rectangles' in msg:
                self.image.remove_all_rois()
                [self.image.add_roi(r[0],r[1], r[2:], movable=False) for r in msg['display_roi_rectangles']]
                self.printc('Displaying {0} rois'.format(len(msg['display_roi_rectangles'])))
            elif 'display_roi_curve' in msg:#Also serves as a main plot for non imaging data
                timg, curve, index, tsync,options = msg['display_roi_curve']
                self.timg=timg
                self.curve=curve
                self.tsync=tsync
                #Highlight roi
                if hasattr(self,  "image"):
                    self.image.highlight_roi(index)
                if isinstance(timg, list) and isinstance(curve, list):
                    self.plot.update_curves(timg, curve,plot_average = options['plot_average'] if 'plot_average' in options else True, colors = options['colors'] if 'colors' in options else [])
                else:
                    #Update plot
                    self.plot.update_curve(timg, curve)
                if hasattr(tsync, "dtype"):
                    self.plot.add_linear_region(list(tsync))
                if "labels" in options:
                    self.plot.plot.setLabels(left=options["labels"]["left"], bottom=options["labels"]["bottom"])
                if 'range' in options and options['range']!= None:
                    #self.plot.plot.autoRange(False)
                    self.plot.plot.setYRange(options['range'][0],options['range'][1])
#                else:
#                    self.plot.plot.autoRange(True)
            elif 'curves2plot2' in msg:
                timg, curve, index, tsync,options = msg['curves2plot2']
                self.timg=timg
                self.curve=curve
                self.tsync=tsync
                #Highlight roi
                if isinstance(timg, list) and isinstance(curve, list):
                    self.plot2.update_curves(timg, curve,plot_average = options['plot_average'] if options.has_key('plot_average') else True, colors = options['colors'] if options.has_key('colors') else [])
                else:
                    #Update plot
                    self.plot2.update_curve(timg, curve)
                if hasattr(tsync, "dtype"):
                    self.plot2.add_linear_region(list(tsync))
                if "labels" in options:
                    self.plot2.plot.setLabels(left=options["labels"]["left"], bottom=options["labels"]["bottom"])
                if 'range' in options and options['range']!= None:
                    #self.plot.plot.autoRange(False)
                    self.plot2.plot.setYRange(options['range'][0],options['range'][1])
            elif 'remove_roi_rectangle' in msg:
                 self.image.remove_roi(*list(msg['remove_roi_rectangle']))
            elif 'fix_roi' in msg:
                for r in self.image.rois:
                    r.translatable=False
            elif 'ask4confirmation' in msg:
                reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                self.to_engine.put(reply == QtGui.QMessageBox.Yes)
            elif 'notify' in msg:
                QtGui.QMessageBox.question(self, msg['notify']['title'], msg['notify']['msg'], QtGui.QMessageBox.Ok)
            elif 'reset_datafile' in msg:
                self.image.remove_all_rois()
            elif 'display_trace_parameters' in msg:
                pass
#                txt='\n'.join(['{0}: {1}'.format(stringop.to_title(k),'{0}'.format(v)[:4]) for k, v in msg['display_trace_parameters'].items()])
#                self.analysis_helper.trace_parameters.setText(txt)
            elif 'display_trace_parameter_distributions' in msg:
                self.tpp = TraceParameterPlots(msg['display_trace_parameter_distributions'])
                self.tpp.show()
            elif 'display_cell_tree' in msg:
                self.cellbrowser.populate(msg['display_cell_tree'])
            elif 'update_network_status' in msg:
                import visexpman
                self.statusbar.showMessage(msg['update_network_status']+20*' '+'visexpman '+visexpman.version)
            elif 'update_status' in msg:
                if msg['update_status']=='idle':
                    self.statusbar.status.setStyleSheet('background:gray;')
                elif msg['update_status']=='recording':
                    self.statusbar.status.setStyleSheet('background:red;')
                elif msg['update_status']=='stimulus only':
                    self.statusbar.status.setStyleSheet('background:orange;')
                elif msg['update_status']=='busy':
                    self.statusbar.status.setStyleSheet('background:yellow;')
                self.statusbar.status.setText(msg['update_status'].capitalize())
            elif 'highlight_multiple_rois' in msg:
                self.image.highlight_roi(msg['highlight_multiple_rois'][0])
            elif 'plot_sync' in msg:
                x,y=msg['plot_sync']
                self.p=gui.Plot(None)
                self.p.move(200, 200)
                pp=[]
                for i in range(len(x)):
                    c=colors.get_color(i)
                    c=(numpy.array(c)*255).tolist()
                    pp.append({'name': (str(i)), 'pen':c})
                self.p.update_curves(x,y,plotparams=pp)
                self.p.show()
            elif 'plot_speed' in msg:
                x,y=msg['plot_speed']
                self.p2=gui.Plot(None)
                self.p2.move(100, 100)
                pp=[]
                for i in range(len(x)):
                    c=colors.get_color(i)
                    c=(numpy.array(c)*255).tolist()
                    pp.append({'name': (str(i)), 'pen':c})
                self.p2.update_curves(x,y,plotparams=pp)
                self.p2.show()
#                self.pb = Progressbar(10)
#                self.pb.show()
            elif 'add_comment' in msg:
                self.printc('')#Don't know why it is needed but needed for comment widget to show up
                self.addnote=gui.AddNote(None,msg['add_comment'][0],  self.from_engine)
                self.addnote.setWindowTitle('Comment')
                self.addnote.text.setFixedWidth(350)
                if QtCore.QT_VERSION_STR[0]=='4':
                    self.addnote.connect(self.addnote, QtCore.SIGNAL('addnote'),self.save_comment)
            elif 'save_comment' in msg:
                self.save_comment(msg['save_comment'])
            elif 'permanent_warning' in msg:
                self._set_window_title(tag=' !'+msg['permanent_warning'])
            elif 'polar_plot' in msg:
                img=msg['polar_plot'][0][1]
                self.p=gui.Image(None)
                self.p.set_image(numpy.fliplr(numpy.flipud(numpy.rot90(img))))
                self.p.move(200, 200)
                self.p.setMinimumWidth(img.shape[0])
                self.p.setMinimumHeight(img.shape[1])
                self.p.show()
            elif 'set_data_folder' in msg:
                self.data_folder_w.setText(msg['set_data_folder'])
                self.datafilebrowser.set_root(msg['set_data_folder'])
                
    def _init_variables(self):
        if hasattr(self.machine_config,'FILTERWHEEL_FILTERS'):
            if isinstance(self.machine_config.FILTERWHEEL_FILTERS, list):
                fw1=list(self.machine_config.FILTERWHEEL_FILTERS[0].keys())
                fw2=list(self.machine_config.FILTERWHEEL_FILTERS[1].keys())
                fw2.sort()
            else:
                fw1=list(self.machine_config.FILTERWHEEL_FILTERS.keys())
                fw2=[]
            fw1.sort()
        else:
            fw1=[]
            fw2=[]
        
        name_name='Name' if not hasattr(self.machine_config,  'NAME_FIELD_NAME') else self.machine_config.NAME_FIELD_NAME
        self.params_config = [
                {'name': 'Experiment', 'type': 'group', 'expanded' : self.machine_config.PLATFORM in ['2p', 'mc_mea', 'generic'], 'children': [#'expanded' : True
                    {'name': name_name, 'type': 'str', 'value': ''},
                    {'name': 'Animal', 'type': 'str', 'value': ''},
                    ]},
                {'name': 'Stimulus', 'type': 'group', 'expanded' : self.machine_config.PLATFORM in ['elphys', 'mc_mea', 'ao_cortical'], 'children': [#'expanded' : True                    
                    {'name': 'Enable Psychotoolbox', 'type': 'bool', 'value': False},
                    {'name': 'Grey Level', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': '%'},
                    {'name': 'Bullseye On', 'type': 'bool', 'value': False},
                    {'name': 'Bullseye Size', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Bullseye Shape', 'type': 'list', 'values': ['bullseye', 'spot', 'L', 'square'], 'value': 'bullseye', 'readonly': self.machine_config.PLATFORM=='mc_mea'},
                    {'name': 'Stimulus Center X', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um', 'readonly': self.machine_config.PLATFORM=='mc_mea'},
                    {'name': 'Stimulus Center Y', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um', 'readonly': self.machine_config.PLATFORM=='mc_mea'},
                    ]},
                    ]
        if len(fw1)>0:
            self.params_config[1]['children'].append({'name': 'Filterwheel', 'type': 'list', 'values': fw1, 'value': ''})
        if len(fw2)>0:
            self.params_config[1]['children'].append({'name': 'Filterwheel 2', 'type': 'list', 'values': fw2, 'value': ''})
        if len(fw1)>0:
            self.params_config[1]['children'].append({'name': 'Block Projector', 'type': 'bool', 'value': False})
        if self.machine_config.PLATFORM in ['retinal']:
            self.params_config[1]['children'].extend([{'name': 'Projector On', 'type': 'bool', 'value': False, },])
        if self.machine_config.PLATFORM in ['retinal','ao_cortical']:
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
        if self.machine_config.PLATFORM in ['retinal']:
            self.params_config[-1]['children'].append({'name': 'Motion Correction', 'type': 'bool', 'value': False})
        if 'santiago' in self.machine_config.__class__.__name__.lower():
            from visexpman.users.santiago import bouton_analysis
            self.params_config[-1]['children'].extend(bouton_analysis.settings)
            self.params_config[-1]['children'][0]['readonly']=True#Disable baseline lenght and threshold
            self.params_config[-1]['children'][1]['readonly']=True#Disable baseline lenght and threshold
        elif self.machine_config.PLATFORM in ['elphys']:
                protocols=['Pulse train']
                protocols.extend([os.path.basename(f) for f in fileop.listdir(self.machine_config.PROTOCOL_PATH) if os.path.splitext(f)[1]=='.mat'])
                pars=[
                                {'name': 'Displayed signal length', 'type': 'float', 'value': 20.0,  'suffix': 's'},
                                {'name': 'Sample Rate', 'type': 'float', 'value': 10000,  'suffix': 'Hz', 'decimals':6},
                                {'name': 'Clamp Mode', 'type': 'list', 'value': 'Current Clamp',  'values': ['Voltage Clamp', 'Current Clamp']},
                                
#                                {'name': 'Clamp Voltage', 'type': 'float', 'value': 0.0,  'suffix': ' mV'},
#                                {'name': 'Clamp Current', 'type': 'float', 'value': 0.0,  'suffix': ' pA'},
                                {'name': 'Current Gain', 'type': 'float', 'value': 0.5,  'suffix': 'V/pA'},
                                {'name': 'Voltage Gain', 'type': 'float', 'value': 100.0, 'suffix': 'mV/mV'}, 
#                                {'name': 'Current Command Sensitivity', 'type': 'float', 'value': 400,  'suffix': 'pA/V'},
#                                {'name': 'Voltage Command Sensitivity', 'type': 'float', 'value': 20.0, 'suffix': 'mV/V'}, 
                                {'name': 'Show raw voltage', 'type': 'bool', 'value': False},
                                {'name': 'Y axis autoscale', 'type': 'bool', 'value': True},
                                {'name': 'Y min', 'type': 'float', 'value': 0},
                                {'name': 'Y max', 'type': 'float', 'value': 10},
                                {'name': 'Stimulus', 'type': 'group', 'expanded' : True, 'children': [
                                    {'name': 'Enable', 'type': 'bool', 'value': False},
                                    {'name': 'Protocol', 'type': 'list', 'value': '',  'values': protocols},
                                    {'name': 'Amplitudes', 'type': 'str', 'value': ''},
                                    {'name': 'Amplitude unit', 'type': 'list', 'value': 'pA',  'values': ['pA', 'mV']},
                                    {'name': 'Wait time', 'type': 'float', 'value': 2000,  'suffix': 'ms', 'decimals':6},
                                    {'name': 'On time', 'type': 'float', 'value': 500,  'suffix': 'ms'},
                                    {'name': 'Off time', 'type': 'float', 'value': 500,  'suffix': 'ms'},
                                    {'name': 'Current Command Sensitivity', 'type': 'float', 'value': 400,  'suffix': 'pA/V'},
                                    {'name': 'Voltage Command Sensitivity', 'type': 'float', 'value': 20.0, 'suffix': 'mV/V'}, 
                            
                                ]}
                                
                                
                                ]
                self.params_config.extend([
                            {'name': 'Electrophysiology', 'type': 'group', 'expanded' : True, 'children': [
                            
                            
                            ]},  ]               
                        )
                self.params_config[-1]['children'].extend(pars)
#        if self.machine_config.PLATFORM=='mc_mea':
#            self.params_config[0]['children'].extend([
#                {'name': 'Comment', 'type': 'str', 'value': ''},
#            ])
        elif self.machine_config.PLATFORM=='us_cortical':
            self.params_config.append(
            {'name': 'Ultrasound', 'type': 'group', 'expanded' : True, 'children': [#'expanded' : True
                    {'name': 'Protocol', 'type': 'list', 'values': self.machine_config.ULTRASOUND_PROTOCOLS},
                    {'name': 'Number of Trials', 'type': 'int', 'value': 1},
                    {'name': 'Motor Positions', 'type': 'str', 'value': ''},
                    ]},
            )
        elif self.machine_config.PLATFORM=='resonant':
            self.params_config[0]['expanded']=True
            self.params_config[0]['children'].append({'name': 'Enable Galvo', 'type': 'bool', 'value': False})
            self.params_config[0]['children'].append({'name': 'Runwheel attached', 'type': 'bool', 'value': False})
            self.params_config[0]['children'].append({'name': 'Record Eyecamera', 'type': 'bool', 'value': False})
            self.params_config[0]['children'].append({'name': 'Partial Save', 'type': 'bool', 'value': False})
        elif self.machine_config.ENABLE_EYE_CAMERA:
            self.params_config[0]['children'].append({'name': 'Record Eyecamera', 'type': 'bool', 'value': False})
        if self.machine_config.PLATFORM in ['2p', 'resonant', 'generic']:
            self.params_config[0]['children'].append({'name': 'Stimulus Only', 'type': 'bool', 'value': False})
        if self.machine_config.ENABLE_FILE_TRIGGER:
            self.params_config[0]['children'].append({'name': 'Enable File Trigger', 'type': 'bool', 'value': False})
        if self.machine_config.ENABLE_BATCH_EXPERIMENT:
            #Append batch experiment settings
            if self.machine_config.PLATFORM=='2p':
                self.params_config.append(
                {'name': 'Batch Experiment', 'type': 'group', 'expanded' : True, 'children': [#'expanded' : True
                        {'name': 'Repeats', 'type': 'int', 'value': 1},
                        {'name': 'Z start', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Z end', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Z step', 'type': 'float', 'value': 10,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Enable tile scan', 'type': 'bool', 'value': False},
                        {'name': 'X start', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'X end', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Y start', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Y end', 'type': 'float', 'value': 0,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Tile overlap', 'type': 'float', 'value': 50,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Tile Width', 'type': 'float', 'value': 300,  'suffix': 'um',  'decimals': 6},
                        {'name': 'Tile Height', 'type': 'float', 'value': 300,  'suffix': 'um',  'decimals': 6},
                        ]},
                    )
            else:
                self.params_config.append(
                        {'name': 'Batch Experiment', 'type': 'group', 'expanded' : True, 'children': [#'expanded' : True
                                {'name': 'Repeats', 'type': 'int', 'value': 1},
                                {'name': ' ', 'type': 'str', 'value': ''},
                    ]},
                    )
            
        if hasattr(self.machine_config, 'SETUP_SETTINGS'):
            if isinstance(self.machine_config.SETUP_SETTINGS, list):
                self.params_config.extend(self.machine_config.SETUP_SETTINGS)
            else:
                self.params_config.append(self.machine_config.SETUP_SETTINGS)

    ############# Actions #############
    def start_experiment_action(self):
        self.to_engine.put({'function': 'start_experiment', 'args':[]})
        
    def start_batch_experiment_action(self):
        self.to_engine.put({'function': 'start_batch_experiment', 'args':[]})
        
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
        
    def save_comment(self, comment):
        self.to_engine.put({'function': 'save_comment', 'args':[comment]})
        
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
        
    def connect_action(self):
        self.to_engine.put({'function': 'connect', 'args':[]})
        
    def select_data_folder_action(self):
        foldername = str(QtGui.QFileDialog.getExistingDirectory(self, "Select Data Folder", self.engine.dataroot))
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        self.to_engine.put({'function': 'set_data_folder', 'args':[foldername]})
        self.to_engine.put({'data': foldername, 'path': 'engine/dataroot', 'name': 'Root Data Folder'})
        
    def exit_action(self):
        if hasattr(self,  'exit_action_called'):
            return
        else:
            self.exit_action_called=True
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
            ref = change[0]
            tree = []
            while True:
                if hasattr(ref, 'name') and callable(getattr(ref, 'name')):
                    tree.append(getattr(ref, 'name')())
                    ref = ref.parent()
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
