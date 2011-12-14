#TODO: Load animal parameters, select ref image should come from that
#TODO: rename to visexp_gui.py
#TODO: log
#TODO:Execute experiment
#TODO: timestamp to gui.hdf5 and string_timestamp node
#TODO: string parsing: re
#TODO: string to binary array: numpy.loadtext, loadfile or struct.struct
ENABLE_NETWORK = True
SEARCH_SUBFOLDERS = True
import sys
import time
import socket
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.utils as utils
import visexpman.engine.visual_stimulation.configuration as configuration
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import Queue
import os.path
import visexpA.engine.datahandlers.hdf5io as hdf5io
try:
    import visexpA.engine.dataprocessors.itk_image_registration as itk_image_registration
    import visexpA.engine.dataprocessors.itk_versor_rigid_registration as itk_versor_rigid_registration
except:
    print 'itk not installed'
import threading
import visexpA.engine.datahandlers.matlabfile as matlabfile
import tempfile
import Image
import numpy
import visexpA.engine.dataprocessors.signal as signal


class AnimalParametersGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Animal parameters', parent)                    
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        date_format = QtCore.QString('dd-mm-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])                
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)        
        self.mouse_birth_date = QtGui.QDateEdit(self)
        self.mouse_birth_date.setDisplayFormat(date_format)
        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        self.ear_punch_l = QtGui.QComboBox(self)        
        self.ear_punch_l.addItems(ear_punch_items)
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        self.ear_punch_r = QtGui.QComboBox(self)                
        self.ear_punch_r.addItems(ear_punch_items)
        self.anesthesia_protocol_label = QtGui.QLabel('Anesthesia protocol',  self)
        self.anesthesia_protocol = QtGui.QComboBox(self)        
        self.anesthesia_protocol.addItems(QtCore.QStringList(['isoflCP 1.0', 'isoflCP 0.5', 'isoflCP 1.5']))
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        self.mouse_strain = QtGui.QComboBox(self)
        self.mouse_strain.addItems(QtCore.QStringList(['bl6', 'chat', 'chatdtr']))
        self.comments = QtGui.QComboBox(self)
        self.comments.setEditable(True)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.mouse_birth_date_label, 0, 0)
        self.layout.addWidget(self.mouse_birth_date, 1, 0)
        self.layout.addWidget(self.gcamp_injection_date_label, 2, 0)
        self.layout.addWidget(self.gcamp_injection_date, 3, 0)
        self.layout.addWidget(self.ear_punch_l_label, 0, 1)
        self.layout.addWidget(self.ear_punch_l, 1, 1)
        self.layout.addWidget(self.ear_punch_r_label, 2, 1)
        self.layout.addWidget(self.ear_punch_r, 3, 1)
        self.layout.addWidget(self.anesthesia_protocol_label, 0, 2)
        self.layout.addWidget(self.anesthesia_protocol, 1, 2)
        self.layout.addWidget(self.mouse_strain_label, 2, 2)
        self.layout.addWidget(self.mouse_strain, 3, 2)
        self.layout.addWidget(self.comments, 4, 0, 1, 3)
        self.layout.setColumnStretch(7, 0)
        self.setLayout(self.layout)
        
class ExperimentFileGroupBox(QtGui.QGroupBox):
    def __init__(self, parent, config):
        self.config = config
        QtGui.QGroupBox.__init__(self, 'Experiment file', parent)                    
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):        
        self.new_experiment_file_button = QtGui.QPushButton('Create new experiment file',  self)
        self.redefine_experiment_file_button = QtGui.QPushButton('Recreate experiment file',  self)
        self.select_experiment_file_label = QtGui.QLabel('Experiment file',  self)
        self.select_experiment_file_experiment = QtGui.QComboBox(self)
        self.select_experiment_file_experiment.addItems(utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter = 'gui')[-1])
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.new_experiment_file_button, 0, 0, 1, 2)
        self.layout.addWidget(self.redefine_experiment_file_button, 0, 2, 1, 2)
        self.layout.addWidget(self.select_experiment_file_label, 1, 0)
        self.layout.addWidget(self.select_experiment_file_experiment, 1, 1, 1, 3)        
        self.setLayout(self.layout)
        
class MasterPositionGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):        
        QtGui.QGroupBox.__init__(self, 'Master position', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):        
        self.z_stack_button = QtGui.QPushButton('Create Z stack',  self)
        self.calculate_brain_surface_angle_button = QtGui.QPushButton('Calculate angle of brain surface',  self)
        self.brain_surface_angle_display = QtGui.QComboBox(self)
        self.brain_surface_angle_display.setEditable(True)
        self.rotate_mouse_button = QtGui.QPushButton('Rotate mouse',  self)
        self.save_master_position_button = QtGui.QPushButton('Save master position',  self)        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.z_stack_button, 0, 1)
        self.layout.addWidget(self.calculate_brain_surface_angle_button, 0, 2)
        self.layout.addWidget(self.brain_surface_angle_display, 0, 3, 1, 1)
        self.layout.addWidget(self.rotate_mouse_button, 0, 4)
        self.layout.addWidget(self.save_master_position_button, 0, 5)
        self.setLayout(self.layout)

class NewScanRegion(QtGui.QGroupBox):
    def __init__(self, parent, experiment_names):
        QtGui.QGroupBox.__init__(self, 'Add new scan region', parent)
        self.experiment_names = QtCore.QStringList(experiment_names)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.name_input = QtGui.QComboBox(self) #This combo box is to be updated with the added items
        self.name_input.setEditable(True)
        self.add_button = QtGui.QPushButton('Add',  self)
        self.z_stack_button = QtGui.QPushButton('Create Z stack',  self)
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(self.experiment_names)
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop experiment',  self)
        self.save_experiment_results_button = QtGui.QPushButton('Save experiment results',  self)
        self.save_region_info_button = QtGui.QPushButton('Save region info',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.name_input, 0, 0)
        self.layout.addWidget(self.add_button, 0, 1)
        self.layout.addWidget(self.z_stack_button, 0, 2)
        self.layout.addWidget(self.experiment_name, 1, 0)
        self.layout.addWidget(self.start_experiment_button, 1, 1)
        self.layout.addWidget(self.stop_experiment_button, 1, 2)
        self.layout.addWidget(self.save_experiment_results_button, 1, 3)
        self.layout.addWidget(self.save_region_info_button, 2, 0)
        self.setLayout(self.layout)

class NewMouseWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        
    def create_widgets(self):
        self.animal_parameters_groupbox = AnimalParametersGroupBox(self)
        self.experiment_file_groupbox = ExperimentFileGroupBox(self, self.config)
        self.master_position_groupbox = MasterPositionGroupBox(self)
        self.new_scan_region_groupbox = NewScanRegion(self, ['moving_dot', 'grating'])        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.animal_parameters_groupbox, 0, 0, 1, 2)
        self.layout.addWidget(self.experiment_file_groupbox, 0, 2, 1, 2)
        self.layout.addWidget(self.master_position_groupbox, 2, 0, 1, 3)
        self.layout.addWidget(self.new_scan_region_groupbox, 3, 0, 1, 3)        
#        self.layout.setRowStretch(3, 300)
        self.setLayout(self.layout)
        
class VisionExperimentGui(QtGui.QWidget):
    def __init__(self, config, command_relay_server = None):
        self.config = config
        self.command_relay_server = command_relay_server
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')        
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])        
        self.create_gui()
        self.show()
        
    def create_gui(self):
        self.new_mouse_widget = NewMouseWidget(self, self.config)
        self.realignment_tab = QtGui.QTabWidget(self)
        self.realignment_tab.addTab(self.new_mouse_widget, 'New mouse')        

class Gui(QtGui.QWidget):
    def __init__(self, config, command_relay_server):
        self.config = config
        self.command_relay_server = command_relay_server
        self.init_network()
        self.init_files()
        self.console_text = ''
        self.mes_timeout = 3.0
        self.z_stack = {}
        #=== Init GUI ===
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')        
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_user_interface()
        self.show()
        self.printc('init done')
        
    def init_network(self):
        self.mes_command_queue = Queue.Queue()
        self.mes_response_queue = Queue.Queue()
        if ENABLE_NETWORK:
            self.mes_connection = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.mes_response_queue, self.mes_command_queue)
        self.mes_interface = mes_interface.MesInterface(self.config, self.mes_connection)
        
        self.visexpman_out_queue = Queue.Queue()
        self.visexpman_in_queue = Queue.Queue()
        if ENABLE_NETWORK:
            #TODO client shall respond to echo messages in the background
            self.stim_connection = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.visexpman_in_queue, self.visexpman_out_queue)
            
    def init_files(self):
        
        #create hdf5io
        #TODO: File name generation shall depend on config class
        pass
        
#============================== Create GUI items ==============================#
    def create_user_interface(self):        
        self.layout = QtGui.QVBoxLayout()
        self.animal_parameters_gui()
        self.mes_control_gui()
        self.experiment_control_gui()
        self.realignment_gui()
        self.visexpa_control_gui()
        self.text_io_gui()
