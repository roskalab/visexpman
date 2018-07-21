'''
vision_experiment.gui implements widgets that build up the user interface of vision experiment manager applciations. Some widgets are used in multiple applications.
'''

import os
import os.path
import numpy
import datetime
import time
import copy
import shutil
import inspect
import pdb
import scipy.io
import pyqtgraph
import pyqtgraph.console

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
import hdf5io
from visexpman.engine.vision_experiment import experiment, experiment_data
from visexpman.engine.hardware_interface import scanner_control,daq_instrument,instrument
from visexpman.engine import ExperimentConfigError, AnimalFileError
from visexpman.engine.generic import gui,fileop,stringop,introspect,utils,colors,signal

#OBSOLETE
BRAIN_TILT_HELP = 'Provide tilt degrees in text input box in the following format: vertical axis [degree],horizontal axis [degree]\n\
        Positive directions: horizontal axis: right, vertical axis: outer side (closer to user)'
              
UNSELECTED_ROI_COLOR = (150,100,100)
SELECTED_ROI_COLOR = (255,00,0)              
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
        QtGui.QGroupBox.__init__(self, '', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.log = QtGui.QTableWidget(self)
        self.log.setColumnCount(2)
        self.log.setHorizontalHeaderLabels(QtCore.QStringList(['Time', 'Log']))
        self.new_entry = AddExperimentLogEntryGroupbox(self)
        self.remove_button = QtGui.QPushButton('Remove entry', self)
        self.remove_button.setToolTip('Before pressing this button, select removeable item(s).')
        self.show_experiments = QtGui.QCheckBox(self)
        self.show_experiments.setText('Show experiments')
        self.show_experiments.setToolTip('If checked, recordings are displayed with experiment logs')
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.log, 0, 0, 4, 4)
        self.log.setColumnWidth(0, 140)
        self.log.setColumnWidth(1, 430)
        self.log.setFixedWidth(600)
        self.log.verticalHeader().setDefaultSectionSize(17)
        self.layout.addWidget(self.new_entry, 4, 0, 2, 4)
        self.new_entry.setFixedWidth(600)
        self.layout.addWidget(self.remove_button, 6, 0)
        self.layout.addWidget(self.show_experiments, 6, 1)
        self.setLayout(self.layout)
        
class AddExperimentLogEntryGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        date_format = QtCore.QString('yyyy-MM-dd hh:mm')
        self.date = QtGui.QDateTimeEdit(self)
        self.date.setDisplayFormat(date_format)
        self.substance = gui.LabeledComboBox(self, 'Substance',self.parent().parent().config.GUI['INJECTED_SUBSTANCE_SUGGESTIONS'])
        self.substance.input.setEditable(True)
        self.amount = gui.LabeledInput(self, 'Amount')
        self.comment = gui.LabeledInput(self, 'Comment')
        self.add_button = QtGui.QPushButton('Add',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.date, 0, 0)
#        self.date.setFixedWidth(150)
        self.layout.addWidget(self.substance, 0, 1)
        self.substance.input.setMinimumWidth(150)
#        self.substance.labelw.setFixedWidth(70)
        self.layout.addWidget(self.amount, 0, 2)
        self.layout.addWidget(self.comment, 1, 0, 1, 2)
        self.layout.addWidget(self.add_button, 1, 2)
        self.setLayout(self.layout)
        
