'''
vision_experiment.gui implements widgets that build up the user interface of vision experiment manager applciations. Some widgets are used in multiple applications.
'''

import os
import os.path
import numpy
import datetime
import copy

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.datadisplay import imaged
from visexpA.engine.datadisplay.plot import Qt4Plot
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import gui
from visexpman.engine.generic import file
from visexpman.engine.generic import stringop
from visexpman.engine.generic import introspect

BUTTON_HIGHLIGHT = 'color: red'#TODO: this has to be eliminated
BRAIN_TILT_HELP = 'Provide tilt degrees in text input box in the following format: vertical axis [degree],horizontal axis [degree]\n\
        Positive directions: horizontal axis: right, vertical axis: outer side (closer to user)'
        
        
############### Common widgets ###############
class StandardIOWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.filter_names = ['',]
        for k, v in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            if 'GUI' in k:
                self.filter_names.append(k.replace('GUI', '').replace('_', '').lower())
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.STANDARDIO_WIDGET_TAB_SIZE['col'], self.config.STANDARDIO_WIDGET_TAB_SIZE['row'])#TODO: remove it
        
    def create_widgets(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        self.text_in = QtGui.QTextEdit(self)
        self.text_in.setToolTip('self.printc()')
        self.text_in.setFixedHeight(50)
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        self.clear_console_button = QtGui.QPushButton('Clear console',  self)
        self.console_message_filter_combobox = QtGui.QComboBox(self)
        self.console_message_filter_combobox.addItems(QtCore.QStringList(self.filter_names))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.text_out, 0, 0, 30, 3)
        self.layout.addWidget(self.text_in, 1, 3, 1, 2)
        self.layout.addWidget(self.execute_python_button, 0, 3, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.clear_console_button, 0, 4, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.console_message_filter_combobox, 2, 3, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.setRowStretch(300, 300)
        self.layout.setColumnStretch(0, 100)
        self.setLayout(self.layout)

class ExperimentLogGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment log', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.log = QtGui.QTableWidget(self)
        self.log.setColumnCount(2)
        self.log.setHorizontalHeaderLabels(QtCore.QStringList(['Time', 'Log']))
        date_format = QtCore.QString('yyyy-MM-dd hh:mm')
        self.date = QtGui.QDateTimeEdit(self)
        self.date.setDisplayFormat(date_format)
        self.substance = gui.LabeledComboBox(self, 'Substance',['', 'chlorprothixene', 'isofluorane'])#TODO: to config
        self.substance.input.setEditable(True)
        self.amount_input = gui.LabeledInput(self, 'Amount')
        self.comment_input = gui.LabeledInput(self, 'Comment')
        self.add_button = QtGui.QPushButton('Add',  self)
        self.remove_button = QtGui.QPushButton('Remove last', self)
        self.show_experiments = gui.LabeledCheckBox(self, 'Show experiments')
        self.show_experiments.setToolTip('If checked, recordings are displayed with experiment logs')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.log, 0, 0, 6, 3)
        self.log.setColumnWidth(0, 100)
        self.log.setColumnWidth(1, 400)
        self.log.setFixedWidth(510)
        self.log.verticalHeader().setDefaultSectionSize(15)
        self.layout.addWidget(self.show_experiments, 0, 3)
        self.layout.addWidget(self.date, 7, 0)
        self.layout.addWidget(self.substance, 7, 1)
        self.layout.addWidget(self.amount_input, 7, 2, 1, 2)
        self.layout.addWidget(self.comment_input, 8, 0, 1, 2)
        self.layout.addWidget(self.add_button, 8, 2)
        self.layout.addWidget(self.remove_button, 8, 3)
        self.setLayout(self.layout)
        
class AnimalParametersGroupbox(QtGui.QGroupBox):
    '''
    Animal parameters:
    ID: user defined identifier of animal
    Birth date: animal birth date, compulsory
    Injection date: injection date of (green) labeling substance, compulsory
    Gender: -
    Ear punch left, ear punch right: number of punches in animal ears
    Strain: strain of animal, compulsory
    Green labeling: green labeling substance, compulsory
    Red labeling:
    Injection target: where the green labeling substance was injected
    Imaging channels:
    
    == For developers ==
    Adding new parameter:
    1. add parameter name to self.parameter_names
    2. create combobox widget if necessary
    Renaming parameter: check _get_animal_filename method
    '''
    def __init__(self, parent, config):
        self.config=config
        QtGui.QGroupBox.__init__(self, 'Animal parameters', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        default_date = QtCore.QDate(datetime.datetime.now().year, 1, 1)
        date_format = QtCore.QString('dd-MM-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])
        birth_date = QtGui.QDateEdit(self)
        birth_date.setDisplayFormat(date_format)
        birth_date.setDate(default_date)
        injection_date = QtGui.QDateEdit(self)
        injection_date.setDisplayFormat(date_format)
        injection_date.setDate(default_date)
        ear_punch_left = QtGui.QComboBox(self)
        ear_punch_left.addItems(ear_punch_items)
        ear_punch_right = QtGui.QComboBox(self)
        ear_punch_right.addItems(ear_punch_items)
        gender = QtGui.QComboBox(self)
        gender.addItems(QtCore.QStringList(['female', 'male']))
        strain = QtGui.QComboBox(self)
        strain.addItems(QtCore.QStringList(self.config.MOUSE_STRAIN_SUGGESTIONS))
        strain.setEditable(True)
        green_labeling = QtGui.QComboBox(self)
        green_labeling.setEditable(True)
        green_labeling.addItems(QtCore.QStringList(self.config.GREEN_LABELING_SUGGESTIONS))
        red_labeling = QtGui.QComboBox(self)
        red_labeling.setEditable(True)
        red_labeling.addItems(QtCore.QStringList(self.config.RED_LABELING_SUGGESTIONS))
        imaging_channels = QtGui.QComboBox(self)
        imaging_channels.addItems(QtCore.QStringList(['green',  'red',  'both']))
        injection_target = QtGui.QComboBox(self)
        injection_target.setEditable(True)
        injection_target.addItems(QtCore.QStringList(self.config.INJECTION_TARGET_SUGGESTIONS))
        self.table = gui.ParameterTable(self)
        self.table.setToolTip(self.__doc__)
        self.parameter_names = ['id', 'birth_date', 'injection_date', 
                            'gender', 'ear_punch_left', 'ear_punch_right', 'strain', 
                            'green_labeling', 'red_labeling', 'injection_target', 'imaging_channels', 
                            'comments']
        self.table.setRowCount(len(self.parameter_names))
        for row in range(len(self.parameter_names)):
            item = QtGui.QTableWidgetItem(stringop.to_title(self.parameter_names[row]))
            item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item)
            if self.parameter_names[row] in locals().keys():
                self.table.setCellWidget(row, 1, locals()[self.parameter_names[row]])
        self.new_animal_file_button = QtGui.QPushButton('Create new animal file',  self)
        self.update_animal_file_button = QtGui.QPushButton('Update',  self)
        self.update_animal_file_button.setToolTip('Current values of animal parameters are written into animal file')
        self.reload_animal_parameters_button = QtGui.QPushButton('Reload',  self)
        self.reload_animal_parameters_button.setToolTip('Reload animal parameters from file')
        
    def create_layout(self):
        row_height = 25
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.table, 0, 0, 1, 3)
        self.table.setFixedWidth(435)
        self.table.setFixedHeight(len(self.parameter_names) * row_height+30)
        self.table.setColumnWidth(0, 155)
        self.table.setColumnWidth(1, 240)
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        self.layout.addWidget(self.new_animal_file_button, 1, 0)
        self.layout.addWidget(self.update_animal_file_button, 1, 1)
        self.layout.addWidget(self.reload_animal_parameters_button, 1, 2)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)
        
