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
import PyQt4.Qwt5 as Qwt

import visexpman
import hdf5io
from visexpman.engine.vision_experiment import experiment, experiment_data
from visexpman.engine.hardware_interface import scanner_control,daq_instrument,instrument
from visexpman.engine import ExperimentConfigError, AnimalFileError
from visexpman.engine.generic import gui,fileop,stringop,introspect,utils,colors,signal

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

class ExperimentControl(gui.WidgetControl):
    '''
    This class handles all experiment configuration/control related operation and stores related data.
    Experiment configuration/parameter handling:
        At software start all the python modules in user folder parsed (subfolders not). 
        A database is built containing parameter names and values for each experiment configuration class. This data
        is displayed on the experiment control widget (experiment names) and experiment parameters groupbox where
        user can edit the values.
    '''
    def __init__(self, poller, config, widget, paramwidget, status_widget, context_experiment_config_file=None):
        self.paramwidget = paramwidget
        self.status_widget = status_widget
        gui.WidgetControl.__init__(self, poller, config, widget)
        self.machine_config = config
        #find all python module in user folder and load users's all experiment configs and parameters
        self.experiment_config_classes = {}
        if context_experiment_config_file is None:
            context_experiment_config_file = fileop.get_user_module_folder(self.config)
        self._load_experiment_config_parameters(context_experiment_config_file)
        self.isstimulus_started=False
        self.experiment_not_started_message_sent = False
        self.daq_queues = daq_instrument.init_daq_queues()
        
    ################# Experiment config parameters ####################
    def browse(self):
        user_folder = fileop.get_user_module_folder(self.config)
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
                    raise ExperimentConfigError('Redundant experiment config class name. Check {0}.' .format(python_module))
                else:                    
                    self.experiment_config_classes.update(new_expconf_classes)
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
            filename = fileop.get_user_module_folder(self.config)
        self._load_experiment_config_parameters(filename)
        
    def _find_out_experiment_config_filename(self):
        '''
            Find out filename and config class name
        '''
        configname = str(self.widget.experiment_name.currentText())
        if len(os.path.split(configname)[0]) > 0:#configname string is in this format: file path/experiment config name
            filename = os.path.split(configname)[0]
            configname = os.path.split(configname)[1]
        else:
            filename = fileop.find_content_in_folder('class '+configname, fileop.get_user_module_folder(self.config), '.py')
            if len(filename)>1:
                raise ExperimentConfigError('{0} experiment config found in more than one files'.format(configname))
            else:
                filename = filename[0]
        return filename, configname
        
    def _get_updated_experiment_config_file(self, filename,configname):
        '''
        Reads experiment configuration parameters from user interface and
        returns modified source code.
        '''
        #Generate source code lines from table parameter values
        new_section = []
        from_table = self.paramwidget.values.get_values().items()
        for k, v in from_table:
            if isinstance(v, list):
                new_section.append(k+' = '+v[0] + '#'+v[1])
            else:
                new_section.append(k+' = '+v)
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
            raise ExperimentConfigError('Modifiable parameters cannot be found in {0} experiment config declaration. Number of parameters in original experiment config does not match with the number of paramaters to be saved.'.format(configname))
        #Modify content by replacing lines where parameters are.
        for i in range(len(lines_to_modify)):
            content[lines_to_modify[i]-1] = 8*' '+new_section[i]+content[0][-1]#Adding 8 spaces before line (2 levels of indentation), using original file's end of line character
        content= ''.join(content)
        #Check for syntax errors, exception is raised if error found
        introspect.import_code(content,'module_under_test', add_to_sys_modules=0)
        return content

    def save_experiment_parameters(self):
        filename,configname = self._find_out_experiment_config_filename()
        if not self.poller.ask4confirmation('Do you really want to overwrite {0} file with modified parameters?'.format(filename)):
            return
        fileop.write_text_file(filename, self._get_updated_experiment_config_file(filename,configname))
        #Parse modified file to make parameter table's data consistent
        self.printc('{1} parameters saved to {0}' .format(filename, configname))

    ################# Experiment execution ####################
    def _get_experiment_run_parameters(self):
        self.optional_parameters = {
            'animal_parameters': 'self.poller.animal_file.animal_parameters',
            'experiment_log': 'self.poller.animal_file.log',
            }
        filename, configname = self._find_out_experiment_config_filename()
        self.mandatory_parameters = {
            'experiment_name': configname,
            'experiment_config_source_code' : self._get_updated_experiment_config_file(filename,configname),
            'cell_name': str(self.poller.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.text()), 
            'recording_channels' : self.poller.parent.central_widget.main_widget.experiment_options_groupbox.recording_channel.get_selected_item_names(), 
            'enable_scanner_synchronization' : self.poller.parent.central_widget.main_widget.experiment_options_groupbox.enable_scanner_synchronization.checkState() == 2, 
            'spike_recording':False,#TODO: put checkbox on main_ui
            'scanning_range' : str(self.poller.parent.central_widget.main_widget.experiment_options_groupbox.scanning_range.input.text()), 
            'pixel_size' : str(self.poller.parent.central_widget.main_widget.experiment_options_groupbox.pixel_size.text()), 
            'resolution_unit' : str(self.poller.parent.central_widget.main_widget.experiment_options_groupbox.resolution_unit.currentText()), 
            'status' : 'queued',
            'state_transition_times':[['queued',time.time()]],#Keeps track of what transitions happened and when
            'id':str(int(numpy.round(time.time(), 2)*100)), 
            'save2file' : (self.poller.parent.central_widget.save2file.input.checkState()==2),
            'averaging' : self.poller.parent.central_widget.averaging.input.text()
                           }
        #Copy values from machine parameters
        for machine_parameter_name in self.poller.parent.central_widget.parameters_groupbox.machine_parameters['scanner'].keys():
            self.mandatory_parameters[stringop.to_variable_name(machine_parameter_name)] = self.poller.parent.central_widget.parameters_groupbox.machine_parameters['scanner'][machine_parameter_name]
        
    def _parse_experiment_run_parameters(self):
        for pn in self.optional_parameters.keys():
            vn = self.optional_parameters[pn].split('.')[-1]
            ref = introspect.string2objectreference(self, '.'.join(self.optional_parameters[pn].split('.')[:-1]))
            if hasattr(ref, vn):
                self.optional_parameters[pn] = getattr(ref,vn)
            else:
                del self.optional_parameters[pn]
        #Parse parameters provided in x,y format
        for pn in ['scanning_range', 'scan_center'] :
            self.mandatory_parameters[pn] = stringop.str2params(self.mandatory_parameters[pn].split('#')[0])
            if len(self.mandatory_parameters[pn]) == 0:
                self.poller.notify_user('WARNING', '{0} shall be provided in the following format: height, width'.format(stringop.to_title(pn)))
                return False
            self.mandatory_parameters[pn] = utils.rc(tuple(self.mandatory_parameters[pn]))
        #Parse numeric parameters
        self.mandatory_parameters['averaging'] = 1 if self.mandatory_parameters['averaging'] == '' else int(self.mandatory_parameters['averaging'])
        for pn in ['pixel_size', 'stimulus_flash_trigger_duty_cycle', 'stimulus_flash_trigger_delay','maximal_x_line_linearity_error','analog_output_sampling_rate', 'analog_input_sampling_rate', 'scanner_position_to_voltage']:
            try:
                self.mandatory_parameters[pn] = float(self.mandatory_parameters[pn].split('#')[0])
            except ValueError:
                self.poller.notify_user('WARNING', '{0} shall be provided in numeric format: {1}'.format(stringop.to_title(pn),self.mandatory_parameters[pn]))
                return False
        if self.mandatory_parameters['analog_output_sampling_rate'] > self.mandatory_parameters['analog_input_sampling_rate']:
            self.poller.notify_user('WARNING', 'Analog input sampling rate cannot be less than analog output sampling rate')
            return False
        self.mandatory_parameters['stimulus_flash_trigger_delay'] *= 1e-6#us to second
        self.mandatory_parameters['stimulus_flash_trigger_duty_cycle'] *= 1e-2#percent to PU
        self.mandatory_parameters['maximal_x_line_linearity_error'] *= 1e-2#percent to PU
        self.mandatory_parameters['duration'] = experiment.get_experiment_duration(
                                                                                   self.mandatory_parameters['experiment_name'], 
                                                                                   self.config, 
                                                                                   source=self.mandatory_parameters['experiment_config_source_code'])
        #Parse boolean parameters:
        for pn in ['enable_flyback_scan', 'enable_scanner_phase_characteristics']:
            try:
                self.mandatory_parameters[pn] = bool(int(self.mandatory_parameters[pn].split('#')[0]))
            except ValueError:
                self.poller.notify_user('WARNING', '{0} shall be provided in boolean format (0 or 1): {1}'.format(stringop.to_title(pn),self.mandatory_parameters[pn]))
                return False
        #Parse list item names to pmt names, remove electrophysiology channel from list
        self.mandatory_parameters['record_electrophysiology_signal'] = len([channel_name for channel_name in self.mandatory_parameters['recording_channels'] if 'electrophysiology' not in channel_name.lower()]) == 1
        self.mandatory_parameters['recording_channels'] = \
            [stringop.string_in_list(self.config.PMTS.keys(), channel_name, return_match = True, any_match = True) for channel_name in self.mandatory_parameters['recording_channels'] if 'electrophysiology' not in channel_name.lower()]
        if len(self.mandatory_parameters['recording_channels'])==0:
            self.poller.notify_user('WARNING', 'Recording channel must be selected')
            return False
        self.mandatory_parameters['optional'] = self.optional_parameters
        if self.optional_parameters.has_key('animal_parameters'):
            self.mandatory_parameters['animal_id'] = self.optional_parameters['animal_parameters']['id']
        self.mandatory_parameters['counter'] = '{0:0=3}'.format(len(self.poller.animal_file.recordings))
        self.mandatory_parameters['elphys_sync_sample_rate'] = self.config.ELPHYS_SYNC_RECORDING['SPIKING_SAMPLE_RATE'] if self.mandatory_parameters['spike_recording'] else self.config.ELPHYS_SYNC_RECORDING['ELPHYS_SAMPLE_RATE']
        return True
            
    def _calculate_and_check_scan_parameters(self):
        '''
        Checks ca imaging related parameters, constructs the command signal and warns user if something is wrong with it
        
        This operation could be initiated by value changes in corresponding widgets. It might run for longer times and that would slow down the whole application
        '''
        #Convert parameters
        if self.mandatory_parameters['resolution_unit'] == 'um/pixel':
            self.mandatory_parameters['resolution'] = 1.0/self.mandatory_parameters['pixel_size']
        elif self.mandatory_parameters['resolution_unit'] == 'pixel/um':
            self.mandatory_parameters['resolution'] = self.mandatory_parameters['pixel_size']
        elif self.mandatory_parameters['resolution_unit'] == 'us':
            raise NotImplementedError('Select different pixel size unit')
        constraints = {}
        constraints['enable_flybackscan']=self.mandatory_parameters['enable_flyback_scan']
        constraints['enable_scanner_phase_characteristics']=self.mandatory_parameters['enable_scanner_phase_characteristics']
        constraints['scanner_position_to_voltage']=self.mandatory_parameters['scanner_position_to_voltage']
        constraints['xmirror_max_frequency']=self.config.XMIRROR_MAX_FREQUENCY
        constraints['ymirror_flyback_time']=self.config.Y_MIRROR_MIN_FLYBACK_TIME
        constraints['sample_frequency']=self.mandatory_parameters['analog_output_sampling_rate']
        constraints['max_linearity_error']=self.mandatory_parameters['maximal_x_line_linearity_error']
        constraints['phase_characteristics']=self.config.SCANNER_CHARACTERISTICS['PHASE']
        constraints['gain_characteristics']=self.config.SCANNER_CHARACTERISTICS['GAIN']
        #Generate scanner signals and data mask
        xsignal,ysignal,frame_trigger_signal, valid_data_mask,signal_attributes =\
                            scanner_control.generate_scanner_signals(self.mandatory_parameters['scanning_range'], 
                                                                                self.mandatory_parameters['resolution'], 
                                                                                self.mandatory_parameters['scan_center'], 
                                                                                constraints)
        #Generate stimulus strigger signal
        stimulus_flash_trigger_signal, signal_attributes['real_duty_cycle'] = scanner_control.generate_stimulus_flash_trigger(
                                                                                                                    self.mandatory_parameters['stimulus_flash_trigger_duty_cycle'], 
                                                                                                                    self.mandatory_parameters['stimulus_flash_trigger_delay'], 
                                                                                                                    signal_attributes, 
                                                                                                                    constraints)
        displayable_scan_parameters = ['frame_rate']
        for k,v in signal_attributes.items():
            if k =='one_period_x_scanner_signal' or k == 'one_period_valid_data_mask':
                continue#Do not print arrays on console
            elif k in displayable_scan_parameters:
                self.printc('{0}: {1:.3}'.format(stringop.to_title(k), v))
            else:
                self.poller.parent.log.info('{0}: {1}'.format(k, v))
        for pn in ['xsignal', 'ysignal', 'stimulus_flash_trigger_signal', 'frame_trigger_signal', 'valid_data_mask']:
            self.mandatory_parameters[pn] = locals()[pn]
        self.mandatory_parameters.update(constraints)
        self.mandatory_parameters.update(signal_attributes)
        return self.mandatory_parameters
        
    def check_scan_parameters(self, experiment=True):#TODO: rename this function
        '''
        if experiment is true, experiment_name and experiment_config_source_code in parameter set is retained
        '''
        self._get_experiment_run_parameters()
        if not self._parse_experiment_run_parameters():
            return
        parameters = self._calculate_and_check_scan_parameters()
        if not experiment:
            del parameters['experiment_name']
            del parameters['experiment_config_source_code']
        else:
            parameters['save2file']=True
        return parameters
        
    def add_experiment(self):
        '''
        
        '''
        if self.check_scan_parameters() is None:
            return
        self.poller.animal_file.recordings.append(self.mandatory_parameters)
        if hasattr(self.poller.animal_file, 'filename'):
            hdf5io.save_item(self.poller.animal_file.filename, 'recordings', utils.object2array(self.poller.animal_file.recordings), self.config, overwrite = True)
        self.printc('{0} added to experiment queue'.format(self.mandatory_parameters['id']))
        self.poller.update_recording_status()

    def _modify_experiment_item(self, function):
        '''
        Finds entry in recordings that is selected in table and calls function
        function: callable called if selected 
        '''
        removable_rows = [item.row() for item in self.status_widget.table.selectedItems()]
        if len(removable_rows) == 0:
            return
        for removable_row in removable_rows:
            for entry in self.poller.animal_file.recordings:
                if entry['id'] in str(self.status_widget.table.item(removable_row, 0).toolTip()) and entry['id'] in str(self.status_widget.table.item(removable_row, 1).toolTip()):
                    if function(entry) == False:
                        return
                    break
        if hasattr(self.poller.animal_file, 'filename'):
            hdf5io.save_item(self.poller.animal_file.filename, 'recordings', utils.object2array(self.poller.animal_file.recordings), self.config, overwrite = True)
        self.poller.update_recording_status()
        return entry['id']
        
    def _remove_experiment(self, entry):
        if entry['status'] == 'queued' and not self.poller.ask4confirmation('Removing issued experiment command. Are you sure?'):
            return False
        elif (entry['status'] == 'done' or entry['status'] == 'analyzed') and not self.poller.ask4confirmation('Deleting experiment recording file. Are you sure?'):
            return False
        if entry['status'] == 'done' or entry['status'] == 'analyzed':
            for fn in fileop.listdir_fullpath(fileop.get_user_experiment_data_folder(self.config)):
                if entry['id'] in fn:
                    os.remove(fn)
                    self.printc('Removing {0}'.format(fn))
        elif (entry['status'] == 'running' or entry['status'] == 'preparing'):
            self.printc('Experiment in {0} state cannot be removed'.format(entry['status']))
            return False
        self.poller.animal_file.recordings = [e for e in self.poller.animal_file.recordings if e['id'] != entry['id']]
        
    def remove_experiment(self):
        res = self._modify_experiment_item(self._remove_experiment)
        if res is not None:
            self.printc('{0} removed from experiment queue.'.format(res))
        
    def _set_experiment_state(self, entry,new_state=None):
        for i in range(len(self.poller.animal_file.recordings)):
            if self.poller.animal_file.recordings[i]['id'] == entry['id']:#id is unique identifier
                self.poller.animal_file.recordings[i]['status'] = str(self.status_widget.new_state.currentText()) if new_state is None else new_state
                self.poller.animal_file.recordings[i]['state_transition_times'].append([self.poller.animal_file.recordings[i]['status'], time.time()])
                break
        
    def set_experiment_state(self):
        self.printc('{0}\'s state updated.'.format(self._modify_experiment_item(self._set_experiment_state)))
        
    def check_recording_state(self, states):
        return len([rec for rec in self.poller.animal_file.recordings if rec['status'] in states]) > 0
        
    def prepare_next_experiment(self):
        '''
        Called by poller regularly, checks command queue and current experiment status and starts a new recording
        
        1. Chose the oldest recording which has issued state 
        '''
        #Do nothing when any recoring is in preparing/running state
        if self.check_recording_state(['preparing',  'running']):
            return
        #Take the oldest issued recording 
        for i in range(len(self.poller.animal_file.recordings)):
            if self.poller.animal_file.recordings[i]['status'] == 'queued':
                #Check if stim and ca_imaging is connected
                expected_connections = ['stim', 'ca_imaging']
                available_connections = [c for c in expected_connections if c in self.poller.connected_nodes]
                if len(available_connections)!=2:
                    if not self.experiment_not_started_message_sent:
                        self.printc('Only {0} is connected, experiment will be started when all connections are active'.format(available_connections))
                    self.experiment_not_started_message_sent = True
                    return
                self.experiment_not_started_message_sent = False
                function_call = {'function': 'live_scan_start', 'args': [self.poller.animal_file.recordings[i]]}
                #Start elphys/sync signal recording
                self.daq_process = daq_instrument.AnalogIOProcess('daq', self.daq_queues, self.poller.parent.log.get_queues()['daq'],
                                ai_channels = self.config.ELPHYS_SYNC_RECORDING['AI_PINOUT'],
                                ao_channels = self.config.ELPHYS_SYNC_RECORDING['AO_PINOUT'],
                                limits={'min_ai_voltage' : -10, 'max_ai_voltage' : 10, 'min_ao_voltage' : -10, 'max_ao_voltage' : 10,
                                'timeout' : self.config.ELPHYS_SYNC_RECORDING['TIMEOUT']}
                                )
                self.daq_process.start()
                ch1_voltage = 0
                ch2_voltage = 0
                voltage_levels = numpy.array([numpy.ones(self.poller.animal_file.recordings[i]['elphys_sync_sample_rate'])*ch1_voltage,numpy.ones(self.poller.animal_file.recordings[i]['elphys_sync_sample_rate'])*ch2_voltage])
                recording_started_result = self.daq_process.start_daq(ai_sample_rate = self.poller.animal_file.recordings[i]['elphys_sync_sample_rate'], 
                                    ao_sample_rate = self.poller.animal_file.recordings[i]['elphys_sync_sample_rate'], 
                                    ao_waveform = voltage_levels, timeout = 30)
                self.printc('Sync {0} signal recording {1}'.format('and elphys' if self.poller.animal_file.recordings[i]['record_electrophysiology_signal'] else '',recording_started_result))
                if recording_started_result != 'started':
                    return
                if self.config.PLATFORM == 'elphys_retinal_ca':
                    self.poller.send(function_call,connection='ca_imaging')
                elif self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical':
                    raise NotImplementedError('')
                self._set_experiment_state(self.poller.animal_file.recordings[i],new_state='preparing')
                self.poller.animal_file.recordings[i]['data ready messages'] = []
                self.poller.update_recording_status()
                self.printc('{0} is preparing'.format(self.poller.animal_file.recordings[i]['id']))
                self.printc('Initiating two photon recording')
                break
        
    def start_stimulation(self):
        if len([r for r in self.poller.animal_file.recordings if r['status'] != 'done'])==0:#it is a live scan or snap
            return True
        #Find out which is the active recording
        for i in range(len(self.poller.animal_file.recordings)):
            rec = self.poller.animal_file.recordings[i]
            if rec['status'] == 'preparing':
                function_call = {'function': 'start_stimulus', 'args': [self.poller.animal_file.recordings[i]]}
                self.printc('Initiating stimulus start')
                self.poller.send(function_call,connection='stim')
                self.isstimulus_started=False
                return True
                
    def stimulation_started(self):
        if len([r for r in self.poller.animal_file.recordings if r['status'] != 'done'])==0:
            return True
        self.isstimulus_started=True
        for i in range(len(self.poller.animal_file.recordings)):
            rec = self.poller.animal_file.recordings[i]
            if rec['status'] == 'preparing':
                self.current_stimulus_start_time = time.time()
                self.current_stimulus_duration = self.poller.animal_file.recordings[i]['duration']
                self.printc('Stimulus duration is {0}, expected end of stimulus is at {1}'\
                        .format(self.current_stimulus_duration, utils.timestamp2hm(self.current_stimulus_start_time+self.current_stimulus_duration)))
                self._set_experiment_state(self.poller.animal_file.recordings[i],new_state='running')
                self.poller.update_recording_status()
                return True
                
    def check_stimulus_and_imaging_start_timeout(self):
        for i in range(len(self.poller.animal_file.recordings)):
            rec = self.poller.animal_file.recordings[i]
            if rec['status'] == 'preparing' and time.time() - rec['state_transition_times'][-1][1]>self.config.STIMULATION_AND_IMAGING_START_TIMEOUT:
                self.printc('Aborting {0} experiment because stimulus or imaging did not start'.format(rec['id']))#TODO: figure out which one happened
                self.stop_image_acquisition()
                self._stop_sync_and_elphys_recording()
                self._remove_files( rec['id'])
                self.poller.animal_file.recordings = [e for e in self.poller.animal_file.recordings if rec['id'] != e['id']]
                self.poller.update_recording_status()
                break
                
    def check_data_ready_timeout(self):
        for i in range(len(self.poller.animal_file.recordings)):
            rec = self.poller.animal_file.recordings[i]
            if rec['status'] == 'running' and\
                    time.time() - rec['state_transition_times'][-1][1]-self.current_stimulus_duration>self.config.DATA_READY_TIMEOUT and\
                    len(rec['data ready messages']) < 2:
                self._stop_sync_and_elphys_recording()
                self._remove_files( rec['id'])
                self.printc('Removing {0} experiment because stimulus or imaging is not available. Received data ready messages: {1}'.format(rec['id'], rec['data ready messages']))
                self.poller.animal_file.recordings = [e for e in self.poller.animal_file.recordings if rec['id'] != e['id']]
                self.poller.update_recording_status()
                break
                
    def stop_experiment(self):
        '''
        Stops currently running experiment and already issued experiment commands will be erased
        '''
        #TODO: check if experiment is running at all
        #TODO: offer if currently running or all shall stop
        if not self.poller.ask4confirmation('Stopping currently running experiment and queued commands are deleted. Are you sure?'):
            return
        self._abort()
        
    def _abort(self, live_scan_only = False):
        '''
        Stop experiment and live scan
        '''
        self.stop_image_acquisition()
        if not live_scan_only:
            self._stop_sync_and_elphys_recording()
        for i in range(len(self.poller.animal_file.recordings)):
            #Aborting all issued/preparing/running recordings
            if self.poller.animal_file.recordings[i]['status'] == 'running' or self.poller.animal_file.recordings[i]['status'] == 'preparing' or self.poller.animal_file.recordings[i]['status'] == 'queued':
                self.poller.animal_file.recordings = [r for r in self.poller.animal_file.recordings if r['status'] == 'done']