class ExperimentLog(gui.WidgetControl):
    '''
        
    '''
    def __init__(self, poller, config, widget):
        gui.WidgetControl.__init__(self, poller, config, widget)
        self.suggested_date_last_update = time.time()
        
        
    def update_suggested_date(self):
        now = time.time()
        if now-self.suggested_date_last_update>self.config.GUI['EXPERIMENT_LOG_UPDATE_PERIOD']:
            self.poller.update_experiment_log_suggested_date()
            self.suggested_date_last_update = now
            
    def _get_new_entry_data(self):
        entry = {}
        date= self.widget.new_entry.date.date()
        tme= self.widget.new_entry.date.time()
        entry['date'] = time.mktime(time.struct_time((date.year(),date.month(),date.day(),tme.hour(),tme.minute(),tme.second(),0,0,-1)))
        entry['substance'] = str(self.widget.new_entry.substance.input.currentText())
        entry['amount'] = str(self.widget.new_entry.amount.input.text())
        entry['comment'] = str(self.widget.new_entry.comment.input.text())
        entry['timestamp'] = time.time()
        return entry
        
    def _is_timestamp_in_log(self, timestamp):
        for entry in self.poller.animal_file.log:
            if entry['date'] == timestamp:
                return True
        return False
        
    def add(self):
        if not hasattr(self.poller.animal_file, 'filename'):
            self.printc('No animal file created yet')
            return
        new_entry = self._get_new_entry_data()
        if len([v for v in ['substance', 'amount', 'comment'] if new_entry[v] == '']) == 3:
            self.printc('Please provide log data')
            return
        self.poller.animal_file.log.append(new_entry)
        hdf5io.save_item(self.poller.animal_file.filename, 'log', utils.object2array(self.poller.animal_file.log), self.config, overwrite = True,filelocking=False)
        self.poller.update_experiment_log()
        self.printc('Log entry saved')
        
    def remove(self):
        selection = self.widget.log.selectedItems()
        if len(selection)==0:
            self.printc('Nothing is selected for removal')
            return
        if not self.poller.ask4confirmation('Are you sure you want to remove selected entries?'):
            return
        #Find removable items by timestamp in log using removable row indexes and table widget items
        removable_rows = [item.row() for item in self.widget.log.selectedItems()]
        for removable_row in removable_rows:
            for log_entry in self.poller.animal_file.log:
                if log_entry['timestamp'] == self.widget.log.item(removable_row, 1).timestamp:
                    self.poller.animal_file.log.remove(log_entry)
                    break
        #Remove item(s) from table widget
        for item in self.widget.log.selectedItems():
            self.widget.log.removeRow(item.row())
        hdf5io.save_item(self.poller.animal_file.filename, 'log', utils.object2array(self.poller.animal_file.log), self.config, overwrite = True,filelocking=False)
        self.printc('Selected log entry removed')

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
        QtGui.QGroupBox.__init__(self, '', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        default_date = QtCore.QDate(datetime.datetime.now().year, 1, 1)
        date_format = QtCore.QString('dd-MM-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])
        birth_date = QtGui.QDateEdit(self)
        birth_date.setDisplayFormat(date_format)
        birth_date.setDate(default_date)
        birth_date.setToolTip('Animal birth date, compulsory')
        injection_date = QtGui.QDateEdit(self)
        injection_date.setDisplayFormat(date_format)
        injection_date.setDate(default_date)
        injection_date.setToolTip('Injection date of (green) labeling substance, compulsory')
        ear_punch_left = QtGui.QComboBox(self)
        ear_punch_left.addItems(ear_punch_items)
        ear_punch_left.setToolTip('Number of punches in animal\'s ears')
        ear_punch_right = QtGui.QComboBox(self)
        ear_punch_right.addItems(ear_punch_items)
        ear_punch_right.setToolTip('Number of punches in animal\'s ears')
        gender = QtGui.QComboBox(self)
        gender.addItems(QtCore.QStringList(['female', 'male']))
        strain = QtGui.QComboBox(self)
        strain.addItems(QtCore.QStringList(self.config.GUI['MOUSE_STRAIN_SUGGESTIONS']))
        strain.setEditable(True)
        green_labeling = QtGui.QComboBox(self)
        green_labeling.setEditable(True)
        green_labeling.addItems(QtCore.QStringList(self.config.GUI['GREEN_LABELING_SUGGESTIONS']))
        green_labeling.setToolTip('Green labeling substance, compulsory')
        red_labeling = QtGui.QComboBox(self)
        red_labeling.setEditable(True)
        red_labeling.addItems(QtCore.QStringList(self.config.GUI['RED_LABELING_SUGGESTIONS']))
        imaging_channels = QtGui.QComboBox(self)
        imaging_channels.addItems(QtCore.QStringList(['green',  'red',  'both']))
        injection_target = QtGui.QComboBox(self)
        injection_target.setEditable(True)
        injection_target.addItems(QtCore.QStringList(self.config.GUI['INJECTION_TARGET_SUGGESTIONS']))
        self.table = gui.ParameterTable(self)
        self.parameter_names = ['id', 'birth_date', 'injection_date', 
                            'gender', 'ear_punch_left', 'ear_punch_right', 'strain', 
                            'green_labeling', 'red_labeling', 'injection_target', 'imaging_channels', 
                            'comment']
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
        
        self.animal_filename = gui.LabeledComboBox(self, 'Animal file')
        self.animal_files_from_data_storage = QtGui.QPushButton('Search data storage',  self)
        self.animal_files_from_data_storage.setToolTip('Search for valid animal files in folder pointed by machine_config.DATA_STORAGE_PATH.\nItems found are added to current animal file list. Might take some time to complete.')
        self.animal_files_from_data_storage.setEnabled(hasattr(self.config, 'DATA_STORAGE_PATH'))
        self.copy_animal_files_from_data_storage = QtGui.QPushButton('Copy animal file',  self)
        self.copy_animal_files_from_data_storage.setEnabled(hasattr(self.config, 'DATA_STORAGE_PATH'))
        self.copy_animal_files_from_data_storage.setToolTip('Copies selected animal file from data storage to experiment data folder')
        
    def create_layout(self):
        row_height = 25
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.animal_filename, 0, 0, 1, 3)
        self.animal_filename.labelw.setFixedWidth(100)
        self.animal_filename.input.setFixedWidth(300)
        self.layout.addWidget(self.animal_files_from_data_storage, 1, 0)
        self.layout.addWidget(self.copy_animal_files_from_data_storage, 1, 1)
        self.layout.addWidget(self.table, 2, 0, 1, 3)
        self.table.setFixedWidth(425)
        self.table.setFixedHeight(len(self.parameter_names) * row_height+30)
        self.table.setColumnWidth(0, 155)
        self.table.setColumnWidth(1, 240)
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        self.layout.addWidget(self.new_animal_file_button, 3, 0)
        self.layout.addWidget(self.update_animal_file_button, 3, 1)
        self.layout.addWidget(self.reload_animal_parameters_button, 3, 2)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)