#        self.layout.addStretch(10)

        self.setLayout(self.layout)
        
#============================== Animal parameters ==============================#
        
    def animal_parameters_gui(self):
        self.animal_parameters_box1 = QtGui.QGroupBox ('Animal parameters', self)
        self.layout.addWidget(self.animal_parameters_box1)
        self.animal_parameters_box2 = QtGui.QGroupBox ('', self)
        self.layout.addWidget(self.animal_parameters_box2)
        layout1 = QtGui.QHBoxLayout()        
        layout2 = QtGui.QHBoxLayout()
        date_format = QtCore.QString('dd-mm-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])

        self.save_animal_parameters_button = QtGui.QPushButton('Save animal parameters',  self)
        layout2.addWidget(self.save_animal_parameters_button)        
        self.connect(self.save_animal_parameters_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        
        self.select_reference_experiment_label = QtGui.QLabel('Select reference experiment',  self)
        layout2.addWidget(self.select_reference_experiment_label)
        self.select_reference_experiment = QtGui.QComboBox(self)
        layout2.addWidget(self.select_reference_experiment)      
        self.select_reference_experiment.addItems(utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter = 'gui')[-1])
        self.connect(self.select_reference_experiment, QtCore.SIGNAL('activated(int)'), self.update_experiment_file_list)
        
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)
        layout1.addWidget(self.mouse_birth_date_label)
        self.mouse_birth_date = QtGui.QDateEdit(self)
        layout1.addWidget(self.mouse_birth_date)
        self.mouse_birth_date.setDisplayFormat(date_format)

        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        layout1.addWidget(self.gcamp_injection_date_label)
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        layout1.addWidget(self.gcamp_injection_date)     
        
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        layout1.addWidget(self.ear_punch_l_label)     
        self.ear_punch_l = QtGui.QComboBox(self)        
        self.ear_punch_l.addItems(ear_punch_items)
        layout1.addWidget(self.ear_punch_l)             
        
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        layout1.addWidget(self.ear_punch_r_label)     
        self.ear_punch_r = QtGui.QComboBox(self)                
        self.ear_punch_r.addItems(ear_punch_items)
        layout1.addWidget(self.ear_punch_r)     
        
        self.anesthesia_protocol_label = QtGui.QLabel('Anesthesia protocol',  self)
        layout1.addWidget(self.anesthesia_protocol_label)
        self.anesthesia_protocol = QtGui.QComboBox(self)        
        self.anesthesia_protocol.addItems(QtCore.QStringList(['isoflCP 1.0', 'isoflCP 0.5', 'isoflCP 1.5']))
        layout1.addWidget(self.anesthesia_protocol)
                
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        layout1.addWidget(self.mouse_strain_label)
        self.mouse_strain = QtGui.QComboBox(self)      
        layout1.addWidget(self.mouse_strain)
        self.mouse_strain.addItems(QtCore.QStringList(['bl6', 'chat', 'chatdtr']))
        
        layout2.addStretch(int(0.25 * self.config.GUI_SIZE['col']))                
        self.animal_parameters_box1.setLayout(layout1)
        self.animal_parameters_box2.setLayout(layout2)
    
    def save_animal_parameters(self):
        self.hdf5_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'gui_MovingDot_{0}.hdf5'.format(int(time.time())))
        self.hdf5_handler = hdf5io.Hdf5io(self.hdf5_path , config = self.config, caller = self)
        
        mouse_birth_date = self.mouse_birth_date.date()
        mouse_birth_date = '{0}{1}20{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = self.gcamp_injection_date.date()
        gcamp_injection_date = '{0}{1}20{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())        
        
        #undefined variables
        stagex = 'tbd'
        stagey = 'tbd'
        stagez = 'tbd'
        i = 'tbd'
        data_type = 'tbd'
        experiment_class_name = 'MovingDot'
        experiment_config_name = 'tbd'
        #[mouse strain](b[birth date] i[injection date] [stagex] [stagey] [zpos])-r[i]-[data type]-[stim class name]-[stimcfgname]-[anesthesia]-[earpunch]
        animal_parameters_text = '{0}(b{1}i{2}{3}{4}{5})-r{6}-{7}-{8}-{9}-{10}-{11}{12}' .format(
                                                                                   self.mouse_strain.currentText(),  
                                                                                   mouse_birth_date, 
                                                                                   gcamp_injection_date, 
                                                                                   stagex, stagey, stagez, 
                                                                                   i, data_type, 
                                                                                   experiment_class_name, experiment_config_name, 
                                                                                   self.anesthesia_protocol.currentText(), 
                                                                                   self.ear_punch_l.currentText(), self.ear_punch_r.currentText(), 
                                                                                   )
        animal_parameters = {'mouse_strain' : str(self.mouse_strain.currentText()),
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'stagex' : stagex,
            'stagey' : stagey,
            'stagez' : stagez,
            'i' : i,
            'data_type' : data_type,
            'experiment_class_name' : experiment_class_name,
            'experiment_config_name' : experiment_config_name,
            'anesthesia_protocol' : str(self.anesthesia_protocol.currentText()),
            'ear_punch_l' : str(self.ear_punch_l.currentText()), 
            'ear_punch_r' : str(self.ear_punch_r.currentText()),
        }
        self.hdf5_handler.animal_parameters = animal_parameters
        self.hdf5_handler.save('animal_parameters')
        hdf5_id = 'gui_' + str(int(time.time()))
        setattr(self.hdf5_handler, hdf5_id, 0)
        self.hdf5_handler.save(hdf5_id)
        self.printc('Animal parameters saved')    
    
    def update_experiment_file_list(self):
        self.update_combo_box_file_list(self.select_reference_experiment, 'gui')
        
    def update_mes_command_parameter_file_names(self):
        if self.reference_settings_checkbox.checkState() == 0 or not hasattr(self, 'parameter_files'): 
            #Issue: sometimes (in virtual box) files created by other computers cannot be seen by the software (on M drive)
            self.parameter_files = {}
            self.parameter_files['acquire_camera_image'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'acquire_camera_image_parameters.mat'), insert_timestamp = True)
            self.parameter_files['acquire_z_stack'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'acquire_z_stack_parameters.mat'), insert_timestamp = True)
            self.parameter_files['line_scan'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'line_scan_parameters.mat'), insert_timestamp = True)
            self.parameter_files['single_two_photon'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'single_two_photon_parameters.mat'), insert_timestamp = True)
            self.parameter_files['rc_scan'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'rc_scan_parameters.mat'), insert_timestamp = True)
            self.parameter_files['rc_scan_points'] = utils.generate_filename(os.path.join(self.config.MES_DATA_PATH, 'rc_scan_points.mat'), insert_timestamp = True)
        else:            
            pass
            #TODO: assign reference filenames

    