#                self._set_experiment_state(self.poller.animal_file.recordings[i],new_state='stopped')
                self.poller.update_recording_status()
                break
        self.isstimulus_started=False
        self.poller.send({'function': 'stop_all'},'stim')
        
    def _stop_sync_and_elphys_recording(self):
        if hasattr(self,'daq_process'):
            self.printc('Stopping elphys/sync data acquistions')
            unread_data = self.daq_process.stop_daq()
            self.daq_process.terminate()
            #Wait till process terminates
            while self.daq_process.is_alive():
                time.sleep(0.2)
            self.printc('DAQ process terminated, sync and elphys data chunks are concatenated')
            if isinstance(unread_data,str):#TODO: popup window
                self.printc('ERROR: Data sync/elphys data is not available: {0}'.format(unread_data))
                return
            sync_and_elphys_data=numpy.zeros((0, unread_data[0][0].shape[1]),dtype=unread_data[0][0].dtype)#dim 1 is the number of channels
            for chunk in unread_data[0]:
                sync_and_elphys_data = numpy.concatenate((sync_and_elphys_data,chunk))
            #Convert to 16 bit, -10..10 range 16 bits
            float216bit_factor = 2**16/20.0
            sync_and_elphys_data = numpy.cast['int16'](sync_and_elphys_data*float216bit_factor)
            rec=[rec for rec in self.poller.animal_file.recordings if rec['status'] == 'running' or rec['status'] == 'preparing']
            if len(rec)==1:
                hh = hdf5io.Hdf5io(fileop.get_recording_path(rec[0], self.config, prefix = 'sync'),filelocking=False)
                hh.sync_and_elphys_data = sync_and_elphys_data
                hh.ephys_sync_conversion_factor = float216bit_factor
                setattr(hh, 'software_environment_{0}'.format(self.config.user_interface_name), experiment_data.pack_software_environment())
                setattr(hh, 'configs_{0}'.format(self.config.user_interface_name), experiment_data.pack_configs(self))
                hh.save(['sync_and_elphys_data', 'conversion_factor', 'software_environment_{0}'.format(self.config.user_interface_name), 'configs_{0}'.format(self.config.user_interface_name)])
                hh.close()
            else:
                self.printc('ERROR: number of running or preparing records is {0}'.format(len(rec)))
        
    def stop_image_acquisition(self):
        '''
        Called when stimulation is done or experiment is aborted
        Initiates the termination of two photon recording and stops sync/elphys signal recording
        '''
        self.printc('Stopping image acquistions')
        self.poller.send({'function': 'stop_all'},'ca_imaging')
        return True
        
    def finish_experiment(self, message):
        if len([r for r in self.poller.animal_file.recordings if r['status'] != 'done'])==0:#it is a live scan or snap
            return True
        for i in range(len(self.poller.animal_file.recordings)):
            rec = self.poller.animal_file.recordings[i]
            if rec['status'] == 'running':
                self.poller.emit(QtCore.SIGNAL('set_experiment_progressbar'), self.current_stimulus_duration)
                self.poller.animal_file.recordings[i]['data ready messages'].append(message)
                if len(self.poller.animal_file.recordings[i]['data ready messages']) == 2:
                    #Now sync and elphys recording can be stopped
                    self._stop_sync_and_elphys_recording()
                    self.printc('Merging files')
                    #stim and imaging data file is available too, merge them to one file
                    files2merge = [fn for fn in fileop.listdir_fullpath(fileop.get_user_experiment_data_folder(self.config)) if self.poller.animal_file.recordings[i]['id'] in fn]
                    nodes2read = self.config.DATA_FILE_NODES
                    hmerged = hdf5io.Hdf5io(fileop.get_recording_path(rec, self.config, prefix = 'data'),filelocking=False)
                    for fn in files2merge:
                        h = hdf5io.Hdf5io(fn,filelocking=False)
                        [h.load(node) for node in nodes2read]
                        [setattr(hmerged, node, getattr(h, node)) for node in nodes2read if hasattr(h, node)]
                        h.close()
                    self._set_experiment_state(self.poller.animal_file.recordings[i],new_state='done')
                    hmerged.recording_parameters = copy.deepcopy(self.poller.animal_file.recordings[i])
                    hmerged.save(nodes2read)
                    self.printc('Checking data')
                    error_msgs = experiment_data.check(hmerged, self.config)
                    if len(error_msgs)>0:
                        self.poller.notify_user('WARNING', 'Problem with datafile: \r\n{0}'.format('\r\n'.join(error_msgs)))
                    hmerged.close()
                    self.poller.emit(QtCore.SIGNAL('set_experiment_progressbar'), 0)
                    self.printc('Removing temporary files')
                    map(os.remove, files2merge)
                    self.poller.update_recording_status()
                    self.isstimulus_started=False
                    self.printc('{0} DONE' .format(self.poller.animal_file.recordings[i]['id']))
                    self.poller.display_datafile(hmerged.filename)
                return True
        
    def live_scan_start(self):
        '''
        
        '''
        if len([r for r in self.poller.animal_file.recordings if r['status'] == 'running' or r['status'] == 'preparing' or r['status'] == 'queued'])>0:
            self.printc('Some experiments are active')
            return
        function_call = {'function': 'live_scan_start', 'args': [self.check_scan_parameters(experiment=False)]}
        self.poller.send(function_call,connection='ca_imaging')
        self.poller.clear_curves()
        
    def live_scan_stop(self):
        if len([r for r in self.poller.animal_file.recordings if r['status'] == 'running' or r['status'] == 'preparing' or r['status'] == 'queued'])>0:
            self.printc('Some experiments are active')
            return
        self.poller.send({'function': 'live_scan_stop'},connection='ca_imaging')
        self._abort(live_scan_only = True)
        
    def snap_ca_image(self):
        if len([r for r in self.poller.animal_file.recordings if r['status'] == 'running' or r['status'] == 'preparing' or r['status'] == 'queued'])>0:
            self.printc('Some experiments are active')
            return
        function_call = {'function': 'snap_ca_image', 'args': [self.check_scan_parameters(experiment=False)]}
        self.poller.send(function_call,connection='ca_imaging')
        
    def _remove_files(self,id):
        map(os.remove, [fn for fn in fileop.listdir_fullpath(fileop.get_user_experiment_data_folder(self.config)) if id in fn])