#OBSOLETE
class AnimalFile(gui.WidgetControl):
    '''
        Handles animal file and animal parameters
    '''
    def __init__(self, poller, config, widget, context_animal_file=None):
        self.variable_names = ['animal_parameters', 'log', 'scan_regions', 'recordings']
        gui.WidgetControl.__init__(self, poller, config, widget)
        self.animal_files = self._get_animal_file_list(fileop.get_user_experiment_data_folder(self.config))
        self.check4animal_files_last_update = time.time()
        self.enable_check4animal_files = True
        #Most recently modified file is selected
        if not context_animal_file is None:
            self.filename = context_animal_file
        else:
            timestamps = self.animal_files.values()
            if len(timestamps)>0:
                timestamp = max(timestamps)
                self.filename = [k for k, v in self.animal_files.items() if v == timestamp][0]
        self.load(update_gui=False)
        if not hasattr(self, 'recordings'):
            self.recordings = []
        
    def _init_variables(self):
        for variable_name in self.variable_names:
            if variable_name == 'log' or variable_name == 'recordings':
                setattr(self, variable_name, [])
            else:
                setattr(self, variable_name, {})
        
    def _get_animal_file_list(self, folder, animal_files = {}):
        '''
        Returns a list of animal files from user's experiment data folder and user's data storage folder.
        
        In case of overlapping items in the two lists, the later modified will be used.
        '''
        directories, all_files = fileop.find_files_and_folders(folder, extension = 'hdf5')
        for fn in all_files:
            if fileop.is_animal_file(fn):
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
            if isinstance(v, list):
                animal_parameters[stringop.to_variable_name(k)] = v[0]
            else:
                animal_parameters[stringop.to_variable_name(k)] = v
        return animal_parameters
        
    def _get_animal_filename(self, animal_parameters):
        '''
        Generate animal file name from animal parameters and user experiment data path.
        '''
        return os.path.join(fileop.get_user_experiment_data_folder(self.config), fileop.generate_animal_filename(animal_parameters))
        
    def _animal_parameters2file(self):
        h=hdf5io.Hdf5io(self.filename,self.config,filelocking=False)
        h.animal_parameters = utils.object2array(copy.deepcopy(self.animal_parameters))
        h.save('animal_parameters')
        h.close()
        
    def save_animal_parameters(self):
        '''
        Saves current animal parameters to animal fileop. Animal file is created if file does not exists.
        '''
        self._init_variables()
        self.animal_parameters = self._get_animal_parameters()
        #Generate animal file filename:
        self.filename = self._get_animal_filename(self.animal_parameters)
        check_parameters = ['id', 'strain', 'green_labeling']
        for parname in check_parameters:
            if self.animal_parameters[parname] == '':#Do not create animal file if parameter is not provided
                self.poller.notify_user('WARNING', '{0} must be provided. Animal file not created.'.format(parname))
                return
        if os.path.exists(self.filename):
            self.poller.notify_user('WARNING', '{0} animal file alread exists. New animal file not created.'.format(self.filename))
            return
        #check if animal file withthe same animal id exists
        for fn in os.listdir(os.path.split(self.filename)[0]):
            if fileop.is_animal_file(fn):
                id = fileop.parse_animal_filename(fn)['id']
                if id == self.animal_parameters['id']:
                    if self.poller.ask4confirmation('Animal ID ({0}) already exists.\nAre you sure you want to create this file?'.format(id)):
                        break
                    else:
                        return
        self._animal_parameters2file()
        self.animal_files = self._get_animal_file_list(fileop.get_user_experiment_data_folder(self.config), self.animal_files)
        self.poller.update_animal_file_list()
        self.poller.update_experiment_log()
        self.printc('{0} file created'.format(self.filename))
        
    def update(self):
        '''
        Current values of animal parameters table are written into animal fileop. If any ID, birthdate, gcamp injection date or ear punch is changed, animal file is renamed.
        '''
        current_animal_parameters = self._get_animal_parameters()
        current_animal_file = self._get_animal_filename(current_animal_parameters)
        #Generate list of modified parameters
        modified_parameters = ', '.join([stringop.to_title(parname) for parname in self.animal_parameters.keys() if current_animal_parameters[parname] != self.animal_parameters[parname]])
        if len(modified_parameters) == 0:
            self.printc('No parameter modified, nothing is updated')
            return
        if not hasattr(self, 'filename'):
            self.printc('No animal file, nothing is updated')
            return
        if os.path.split(self.filename)[0] != fileop.get_user_experiment_data_folder(self.config):
            self.poller.notify_user('WARNING', 'Only files experiment data folder can be modified. Animal files from datastorage shall be first copied to experiment data folder')
            return
        if self.filename != current_animal_file:#Rename animal file if necessary
            if not self.poller.ask4confirmation('Renaming animal file from {0} to {1}'.format(os.path.split(self.filename)[1], os.path.split(current_animal_file)[1])):
                return
            os.rename(self.filename, current_animal_file)
            self.printc('Animal file renamed from {0} to {1}'.format(self.filename, current_animal_file))
        #Update animal parameters and animal file name
        self.filename = current_animal_file
        self.animal_parameters = current_animal_parameters
        if not self.poller.ask4confirmation('Do you want to update the following parameters in {1}?\n{0}'.format(modified_parameters, os.path.split(self.filename)[1])):
            return
        #Rewrite file with modified data
        self._animal_parameters2file()
        self.printc('{0} file updated. Following parameters were modified: {1}'.format(self.filename, modified_parameters))

    def load(self, update_gui=True):
        if not hasattr(self, 'filename'):
            return
        if not os.path.exists(self.filename):
            return
        h=hdf5io.Hdf5io(self.filename,self.config,filelocking=False)
        self._init_variables()
        for variable_name in self.variable_names:
            h.load(variable_name)
            if hasattr(h, variable_name):
                setattr(self, variable_name, copy.deepcopy(utils.array2object(getattr(h, variable_name))))#TODO: later perhaps object serialization&compression is needed
            elif variable_name == 'animal_parameters':
                raise AnimalFileError('animal_parameters node is missing, {0} animal file is invalid'.format(self.filename))
        h.close()
        if update_gui:
            self.poller.update_animal_parameters_table()
            self.poller.update_experiment_log()
        pass
       
    def load_animal_parameters(self, update_gui=True):
        '''
        Reloads animal parameters from animal file to gui. User modifications since last update are overwritten
        '''
        if not hasattr(self.printc,'__call__'):
            return#Called as standalone without GUI
        if not hasattr(self, 'filename'):
            self.printc('No animal file, nothing is updated')
            return
        if not os.path.exists(self.filename):
            self.printc('Animal file does not exists: {0} '.format(self.filename))
            return
        #Get it from file
        h=hdf5io.Hdf5io(self.filename,self.config)
        h.load('animal_parameters')
        if not hasattr(h, 'animal_parameters'):
            self.printc('Animal file does not contain animal parameters.')
            h.close()
            return
        self.animal_parameters = copy.deepcopy(utils.array2object(h.animal_parameters))
        h.close()
        if update_gui:#Update to user interface
            self.poller.update_animal_parameters_table()
        
    def reload_animal_parameters(self):
        self.load_animal_parameters()

    def search_data_storage(self):
        if not hasattr(self.config, 'DATA_STORAGE_PATH'):
            self.printc('machine_config.DATA_STORAGE_PATH parameter needs to be defined')
            return
        if not self.poller.ask4confirmation('Do you want to search {0} for animal files and will be added to current list. It can take some time.'.format(self.config.DATA_STORAGE_PATH)):
            return
        self.printc('Searching for animal parameter files, please wait!')
        self.animal_files = self._get_animal_file_list(self.config.DATA_STORAGE_PATH, self.animal_files)
        self.enable_check4animal_files=False
        self.poller.update_animal_file_list()
        self.printc('Done, animal file list updated')
        
    def copy(self):
        '''
        Copy animal parameter file from data storage to experiment data folder
        '''
        if fileop.get_user_experiment_data_folder(self.config) in self.filename:
            self.poller.notify_user('', 'This animal file is already in experiment data folder')
            return
        if os.path.exists(os.path.join(fileop.get_user_experiment_data_folder(self.config), os.path.split(self.filename)[1])):
            message = 'Copy of this file already exists in experiment data folder. Do you want to overwrite it?'
            if not self.poller.ask4confirmation(message):
                return
        self.printc('Copying file, please wait!')
        shutil.copy(self.filename, fileop.get_user_experiment_data_folder(self.config))
        self.printc('Animal file copied.')
        new_animal_filename = os.path.join(fileop.get_user_experiment_data_folder(self.config), os.path.split(self.filename)[1])
        self.animal_files[new_animal_filename] = os.path.getctime(new_animal_filename)
        self.poller.update_animal_file_list()
        
    def chec4new_animal_file(self):
        '''
        Disabled when files data strorage is searched. Reenabling is only possible when application restarts
        The idea is that no periodic checking is necessary when user looks for animal file in data storage
        '''
        if not self.enable_check4animal_files:
            return
        now = time.time()
        if introspect.is_test_running():
            check_time = 3.0
        else:
            check_time = 10.0
        if now-self.check4animal_files_last_update>check_time:
             new_animal_files= self._get_animal_file_list(fileop.get_user_experiment_data_folder(self.config), {})
             if new_animal_files != self.animal_files:#TODO: content needs to be compared
                self.animal_files = new_animal_files
                self.poller.update_animal_file_list()
                self.check4animal_files_last_update = now
                self.printc('Animal file list updated')