class AnimalParameters(gui.WidgetControl):
    '''
        
    '''
    def __init__(self, poller, config, widget):
        gui.WidgetControl.__init__(self, poller, config, widget)
        self.animal_files = self._get_animal_file_list(file.get_user_experiment_data_folder(self.config))
        
    def _get_animal_file_list(self, folder, animal_files = {}):
        '''
        Returns a list of animal files from user's experiment data folder and user's data storage folder.
        
        In case of overlapping items in the two lists, the later modified will be used.
        '''
        directories, all_files = file.find_files_and_folders(folder, extension = 'hdf5')
        for fn in all_files:
            if os.path.split(fn)[1][:7] == 'animal_':
                ctime = os.path.getctime(fn)
                if animal_files.has_key(fn) and animal_files[fn]>ctime:
                    pass#Do not add file to list
                else:
                    animal_files[fn]=ctime
        return animal_files
        
    def _get_animal_parameters(self):
        '''
        Get animal parameter values from user interface
        '''
        animal_parameters = {}
        for k, v in self.widget.table.get_values().items():
            animal_parameters[stringop.to_variable_name(k)] = v
        return animal_parameters
        
    def _get_animal_filename(self, animal_parameters):
        '''
        Generate animal file name from animal parameters.
        '''
        filename = 'animal_{0}_{1}_{2}_{3}_L{4}R{5}.hdf5'.format(animal_parameters['id'], 
                                                                                                animal_parameters['strain'], 
                                                                                                animal_parameters['birth_date'] , 
                                                                                                animal_parameters['injection_date'],
                                                                                                animal_parameters['ear_punch_left'], 
                                                                                                animal_parameters['ear_punch_right'])
        return os.path.join(file.get_user_experiment_data_folder(self.config), filename)
        
    def _save_animal_parameters(self):
        h=hdf5io.Hdf5io(self.animal_file,self.config)
        h.animal_parameters = copy.deepcopy(self.animal_parameters)
        h.save('animal_parameters')
        h.close()
        
    def save(self):
        '''
        Saves current animal parameters to animal file. Animal file is created if file does not exists.
        '''
        self.animal_parameters = self._get_animal_parameters()
        #Generate animal file filename:
        self.animal_file = self._get_animal_filename(self.animal_parameters)
        check_parameters = ['id', 'strain', 'green_labeling']
        for parname in check_parameters:
            if self.animal_parameters[parname] == '':#Do not create animal file if parameter is not provided
                self.poller.notify_user('WARNING', '{0} must be provided. Animal file not created.'.format(parname))
                return
        if os.path.exists(self.animal_file):
            self.poller.notify_user('WARNING', '{0} animal file alread exists. New animal file not created.'.format(self.animal_file))
            return
        self._save_animal_parameters()
        self.animal_files = self._get_animal_file_list(file.get_user_experiment_data_folder(self.config), self.animal_files)
        self.poller.update_animal_file_list()
        self.printc('{0} file created'.format(self.animal_file))
        
    def update(self):
        '''
        Current values of animal parameters table are written into animal file. If any ID, birthdate, gcamp injection date or ear punch is changed, animal file is renamed.
        '''
        current_animal_parameters = self._get_animal_parameters()
        current_animal_file = self._get_animal_filename(current_animal_parameters)
        #Generate list of modified parameters
        modified_parameters = ', '.join([stringop.to_title(parname) for parname in self.animal_parameters.keys() if current_animal_parameters[parname] != self.animal_parameters[parname]])
        if len(modified_parameters) == 0:
            self.printc('No parameter modified, nothing is updated')
            return
        if not hasattr(self, 'animal_file'):
            self.printc('No animal file, nothing is updated')
            return
        if self.animal_file != current_animal_file:#Rename animal file if necessary
            if not self.poller.ask4confirmation('Renaming animal file from {0} to {1}'.format(os.path.split(self.animal_file)[1], os.path.split(current_animal_file)[1])):
                return
            self.printc('Animal file renamed from {0} to {1}'.format(self.animal_file, current_animal_file))
            os.rename(self.animal_file, current_animal_file)
        #Update animal parameters and animal file name
        self.animal_file = current_animal_file
        self.animal_parameters = current_animal_parameters
        if not self.poller.ask4confirmation('Do you want to update the following parameters in {1}?\n{0}'.format(modified_parameters, os.path.split(self.animal_file)[1])):
            return
        #Rewrite file with modified data
        self._save_animal_parameters()
        self.printc('{0} file updated. Following parameters were modified: {1}'.format(self.animal_file, modified_parameters))

    def load(self):
        '''
        Reloads animal parameters from animal file to gui. User modifications since last update are overwritten
        '''
        if not hasattr(self, 'animal_file'):
            self.printc('No animal file, nothing is updated')
            return
        #Get it from file
        h=hdf5io.Hdf5io(self.animal_file,self.config)
        h.load('animal_parameters')
        if not hasattr(h, 'animal_parameters'):
            self.printc('Animal file does not contain animal parameters.')
            h.close()
            return
        self.animal_parameters = copy.deepcopy(h.animal_parameters)
        h.close()
        #Update to user interface
        self.poller.update_animal_parameters_table()

    def reload(self):
        self.load()
        
    def search_data_storage(self):
        if not hasattr(self.config, 'DATA_STORAGE_PATH'):
            self.printc('machine_config.DATA_STORAGE_PATH parameter needs to be defined')
            return
        if not self.poller.ask4confirmation('Do you want to search {0} for animal files and will be added to current list. It can take some time.'.format(self.config.DATA_STORAGE_PATH)):
            return
        self.printc('Searching for animal parameter files, please wait!')
        self.animal_files = self._get_animal_file_list(self.config.DATA_STORAGE_PATH, self.animal_files)
        self.poller.update_animal_file_list()
        self.printc('Done, animal file list updated')

class AnalysisStatusGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Analysis status', parent)
        self.create_widgets()
        self.create_layout()
        
    def set_headers(self):
        self.analysis_status_table.setHorizontalHeaderLabels(QtCore.QStringList(['Scan\nmode', 'Depth\n[um]', 'Id', 'Laser\n[%]', 'Status', 'Stimulus']))
        
    def create_widgets(self):
#        self.analysis_status_label = QtGui.QLabel('', self)
        self.analysis_status_table = QtGui.QTableWidget(self)
        self.analysis_status_table.setColumnCount(6)
        self.set_headers()
        
        self.analysis_status_table.setColumnWidth(0, 35)
        self.analysis_status_table.setColumnWidth(1, 35)
        self.analysis_status_table.setColumnWidth(2, 30)
        self.analysis_status_table.setColumnWidth(3, 35)
        self.analysis_status_table.setColumnWidth(4, 35)
        self.analysis_status_table.setColumnWidth(5, 115)
        self.analysis_status_table.verticalHeader().setDefaultSectionSize(15)
        
        self.ids_combobox = QtGui.QComboBox(self)
        self.ids_combobox.setEditable(True)
        self.remove_measurement_button = QtGui.QPushButton('Remove measurement',  self)
        self.set_state_to_button = QtGui.QPushButton('Set state to',  self)
        self.set_to_state_combobox = QtGui.QComboBox(self)
        self.set_to_state_combobox.addItems(QtCore.QStringList(['not processed', 'mesextractor_ready', 'find_cells_ready']))
        self.reset_jobhandler_button = QtGui.QPushButton('Reset jobhandler',  self)
        self.add_id_button = QtGui.QPushButton('Add id',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.ids_combobox, 1, 0)
        self.layout.addWidget(self.remove_measurement_button, 1, 1)
        self.layout.addWidget(self.set_state_to_button, 2, 0)
        self.layout.addWidget(self.set_to_state_combobox, 2, 1)
        self.layout.addWidget(self.reset_jobhandler_button, 0, 1)
        self.layout.addWidget(self.analysis_status_table, 3, 0, 4, 3)
        self.layout.addWidget(self.add_id_button, 0, 0)
        self.setLayout(self.layout)

class ExperimentControlGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment control', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        #Stimulation/experiment control related
        self.browse_experiment_file_button = QtGui.QPushButton('Browse',  self)
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList([]))
        self.experiment_name.setMinimumWidth(150)
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop',  self)
        self.experiment_progress = QtGui.QProgressBar(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.browse_experiment_file_button, 0, 0, 1, 1)
        self.layout.addWidget(self.experiment_name, 0, 1, 1, 2)
        self.layout.addWidget(self.start_experiment_button, 1, 0, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 1, 2)
        self.layout.addWidget(self.experiment_progress, 2, 0, 1, 3)
        self.setLayout(self.layout)
        