class ExperimentParametersGroupBox(QtGui.QGroupBox):
    '''
    Displays experiment config values and user can edit them
    '''
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment parameters', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.button_names = ['Reload', 'Save']
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
        self.enable_scanner_synchronization = QtGui.QCheckBox(self)
        self.enable_scanner_synchronization.setText('Scanner-stimulus synchronization')
        self.enable_scanner_synchronization.setToolTip('Synchronize stimulation with two photon scanning')
        rec_channels = []
        rec_channels.extend(['Calcium fluorescence, ' + item+' PMT' for item in self.parent().config.PMTS.keys()])
        rec_channels.append('Electrophysiology signal')
        self.recording_channel = gui.LabeledListWidget(self, 'Recording channels', items = rec_channels)
        self.recording_channel.setFixedHeight(100)
        self.recording_channel.setFixedWidth(270)
        self.recording_channel.setToolTip('Selection of any channels enables calcium or electrophysiology signal recording.\nSelect none of the PMTs for disabling calcium imaging.\nMultiple channels can be also selected.' )
        self.scanning_range = gui.LabeledInput(self, 'Scan range (height, width) [um]')
        self.scanning_range.setFixedWidth(270)
        self.resolution_label = QtGui.QLabel('Pixel size', self)
        self.resolution_unit = QtGui.QComboBox(self)
        self.resolution_unit.addItems(QtCore.QStringList(['pixel/um', 'um/pixel', 'us']))
        self.pixel_size = QtGui.QLineEdit(self)
        self.pixel_size.setFixedWidth(70)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.cell_name, 0, 0, 1, 3)
        self.layout.addWidget(self.recording_channel, 1, 0, 1, 3)
        self.layout.addWidget(self.enable_scanner_synchronization, 2, 0, 1, 3)
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
        self.bullseye_type = QtGui.QComboBox(self)
        self.bullseye_type.setFixedWidth(100)
        self.bullseye_type.addItems(QtCore.QStringList(['bullseye', 'spot', 'L']))
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
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        widgets_1st_line = [self.filterwheel0, self.filterwheel1, self.grey_level, self.projector_enable]
        widgets_2nd_line = [self.bullseye_type, self.bullseye_size, self.bullseye_toggle]
        for i in range(len(widgets_1st_line)):
            self.layout.addWidget(widgets_1st_line[i], 0, i, 1, 1)
        for i in range(len(widgets_2nd_line)):
            self.layout.addWidget(widgets_2nd_line[i], 1, i, 1, 1)
        self.layout.addWidget(self.stimulus_centering, 0, max(len(widgets_1st_line), len(widgets_2nd_line)), 2, 2)
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
            