class RecordingStatusGroupbox(QtGui.QGroupBox):
    '''
    Displays recordings including planned ones - experiment start command issued but not yet executed
    '''
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Recording status', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.table = gui.ParameterTable(self)
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 80)
        self.table.setHorizontalHeaderLabels(QtCore.QStringList(['', 'state']))
        self.remove = QtGui.QPushButton('Remove',  self)
        self.remove.setToolTip('Remove selected recording')
        self.set_state = QtGui.QPushButton('Change state to',  self)
        self.new_state = QtGui.QComboBox(self)
        self.new_state.addItems(QtCore.QStringList(['', 'queued', 'preparing', 'running', 'done', 'analyzed']))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.remove, 0, 0)
        self.layout.addWidget(self.new_state, 0, 1)
        self.layout.addWidget(self.set_state, 0, 2)
        self.layout.addWidget(self.table, 1, 0, 1, 3)
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

############### Application specific widgets ###############
class RetinalExperimentOptionsGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment options', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.cell_name = gui.LabeledInput(self, 'Cell name')
        self.cell_name.setToolTip('Providing cell name is not mandatory')
        self.cell_name.setFixedWidth(270)
        rec_channels = []
        rec_channels.extend(['Calcium fluorescence, ' + item+' PMT' for item in self.parent().config.PMTS.keys()])
        rec_channels.append('Electrophysiology signal')
        self.recording_channel = gui.LabeledListWidget(self, 'Recording channels', items = rec_channels)
        self.recording_channel.setFixedHeight(100)
        self.recording_channel.setFixedWidth(270)
        self.recording_channel.setToolTip('Selection of any channels enables calcium or electrophysiology signal recording.\nSelect none of the PMTs for disabling calcium imaging.\nMultiple channels can be also selected.' )
        self.scanning_range = gui.LabeledInput(self, 'Scan range (height, width) [um]')
        self.scanning_range.setFixedWidth(290)
        self.resolution_label = QtGui.QLabel('Pixel size', self)
        self.resolution_unit = QtGui.QComboBox(self)
        self.resolution_unit.addItems(QtCore.QStringList(['pixel/um', 'um/pixel', 'us']))
        self.pixel_size = QtGui.QLineEdit(self)
        self.pixel_size.setFixedWidth(70)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.cell_name, 0, 0, 1, 3)
        self.layout.addWidget(self.recording_channel, 1, 0, 1, 3)
        self.layout.addWidget(self.scanning_range, 3, 0, 1, 3)
        self.layout.addWidget(self.resolution_label, 4, 0)
        self.layout.addWidget(self.resolution_unit, 4, 1)
        self.layout.addWidget(self.pixel_size, 4, 2)
        
        self.setLayout(self.layout)
        
class RetinalToolbox(QtGui.QGroupBox):
    '''
    Filterwheels
    Bullseye
    Adjust grey level
    Projector on/off
    Stimulus centering
    '''
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
    
    def create_widgets(self):
        if len(self.config.FILTERWHEEL)!=2:
            raise NotImplementedError('2 filterwheel configs are expected')
        for fw_config in self.config.FILTERWHEEL:
            vname = 'filterwheel{0}'.format(self.config.FILTERWHEEL.index(fw_config))
            setattr(self, vname, QtGui.QComboBox(self))
            getattr(self, vname).setFixedWidth(80)
            filters = ['']
            filters.extend(fw_config['filters'].keys())
            getattr(self, vname).addItems(QtCore.QStringList(filters))
            if not fw_config.has_key('connected to') or fw_config['connected to'] == '':
                getattr(self, vname).setEnabled(False)
        self.grey_level = QtGui.QComboBox(self)
        self.grey_level.addItems(QtCore.QStringList(['0 %', '50 %', '100 %']))
        self.grey_level.setFixedWidth(80)
        self.grey_level.setToolTip('Set grey level')
        self.grey_level.setEditable(True)
        self.bullseye_type = QtGui.QComboBox(self)
        self.bullseye_type.setFixedWidth(100)
        self.bullseye_type.addItems(QtCore.QStringList(['bullseye', 'spot', 'L', 'square']))
        self.bullseye_type.setToolTip('''
        Bullseye: size is the diameter
        L: size corresponds to the longer side. Shape center is the concave vertice of the L
        Spot: TBD
        ''')
        self.bullseye_size = gui.LabeledInput(self, 'size')
        self.bullseye_size.setToolTip('[um]')
        self.bullseye_toggle = QtGui.QPushButton('Toggle\r\nBullseye',  self)
        self.projector_enable = gui.LabeledCheckBox(self, 'Projector ON')
        self.stimulus_centering = XYWidget(self)
        self.stimulus_centering.setToolTip('Center X, Y of stimulus [um]')
        self.stimulus_centering.center_x.setFixedWidth(90)
        self.stimulus_centering.center_y.setFixedWidth(90)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        widgets_1st_line = [self.filterwheel0, self.filterwheel1, self.grey_level]
        widgets_2nd_line = [self.bullseye_type, self.bullseye_size, self.bullseye_toggle]
        widgets_3rd_line = [self.projector_enable]
        for i in range(len(widgets_1st_line)):
            self.layout.addWidget(widgets_1st_line[i], 0, i, 1, 1)
        for i in range(len(widgets_2nd_line)):
            self.layout.addWidget(widgets_2nd_line[i], 1, i, 1, 1)
        for i in range(len(widgets_3rd_line)):
            self.layout.addWidget(widgets_3rd_line[i], 2, i, 1, 1)
        self.layout.addWidget(self.stimulus_centering, 3, 0, 2, 3)
        self.setLayout(self.layout)
        