class ExperimentControl(gui.WidgetControl):
    '''
    This class handles all experiment configuration/control related operation and stores related data.
    Experiment configuration/parameter handling:
        At software start all the python modules in user folder parsed (subfolders not). 
        A database is built containing parameter names and values for each experiment configuration class. This data
        is displayed on the experiment control widget (experiment names) and experiment parameters groupbox where
        user can edit the values.
    '''
    def __init__(self, poller, config, widget, paramwidget):
        self.paramwidget = paramwidget
        gui.WidgetControl.__init__(self, poller, config, widget)
        #find all python module in user folder and load users's all experiment configs and parameters
        self.experiment_config_classes = {}
        self._load_experiment_config_parameters(file.get_user_folder(self.config))
        
    ################# Experiment config parameters ####################
    def browse(self):
        user_folder = file.get_user_folder(self.config)
        self.user_selected_stimulation_module = self.poller.ask4filename('Select stimulation file', user_folder,  '*.py')
        if os.path.exists(self.user_selected_stimulation_module):#Parses files unless cancel pressed on file dialog box
            self._load_experiment_config_parameters(self.user_selected_stimulation_module)

    def _load_experiment_config_parameters(self, filename):
        '''
        If filename is a directory, all py files are with experiment config are loaded and the config names are put to experiment names dropdown box
        Otherwise the experiment configurations within the provided py file are put to experiment names dropdown box in the following format:
        filename/experiment config name
        '''
        if os.path.isdir(filename):
            self.experiment_config_classes = {}
            for python_module in [os.path.join(filename, fn) for fn in os.listdir(filename) if fn.split('.')[-1] == 'py']:
                new_expconf_classes = experiment.parse_stimulation_file(python_module)
                if any([origexpconfs in new_expconf_classes.keys() for origexpconfs in self.experiment_config_classes.keys()]):
                    raise RuntimeError('Redundant experiment config class name. Check {0}.' .format(python_module))
                else:                    
                    self.experiment_config_classes.update(experiment.parse_stimulation_file(python_module))
            self.poller.set_experiment_names(self.experiment_config_classes.keys())
        else:
            self.experiment_config_classes = experiment.parse_stimulation_file(filename)
            #Update list of experiment names with the experiment config names in selected module in filename/experiment_config_name format
            self.poller.set_experiment_names([os.path.join(filename, experiment_config_name) for experiment_config_name in self.experiment_config_classes.keys()])
        pass

    def reload_experiment_parameters(self):
        '''
        Reload experiment configuration parameters with their values from corresponding file
        '''
        if hasattr(self, 'user_selected_stimulation_module'):
            filename = self.user_selected_stimulation_module
        else:
            filename = file.get_user_folder(self.config)
        self._load_experiment_config_parameters(filename)

    def save_experiment_parameters(self):
        #Find out filename and config class name
        configname = str(self.widget.experiment_name.currentText())
        if len(os.path.split(configname)[0]) > 0:#configname string is in this format: file path/experiment config name
            filename = os.path.split(configname)[0]
            configname = os.path.split(configname)[1]
        else:
            filename = file.find_content_in_folder('class '+configname, file.get_user_folder(self.config), '.py')
            if len(filename)>1:
                raise RuntimeError('{0} experiment config found in more than one files'.format(configname))
            else:
                filename = filename[0]
        if not self.poller.ask4confirmation('Do you really want to overwrite {0} file with modified parameters?'.format(filename)):
            return
        #Generate source code lines from table parameter values
        new_section = []
        from_table = self.paramwidget.values.get_values().items()
        for k, v in from_table:
            new_section.append(k+'='+v)
        #Find lines corresponding to modifed parameters
        with open(filename) as f:
            content = f.readlines()
        lines_to_modify = []
        for i in range(len(content)):
            for par in from_table:
                if par[0] in content[i] and par[1] != content[i].replace(' ', ''):#parameter name matches but value does not
                    lines_to_modify.append(i+1)#line number is used instead of index to help debug
            if 'class ' + configname in content[i]:
                header = i+1
            elif ('class ' == content[i][:6] or 'def ' == content[i][:4]) and 'header' in locals() and 'footer' not in locals():#Find next class or def declaration after exp config class
                footer = i+1
        if 'footer' not in locals():
            footer = i+1
        #Replaceble line numbers shall be between header and footer line numbers
        lines_to_modify = [line for line in lines_to_modify if header < line and footer > line]
        if len(lines_to_modify) != len(new_section):
            self.printc(from_table)
            self.printc(lines_to_modify)
            self.printc(new_section)
            raise RuntimeError('Modifiable parameters cannot be found in {0} experiment config declaration. Number of parameters in original experiment config does not match with the number of paramaters to be saved.'.format(configname))
        #Modify content by replacing lines where parameters are.
        for i in range(len(lines_to_modify)):
            content[lines_to_modify[i]-1] = 8*' '+new_section[i]+content[0][-1]#Adding 8 spaces before line (2 levels of indentation), using original file's end of line character
        content= ''.join(content)
        #Check for syntax errors
        introspect.import_code(content,'module_under_test', add_to_sys_modules=0)
        file.write_text_file(filename, content)
        #Parse modified file to make parameter table's data consistent
        self.printc('{1} parameters saved to {0}' .format(filename, configname))

    ################# Experiment execution ####################
    def start_experiment(self):
        '''
        
        '''
        self.printc('test')
#        self.printc('Starting experiment, please wait')
#        self.experiment_parameters = {}
#        self.experiment_parameters['experiment_config'] = str(self.widget.experiment_name.currentText())
#        self.experiment_parameters['enable_ca_recording'] = (self.parent.central_widget.main_widget.experiment_options_groupbox.enable_ca_recording.input.checkState() == 2)
#        self.experiment_parameters['enable_elphys_recording'] = (self.parent.central_widget.main_widget.experiment_options_groupbox.enable_elphys_recording.input.checkState() == 2)
#        self.experiment_parameters['id'] = str(int(time.time()))
#        #Find out experiment duration
#        from visexpman.engine.vision_experiment import experiment
#        fragment_durations = experiment.get_fragment_duration(self.experiment_parameters['experiment_config'], self.config)
#        if fragment_durations is None:
#            self.printc('Fragment duration is not calculated in experiment class')
#            return
#        elif len(fragment_durations) > 1:
#            raise RuntimeError('Multiple fragment experiments not yet supported')
#        self.measurement_duration = 1.1*fragment_durations[0]+self.config.CA_IMAGING_START_DELAY+self.config.GUI_DATA_SAVE_TIME
#        self.experiment_parameters['measurement_duration'] = self.measurement_duration
#        #Save parameters to hdf5 file
#        parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
#        if os.path.exists(parameter_file):
#            self.printc('ID already exists: {0}'.format(self.experiment_parameters['id']))
#        h = hdf5io.Hdf5io(parameter_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
#        fields_to_save = ['parameters']
#        h.parameters = copy.deepcopy(self.experiment_parameters)
#        if hasattr(self, 'animal_parameters'):
#            h.animal_parameters = copy.deepcopy(self.animal_parameters)
#            fields_to_save.append('animal_parameters')
#        if hasattr(self, 'anesthesia_history'):
#            h.anesthesia_history = copy.deepcopy(self.anesthesia_history)
#            fields_to_save.append('anesthesia_history')
#        h.save(fields_to_save)
#        h.close()
#        self.printc('{0} parameter file generated'.format(self.experiment_parameters['id']))
#        command = 'SOCstart_experimentEOCid={0}EOP' .format(self.experiment_parameters['id'])
#        self.queues['stim']['out'].put(command)
#        self._start_analog_recording()
#        self.stimulation_finished = False
#        self.imaging_finished = False
#        self.printc('Experiment duration is {0} seconds, expected end at {1}'.format(int(self.measurement_duration), utils.time_stamp_to_hm(time.time() + self.measurement_duration)))
#        self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_progress.setRange(0, self.measurement_duration)
#        self.measurement_starttime=time.time()

class ExperimentParametersGroupBox(QtGui.QGroupBox):
    '''
    Displays experiment config values and user can edit them
    '''
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment parameters', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.button_names = ['Reload',  'Save']
        for button_name in self.button_names:
            setattr(self, stringop.to_variable_name(button_name), QtGui.QPushButton(button_name,  self))
        self.values = gui.ParameterTable(self)
        self.values.setToolTip('Parameter values shall be python syntax compatible:text like values shall be embedded into quotes, use references only to valid variable names')

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        for i in range(len(self.button_names)):
            self.layout.addWidget(getattr(self, stringop.to_variable_name(self.button_names[i])), 0, i)
        self.layout.addWidget(self.values, 1, 0, 1, len(self.button_names))
        self.setLayout(self.layout)

class AnimalParametersAndExperimentLogWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.animal_filename = gui.LabeledComboBox(self, 'Animal file')
        self.animal_files_from_data_storage = QtGui.QPushButton('Search data storage for animal files',  self)
        self.animal_files_from_data_storage.setToolTip('Search for valid animal files in folder pointed by machine_config.DATA_STORAGE_PATH.\nItems found are added to current animal file list. Might take some time to complete.')
        self.animal_files_from_data_storage.setEnabled(hasattr(self.config, 'DATA_STORAGE_PATH'))
        self.animal_parameters_groupbox = AnimalParametersGroupbox(self, self.config)
        self.log_groupbox = ExperimentLogGroupbox(self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.animal_filename, 0, 0)
        self.layout.addWidget(self.animal_files_from_data_storage, 0, 1)
        self.layout.addWidget(self.animal_parameters_groupbox, 1, 0)
        self.layout.addWidget(self.log_groupbox, 1, 1, 1, 3)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)

############### Application specific widgets ###############
class RetinalExperimentOptionsGroupBox(QtGui.QGroupBox):
    #TODO: add cell name
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment options', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.enable_ca_recording = gui.LabeledCheckBox(self, 'Record Ca signal')
        self.enable_elphys_recording = gui.LabeledCheckBox(self, 'Record electrophyisiology signal')

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.enable_ca_recording, 0, 0, 1, 2)
        self.layout.addWidget(self.enable_elphys_recording, 0, 2, 1, 2)
        self.setLayout(self.layout)

class ExperimentLoopGroupBox(QtGui.QGroupBox):
    '''
    Support controlling a sequence of cortical experiments:
    -objective position and laser intensity ranges
    -enable/disable run all scheduled experiments/next/previous/redo/skip>>/skip<< experiments
    -show list of scheduled experiments
    '''
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment control', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        #Stimulation/experiment control related
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList([]))
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop',  self)
        if self.extended:
            
            self.next_depth_button = QtGui.QPushButton('Next',  self)
            self.redo_depth_button = QtGui.QPushButton('Redo',  self)
            self.previous_depth_button = QtGui.QPushButton('Prev',  self)
            self.graceful_stop_experiment_button = QtGui.QPushButton('Graceful\nstop',  self)
            self.objective_positions_label = QtGui.QLabel('Objective range [um]\n start,end,step',  self)
            self.objective_positions_combobox = QtGui.QComboBox(self)
            self.objective_positions_combobox.setEditable(True)
            self.laser_intensities_label = QtGui.QLabel('Laser intensity \n(min, max) [%]',  self)
            self.laser_intensities_combobox = QtGui.QComboBox(self)
            self.laser_intensities_combobox.setEditable(True)
            self.scan_mode = QtGui.QComboBox(self)
            self.scan_mode.addItems(QtCore.QStringList(['xy', 'xz']))
            self.enable_intrinsic = gui.LabeledCheckBox(self, 'Enable instrinsic imaging')
        self.experiment_progress = QtGui.QProgressBar(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_name, 0, 0, 1, 2)
        self.layout.addWidget(self.start_experiment_button, 0, 2, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 0, 4)
        if self.extended:
            self.layout.addWidget(self.graceful_stop_experiment_button, 1, 4)
            self.layout.addWidget(self.previous_depth_button, 1, 1, 1, 1)
            self.layout.addWidget(self.next_depth_button, 1, 3, 1, 1)
            self.layout.addWidget(self.redo_depth_button, 1, 2, 1, 1)
            self.layout.addWidget(self.scan_mode, 1, 0)
            self.layout.addWidget(self.objective_positions_label, 2, 0)
            self.layout.addWidget(self.objective_positions_combobox, 2, 1, 1, 2)
            self.layout.addWidget(self.laser_intensities_label, 2, 3, 1, 1)
            self.layout.addWidget(self.laser_intensities_combobox, 2, 4, 1, 1)
            self.layout.addWidget(self.enable_intrinsic, 3, 2, 1, 2)
            self.layout.addWidget(self.experiment_progress, 3, 0, 1, 2)
        else:
            self.layout.addWidget(self.experiment_progress, 3, 0, 1, 4)
        self.setLayout(self.layout)        

class FlowmeterControl(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Flowmeter control', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.start_button = QtGui.QPushButton('Start', self)
        self.stop_button = QtGui.QPushButton('Stop', self)
        self.reset_button = QtGui.QPushButton('Reset', self)
        self.status_label = QtGui.QLabel('', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.start_button, 0, 0)
        self.layout.addWidget(self.stop_button, 0, 1)
        self.layout.addWidget(self.reset_button, 0, 2)
        self.layout.addWidget(self.status_label, 0, 3)
        self.setLayout(self.layout)

class TileScanGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Tile scan', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.nrows = gui.LabeledInput(self, 'number of rows')
        self.ncols = gui.LabeledInput(self, 'number of columns')
        self.overlap = gui.LabeledInput(self, 'Overlap [um]')
        self.start_button = QtGui.QPushButton('Start', self)
        self.stop_button = QtGui.QPushButton('Stop', self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.nrows, 0, 0)
        self.layout.addWidget(self.ncols, 0, 1)
        self.layout.addWidget(self.overlap, 0, 2)
        self.layout.addWidget(self.start_button, 1, 0)
        self.layout.addWidget(self.stop_button, 1, 1)
        self.setLayout(self.layout)

class ZstackWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        if hasattr(self.config, 'TAB_SIZE'):
            self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])

    def create_widgets(self):
        self.tile_scan_groupbox = TileScanGroupBox(self)
        self.z_stack_button = QtGui.QPushButton('Create Z stack', self)
        self.zstart = gui.LabeledInput(self, 'z start')
        self.zstop = gui.LabeledInput(self, 'z stop')
        self.zstep = gui.LabeledInput(self, 'z step')
        self.averaging = gui.LabeledInput(self, 'Averaging')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.z_stack_button, 0, 0, 1, 1)
        ct = 0
        for w in [self.zstart, self.zstop, self.zstep, self.averaging]:
            self.layout.addWidget(w, 1, 2*ct, 1, 1)
            ct += 1
        self.layout.addWidget(self.tile_scan_groupbox, 3, 0, 1, 8)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)
        
class ScanRegionGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Scan regions', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.select_mouse_file_label = QtGui.QLabel('Select mouse file', self)
        self.select_mouse_file = QtGui.QComboBox(self)
        self.animal_parameters_label = QtGui.QLabel('', self)
        self.get_xy_scan_button = QtGui.QPushButton('XY scan',  self)
        self.get_xy_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.use_saved_scan_settings_label = QtGui.QLabel('Use saved scan settings', self)
        self.use_saved_scan_settings_settings_checkbox = QtGui.QCheckBox(self)
        self.add_button = QtGui.QPushButton('Add scan region',  self)
        self.scan_regions_combobox = QtGui.QComboBox(self)
        self.scan_regions_combobox.setEditable(True)
        self.remove_button = QtGui.QPushButton('Remove',  self)
        self.update_xy_button = QtGui.QPushButton('Update XY',  self)
        self.update_xz_button = QtGui.QPushButton('Update XZ',  self)
        self.update_xyt_button = QtGui.QPushButton('Update XYT',  self)
        self.move_to_button = QtGui.QPushButton('Move to',  self)
        self.region_info = QtGui.QLabel('',  self)
        self.move_to_region_options = {}
        self.move_to_region_options['header_labels'] = [ QtGui.QLabel('Move', self), QtGui.QLabel('Realign', self), QtGui.QLabel('Adjust origin', self)]
        self.move_to_region_options['row_labels'] = [ QtGui.QLabel('Stage', self), QtGui.QLabel('Objective', self)]
        self.move_to_region_options['checkboxes'] = {}
        self.move_to_region_options['checkboxes']['stage_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_origin_adjust'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'].setEnabled(False)
        self.move_to_region_options['checkboxes']['objective_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_origin_adjust'] = QtGui.QCheckBox(self)
        for k, v in self.move_to_region_options['checkboxes'].items():
#            if 'origin_adjust' not in k and 'objective_move' not in k:
            if 'stage_move' in k:
                v.setCheckState(2)
        self.xz_scan_button = QtGui.QPushButton('XZ scan',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.select_mouse_file_label, 0, 0, 1, 1)
        self.layout.addWidget(self.select_mouse_file, 0, 1, 1, 3)
        self.layout.addWidget(self.animal_parameters_label, 1, 0, 1, 4)
        self.layout.addWidget(self.use_saved_scan_settings_label, 2, 1, 1, 1)
        self.layout.addWidget(self.use_saved_scan_settings_settings_checkbox, 2, 2, 1, 1)
        self.layout.addWidget(self.get_xy_scan_button, 3, 3, 1, 1)
        self.layout.addWidget(self.xz_scan_button, 3, 2, 1, 1)
        self.layout.addWidget(self.add_button, 3, 0, 1, 1)
        self.layout.addWidget(self.scan_regions_combobox, 4, 0, 1, 2)
        self.layout.addWidget(self.region_info, 4, 3, 1, 1)
        self.layout.addWidget(self.remove_button, 5, 0, 1, 1)
        self.layout.addWidget(self.update_xy_button, 5, 1, 1, 1)
        self.layout.addWidget(self.update_xz_button, 5, 2, 1, 1)
        self.layout.addWidget(self.update_xyt_button, 5, 3, 1, 1)
        self.layout.addWidget(self.move_to_button, 4, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][0], 6, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][1], 6, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][2], 6, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][0], 7, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][1], 8, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_move'], 7, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_realign'], 7, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_origin_adjust'], 7, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_move'], 8, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_realign'], 8, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_origin_adjust'], 8, 3, 1, 1)
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)
        
class RoiWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.scan_region_name_label = QtGui.QLabel()
        self.roi_info_image_display = QtGui.QLabel()