class BarCurve(Qwt.QwtPlotCurve):
    
    def drawFromTo(self, painter, xMap, yMap, start, stop):
        """Draws rectangles with the corners taken from the x- and y-arrays.
        """
        barcolor = Qt.QColor(50,50,50,100)
        painter.setPen(Qt.QPen(barcolor))
        painter.setBrush(barcolor)
        if stop == -1:
            stop = self.dataSize()
        # force 'start' and 'stop' to be even and positive
        if start & 1:
            start -= 1
        if stop & 1:
            stop -= 1
        start = max(start, 0)
        stop = max(stop, 0)
        for i in range(start, stop, 2):
            px1 = xMap.transform(self.x(i))
            py1 = yMap.transform(self.y(i))
            px2 = xMap.transform(self.x(i+1))
            py2 = yMap.transform(self.y(i+1))
            painter.drawRect(px1, py1, (px2 - px1), (py2 - py1))

class Plot(Qwt.QwtPlot):
    def __init__(self, parent):
        Qwt.QwtPlot.__init__(self)
        self.setCanvasBackground(QtCore.Qt.white)
        self.setFixedWidth(700)
        self.setFixedHeight(220)
        self.grid = Qwt.QwtPlotGrid()
        self.grid.enableXMin(True)
        self.grid.setMajPen(QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.DotLine))
        self.grid.setMinPen(QtGui.QPen(QtCore.Qt.gray, 0, QtCore.Qt.DotLine))
        self.grid.attach(self)