class XYWidget(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
    
    def create_widgets(self):
        self.center_x = gui.LabeledInput(self, 'X')
        self.center_y = gui.LabeledInput(self, 'Y')
        self.up = QtGui.QPushButton('^',  self)
        self.down = QtGui.QPushButton('v',  self)
        self.left = QtGui.QPushButton('<',  self)
        self.right = QtGui.QPushButton('>',  self)
        for w in [self.left, self.right, self.up, self.down]:
            w.setFixedWidth(50)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.setVerticalSpacing(1)
        self.layout.addWidget(self.center_x, 0, 0, 1, 2)
        self.layout.addWidget(self.center_y, 1, 0, 1, 2)
        self.layout.addWidget(self.left, 1, 2, 1, 1)
        self.layout.addWidget(self.up, 0, 3, 1, 1)
        self.layout.addWidget(self.right, 1, 4, 1, 1)
        self.layout.addWidget(self.down, 1, 3, 1, 1)
        self.setLayout(self.layout)

class RetinaTools(gui.WidgetControl):
    '''
        Handles animal file and animal parameters
    '''
    def __init__(self, poller, config, widget, context_animal_file=None):
        gui.WidgetControl.__init__(self, poller, config, widget)

    def toggle_bullseye(self):
        type = str(self.widget.bullseye_type.currentText())
        size = float(str(self.widget.bullseye_size.input.text()))
        msgs = [{'function': 'set_variable', 'args': ['bullseye_size', size]},
            {'function': 'set_variable', 'args': ['bullseye_type', type]},
            {'function': 'toggle_bullseye'}]
        for msg in msgs:
            self.poller.send(msg, connection='stim')
    
    def set_filterwheel0(self):
        self._set_filterwheel(0)
        
    def set_filterwheel1(self):
        self._set_filterwheel(1)

    def _set_filterwheel(self, channel):
        connection = self.config.FILTERWHEEL[channel].get('connected to', None)
        filter = str(getattr(self.widget, 'filterwheel{0}'.format(channel)).currentText())
        if filter == '':
            return
        if connection == 'stim':
            self.poller.send({'function': 'set_filterwheel', 'args': [channel, filter]}, connection='stim')
        elif connection == 'main_ui':
            instrument.set_filterwheel(filter, self.config.FILTERWHEEL[channel])
            self.printc('Filterwheel is set to {1}/{0}'.format(self.config.FILTERWHEEL[channel]['filters'][filter], filter))
            
    def set_color(self):
        color = float(str(self.widget.grey_level.currentText()).replace('%',''))/100
        self.printc('Screen color set to {0}'.format(color))
        self.poller.send({'function': 'set_context_variable', 'args': ['background_color', color]}, connection='stim')
        
    def set_projector(self):
        self.printc('Turning {0} projector'.format('on' if self.widget.projector_enable.input.checkState() == 2 else 'off'))
        self.poller.send({'function': 'set_variable', 'args': ['projector_state', self.widget.projector_enable.input.checkState() == 2]}, connection='ca_imaging')
            
        
    

class CorticalExperimentOptionsGroupBox(QtGui.QGroupBox):
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

class CalibrationGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.config=self.parent().config
        self.create_widgets()
        self.create_layout()
    
    def create_widgets(self):
        pass
        
    def create_layout(self):
        pass
        
class MachineParametersGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.config=self.parent().config
        self.create_widgets()
        self.create_layout()
        self.machine_parameters = {}
        stimdevice_help = '''Empty: the experiment and experiment class will be executed as it is\n
Any stimulation device: stimulation will be presented by the selected device,\n
Choices: {0}:\n Selected Experiment config is overridden by this value'''.format(self.parent().config.STIMULATION_DEVICES)

        self.machine_parameters['scanner'] = {'Scan center':  '0, 0#Center of scanning, format: (row, col) [um]', 
                                                                        'Stimulus flash trigger duty cycle': '100#[%] 100% means that the flash is on during the whole flyback of the x mirror', 
                                                                        'Stimulus flash trigger delay': '0#[us]',
                                                                        'Analog input sampling rate': '200000#[Hz]',
                                                                        'Analog output sampling rate': '200000#[Hz]',
                                                                        'Enable flyback scan': '0#If set to 1, x mirror\'s flyback movement is also used for data acquisition',
                                                                        'Maximal x line linearity error':'5#[%], Increase: better scan speed but more distortion at the left and right edges.\nKeep it below 15 %.',
                                                                        'Enable scanner phase characteristics': '1#1=enable',
                                                                        'Scanner position to voltage': '0.013#Conversion factor between scanner voltage and scanning range, voltage=size*factor',
                                                                        #'Stimulation device': 'projector#{0}'.format(stimdevice_help)
                                                                        }
                                                                        
        self.machine_parameter_order = {}
        self.machine_parameter_order['scanner'] = ['Scan center', 'Maximal x line linearity error',
                                            'Analog input sampling rate', 'Analog output sampling rate',
                                            'Stimulus flash trigger duty cycle', 'Stimulus flash trigger delay', 'Enable flyback scan', 
                                            'Enable scanner phase characteristics','Scanner position to voltage']

    def create_widgets(self):
        self.table = {}
        self.scanner_section_title = QtGui.QLabel('Scanner parameters', self)
        self.table['scanner'] = gui.ParameterTable(self)
        self.table['scanner'].setFixedWidth(450)
        self.table['scanner'].setFixedHeight(550)
        self.table['scanner'].setColumnWidth(0, 250)
        self.check_scan_parameters_button = QtGui.QPushButton('Check scan parameters', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.scanner_section_title, 0, 0, 1, 1)
        self.layout.addWidget(self.check_scan_parameters_button, 1, 0, 1, 1)
        self.layout.addWidget(self.table['scanner'], 2, 0, 1, 2)
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
        
class RoiWidget(QtGui.QWidget):#OBSOLETE
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
class DisplayConfigurationGroupbox(QtGui.QGroupBox):
    def __init__(self, parent, default_name):
        QtGui.QGroupBox.__init__(self, '', parent)
        self.default_name = default_name
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.name = gui.LabeledInput(self, 'Name')
        self.name.input.setText(self.default_name)
        self.enable = QtGui.QCheckBox(self)
        display_channels_list= ['ALL', 'IR camera']
        display_channels_list.extend(self.config.PMTS.keys())
        self.channel_select = gui.LabeledComboBox(self, 'Channel', display_channels_list)
        default_options = ['raw', 'Half scale', 'Quarter scale', '1/8th scale']
        filter_tooltip =''' \nBy default the maximum intensity is the maximal pmt voltage, therefore maximal intensity is reserved for saturation.
        Half, quarter and 1/8th scale could be used to decrease the value of this maximal intensity' and make dim images visible'''
        #TODO: rename histogram shift
        emo = ['3x3 median filter', 'Histogram shift', 'Histogram equalize', 'Ca activity']
        emo.extend(default_options)
        emo.reverse()
        self.exploring_mode_options = gui.LabeledComboBox(self, 'Exploring', emo)
        self.exploring_mode_options.input.setCurrentIndex(emo.index('raw'))
        self.exploring_mode_options.setToolTip('The selected option will be applied on the display when no recording is ongoing. Filters are applied separately on each channel.'+filter_tooltip)#TODO: append info about filters
        rmo = ['MIP', 'Ca activity']
        rmo.extend(default_options)
        rmo.reverse()
        self.recording_mode_options = gui.LabeledComboBox(self, 'Recording', rmo)
        self.recording_mode_options.setToolTip('The selected option will be applied on the display when no recording is ongoing. MIP: maximum intensity projection.'+filter_tooltip)
        self.recording_mode_options.input.setCurrentIndex(rmo.index('raw'))
        self.gridline_select = gui.LabeledComboBox(self, 'Gridline', ['off', 'sparse', 'dense', 'scanner nonlienarity'])
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.enable, 0, 0)
        self.layout.addWidget(self.name, 0, 1)
        self.layout.addWidget(self.channel_select, 1, 0,1,2)
        self.layout.addWidget(self.exploring_mode_options, 2, 0,1,2)
        self.layout.addWidget(self.recording_mode_options, 3, 0,1,2)
        self.layout.addWidget(self.gridline_select, 4, 0,1,2)
        self.setLayout(self.layout)
        