#============================== MES ==============================#
    def mes_control_gui(self):        
        self.mes_box1 = QtGui.QGroupBox ('MES', self)
        self.layout.addWidget(self.mes_box1)
        layout1 = QtGui.QHBoxLayout()       
       
        self.acquire_z_stack_button = QtGui.QPushButton('Acquire z stack',  self)
        layout1.addWidget(self.acquire_z_stack_button)
        self.connect(self.acquire_z_stack_button, QtCore.SIGNAL('clicked()'),  self.acquire_z_stack)
        
        self.line_scan_button = QtGui.QPushButton('Line scan',  self) 
        layout1.addWidget(self.line_scan_button)
        self.connect(self.line_scan_button, QtCore.SIGNAL('clicked()'),  self.line_scan)
        
        self.rc_scan_button = QtGui.QPushButton('RC scan',  self)
        layout1.addWidget(self.rc_scan_button)
        self.connect(self.rc_scan_button, QtCore.SIGNAL('clicked()'),  self.rc_scan)
        
        self.rc_set_points_button = QtGui.QPushButton('Set trajectory',  self)
        layout1.addWidget(self.rc_set_points_button)
        self.connect(self.rc_set_points_button, QtCore.SIGNAL('clicked()'),  self.rc_set_trajectory)
        
        self.echo_button = QtGui.QPushButton('Echo MES', self)
        layout1.addWidget(self.echo_button)
        self.connect(self.echo_button, QtCore.SIGNAL('clicked()'), self.echo)

        self.reference_settings_label = QtGui.QLabel('Use reference settings', self)
        layout1.addWidget(self.reference_settings_label)
        self.reference_settings_checkbox = QtGui.QCheckBox(self)
        layout1.addWidget(self.reference_settings_checkbox)
        self.connect(self.reference_settings_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.update_mes_command_parameter_file_names)

        self.select_z_stack_mat = QtGui.QComboBox(self)
        layout1.addWidget(self.select_z_stack_mat)
        self.select_z_stack_mat.addItems(QtCore.QStringList(utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter ='z_stack')[-1]) )
        self.connect(self.select_z_stack_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list)

        layout1.addStretch(int(0.2 * self.config.GUI_SIZE['col']))
        self.mes_box1.setLayout(layout1)
        
    def update_z_stack_list(self, index):
        self.update_combo_box_file_list(self.select_acquired_mat, 'z_stack')
        self.update_combo_box_file_list(self.select_reference_mat, 'z_stack')   
        self.update_combo_box_file_list(self.select_z_stack_mat, 'z_stack')
        
    def acquire_z_stack(self):
        self.z_stack, results = self.mes_interface.acquire_z_stack(self.mes_timeout)
        self.printc((results, self.z_stack))
        
    def rc_scan(self):
        self.z_stack = self.mes_interface.mes_file_handler.z_stack_from_mes_file(str(self.select_z_stack_mat.currentText()))
        self.trajectory = self.generate_trajectory(self.z_stack)
        self.scanned_trajectory, result = self.mes_interface.rc_scan(self.trajectory, timeout = self.mes_timeout)
        self.printc((result, self.scanned_trajectory))
        
    def rc_set_trajectory(self):
        self.z_stack = self.mes_interface.mes_file_handler.z_stack_from_mes_file(str(self.select_z_stack_mat.currentText()))
        points = self.generate_trajectory(self.z_stack)
        self.printc(self.mes_interface.set_trajectory(points, timeout = self.mes_timeout))
        
    def line_scan(self):
        result, parameter_file = self.mes_interface.prepare_line_scan(10.0)
        self.printc((result, parameter_file))
        result = self.mes_interface.start_line_scan(parameter_file = parameter_file, timeout = 10.0)
        self.printc(result)
        if result[0]:
            result = self.mes_interface.wait_for_line_scan_complete(15.0)
            self.printc(result)
            if result:
                result = self.mes_interface.wait_for_line_scan_save_complete(15.0)
                self.printc(result)
            else:
                self.printc('scan completition failed')
        else:
            self.printc('line scan not started')
    
    def echo(self):
        self.mes_command_queue.put('SOCechoEOCguiEOP')
        self.visexpman_out_queue.put('SOCechoEOCguiEOP')
        