#        legend = Qwt.QwtLegend()
#        self.insertLegend(legend, Qwt.QwtPlot.BottomLegend)
        self.setAxisTitle(Qwt.QwtPlot.xBottom, 'time [s]')
        self.colors = [QtCore.Qt.red, QtCore.Qt.green, QtCore.Qt.blue, QtCore.Qt.black]
        ncurves = 3
        self.curves = []
        for i in range(ncurves):
            if i != 0:
                c = Qwt.QwtPlotCurve(str(i))
            else:
                c = BarCurve(str(i))
            self.curves.append(c)
            self.curves[-1].setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
            self.curves[-1].setPen(QtGui.QPen(self.colors[i]))
            self.curves[-1].setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Cross,
                                      Qt.QBrush(),
                                      Qt.QPen(self.colors[i]),
                                      Qt.QSize(8, 8)))
            self.curves[-1].attach(self)
        
#        duration=5
##        self.set_stimulus_duration(duration)
#        t=numpy.arange(0,duration, 1./100)
#        data = t**2
#        self.update_curve(t, data)
#        self.update_curve(t, data*2)
    
        
    def set_stimulus_duration(self,duration):
        self.setAxisScale(Qwt.QwtPlot.xBottom, 0, duration)
        
    def update(self, curves):
        if curves is None:
             for ci in range(3):
                 self.curves[ci].setData([],[])
        else:
            for ci in range(len(curves)):
                if curves[ci] == []:
                    continue
                self.curves[ci].setData(curves[ci][0], curves[ci][1])