class CaImagingVisualisationControlWidget(QtGui.QWidget):
    '''
    Container of Ca Image display configurations (max 6), display selection, plot source selector and the plot itself
    
    Advanced filter configuration widgets could be added later
    '''
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.display_configs = []
        for i in range(self.config.MAX_CA_IMAGE_DISPLAYS):
            self.display_configs.append(DisplayConfigurationGroupbox(self, str(i)))
            self.display_configs[-1].setFixedWidth(200)
            self.display_configs[-1].setFixedHeight(250)
        self.select_display =  gui.LabeledComboBox(self, 'Select diplay', map(str, range(self.config.MAX_CA_IMAGE_DISPLAYS)))
        self.select_display.setToolTip('Select display for tuning advanced filter parameters')
        self.select_plot = gui.LabeledComboBox(self, 'Select plot', ['histogram', 'Ca activity'])#TODO might be unnecessary
            
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        index = 0
        for row in range(2):
            for col in range(self.config.MAX_CA_IMAGE_DISPLAYS/2):
                self.layout.addWidget(self.display_configs[index], row+2, 2*col,1,2)
                index += 1
        self.layout.addWidget(self.select_display, 4, 0)
        self.layout.addWidget(self.select_plot, 5, 0)
        self.setLayout(self.layout)
        
class CaImagingVisualisationControl(gui.WidgetControl):
    def __init__(self, poller, config, widget):
        gui.WidgetControl.__init__(self, poller, config, widget)
        self.display_configuration = {}
        
    def generate_display_configuration(self, force_send=False):
        display_configuration = {}
        for i in range(self.config.MAX_CA_IMAGE_DISPLAYS):
            if self.widget.display_configs[i].enable.checkState()==2:#If enabled
                name = str(self.widget.display_configs[i].name.input.text())
                if display_configuration.has_key(name):
                    self.poller.notify_user('WARNING', '{0} display name is redundant'.format(name))
                    return
                display_configuration[name] = {}
                for n in ['channel_select', 'exploring_mode_options', 'recording_mode_options', 'gridline_select']:
                    display_configuration[name][n] = str(getattr(self.widget.display_configs[i], n).input.currentText())
        #Check if configuration has changed
        send = False
        if len(self.display_configuration.keys()) != len(display_configuration.keys()):
            send = True
        else:
            for k in display_configuration.keys():
                for kk in display_configuration[k]:
                    try:
                        if display_configuration[k][kk] != self.display_configuration[k][kk]:
                            send=True
                            break
                    except KeyError:
                        send=True
                        break
                if send:
                    break
        self.display_configuration = copy.deepcopy(display_configuration)
        if send or force_send:#If changed, send the display configuration to ca_imaging
            function_call = {'function': 'set_variable', 'args': ['display_configuration', display_configuration]}
            self.poller.send(function_call,connection='ca_imaging')
            self.printc('Ca imaging display updated')
                    
class ROITools(QtGui.QGroupBox):
    def __init__(self,parent):
        QtGui.QGroupBox.__init__(self,'ROI', parent)
        self.save = QtGui.QPushButton('Save',  self)
        self.suggest = QtGui.QPushButton('Suggest',  self)
        self.show_label= QtGui.QLabel('Show',self)
        self.show_center = gui.LabeledCheckBox(self, 'Centers')
        self.show_center.input.setCheckState(2)
        self.show_roi = gui.LabeledCheckBox(self, 'ROI')
        self.show_roi.input.setCheckState(2)
        self.prev = QtGui.QPushButton('<<',  self)
        self.select = QtGui.QComboBox(self)
        self.next = QtGui.QPushButton('>>',  self)
        self.remove = QtGui.QPushButton('Remove',  self)
        for w in [self.save,self.suggest, self.prev, self.next]:
            w.setFixedWidth(70)
        self.roi_size_label = self.trace_analysis_results = QtGui.QLabel('Roi size [um]', self)
        self.min_roi_size = gui.LabeledInput(self, 'min')
        self.max_roi_size = gui.LabeledInput(self, 'max')
        self.sigma = gui.LabeledInput(self, 'Sigma')
        self.threshold_factor = gui.LabeledInput(self, 'Threshold')
        
        self.select.setFixedWidth(120)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.save, 0, 0)
        self.layout.addWidget(self.suggest, 0, 1)
        self.layout.addWidget(self.show_label, 0, 2)
        self.layout.addWidget(self.show_center, 0, 3)
        self.layout.addWidget(self.show_roi, 0, 4)
        self.layout.addWidget(self.prev, 1, 0)
        self.layout.addWidget(self.select, 1, 1)
        self.layout.addWidget(self.next, 1, 2)
        self.layout.addWidget(self.remove, 1, 3)
        self.layout.addWidget(self.roi_size_label, 2, 0)
        self.layout.addWidget(self.min_roi_size, 2, 1)
        self.layout.addWidget(self.max_roi_size, 2, 2)
        self.layout.addWidget(self.sigma, 2, 3)
        self.layout.addWidget(self.threshold_factor, 2, 4)
        self.setLayout(self.layout)
        
class TraceAnalysis(QtGui.QGroupBox):
    def __init__(self,parent):
        QtGui.QGroupBox.__init__(self,'Trace', parent)
        self.normalization = gui.LabeledComboBox(self, 'Normalization',items = ['no', 'dF/F', 'std'])
        self.normalization.input.setCurrentIndex(1)
        self.baseline_start = gui.LabeledInput(self, 'Baseline start [s]')
        self.baseline_start.setToolTip('Relative to stimulus start')
        self.baseline_end = gui.LabeledInput(self, 'Baseline end [s]')
        self.baseline_end.setToolTip('Relative to stimulus start')
        self.post_response_duration = gui.LabeledInput(self, 'Post response duration [s]')
        self.post_response_duration.setToolTip('Duration of interval after stimulation. This part of the trace will be used to quantify how much was the response sustained')
        self.initial_drop_duration = gui.LabeledInput(self, 'Initial drop duration [s]')
        self.initial_drop_duration.setToolTip('From the beginning to this time point will be used to determine the initial Ca signal level')
        self.trace_analysis_results = QtGui.QLabel('', self)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.trace_analysis_results, 0, 0,3,2)
        self.layout.addWidget(self.baseline_start, 0, 2)
        self.layout.addWidget(self.baseline_end, 0, 3)
        self.layout.addWidget(self.normalization, 0, 4)
        self.layout.addWidget(self.post_response_duration, 1, 2)
        self.layout.addWidget(self.initial_drop_duration, 1, 3)
        self.setLayout(self.layout)
                