#============================== Visexpman ==============================#
        
    def experiment_control_gui(self):       
        self.experiment_control_box = QtGui.QGroupBox ('Experiment control', self)
        self.layout.addWidget(self.experiment_control_box)
        layout = QtGui.QHBoxLayout()
    
        self.select_experiment = QtGui.QComboBox(self)      
        layout.addWidget(self.select_experiment)
        self.select_experiment.addItems(QtCore.QStringList(['moving_dot', 'grating']))
        
        self.execute_experiment_button = QtGui.QPushButton('Execute experiment',  self)
        layout.addWidget(self.execute_experiment_button)
        self.connect(self.execute_experiment_button, QtCore.SIGNAL('clicked()'),  self.execute_experiment)        
        layout.addStretch(int(0.6 * self.config.GUI_SIZE['col']))
        
        self.experiment_control_box.setLayout(layout)
        
    
    def execute_experiment(self):
        command = 'SOCexecute_experimentEOC{0}EOP'.format(self.experiment_config_input.toPlainText())
        self.visexpman_out_queue.put(command)
        self.printc (command)
        
#============================== Analysis ==============================#
    def visexpa_control_gui(self):
        pass

#============================== Realignment ==============================#
    def realignment_gui(self):
        self.realignment_box = QtGui.QGroupBox ('Realign', self)
        self.layout.addWidget(self.realignment_box)
        self.realignment_box1 = QtGui.QGroupBox ('', self)
        self.layout.addWidget(self.realignment_box1)
        file_list = utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter ='z_stack')[-1]
        file_list = QtCore.QStringList(file_list)
        layout = QtGui.QHBoxLayout()
        layout1 = QtGui.QHBoxLayout()

        self.realign_button = QtGui.QPushButton('Realign',  self)        
        self.connect(self.realign_button, QtCore.SIGNAL('clicked()'),  self.realign)
        layout.addWidget(self.realign_button)
        
        self.select_reference_mat = QtGui.QComboBox(self)
        layout.addWidget(self.select_reference_mat)    
        self.select_reference_mat.addItems(file_list)
        self.connect(self.select_reference_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list)
        
        self.select_acquired_mat = QtGui.QComboBox(self)
        layout.addWidget(self.select_acquired_mat)   
        self.select_acquired_mat.addItems(file_list)
        self.connect(self.select_acquired_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list) 
        
        layout.addStretch(int(0.2 * self.config.GUI_SIZE['col']))
        
        self.read_stage_button = QtGui.QPushButton('Read stage',  self)        
        self.connect(self.read_stage_button, QtCore.SIGNAL('clicked()'),  self.read_stage)
        layout1.addWidget(self.read_stage_button) 
        
        self.move_stage_button = QtGui.QPushButton('Move stage',  self)
        self.connect(self.move_stage_button, QtCore.SIGNAL('clicked()'),  self.move_stage)
        layout1.addWidget(self.move_stage_button)
        
        self.select_cortical_region = QtGui.QComboBox(self)
        layout1.addWidget(self.select_cortical_region)    
        self.select_cortical_region.addItems(QtCore.QStringList(['this list will be updated from hdf5']))
        
        self.add_cortical_region_button = QtGui.QPushButton('Add cortical region',  self)
        self.connect(self.add_cortical_region_button, QtCore.SIGNAL('clicked()'),  self.add_cortical_region)
        layout1.addWidget(self.add_cortical_region_button) 
        
        layout1.addStretch(int(0.5 * self.config.GUI_SIZE['col']))
        
        self.realignment_box.setLayout(layout)
        self.realignment_box1.setLayout(layout1)        
        
    def read_stage(self):
        self.visexpman_out_queue.put('SOCstageEOCreadEOP')
        self.printc('reads x, y, z, objective z,  rotation x,  rotation y')
        self.current_position = {}
        self.current_position['x'] = 0
        self.current_position['y'] = 0
        self.current_position['z_stage'] = 0
        self.current_position['z'] = 0
        self.current_position['rot axis x'] = 0
        self.current_position['rot axis y'] = 0
        
        while not True:
            if not self.visexpman_in_queue.empty():
                response = self.visexpman_in_queue.get()
                if 'SOCstageEOC' in response:
                    position = response.split('EOC')[-1].replace('EOP', '')
                    self.printc([map(int, i) for i in position.split(',')])
                    break
                    
    def move_stage(self):
        self.printc('moves to {0}'.format(self.scan_console()))

    def add_cortical_region(self):
        #Current stage position is saved to hdf5 as cortical scanning region, text input is added as name of region
        scanning_region_name = self.scanc()
        if len(scanning_region_name) == 0:
            self.printc('Region name is not provided')
            return
        if not hasattr(self, 'current_position'):
            self.printc('Stage position is unknown')
            return
        if not hasattr(self, 'hdf5_handler'):
            self.printc('Experiment file does not exist')
            return
        scanning_region_name += '_' + str(int(time.time()))
        setattr(self.hdf5_handler, scanning_region_name, self.current_position)
        self.hdf5_handler.save(scanning_region_name)
    
    def realign(self):
        #Read image from mat files:
        acquired_z_stack_path = str(self.select_acquired_mat.currentText())        
        reference_image_np_array = mes_interface.image_from_mes_mat(str(self.select_reference_mat.currentText()), z_stack = True)
        acquired_image_np_array = mes_interface.image_from_mes_mat(acquired_z_stack_path, z_stack = True)
        st = time.time()
        metric = 'MattesMutual'
        metric = 'MeanSquares'
        result = itk_versor_rigid_registration.register(reference_image_np_array, acquired_image_np_array,metric= metric, multiresolution=True, calc_difference = True, debug = True)
        from visexpA.engine.datadisplay.imaged import imshow
        path,name = os.path.split(acquired_z_stack_path)
        outdir = os.path.join(path,'debug')
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        out = result[1].copy()
        diff = result[2].copy()
        translation = result[0]
        del result
        for i1 in range(out.shape[0]):
            imshow(numpy.c_[reference_image_np_array[i1], acquired_image_np_array[i1], out[i1,:,:],diff[i1,:,:]],save=os.path.join(outdir,'realign'+str(i1)+'.png'))
                                                                                               
        self.printc (translation)
        self.printc (time.time()-st)
        versor = translation[:3]
        angle, axis = geometry.versor2angle_axis(versor) 
        angle = angle * 180.0/numpy.pi
        message = 'translation {0}   angle {1}, axis {2}'.format(numpy.round(translation[3:],2),angle, axis)
        print message
        self.required_translation_label.setText(message)
        #Save to hdf5
        timestamp = str(int(time.time()))
        hdf5_id = 'realignment_' + timestamp
        self.realignment_hdf5_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, hdf5_id + '.hdf5')
        self.realignment_hdf5_handler = hdf5io.Hdf5io(realignment_hdf5_path , config = self.config, caller = self)
        #Save hdf5 id
        setattr(realignment_hdf5_handler, hdf5_id, 0)
        #save position
        stagexyz = [0,0,0]#placeholder for command querying current stage position
        utils.save_position(self.realignment_hdf5_handler, stagexyz, mes_interface.get_objective_position(acquired_z_stack_path))
        self.realignment_hdf5_handler.z_stack_mat = utils.file_to_binary_array(acquired_z_stack_path)
        self.realignment_hdf5_handler.z_stack = acquired_image_np_array        
        self.realignment_hdf5_handler.translation = {'translation' : numpy.array(translation[:3]), 'angle' : angle ,'axis' : axis}
        self.realignment_hdf5_handler.save('z_stack_mat')
        self.realignment_hdf5_handler.save('z_stack')
        self.realignment_hdf5_handler.save('translation')
        self.realignment_hdf5_handler.close()
        