#        self.setAxisScale(Qwt.QwtPlot.yLeft, min(data), max(data))
        self.replot()
        
#        self.setAxisScaleDraw(
#            Qwt.QwtPlot.xBottom, TimeScaleDraw(Qt.QDate(int(self.months[0].split('-')[0]), int(self.months[0].split('-')[1]), 1)))
#        self.setAxisScale(Qwt.QwtPlot.xBottom, 0, len(self.months))        

class ImageWidget(QtGui.QWidget):
    '''
    Depends on platform
    
    Requirements:
    show image
    roi selection
    zoom
    pan
    
    '''
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.config = parent.config
        self.create_widgets()
        self.create_layout()
        
        
    def create_widgets(self):
        self.imagefilter = gui.LabeledComboBox(self, 'Filter', items = ['median_filter', 'fft bandfilter'])
        display_channels_list= ['ALL']
        display_channels_list.extend(self.config.PMTS.keys())
        self.imagechannel = gui.LabeledComboBox(self, 'Display channel', items = display_channels_list)
        
        if not False:
            self.v=QtGui.QGraphicsView(self)
            scene = QtGui.QGraphicsScene(self.v)
            self.v.setScene(scene)
            
            img = numpy.random.random((200,100, 3))
            scene.addPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(img, img.shape[1], img.shape[0], 3*img.shape[1], QtGui.QImage.Format_RGB888)))
            self.v.scale(1.5, 1.5)
        