class Analysis(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.parent=parent
        self.export2mat = QtGui.QPushButton('Export to mat', self)
        self.export2mat.setToolTip('Exports datafile to mat file. Current rois are also saved to both hdf5 and mat')
        self.roi=ROITools(self)
        self.ta=TraceAnalysis(self)
        self.gw = pyqtgraph.GraphicsLayoutWidget(self)
        self.gw.setBackground((255,255,255))
        self.gw.setFixedHeight(300)
        self.gw.setAntialiasing(True)
        self.plot=self.gw.addPlot()
        self.plot.enableAutoRange()
        self.plot.showGrid(True,True,1.0)
        self.curve = self.plot.plot(pen=(0,0,0))
        
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.gw, 0, 0, 2,4)
        self.layout.addWidget(self.roi, 2, 0, 1,2)
        self.layout.addWidget(self.ta, 3, 0, 1,2)

        self.layout.addWidget(self.export2mat, 4, 0)
        self.layout.setRowStretch(300, 300)
        self.setLayout(self.layout)
        
        self.connect(self.roi.select, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.roi.suggest, QtCore.SIGNAL('clicked()'), self.suggest)
        self.connect(self.roi.next, QtCore.SIGNAL('clicked()'), self.next_roi)
        self.connect(self.roi.prev, QtCore.SIGNAL('clicked()'), self.prev_roi)
        self.connect(self.roi.remove, QtCore.SIGNAL('clicked()'), self.remove_roi)
        self.connect(self.roi.save, QtCore.SIGNAL('clicked()'), self.save)
        self.connect(self.export2mat, QtCore.SIGNAL('clicked()'), self.export)
        self.connect(self.roi.show_center.input, QtCore.SIGNAL('stateChanged(int)'), self.update_image)
        self.connect(self.roi.show_roi.input, QtCore.SIGNAL('stateChanged(int)'), self.update_image)
        self.connect(self.ta.normalization.input, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.ta.baseline_start.input, QtCore.SIGNAL('textChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.ta.baseline_end.input, QtCore.SIGNAL('textChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.ta.post_response_duration.input, QtCore.SIGNAL('textChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.ta.initial_drop_duration.input, QtCore.SIGNAL('textChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self, QtCore.SIGNAL('update_image'), self.parent.parent.update_image)
        self.connect(self, QtCore.SIGNAL('printc'), self.parent.parent.printc)
        self.connect(self, QtCore.SIGNAL('notify_user'), self.parent.parent.notify_user)
        
    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)
        
    def roi_update(self):
        self.roi.select.blockSignals(True)
        self.roi.select.clear()
        self.roi.select.blockSignals(False)
        self.roi.select.addItems(QtCore.QStringList(['{0} {1:1.0f},{2:1.0f}@{3:1.0f}'.format(r[0],r[1],r[2],r[3]) for r in self.parent.image.roi_info]))
        self.roi.select.setCurrentIndex(len(self.parent.image.roi_info)-1)
        
    def next_roi(self):
        self.roi.select.setCurrentIndex(self.roi.select.currentIndex()+1)
        
    def prev_roi(self):
        self.roi.select.setCurrentIndex(self.roi.select.currentIndex()-1)
        
    def roi_mouse_selected(self,index):
        self.roi.select.setCurrentIndex(index)
        
    def remove_roi(self):
        x,y=self.parent.image.roi_info[int(self.roi.select.currentIndex())][1:3]
        self.parent.image.remove_roi(x,y)
        self.parent.image.update_roi_info()
        
    def selected_roi_changed(self):
        self.poller = self.parent.parent.poller
        if not hasattr(self.poller, 'rawdata'):
            return
        index=int(self.roi.select.currentIndex())
        for i in range(len(self.parent.image.rois)):
            if i == index:
                self.parent.image.rois[i].setPen(SELECTED_ROI_COLOR)
            else:
                self.parent.image.rois[i].setPen(UNSELECTED_ROI_COLOR)
        #Update plot
        roi_info=self.parent.image.roi_info[index]
        self.ca = experiment_data.extract_roi_curve(self.poller.rawdata, roi_info[1],roi_info[2],roi_info[3],'circle', self.poller.scale)[:self.poller.ti.shape[0]]
        #normalize
        try:
            baseline_start=float(str(self.ta.baseline_start.input.text()))
            baseline_end=float(str(self.ta.baseline_end.input.text()))
            baseline_length=baseline_end-baseline_start
            post_response_duration=float(str(self.ta.post_response_duration.input.text()))
        except ValueError:
            self.emit(QtCore.SIGNAL('notify_user'), 'WARNING', 'Please provide baseline start and end, post response and initial drop durations')
            return
        normalization_mode = str(self.ta.normalization.input.currentText())
        transient_analysis = cone_data.TransientAnalysator(baseline_start, baseline_end, post_response_duration)
        scaled_trace, rise_time_constant, fall_time_constant, response_amplitude, post_response_signal_level, initial_drop = transient_analysis.calculate_trace_parameters(self.ca, {'ti':self.poller.ti, 'ts': self.poller.ts})
        if normalization_mode == 'no':
            self.normalized = self.ca
        elif normalization_mode == 'dF/F':
            baseline = self.ca[numpy.where(numpy.logical_and(self.poller.ti<self.poller.ts[0],self.poller.ti>self.poller.ts[0]-baseline_length))].mean()
            self.normalized = self.ca / baseline
        elif normalization_mode == 'std':
            self.normalized = scaled_trace
        self.curve.setData(self.poller.ti, self.normalized)
        self.plot.setYRange(min(self.normalized), max(self.normalized))
        if hasattr(self,'stimulus_time'):
            self.plot.removeItem(self.stimulus_time)
        if 0:
            #Color stimulus band depending on response amplitude:
            if abs(response_amplitude) <3:
                c=(40,40,40,100)
            elif abs(response_amplitude) >=3 and abs(response_amplitude) <4:
                c=(100,40,40,100)
            elif abs(response_amplitude) >=4:
                c=(40,100,40,100)
        c=(40,40,40,100)
        self.stimulus_time = pyqtgraph.LinearRegionItem(self.poller.ts, movable=False, brush = c)
        self.plot.addItem(self.stimulus_time)
        self.ta.trace_analysis_results.setText(
        'Response size: {0:0.2f} std\nTime constants\nrise {1:0.3f} s\nfall {2:0.3f} s\nPost response {3:0.2f} std\nInitial drop {4:0.2f} std'
            .format(response_amplitude, rise_time_constant, fall_time_constant, post_response_signal_level, initial_drop))
        
    def suggest(self):
        self.poller = self.parent.parent.poller
        try:
            min_ = int(float(str(self.roi.min_roi_size.input.text()))/self.poller.scale)
            max_ = int(float(str(self.roi.max_roi_size.input.text()))/self.poller.scale)
            sigma = float(str(self.roi.sigma.input.text()))*max_
            threshold_factor = float(str(self.roi.threshold_factor.input.text()))
        except ValueError:
            self.emit(QtCore.SIGNAL('notify_user'), 'WARNING', 'Invalid roi size or sigma parameters')
            return
        self.suggested_rois = cone_data.find_rois(numpy.cast['uint16'](signal.scale(self.poller.meanimage, 0,2**16-1)), min_,max_,sigma,threshold_factor)
        self.suggested_roi_contours = map(cone_data.area2edges, self.suggested_rois)
        self.last_find_roi_parameters = {'min_roi_size':min_, 'max_roi_size':max_, 'sigma':sigma, 'threshold_factor':threshold_factor}
        #Add rois
        for r in self.suggested_roi_contours:
            size=(r.max(axis=0)-r.min(axis=0)+1)*self.poller.scale
            self.parent.image.add_roi(*(r.min(axis=0)*self.poller.scale+0.5*size), size = size)
        self.update_image()
        self.parent.image.update_roi_info()
        
    def update_image(self):
        self.poller = self.parent.parent.poller
        show_contour = True
        show_center = self.roi.show_center.input.checkState()==2
        show_roi = self.roi.show_roi.input.checkState()==2
        mi=numpy.zeros((self.poller.meanimage.shape[0],self.poller.meanimage.shape[1],3))
        mi[:,:,1]=self.poller.meanimage
        if hasattr(self, 'suggested_rois'):
            for r in self.suggested_roi_contours if show_contour else self.suggested_rois:
                coo = r
                if show_roi:
                    mi[coo[:,0],coo[:,1],2]=self.poller.meanimage.max()*0.4
                self.parent.image.set_roi_visibility(*(r.mean(axis=0)*self.poller.scale), visibility = show_center)
        self.emit(QtCore.SIGNAL('update_image'), mi,self.poller.scale)
        
    def save(self):
        '''
        Saving rois
        '''
        if not hasattr(self.parent.parent.poller, 'current_datafile') and not hasattr(self.parent.image, 'roi_info'):
            return
        file_info = os.stat(self.parent.parent.poller.current_datafile)
        h=hdf5io.Hdf5io(self.parent.parent.poller.current_datafile,filelocking=False)
        h.timing = {'ti': self.poller.ti, 'ts':self.poller.ts}
        h.rois = self.parent.image.roi_info
        h.roi_curves = [experiment_data.extract_roi_curve(self.poller.rawdata, roi_info[1],roi_info[2],roi_info[3],'circle', self.poller.scale)[:self.poller.ti.shape[0]] for roi_info in self.parent.image.roi_info]
        h.save(['rois','roi_curves','timing'])
        h.close()
        fileop.set_file_dates(self.parent.parent.poller.current_datafile, file_info)
        self.printc('{0} rois are saved'.format(len(h.rois)))
        
    def export(self):
        if not hasattr(self.parent.parent.poller, 'current_datafile'):
            return
        self.save()
        h=hdf5io.Hdf5io(self.parent.parent.poller.current_datafile, filelocking=False)
        items = [r._v_name for r in h.h5f.list_nodes('/')]
        data={}
        for item in items:
            h.load(item)
            data[item]=getattr(h,item)
        outfile=self.parent.parent.poller.current_datafile.replace('.hdf5', '.mat')
        scipy.io.savemat(outfile, data, oned_as = 'row', long_field_names=True)
        fileop.set_file_dates(outfile, os.stat(self.parent.parent.poller.current_datafile))
        h.close()
        self.printc('Data exported to {0}'.format(outfile))
        
        
class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent):
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':self, 'analysis': parent.analysis, 'utils':utils, 'fileop': fileop, 'signal':signal, numpy: 'numpy'}, text = 'Poller: self.p  Also available: analysis, numpy, utils, fileop, signal')
        
    def set_poller(self, poller):
        self.p=poller
        