#        blank_image = 128*numpy.ones((self.config.ROI_INFO_IMAGE_SIZE['col'], self.config.ROI_INFO_IMAGE_SIZE['row']), dtype = numpy.uint8)
#        self.roi_info_image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        self.roi_plot = Qt4Plot()
        self.roi_plot.setMinimumHeight(230)
        self.select_cell_label = QtGui.QLabel('Select cell',  self)
        self.select_cell_combobox = QtGui.QComboBox(self)
        self.select_cell_combobox.setEditable(False)
        self.next_button = QtGui.QPushButton('>>',  self)
        self.previous_button = QtGui.QPushButton('<<',  self)
        self.accept_cell_button = QtGui.QPushButton('Accept cell',  self)
        self.accept_cell_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.ignore_cell_button = QtGui.QPushButton('Ignore cell',  self)
        self.cell_filter_name_combobox = QtGui.QComboBox(self)
        self.cell_filter_name_combobox.addItems(QtCore.QStringList(['No filter', 'depth', 'id', 'date', 'stimulus']))
        self.cell_filter_combobox = QtGui.QComboBox(self)
        self.show_current_soma_roi_label = QtGui.QLabel('Show current soma roi',  self)
        self.show_current_soma_roi_checkbox = QtGui.QCheckBox(self)
        self.show_current_soma_roi_checkbox.setCheckState(2)
        self.show_selected_soma_rois_label = QtGui.QLabel('Show selected soma rois',  self)
        self.show_selected_soma_rois_checkbox = QtGui.QCheckBox(self)
        self.show_selected_roi_centers_label = QtGui.QLabel('Show selected roi centers',  self)
        self.show_selected_roi_centers_checkbox = QtGui.QCheckBox(self)
        self.show_selected_roi_centers_checkbox.setCheckState(2)
        self.show_selection_on_left_label = QtGui.QLabel('Show selections on left image',  self)
        self.show_selection_on_left_checkbox = QtGui.QCheckBox(self)
        self.xz_line_length_label = QtGui.QLabel('XZ line length',  self)
        self.xz_line_length_combobox = QtGui.QComboBox(self)
        self.xz_line_length_combobox.setEditable(True)
        self.xz_line_length_combobox.setEditText(str(self.config.XZ_SCAN_CONFIG['LINE_LENGTH']))
        self.cell_merge_distance_label =  QtGui.QLabel('Cell merge \ndistance [um]',  self)
        self.cell_merge_distance_combobox = QtGui.QComboBox(self)
        self.cell_merge_distance_combobox.setEditable(True)
        self.cell_merge_distance_combobox.setEditText(str(self.config.CELL_MERGE_DISTANCE))
        self.cell_group_label =  QtGui.QLabel('Cell group name',  self)
        self.cell_group_combobox = QtGui.QComboBox(self)
        self.cell_group_combobox.setEditable(True)
        self.create_xz_lines_button = QtGui.QPushButton('XZ lines',  self)
        self.create_xz_lines_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.xy_scan_button = QtGui.QPushButton('XY scan',  self)
        self.xy_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.suggested_depth_label = QtGui.QLabel('',  self)
        self.roi_pattern_parameters_label = QtGui.QLabel('ROI pattern parameters: pattern size, distance from center [um]',  self)
        self.roi_pattern_parameters_lineedit = QtGui.QComboBox(self)
        self.roi_pattern_parameters_lineedit.setEditable(True)
        self.roi_pattern_parameters_lineedit.setEditText('{0},{1}'.format(self.config.ROI_PATTERN_SIZE, self.config.ROI_PATTERN_RADIUS))
        self.cell_info = QtGui.QLabel('',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        image_height_in_rows = 3
        
        self.layout.addWidget(self.scan_region_name_label, 0, 0, 1, 5)
#        self.layout.addWidget(self.roi_info_image_display, 1, 0, image_height_in_rows, 13)
        self.layout.addWidget(self.roi_plot, 1, 0, image_height_in_rows, 13)
        
        self.layout.addWidget(self.show_current_soma_roi_label, image_height_in_rows + 2, 8)
        self.layout.addWidget(self.show_current_soma_roi_checkbox, image_height_in_rows + 2, 9)
        self.layout.addWidget(self.show_selected_soma_rois_label, image_height_in_rows + 3, 8)
        self.layout.addWidget(self.show_selected_soma_rois_checkbox, image_height_in_rows + 3, 9)
        self.layout.addWidget(self.show_selected_roi_centers_label, image_height_in_rows + 4, 8)
        self.layout.addWidget(self.show_selected_roi_centers_checkbox, image_height_in_rows + 4, 9)
        self.layout.addWidget(self.show_selection_on_left_label, image_height_in_rows + 5, 8)
        self.layout.addWidget(self.show_selection_on_left_checkbox, image_height_in_rows + 5, 9)
        self.layout.addWidget(self.xy_scan_button, image_height_in_rows + 6, 8)
        
        self.layout.addWidget(self.select_cell_label, image_height_in_rows + 2, 0)
        self.layout.addWidget(self.select_cell_combobox, image_height_in_rows + 2, 1, 1, 3)        

        self.layout.addWidget(self.previous_button, image_height_in_rows + 2, 4)
        self.layout.addWidget(self.accept_cell_button, image_height_in_rows + 2, 5)
        self.layout.addWidget(self.ignore_cell_button, image_height_in_rows + 2, 6)
        self.layout.addWidget(self.next_button, image_height_in_rows + 2, 7)
        
        self.layout.addWidget(self.cell_filter_name_combobox, image_height_in_rows + 3, 0, 1, 1)
        self.layout.addWidget(self.cell_filter_combobox, image_height_in_rows + 3, 1, 1, 2)
#        self.layout.addWidget(self.cell_group_edit_label, image_height_in_rows + 3, 4)
#        self.layout.addWidget(self.cell_group_edit_combobox, image_height_in_rows + 3, 5)
        self.layout.addWidget(self.suggested_depth_label, image_height_in_rows + 3, 6, 1, 2)
        
        self.layout.addWidget(self.cell_group_label, image_height_in_rows + 5, 0)
        self.layout.addWidget(self.cell_group_combobox, image_height_in_rows + 5, 1, 1, 2)
        self.layout.addWidget(self.xz_line_length_label, image_height_in_rows + 6, 0)
        self.layout.addWidget(self.xz_line_length_combobox, image_height_in_rows + 6, 1)
        self.layout.addWidget(self.cell_merge_distance_label, image_height_in_rows + 6, 2)
        self.layout.addWidget(self.cell_merge_distance_combobox, image_height_in_rows + 6, 3)
        self.layout.addWidget(self.create_xz_lines_button, image_height_in_rows + 6, 4)
        self.layout.addWidget(self.roi_pattern_parameters_label, image_height_in_rows + 7, 0, 1, 4)
        self.layout.addWidget(self.roi_pattern_parameters_lineedit, image_height_in_rows + 7, 4)
        self.layout.addWidget(self.cell_info, image_height_in_rows + 8, 0, 1, 9)
        
        self.layout.setRowStretch(15, 15)
        self.layout.setColumnStretch(15, 15)
        self.setLayout(self.layout)

################### Image display #######################
class ImagesWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.OVERVIEW_IMAGE_SIZE['col'], self.config.OVERVIEW_IMAGE_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = []
        for i in range(4):
            self.image_display.append(QtGui.QLabel())
        self.blank_image = 128*numpy.ones((self.config.IMAGE_SIZE['col'], self.config.IMAGE_SIZE['row']), dtype = numpy.uint8)
        for image in self.image_display:
            image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
            
    def clear_image_display(self, index):
        self.image_display[index].setPixmap(imaged.array_to_qpixmap(self.blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        for i in range(len(self.image_display)):
            self.layout.addWidget(self.image_display[i], i/2, (i%2)*2, 1, 1)
        
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
class OverviewWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = QtGui.QLabel()
        blank_image = 128*numpy.ones((self.config.OVERVIEW_IMAGE_SIZE['col'], self.config.OVERVIEW_IMAGE_SIZE['row']), dtype = numpy.uint8)
        self.image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.image_display, 0, 0, 1, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
################### Application widgets #######################
#TODO: needs to be moved elsewhere
class MainWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.scan_region_groupbox = ScanRegionGroupBox(self)
        self.measurement_datafile_status_groupbox = AnalysisStatusGroupbox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 2, 4)
#        self.layout.addWidget(self.set_objective_value_button, 2, 8, 1, 1)
        self.layout.addWidget(self.scan_region_groupbox, 2, 0, 2, 4)
        self.layout.addWidget(self.measurement_datafile_status_groupbox, 0, 4, 10, 4)
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)
        
class CommonWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        #generate connection name list
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.COMMON_TAB_SIZE['col'], int(self.config.COMMON_TAB_SIZE['row']))
        
    def create_widgets(self):
        self.show_gridlines_label = QtGui.QLabel('Show gridlines', self)
        self.show_gridlines_checkbox = QtGui.QCheckBox(self)
        self.show_gridlines_checkbox.setCheckState(2)
        self.show_xzlines_label = QtGui.QLabel('Show xz lines', self)
        self.show_xzlines_checkbox = QtGui.QCheckBox(self)
        self.connected_clients_label = QtGui.QLabel('', self)
        self.set_stage_origin_button = QtGui.QPushButton('Set stage origin', self)
        self.set_stage_origin_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.read_stage_button = QtGui.QPushButton('Read stage', self)
        self.move_stage_button = QtGui.QPushButton('Move stage', self)
        self.tilt_brain_surface_button = QtGui.QPushButton('Tilt brain surface', self)
        self.tilt_brain_surface_button.setToolTip(BRAIN_TILT_HELP)
        self.enable_tilting_label = QtGui.QLabel('Enable tilting', self)
        self.enable_tilting_checkbox = QtGui.QCheckBox(self)
        self.enable_xy_scan_with_move_stage_label = QtGui.QLabel('XY scan after\n move stage', self)
        self.enable_xy_scan_with_move_checkbox = QtGui.QCheckBox(self)
        
        self.stop_stage_button = QtGui.QPushButton('Stop stage', self)
        self.set_objective_button = QtGui.QPushButton('Set objective', self)
        self.enable_reset_objective_origin_after_moving_label = QtGui.QLabel('Set objective to 0\n after moving it', self)
        self.enable_set_objective_origin_after_moving_checkbox = QtGui.QCheckBox(self)
        self.current_position_label = QtGui.QLabel('', self)
        self.enable_laser_adjust_label = QtGui.QLabel('Adjust laser\nwhen moving\nto surface', self)
        self.enable_laser_adjust_checkbox = QtGui.QCheckBox(self)
        
        self.registration_subimage_label = QtGui.QLabel('Registration subimage, upper left (x,y),\nbottom right (x,y) [um]', self)
        self.registration_subimage_combobox = QtGui.QComboBox(self)
        self.registration_subimage_combobox.setEditable(True)
        self.register_button = QtGui.QPushButton('Register', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_gridlines_label, 0, 0)
        self.layout.addWidget(self.show_gridlines_checkbox, 0, 1)
        self.layout.addWidget(self.show_xzlines_label, 0, 2)
        self.layout.addWidget(self.show_xzlines_checkbox, 0, 3)
        self.layout.addWidget(self.connected_clients_label, 0,4, 1, 4)
        
        self.layout.addWidget(self.set_stage_origin_button, 2, 0, 1, 1)
        self.layout.addWidget(self.read_stage_button, 2, 1, 1, 1)
        self.layout.addWidget(self.move_stage_button, 2, 2, 1, 1)
        self.layout.addWidget(self.enable_xy_scan_with_move_stage_label, 2, 3, 1, 1)
        self.layout.addWidget(self.enable_xy_scan_with_move_checkbox, 2, 4, 1, 1)
        self.layout.addWidget(self.stop_stage_button, 2, 5, 1, 1)
        self.layout.addWidget(self.set_objective_button, 2, 6, 1, 1)
        self.layout.addWidget(self.enable_reset_objective_origin_after_moving_label, 2, 7, 1, 1)
        self.layout.addWidget(self.enable_set_objective_origin_after_moving_checkbox, 2, 8, 1, 1)
        self.layout.addWidget(self.enable_laser_adjust_label, 2, 9, 1, 1)
        self.layout.addWidget(self.enable_laser_adjust_checkbox, 2, 10, 1, 1)
        self.layout.addWidget(self.current_position_label, 0, 8, 1, 2)
        self.layout.addWidget(self.tilt_brain_surface_button, 1, 5, 1, 1)
        self.layout.addWidget(self.enable_tilting_label, 1, 0, 1, 1)
        self.layout.addWidget(self.enable_tilting_checkbox, 1, 1, 1, 1)
        
        self.layout.addWidget(self.registration_subimage_label, 1, 6, 1, 2)
        self.layout.addWidget(self.registration_subimage_combobox, 1, 8, 1, 3)
        self.layout.addWidget(self.register_button, 1, 11)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)