#        scene.addLine(0, 0, 1000, 1000)




    
        
        self.max = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.min = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        
        
#        self.v = pg.GraphicsView(background = pg.mkColor(150,150,150))
#        self.vb = pg.ViewBox(enableMouse=not False)
##        s = self.vb.getState()
##        s['autoRange'] = [False, False]
##        self.vb.setState(s)
#        self.vb.setAspectLocked()
#        self.v.setCentralItem(self.vb)
#        self.img = pg.ImageItem()
#        self.img.scale(0.1, 0.1)
#        self.vb.addItem(self.img)
#        g=pg.GridItem()
#        self.vb.addItem(g)
#        self.lut = pg.HistogramLUTItem(self.img)
#        self.vb.addItem(self.lut)
        
        
        
#        self.vb.menu.ctrl[0].mouseCheck.setChecked(0)
#        self.vb.menu.ctrl[1].mouseCheck.setChecked(0)
#        scale = pg.ScaleBar(size=100, width=10,  brush=pg.mkBrush(color=[255,255,255]))
#        scale.setParentItem(self.vb)
#        scale.anchor((1, 1), (1, 1), offset=(-40, -40))
#        self.img.setImage(numpy.random.random((300,300,3)))
        
#        self.img= CImage(numpy.zeros((self.meanimg_size,self.meanimg_size,3),dtype = numpy.uint8), self)
#        self.img_view=QtGui.QGraphicsView(self)
#        self.img_scene=QtGui.QGraphicsScene(self.img_view)
#        self.img_view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)
#        self.img_scene.addWidget(self.img)
#        self.img_view.setScene(self.img_scene)
#        return
#        self.image_display = []
#        for i in range(4):
#            self.image_display.append(QtGui.QLabel())
#        self.blank_image = 128*numpy.ones((100, 100), dtype = numpy.uint8)
#        for image in self.image_display:
#            image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
            
    
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        
        self.layout.addWidget(self.imagechannel, 0, 1)
        self.layout.addWidget(self.imagefilter, 0, 2)
        if not False:
            self.layout.addWidget(self.v, 1, 0, 1, 3)
        self.layout.addWidget(self.max, 3, 0, 1, 1)
        self.layout.addWidget(self.min, 3, 1, 1, 1)
        
        self.setLayout(self.layout)
        
class Image(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent, roi_diameter = 20):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.roi_default_diameter = roi_diameter
        self.plot=self.addPlot()
        self.img = pyqtgraph.ImageItem(border='w')
        self.plot.addItem(self.img)
        self.plot.showGrid(True,True,1.0)
        self.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.rois = []
        
    def set_image(self, image):
        im=0.8*numpy.ones((image.shape[0],image.shape[1], 4))*image.max()
        im[:,:,:3]=image
        self.img.setImage(im)
        
    def set_scale(self,scale):
        self.img.setScale(scale)

    def mouse_clicked(self,e):
        p=self.img.mapFromScene(e.scenePos())
        if e.double():
            if int(e.buttons()) == 1:
                self.add_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            elif int(e.buttons()) == 2:
                self.remove_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            self.update_roi_info()
        
    def add_roi(self,x,y, size=None):
        if size is None:
            size = self.roi_default_diameter
        roi = pyqtgraph.CircleROI([x-0.5*size, y-0.5*size], [size, size])
        roi.setPen((255,0,0,255), width=2)
        roi.sigRegionChanged.connect(self.update_roi_info)
        self.rois.append(roi)
        self.plot.addItem(self.rois[-1])
        
    def remove_roi(self,x,y):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        if len(distances)==0:return
        removable_roi = self.rois[numpy.array(distances).argmin()]
        self.plot.removeItem(removable_roi)
        self.rois.remove(removable_roi)
        
    def update_roi_info(self):
        self.roi_info = [[i, self.rois[i].x(), self.rois[i].y(), self.rois[i].size().x()] for i in range(len(self.rois))]
        self.emit(QtCore.SIGNAL('roi_update'))
        
    def load_rois(self,roi_info):
        scale=1
        self.roi_info = roi_info
        for r in self.rois:
            self.plot.removeItem(r)
        self.rois=[]
        for r in roi_info:
            self.add_roi(r[1]+0.5*r[3],r[2]+0.5*r[3],r[3])
        self.emit(QtCore.SIGNAL('roi_update'))
        
class ImageMainUI(Image):
    def __init__(self, parent, roi_diameter=10):
        Image.__init__(self, parent, roi_diameter)
        self.connect(self, QtCore.SIGNAL('roi_update'), parent.analysis.roi_update)
        
class ROITools(QtGui.QGroupBox):
    def __init__(self,parent):
        QtGui.QGroupBox.__init__(self,'ROI', parent)
        self.save = QtGui.QPushButton('Save',  self)
        self.suggest = QtGui.QPushButton('Suggest',  self)
        self.show = gui.LabeledCheckBox(self, 'Show/hide suggested')
        for w in [self.save,self.suggest]:
            w.setFixedWidth(70)
        self.select = gui.LabeledComboBox(self, 'Select')
        self.select.input.setFixedWidth(120)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.save, 0, 0)
        self.layout.addWidget(self.suggest, 0, 1)
        self.layout.addWidget(self.show, 0, 2)
        self.layout.addWidget(self.select, 0, 3)
        self.setLayout(self.layout)
        