#============================== Debug, network, helpers ==============================#
    def text_io_gui(self):            
        self.text_io_box = QtGui.QGroupBox ('Console', self)
        self.layout.addWidget(self.text_io_box)        
        layout = QtGui.QHBoxLayout()
        self.text_o = QtGui.QTextEdit(self)
        layout.addWidget(self.text_o, stretch = 500)
        self.text_o.setPlainText('')
        self.text_o.setReadOnly(True)
        self.text_o.ensureCursorVisible()
        self.text_o.setCursorWidth(5)
        
        self.text_i = QtGui.QTextEdit(self)
        self.text_i.setToolTip('self.printc()')
        layout.addWidget(self.text_i, stretch = 0) 
        
        self.text_button_box = QtGui.QGroupBox ('', self)
        layout.addWidget(self.text_button_box, alignment = QtCore.Qt.AlignTop) 
        sublayout = QtGui.QVBoxLayout()
        
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        sublayout.addWidget(self.execute_python_button, alignment = QtCore.Qt.AlignTop)        
        self.connect(self.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        
        self.clear_consol_button = QtGui.QPushButton('Clear consol',  self)
        sublayout.addWidget(self.clear_consol_button, alignment = QtCore.Qt.AlignTop)        
        self.connect(self.clear_consol_button, QtCore.SIGNAL('clicked()'),  self.clear_consol)
        
        self.text_button_box.setLayout(sublayout)
        
        self.network_gui()
        layout.addWidget(self.network_box, alignment = QtCore.Qt.AlignTop) 
        
        self.text_io_box.setLayout(layout)

    def network_gui(self):
        self.network_box = QtGui.QGroupBox ('Network', self)
#        self.layout.addWidget(self.network_box)
        layout = QtGui.QVBoxLayout()
        
        self.network_connection_status_button = QtGui.QPushButton('Read network connection status',  self)
        layout.addWidget(self.network_connection_status_button)        
        self.connect(self.network_connection_status_button, QtCore.SIGNAL('clicked()'),  self.network_connection_status)
        
        self.server_debug_info_button = QtGui.QPushButton('Read server debug info',  self)
        layout.addWidget(self.server_debug_info_button)        
        self.connect(self.server_debug_info_button, QtCore.SIGNAL('clicked()'),  self.get_server_debug_info)
        
        self.select_connection_list = QtGui.QComboBox(self)
        layout.addWidget(self.select_connection_list)
        self.select_connection_list.addItems(QtCore.QStringList(['','mes', 'stimulation', 'analysis']))
        
        self.send_command_button = QtGui.QPushButton('Send command',  self)
        layout.addWidget(self.send_command_button)
        self.connect(self.send_command_button, QtCore.SIGNAL('clicked()'),  self.send_command)
        
        layout.addStretch(int(0.5 * self.config.GUI_SIZE['col']))
        
        self.network_box.setLayout(layout)

    def send_command(self):
        connection_name = str(self.select_connection_list.currentText())
        message = str(self.text_i.toPlainText())
        connection_name_to_queue = {}
        connection_name_to_queue['mes'] = self.mes_command_queue
        connection_name_to_queue['stimulation'] = self.visexpman_out_queue
        connection_name_to_queue['analysis'] = None
        connection_name_to_queue[connection_name].put(message)
        
    def network_connection_status(self):
        connection_info = str(self.command_relay_server.get_connection_status()).replace(',', '\n')
        self.printc(connection_info)
        self.printc('\n')
        
    def get_server_debug_info(self):
        self.printc(str(self.command_relay_server.get_debug_info()).replace('],', ']\n'))
        self.printc('\n')
        
    def execute_python(self):
        exec(str(self.scanc()))
        
    def clear_consol(self):
        self.console_text  = ''
        self.text_o.setPlainText(self.console_text)  
        

    
#== Realignment ==
#    def select_reference_mat(self):
#        file_name_dialog = QtGui.QFileDialog(self)
#        self.realignment_reference_image_path = file_name_dialog.getOpenFileName()
#        self.select_reference_image_label.setText(self.realignment_reference_image_path)
#        if '.mat' in self.realignment_reference_image_path:
#            self.update_realignment_images()
        
#============================== Others ==============================#

#    def printc(self, text):
#        if not isinstance(text, str):
#            text = str(text)
#        self.console_text  += text + '\n'
#        self.text_o.setPlainText(self.console_text)
#        self.text_o.moveCursor(QtGui.QTextCursor.End)
#        
#    def scanc(self):
#        return str(self.text_i.toPlainText())
#        
    def generate_trajectory(self, z_stack):
        #Find cell centers
        dim_order = [0, 1, 2]
        centroids = signal.regmax(z_stack['data'],dim_order)
        #convert from record array to normal array, so that it could be shifted and scaled, when RC array operators are ready,. this wont be necessary anymore
        centroids = numpy.array([centroids['row'], centroids['col'], centroids['depth']], dtype = numpy.float64).transpose()
        #Scale to um
        centroids *=  z_stack['scale']
        #Move with MES system origo
        centroids += z_stack['origin']
        #Convert back to recordarray
        centroid_dtype = [('row', numpy.float64), ('col', numpy.float64), ('depth', numpy.float64)]
        centroids_tuple = []
        for centroid in centroids:
            centroids_tuple.append((centroid[0], centroid[1], centroid[2]))
        trajectory = numpy.array(centroids_tuple, dtype = centroid_dtype)
        return trajectory
        
    def update_combo_box_file_list(self, widget, filter):
        current_value = widget.currentText()
        file_list = utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter = filter)[-1]
        current_index = file_list.index(current_value)
        items_list = QtCore.QStringList(file_list)
        widget.clear()
        widget.addItems(QtCore.QStringList(file_list))
        widget.setCurrentIndex(current_index)
        return file_list
        
    def get_win_path_of_parameter_file(self,file):        
        #Obsolete
        return self.parameter_files[file].replace(self.config.MES_DATA_PATH, self.config.MES_DATA_FOLDER).replace('/','\\')
        
    def update_realignment_images(self, reference_image, acquired_image):
        #Obsolete
        self.reference_image_label.setPixmap(QtGui.QPixmap(reference_image))
        self.acquired_image_label.setPixmap(QtGui.QPixmap(acquired_image))
        
    def printc(self, text):
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.text_o.setPlainText(self.console_text)
        self.text_o.moveCursor(QtGui.QTextCursor.End)
        
    def scanc(self):
        return str(self.text_i.toPlainText())
        
    def closeEvent(self, e):
        e.accept()
        self.printc('Wait till server is closed')
        self.mes_command_queue.put('SOCclose_connectionEOCstop_clientEOP')
        self.visexpman_out_queue.put('SOCclose_connectionEOCstop_clientEOP')
        if hasattr(self, 'hdf5_handler'):
            self.hdf5_handler.close()
        if ENABLE_NETWORK:
#            for i in self.command_relay_server.get_debug_info():
#                print i
            self.command_relay_server.shutdown_servers()            
            time.sleep(2.0) #Enough time to close network connections    
        sys.exit(0)
        
class GuiConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        COORDINATE_SYSTEM='center'
        
        if self.OS == 'win':
            v_drive_folder = 'V:'
        elif self.OS == 'linux':                        
            v_drive_folder = '/home/zoltan/visexp'
        data_folder = os.path.join(v_drive_folder, 'data')
        TEST_DATA_PATH = os.path.join(data_folder, 'test')
        LOG_PATH = data_folder
        EXPERIMENT_LOG_PATH = data_folder        
        EXPERIMENT_DATA_PATH = data_folder
        MES_DATA_PATH = os.path.join(v_drive_folder, 'data')        
        MES_DATA_FOLDER = 'V:\\data'     
        self.COMMAND_RELAY_SERVER['ENABLE'] = ENABLE_NETWORK
        
        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1200, 800))
        self._create_parameters_from_locals(locals())
        
def run_gui():
    config = GuiConfig()
    if ENABLE_NETWORK:
        cr = network_interface.CommandRelayServer(config)
    else:
        cr = None
    app = Qt.QApplication(sys.argv)
    gui = Gui(config, cr)
#    gui2 = VisionExperimentGui(config, cr)
    app.exec_()

if __name__ == '__main__':
#    m = Main()
#    m.start()
    run_gui()
    
    
#TODO: send commands to visexpman