class ReceptiveFieldPlots(pyqtgraph.GraphicsLayoutWidget):
    '''
    Number of plots can be updated in runtime
    '''
    def __init__(self,parent):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plots = []
        return
        self.set_plot_num(3,4)
        traces = []
        for i in range(3):
            traces1 = []
            for j in range(4):
                traces1.append({'x':numpy.arange(100), 'y': numpy.sin(numpy.arange(100)/(j+1+i)), 'title': (i,j)})
            traces.append(traces1)
        self.addplots(traces)
        
    def addplots(self,traces):
        self.plots = []
        self.clear()
        for r in range(self.nrows):
            for c in range(self.ncols):
                self.addplot(traces[r][c])
            self.nextRow()
        
    def set_plot_num(self,nrows,ncols):
        self.nrows=nrows
        self.ncols=ncols
        
    def addplot(self,traces):
        self.plots.append(self.addPlot(title=traces['title']))
        color_index=0
        for trace in traces['trace']:
            if trace.has_key('color'):
                c=trace['color']
            else:
                c = tuple(numpy.cast['int'](numpy.array(colors.get_color(0))*255))
            self.plots[-1].plot(trace['x'], trace['y'], pen=c)
            color_index+=1
        self.plots[-1].showGrid(True,True,1.0)
        
################### Application widgets #######################
class MainWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        leftcolwidth = 360
        rightcolwidth = 400
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.experiment_control_groupbox.setMaximumWidth(leftcolwidth)
        self.experiment_control_groupbox.setFixedHeight(140)
        if self.config.PLATFORM == 'elphys_retinal_ca':
            self.experiment_options_groupbox = RetinalExperimentOptionsGroupBox(self)
            self.toolbox = RetinalToolbox(self)
            self.toolbox.setMaximumWidth(rightcolwidth)
        elif self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical':
            self.experiment_options_groupbox = CorticalExperimentOptionsGroupBox(self)
        self.experiment_options_groupbox.setMaximumWidth(leftcolwidth)
        self.experiment_options_groupbox.setFixedHeight(260)
        self.recording_status = RecordingStatusGroupbox(self)
        self.recording_status.setMaximumWidth(rightcolwidth)
        self.recording_status.setFixedHeight(330)
        self.experiment_parameters = ExperimentParametersGroupBox(self)
        self.experiment_parameters.setMaximumWidth(leftcolwidth)
        self.experiment_parameters.setFixedHeight(170)
        self.experiment_parameters.values.setColumnWidth(0, 200)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 1, 1)
        self.layout.addWidget(self.experiment_options_groupbox, 1, 0, 2, 1)
        self.layout.addWidget(self.experiment_parameters, 3, 0, 1, 1)
        self.layout.addWidget(self.recording_status, 0, 1, 2, 1)
        self.layout.addWidget(self.toolbox, 2, 1, 2, 1)
#        self.layout.setRowStretch(10, 5)
#        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)

class CommonWidget(QtGui.QWidget):#OBSOLETE
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
class HelpersWidget(QtGui.QWidget):#OBSOLETE
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
    