class TraceAnalysis(QtGui.QGroupBox):
    def __init__(self,parent):
        QtGui.QGroupBox.__init__(self,'Trace', parent)
        self.normalization = gui.LabeledComboBox(self, 'Normalization',items = ['no', 'dF/F', 'std'])
        self.normalization.input.setCurrentIndex(2)
        self.baseline_lenght = gui.LabeledInput(self, 'Baseline lenght [s]')
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.baseline_lenght, 0, 0)
        self.layout.addWidget(self.normalization, 0, 1)
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
        self.gw.setFixedHeight(400)
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
        
        self.connect(self.roi.select.input, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.roi.suggest, QtCore.SIGNAL('clicked()'), self.suggest)
        self.connect(self.roi.save, QtCore.SIGNAL('clicked()'), self.save)
        self.connect(self.export2mat, QtCore.SIGNAL('clicked()'), self.export)
        self.connect(self.roi.show.input, QtCore.SIGNAL('stateChanged(int)'), self.update_image)
        self.connect(self.ta.normalization.input, QtCore.SIGNAL('currentIndexChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self.ta.baseline_lenght.input, QtCore.SIGNAL('textChanged(const QString &)'), self.selected_roi_changed)
        self.connect(self, QtCore.SIGNAL('update_image'), self.parent.parent.update_image)
        self.connect(self, QtCore.SIGNAL('printc'), self.parent.parent.printc)
        self.connect(self, QtCore.SIGNAL('notify_user'), self.parent.parent.notify_user)
        
    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)
        
    def roi_update(self):
        self.roi.select.update_items(['{0} {1:1.0f},{2:1.0f}@{3:1.0f}'.format(r[0],r[1],r[2],r[3]) for r in self.parent.image.roi_info])
        self.roi.select.input.setCurrentIndex(len(self.parent.image.roi_info)-1)
        
    def selected_roi_changed(self):
        self.poller = self.parent.parent.poller
        if not hasattr(self.poller, 'rawdata'):
            return
        index=int(self.roi.select.input.currentIndex())
        for i in range(len(self.parent.image.rois)):
            if i == index:
                self.parent.image.rois[i].setPen((255,102,0))
            else:
                self.parent.image.rois[i].setPen((255,0,0))
        #Update plot
        roi_info=self.parent.image.roi_info[index]
        self.ca = experiment_data.extract_roi_curve(self.poller.rawdata, roi_info[1],roi_info[2],roi_info[3],'circle', self.poller.scale)[:self.poller.ti.shape[0]]
        #normalize
        try:
            baseline_length=float(str(self.ta.baseline_lenght.input.text()))
        except ValueError:
            self.emit(QtCore.SIGNAL('notify_user'), 'WARNING', 'Please provide baseline length')
            return
        normalization_mode = str(self.ta.normalization.input.currentText())
        if normalization_mode == 'no':
            self.normalized = self.ca
        elif normalization_mode == 'dF/F':
            baseline = self.ca[numpy.where(numpy.logical_and(self.poller.ti<self.poller.ts[0],self.poller.ti>self.poller.ts[0]-baseline_length))].mean()
            self.normalized = self.ca / baseline
        elif normalization_mode == 'std':
            baseline = self.ca[numpy.where(numpy.logical_and(self.poller.ti<self.poller.ts[0],self.poller.ti>self.poller.ts[0]-baseline_length))]
            self.normalized = (self.ca-baseline.mean())/baseline.std()
        self.curve.setData(self.poller.ti, self.normalized)
        self.plot.setYRange(min(self.normalized), max(self.normalized))
        if hasattr(self,'stimulus_time'):
            self.plot.removeItem(self.stimulus_time)
        self.stimulus_time = pyqtgraph.LinearRegionItem(self.poller.ts, movable=False)
        self.plot.addItem(self.stimulus_time)
        
    def suggest(self):
        self.poller = self.parent.parent.poller
        self.suggested_rois = experiment_data.find_rois(numpy.cast['uint16'](signal.scale(self.poller.meanimage, 0,2**16-1)))
        self.update_image()
        
    def update_image(self):
        show = self.roi.show.input.checkState()==2
        mi=numpy.zeros((self.poller.meanimage.shape[0],self.poller.meanimage.shape[1],3))
        mi[:,:,1]=self.poller.meanimage
        if show:
            mi[:,:,2]=numpy.where(self.suggested_rois>0,1,0)*self.poller.meanimage.max()*0.2
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
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':self, 'utils':utils, 'fileop': fileop, 'signal':signal, numpy: 'numpy'}, text = 'Poller: self.p, Also available: numpy.utils, fileop, signal')
        
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
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.experiment_control_groupbox.setMaximumWidth(350)
        self.experiment_control_groupbox.setFixedHeight(150)
        if self.config.PLATFORM == 'elphys_retinal_ca':
            self.experiment_options_groupbox = RetinalExperimentOptionsGroupBox(self)
            self.toolbox = RetinalToolbox(self)
        elif self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical':
            self.experiment_options_groupbox = CorticalExperimentOptionsGroupBox(self)
        self.experiment_options_groupbox.setMaximumWidth(350)
        self.experiment_options_groupbox.setFixedHeight(380)
        self.recording_status = RecordingStatusGroupbox(self)
        self.recording_status.setMaximumWidth(400)
        self.recording_status.setFixedHeight(300)
        self.experiment_parameters = ExperimentParametersGroupBox(self)
        self.experiment_parameters.setMaximumWidth(400)
        self.experiment_parameters.setFixedHeight(230)
        self.experiment_parameters.values.setColumnWidth(0, 200)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 1, 1)
        self.layout.addWidget(self.experiment_options_groupbox, 1, 0, 2, 1)
        self.layout.addWidget(self.recording_status, 0, 1, 2, 1)
        self.layout.addWidget(self.experiment_parameters, 2, 1, 1, 1)
        self.layout.addWidget(self.toolbox, 3, 0, 1, 2)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
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
    