################### Debug/helper widgets #######################
class HelpersWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        #generate connection name list
        self.connection_names = ['']
        for k, v in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            if 'GUI' in k:
                self.connection_names.append(k.replace('GUI', '').replace('_', '').lower())
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        #Helpers
        self.save_xy_scan_button = QtGui.QPushButton('Save xy image',  self)
        self.help_button = QtGui.QPushButton('Help',  self)
        self.override_enforcing_set_stage_origin_checkbox = QtGui.QCheckBox(self)
        self.override_enforcing_set_stage_origin_checkbox.setToolTip('Do not check for set stage origin')
        self.add_simulated_measurement_file_button = QtGui.QPushButton('Add simulated measurement file',  self)
        self.rebuild_cell_database_button = QtGui.QPushButton('Rebuild cell database button',  self)
        #Network related
        self.show_connected_clients_button = QtGui.QPushButton('Show connected clients',  self)
        self.show_network_messages_button = QtGui.QPushButton('Show network messages',  self)
        self.select_connection_list = QtGui.QComboBox(self)
        self.select_connection_list.addItems(QtCore.QStringList(self.connection_names))
        self.send_command_button = QtGui.QPushButton('Send command',  self)
        self.gui_test_button = QtGui.QPushButton('Gui test',  self)
        self.camera_button = QtGui.QPushButton('Camera',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_connected_clients_button, 0, 0, 1, 1)
        self.layout.addWidget(self.show_network_messages_button, 0, 1, 1, 1)
        self.layout.addWidget(self.select_connection_list, 0, 2, 1, 1)
        self.layout.addWidget(self.send_command_button, 0, 3, 1, 1)
        
        self.layout.addWidget(self.save_xy_scan_button, 1, 0, 1, 1)
        self.layout.addWidget(self.help_button, 1, 1, 1, 1)
        self.layout.addWidget(self.override_enforcing_set_stage_origin_checkbox, 1, 2, 1, 1)
        self.layout.addWidget(self.add_simulated_measurement_file_button, 1, 3, 1, 1)
        self.layout.addWidget(self.rebuild_cell_database_button, 1, 4, 1, 1)
        
        self.layout.addWidget(self.gui_test_button, 2, 0)
        self.layout.addWidget(self.camera_button, 3, 0)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)

if __name__ == '__main__':
    pass
    
