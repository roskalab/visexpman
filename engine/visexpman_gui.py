#TODO: Load animal parameters, select ref image should come from that
#TODO: rename to visexp_gui.py
#TODO: log
#TODO:Execute experiment
#TODO: timestamp to gui.hdf5 and string_timestamp node
#TODO: string parsing: re
#TODO: string to binary array: numpy.loadtext, loadfile or struct.struct
ENABLE_NETWORK = True
SEARCH_SUBFOLDERS = False
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

class Gui(Qt.QMainWindow):
    def __init__(self, config, command_relay_server):
        self.config = config
        self.command_relay_server = command_relay_server
        self.init_network()
        self.init_files()       
        
        #=== Init GUI ===
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')        
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_user_interface()
        self.show()
        
    def init_network(self):
        self.mes_command_queue = Queue.Queue()
        self.mes_response_queue = Queue.Queue()
        if ENABLE_NETWORK:
            self.mes_connection = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.mes_response_queue, self.mes_command_queue)
        
        self.visexpman_out_queue = Queue.Queue()
        self.visexpman_in_queue = Queue.Queue()
        if ENABLE_NETWORK:
            self.stim_connection = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.visexpman_in_queue, self.visexpman_out_queue)        
        
    def create_user_interface(self):
        self.panel_size = utils.cr((150, 35))
        self.wide_panel_size = utils.cr((700, 35))
        self.image_size = utils.cr((300, 300))
        self.experiment_identification_gui(50)
        self.mes_control(50 + 4 * self.panel_size['row'])
        self.visexpman_control(50 + 7.5 * self.panel_size['row'])
        self.realignment_gui(50 + 10 * self.panel_size['row'])
        self.visexpa_control(50 + 20 * self.panel_size['row'])
        
        
    def experiment_identification_gui(self, row):
        
        #== Parameters of gui items ==
        title = {'title' : '---------------------    Experiment identification    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        date_format = QtCore.QString('dd-mm-yyyy')
        mouse_birth_date = {'size' : self.panel_size,  'position' : utils.cr((0, row + 1.1 * self.panel_size['row']))}
        gcamp_injection_date = {'size' : self.panel_size,  'position' : utils.cr((2.1*self.panel_size['col'],  row + 1.1 * self.panel_size['row']))}
        anesthesia_protocol = {'size' : self.panel_size,  'position' : utils.cr((4.1*self.panel_size['col'], row + 1.1 * self.panel_size['row']))}
        anesthesia_protocol_items = QtCore.QStringList(['isoflCP 1.0', 'isoflCP 0.5', 'isoflCP 1.5'])        
        ear_punch_l = {'size' : self.panel_size,  'position' : utils.cr((0, row + 2.1 * self.panel_size['row']))}
        ear_punch_r = {'size' : self.panel_size,  'position' : utils.cr((2.1*self.panel_size['col'], row + 2.1 * self.panel_size['row']))}
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])               
        mouse_strain = {'size' : self.panel_size,  'position' : utils.cr((4.1*self.panel_size['col'], row + 2.1 * self.panel_size['row']))}
        mouse_strain_items = QtCore.QStringList(['bl6', 'chat', 'chatdtr'])
        generate_animal_parameters = {'size' : self.panel_size,  'position' : utils.cr((0, row + 3.1 * self.panel_size['row']))}
        
        animal_parameters = {'size' : utils.cr((self.config.GUI_SIZE['col'] - self.panel_size['col'], 40)),  'position' : utils.cr((1.1 * self.panel_size['col'], row + 3.1 * self.panel_size['row']))}       
        
        #== Create gui items ==
        self.experiment_identification_title = QtGui.QLabel(title['title'],  self)
        self.experiment_identification_title.resize(title['size']['col'],  title['size']['row'])
        self.experiment_identification_title.move(title['position']['col'],  title['position']['row'])
        self.experiment_identification_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.generate_animal_parameters_button = QtGui.QPushButton('Save animal parameters',  self)
        self.generate_animal_parameters_button.resize(generate_animal_parameters['size']['col'],  generate_animal_parameters['size']['row'])
        self.generate_animal_parameters_button.move(generate_animal_parameters['position']['col'],  generate_animal_parameters['position']['row'])
        self.connect(self.generate_animal_parameters_button, QtCore.SIGNAL('clicked()'),  self.generate_animal_parameters)
        
        self.mouse_birth_date = QtGui.QDateEdit(self)
        self.mouse_birth_date.setDisplayFormat(date_format)
        self.mouse_birth_date.resize(mouse_birth_date['size']['col'],  mouse_birth_date['size']['row'])
        self.mouse_birth_date.move(mouse_birth_date['position']['col'] + mouse_birth_date['size']['col'],  mouse_birth_date['position']['row'])
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)
        self.mouse_birth_date_label.resize(mouse_birth_date['size']['col'],  mouse_birth_date['size']['row'])
        self.mouse_birth_date_label.move(mouse_birth_date['position']['col'],  mouse_birth_date['position']['row'])
        
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        self.gcamp_injection_date.resize(gcamp_injection_date['size']['col'],  gcamp_injection_date['size']['row'])
        self.gcamp_injection_date.move(gcamp_injection_date['position']['col'] + gcamp_injection_date['size']['col'],  gcamp_injection_date['position']['row'])
        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        self.gcamp_injection_date_label.resize(gcamp_injection_date['size']['col'],  gcamp_injection_date['size']['row'])
        self.gcamp_injection_date_label.move(gcamp_injection_date['position']['col'],  gcamp_injection_date['position']['row'])
        
        self.ear_punch_l = QtGui.QComboBox(self)
        self.ear_punch_l.resize(ear_punch_l['size']['col'],  ear_punch_l['size']['row'])
        self.ear_punch_l.move(ear_punch_l['position']['col'] + ear_punch_l['size']['col'],  ear_punch_l['position']['row'])
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        self.ear_punch_l_label.resize(ear_punch_l['size']['col'],  ear_punch_l['size']['row'])
        self.ear_punch_l_label.move(ear_punch_l['position']['col'],  ear_punch_l['position']['row'])
        self.ear_punch_l.addItems(ear_punch_items)
        
        self.ear_punch_r = QtGui.QComboBox(self)
        self.ear_punch_r.resize(ear_punch_r['size']['col'],  ear_punch_r['size']['row'])
        self.ear_punch_r.move(ear_punch_r['position']['col'] + ear_punch_r['size']['col'],  ear_punch_r['position']['row'])
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        self.ear_punch_r_label.resize(ear_punch_r['size']['col'],  ear_punch_r['size']['row'])
        self.ear_punch_r_label.move(ear_punch_r['position']['col'],  ear_punch_r['position']['row'])
        self.ear_punch_r.addItems(ear_punch_items)
        
        self.anesthesia_protocol = QtGui.QComboBox(self)
        self.anesthesia_protocol.resize(anesthesia_protocol['size']['col'],  anesthesia_protocol['size']['row'])
        self.anesthesia_protocol.move(anesthesia_protocol['position']['col'] + anesthesia_protocol['size']['col'],  anesthesia_protocol['position']['row'])
        self.anesthesia_protocol_label = QtGui.QLabel('Anesthesia protocol',  self)
        self.anesthesia_protocol_label.resize(anesthesia_protocol['size']['col'],  anesthesia_protocol['size']['row'])
        self.anesthesia_protocol_label.move(anesthesia_protocol['position']['col'],  anesthesia_protocol['position']['row'])
        self.anesthesia_protocol.addItems(anesthesia_protocol_items)
                
        self.mouse_strain = QtGui.QComboBox(self)
        self.mouse_strain.resize(mouse_strain['size']['col'],  mouse_strain['size']['row'])
        self.mouse_strain.move(mouse_strain['position']['col'] + mouse_strain['size']['col'],  mouse_strain['position']['row'])
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        self.mouse_strain_label.resize(mouse_strain['size']['col'],  mouse_strain['size']['row'])
        self.mouse_strain_label.move(mouse_strain['position']['col'],  mouse_strain['position']['row'])
        self.mouse_strain.addItems(mouse_strain_items)
        
        self.animal_parameters = QtGui.QLabel('',  self)
        self.animal_parameters.resize(animal_parameters['size']['col'],  animal_parameters['size']['row'])
        self.animal_parameters.move(animal_parameters['position']['col'],  animal_parameters['position']['row'])    
    
    def mes_control(self, row):
        '''
        
        '''
        #== Params ==#
        title = {'title' : '---------------------    MES    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        acquire_camera_image = {'size' : self.panel_size,  'position' : utils.cr((0,  row + 1.1 *  self.panel_size['row']))}
        acquire_z_stack = {'size' : self.panel_size,  'position' : utils.cr((self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        single_two_photon_recording = {'size' : self.panel_size,  'position' : utils.cr((2*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        two_photon_recording = {'size' : self.panel_size,  'position' : utils.cr((3*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        rc_scan = {'size' : self.panel_size,  'position' : utils.cr((4*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        echo = {'size' : self.panel_size, 'position' : utils.cr((5*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        reference_settings = {'size' : self.panel_size, 'position' : utils.cr((0,  row + 2.1 *  self.panel_size['row']))}
        roller_coaster_set_points = {'size' : self.panel_size,  'position' : utils.cr((2*self.panel_size['col'],  row + 2.1 *  self.panel_size['row']))}
                
        #== gui items ==#        
        self.mes_title = QtGui.QLabel(title['title'],  self)
        self.mes_title.resize(title['size']['col'],  title['size']['row'])
        self.mes_title.move(title['position']['col'],  title['position']['row'])
        self.mes_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.acquire_camera_image_button = QtGui.QPushButton('Acquire camera image',  self)
        self.acquire_camera_image_button.resize(acquire_camera_image['size']['col'],  acquire_camera_image['size']['row'])
        self.acquire_camera_image_button.move(acquire_camera_image['position']['col'],  acquire_camera_image['position']['row'])
        self.connect(self.acquire_camera_image_button, QtCore.SIGNAL('clicked()'),  self.acquire_camera_image)
        
        self.acquire_z_stack_button = QtGui.QPushButton('Acquire z stack',  self)
        self.acquire_z_stack_button.resize(acquire_z_stack['size']['col'],  acquire_z_stack['size']['row'])
        self.acquire_z_stack_button.move(acquire_z_stack['position']['col'],  acquire_z_stack['position']['row'])
        self.connect(self.acquire_z_stack_button, QtCore.SIGNAL('clicked()'),  self.acquire_z_stack)
        
        self.two_photon_recording_button = QtGui.QPushButton('Two photon record',  self)
        self.two_photon_recording_button.resize(two_photon_recording['size']['col'],  two_photon_recording['size']['row'])
        self.two_photon_recording_button.move(two_photon_recording['position']['col'],  two_photon_recording['position']['row'])
        self.connect(self.two_photon_recording_button, QtCore.SIGNAL('clicked()'),  self.two_photon_recording)
        
        self.single_photon_recording_button = QtGui.QPushButton('Single two photon',  self)
        self.single_photon_recording_button.resize(single_two_photon_recording['size']['col'],  single_two_photon_recording['size']['row'])
        self.single_photon_recording_button.move(single_two_photon_recording['position']['col'],  single_two_photon_recording['position']['row'])
        self.connect(self.single_photon_recording_button, QtCore.SIGNAL('clicked()'),  self.single_two_photon_recording)
        
        self.rc_scan_button = QtGui.QPushButton('RC scan',  self)
        self.rc_scan_button.resize(rc_scan['size']['col'],  rc_scan['size']['row'])
        self.rc_scan_button.move(rc_scan['position']['col'],  rc_scan['position']['row'])
        self.connect(self.rc_scan_button, QtCore.SIGNAL('clicked()'),  self.rc_scan)
        
        self.echo_button = QtGui.QPushButton('Echo MES', self)
        self.echo_button.resize(echo['size']['col'], echo['size']['row'])
        self.echo_button.move(echo['position']['col'], echo['position']['row'])
        self.connect(self.echo_button, QtCore.SIGNAL('clicked()'), self.echo)
        
        self.reference_settings_checkbox = QtGui.QCheckBox(self)        
        self.reference_settings_checkbox.move(reference_settings['size']['col'] + reference_settings['position']['col'], reference_settings['position']['row'])
        self.reference_settings_label = QtGui.QLabel('Use reference settings', self)
        self.reference_settings_label.resize(reference_settings['size']['col'], reference_settings['size']['row'])
        self.reference_settings_label.move(reference_settings['position']['col'], reference_settings['position']['row'])
        self.connect(self.reference_settings_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.update_mes_command_parameter_file_names)
        
        self.roller_coaster_set_points_button = QtGui.QPushButton('Set RC points',  self)
        self.roller_coaster_set_points_button.resize(roller_coaster_set_points['size']['col'],  roller_coaster_set_points['size']['row'])
        self.roller_coaster_set_points_button.move(roller_coaster_set_points['position']['col'],  roller_coaster_set_points['position']['row'])
        self.connect(self.roller_coaster_set_points_button, QtCore.SIGNAL('clicked()'),  self.roller_coaster_set_points)
        
        
    def visexpman_control(self, row):
        #== Params ==
        title = {'title' : '---------------------    Visexpman    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        execute_experiment = {'size' : self.panel_size,  'position' : utils.cr((0,  row + 1.1 *  self.panel_size['row']))}
        experiment_config = {'size' : self.panel_size,  'position' : utils.cr((self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        
        #== Gui items ==
        self.visexpman_title = QtGui.QLabel(title['title'],  self)
        self.visexpman_title.resize(title['size']['col'],  title['size']['row'])
        self.visexpman_title.move(title['position']['col'],  title['position']['row'])
        self.visexpman_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.execute_experiment_button = QtGui.QPushButton('Execute experiment',  self)
        self.execute_experiment_button.resize(execute_experiment['size']['col'],  execute_experiment['size']['row'])
        self.execute_experiment_button.move(execute_experiment['position']['col'],  execute_experiment['position']['row'])
        self.connect(self.execute_experiment_button, QtCore.SIGNAL('clicked()'),  self.execute_experiment)
        
        self.experiment_config_input = QtGui.QTextEdit(self)
        self.experiment_config_input.resize(experiment_config['size']['col'],  experiment_config['size']['row'])
        self.experiment_config_input.move(experiment_config['position']['col'],  experiment_config['position']['row'])
        
    def visexpa_control(self, row):
        #== Params ==
        title = {'title' : '---------------------    VisexpA    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        execute_experiment = {'size' : self.panel_size,  'position' : utils.cr((0,  row + 1.1 *  self.panel_size['row']))}
        experiment_config = {'size' : self.panel_size,  'position' : utils.cr((self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        
        #== Gui items ==
        self.visexpa_title = QtGui.QLabel(title['title'],  self)
        self.visexpa_title.resize(title['size']['col'],  title['size']['row'])
        self.visexpa_title.move(title['position']['col'],  title['position']['row'])
        self.visexpa_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        
    def realignment_gui(self, row):
        title = {'title' : '---------------------    Realignment    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        realign = {'size' : self.panel_size,  'position' : utils.cr((0,  row + 1.1 *  self.panel_size['row']))}
        read_stage = {'size' : self.panel_size,  'position' : utils.cr((0, row + 2.1 * self.panel_size['row']))}
        required_translation = {'size' : self.panel_size,  'position' : utils.cr((0, row + 3.1 * self.panel_size['row']))}
        file_list = file_list = self.get_z_stack_file_list()        
        select_reference_mat = {'size' : self.wide_panel_size,  'position' : utils.cr((self.panel_size['col'], row + 1.1 * self.wide_panel_size['row']))}
        select_reference_mat_items = QtCore.QStringList(file_list)
        select_acquired_mat = {'size' : self.wide_panel_size,  'position' : utils.cr((self.panel_size['col'] , row + 2.1 * self.wide_panel_size['row']))}
        select_acquired_mat_items = QtCore.QStringList(file_list)
                
        reference_image = {'size' : self.image_size,  'position' : utils.cr((self.wide_panel_size['col'], row + 2.1 * self.wide_panel_size['row']))}
        acquired_image = {'size' : self.image_size,  'position' : utils.cr((self.wide_panel_size['col'] + self.image_size['col'] , row + 2.1 * self.wide_panel_size['row']))}
        
        #== Gui items ==
        self.visexpa_title = QtGui.QLabel(title['title'],  self)
        self.visexpa_title.resize(title['size']['col'],  title['size']['row'])
        self.visexpa_title.move(title['position']['col'],  title['position']['row'])
        self.visexpa_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.realign_button = QtGui.QPushButton('Realign',  self)
        self.realign_button.resize(realign['size']['col'],  realign['size']['row'])
        self.realign_button.move(realign['position']['col'],  realign['position']['row'])
        self.connect(self.realign_button, QtCore.SIGNAL('clicked()'),  self.realign)
        
        self.read_stage_button = QtGui.QPushButton('Read stage',  self)
        self.read_stage_button.resize(read_stage['size']['col'],  read_stage['size']['row'])
        self.read_stage_button.move(read_stage['position']['col'],  read_stage['position']['row'])
        self.connect(self.read_stage_button, QtCore.SIGNAL('clicked()'),  self.read_stage)
        
        self.required_translation_label = QtGui.QLabel('unknown',  self)
        self.required_translation_label.resize(2*required_translation['size']['col'],  required_translation['size']['row'])
        self.required_translation_label.move(required_translation['position']['col'],  required_translation['position']['row'])
        
        self.select_reference_mat = QtGui.QComboBox(self)
        self.select_reference_mat.resize(select_reference_mat['size']['col'],  select_reference_mat['size']['row'])
        self.select_reference_mat.move(select_reference_mat['position']['col'] + 0.0*select_reference_mat['size']['col'],  select_reference_mat['position']['row'])
        self.select_reference_mat.addItems(select_reference_mat_items)
        self.connect(self.select_reference_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list)
        
        self.select_acquired_mat = QtGui.QComboBox(self)
        self.select_acquired_mat.resize(select_acquired_mat['size']['col'],  select_acquired_mat['size']['row'])
        self.select_acquired_mat.move(select_acquired_mat['position']['col'] + 0.0*select_acquired_mat['size']['col'],  select_acquired_mat['position']['row'])
        self.select_acquired_mat.addItems(select_acquired_mat_items)
        self.connect(self.select_acquired_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list)
        
        self.reference_image_label = QtGui.QLabel('',self)
        self.reference_image_label.resize(reference_image['size']['col'],  reference_image['size']['row'])
        self.reference_image_label.move(reference_image['position']['col'],  reference_image['position']['row'])
        
        self.acquired_image_label = QtGui.QLabel('',self)
        self.acquired_image_label.resize(acquired_image['size']['col'],  acquired_image['size']['row'])
        self.acquired_image_label.move(acquired_image['position']['col'],  acquired_image['position']['row'])
        
    def init_files(self):   
        
        #create hdf5io
        #TODO: File name generation shall depend on config class
        self.hdf5_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'gui_MovingDot_{0}.hdf5'.format(int(time.time())))
        self.hdf5_handler = hdf5io.Hdf5io(self.hdf5_path , config = self.config, caller = self)
        
    def read_stage(self):
        self.visexpman_out_queue.put('SOCstageEOCreadEOP')
        while True:
            if not self.visexpman_in_queue.empty():
                response = self.visexpman_in_queue.get()
                if 'SOCstageEOC' in response:
                    position = response.split('EOC')[-1].replace('EOP', '')
                    print [map(int, i) for i in position.split(',')]
                    break
        
    def roller_coaster_set_points(self):
        #using acquired z stack, calculate points select_acquired_mat_current_value = self.select_acquired_mat.currentText()
        self.update_mes_command_parameter_file_names()
        points = numpy.zeros((3,100), {'names': ('x', 'y', 'z'), 'formats': (numpy.float64, numpy.float64, numpy.float64)})
        mes_interface.roller_coaster_set_points(points, self.parameter_files['rc_scan_points'])
        points_win_path = self.get_win_path_of_parameter_file('rc_scan_points')
        self.mes_command_queue.put('SOCset_pointsEOC{0}EOP' .format(points_win_path))
        self.get_response_from_mes()

    def update_mes_command_parameter_file_names(self):
        
        if self.reference_settings_checkbox.checkState() == 0 or not hasattr(self, 'parameter_files'): 
            #Issue: sometimes (in virtual box) files created by other computers cannot be seen by the software (on M drive)
            self.parameter_files = {}
            self.parameter_files['acquire_camera_image'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'acquire_camera_image_parameters.mat'), insert_timestamp = True)
            self.parameter_files['acquire_z_stack'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'acquire_z_stack_parameters.mat'), insert_timestamp = True)
            self.parameter_files['line_scan'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'line_scan_parameters.mat'), insert_timestamp = True)
            self.parameter_files['single_two_photon'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'single_two_photon_parameters.mat'), insert_timestamp = True)
            self.parameter_files['rc_scan'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'rc_scan_parameters.mat'), insert_timestamp = True)
            self.parameter_files['rc_scan_points'] = utils.generate_filename(os.path.join(self.config.MES_OUTPUT_PATH, 'rc_scan_points.mat'), insert_timestamp = True)
        else:            
            pass
            #TODO: assign reference filenames


    def get_z_stack_file_list(self):
        filter = 'acquire_z_stack'
        if SEARCH_SUBFOLDERS:
            file_list = utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH+os.sep+"rotated_z_stacks", filter = filter)[-1]
        else:
            file_list = utils.filtered_file_list(self.config.EXPERIMENT_DATA_PATH+os.sep+"rotated_z_stacks", filter = filter,  fullpath = True)
        return file_list

        
    def get_win_path_of_parameter_file(self,file):        
        return self.parameter_files[file].replace(self.config.MES_OUTPUT_PATH, self.config.MES_OUTPUT_FOLDER_WIN).replace('/','\\')        

#==== Function called via signals ====

#== Realignment ==
#    def select_reference_mat(self):
#        file_name_dialog = QtGui.QFileDialog(self)
#        self.realignment_reference_image_path = file_name_dialog.getOpenFileName()
#        self.select_reference_image_label.setText(self.realignment_reference_image_path)
#        if '.mat' in self.realignment_reference_image_path:
#            self.update_realignment_images()

    def update_z_stack_list(self, index):        
        select_acquired_mat_current_value = self.select_acquired_mat.currentText()
        select_reference_mat_current_value = self.select_reference_mat.currentText()        
        file_list = self.get_z_stack_file_list()
        select_acquired_mat_index = file_list.index(select_acquired_mat_current_value)
        select_reference_mat_index = file_list.index(select_reference_mat_current_value)        
        z_stack_list = QtCore.QStringList(file_list)
        self.select_acquired_mat.clear()
        self.select_acquired_mat.addItems(z_stack_list)
        self.select_reference_mat.clear()
        self.select_reference_mat.addItems(z_stack_list)
        self.select_acquired_mat.setCurrentIndex(select_acquired_mat_index)
        self.select_reference_mat.setCurrentIndex(select_reference_mat_index)

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
                                                                                               
        print translation
        print time.time()-st
        versor = translation[:3]
        angle, axis = geometry.versor2angle_axis(versor) 
        angle = angle * 180.0/numpy.pi
        message = 'translation {0}   angle {1}, axis {2}'.format(numpy.round(translation[3:],2),angle, axis)
        print message
        self.required_translation_label.setText(message)
        #Save to hdf5
        timestamp = str(int(time.time()))
        hdf5_id = 'realignment_' + timestamp
        realignment_hdf5_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, hdf5_id + '.hdf5')
        realignment_hdf5_handler = hdf5io.Hdf5io(realignment_hdf5_path , config = self.config, caller = self)
        #Save hdf5 id
        setattr(realignment_hdf5_handler, hdf5_id, 0)
        #save position
        stagexyz = [0,0,0]#placeholder for command querying current stage position
        utils.save_position(realignment_hdf5_handler, stagexyz, mes_interface.get_objective_position(acquired_z_stack_path))
        realignment_hdf5_handler.z_stack_mat = utils.file_to_binary_array(acquired_z_stack_path)
        realignment_hdf5_handler.z_stack = acquired_image_np_array        
        realignment_hdf5_handler.translation = {'translation' : numpy.array(translation[:3]), 'angle' : angle ,'axis' : axis}
        realignment_hdf5_handler.save('z_stack_mat')
        realignment_hdf5_handler.save('z_stack')
        realignment_hdf5_handler.save('translation')
        realignment_hdf5_handler.close()
        
    def update_realignment_images(self, reference_image, acquired_image):
        self.reference_image_label.setPixmap(QtGui.QPixmap(reference_image))
        self.acquired_image_label.setPixmap(QtGui.QPixmap(acquired_image))
#== Visesxpman ==
    def execute_experiment(self):
        command = 'SOCexecute_experimentEOC{0}EOP'.format(self.experiment_config_input.toPlainText())
        self.visexpman_out_queue.put(command)
        print command
        
#== General ==
    def generate_animal_parameters(self):
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
        self.animal_parameters.setText(animal_parameters_text)        
#== MES ==        
    def acquire_camera_image(self):
        self.update_mes_command_parameter_file_names()        
        self.mes_command_queue.put('SOCacquire_camera_imageEOC{0}EOP' .format(self.get_win_path_of_parameter_file('acquire_camera_image')))
        self.get_response_from_mes()
        
    def acquire_z_stack(self):
        self.update_mes_command_parameter_file_names()
        self.mes_command_queue.put('SOCacquire_z_stackEOC{0}EOP' .format(self.get_win_path_of_parameter_file('acquire_z_stack')))
        self.get_response_from_mes()
        
    def two_photon_recording(self):
        self.update_mes_command_parameter_file_names()        
        self.mes_command_queue.put('SOCacquire_line_scanEOC{0}EOP'.format(self.get_win_path_of_parameter_file('line_scan')))
        self.get_response_from_mes()
        
    def single_two_photon_recording(self):
        self.update_mes_command_parameter_file_names()
        self.mes_command_queue.put('SOCacquire_xy_imageEOC{0}EOP'.format(self.get_win_path_of_parameter_file('single_two_photon')))
        self.get_response_from_mes()

    def rc_scan(self):
        self.update_mes_command_parameter_file_names()
        self.mes_command_queue.put('SOCrc_scanEOC{0}EOP'.format(self.get_win_path_of_parameter_file('rc_scan')))
        self.get_response_from_mes()
        
    def echo(self):
        self.mes_command_queue.put('SOCechoEOCguiEOP')
        self.visexpman_out_queue.put('SOCechoEOCguiEOP')
        self.get_response_from_mes()
        self.get_response_from_visexpman()
        
    def get_response_from_mes(self):
        time.sleep(1.0)
        while not self.mes_response_queue.empty():
            print self.mes_response_queue.get()
            
    def get_response_from_visexpman(self):
        time.sleep(1.0)
        while not self.visexpman_in_queue.empty():
            print self.visexpman_in_queue.get()
        
#== Others ==        
    def closeEvent(self, e):
        e.accept()
        self.mes_command_queue.put('SOCclose_connectionEOCstop_clientEOP')
        self.visexpman_out_queue.put('SOCclose_connectionEOCstop_clientEOP')
        self.hdf5_handler.close()
        if ENABLE_NETWORK:
            for i in self.command_relay_server.get_debug_info():
                print i
            self.command_relay_server.shutdown_servers()            
            time.sleep(2.0) #Enough time to close network connections    
        sys.exit(0)
        
class GuiConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        COORDINATE_SYSTEM='center'
        
        if self.OS == 'win':
            m_drive_folder = 'M:\\Zoltan\\visexpman'
        elif self.OS == 'linux':
            m_drive_folder = '/home/zoltan/mdrive/Zoltan/visexpman'
            if not os.path.exists(m_drive_folder):
                m_drive_folder = '/media/sf_M_DRIVE/Zoltan/visexpman'
        data_folder = os.path.join(m_drive_folder, 'data')
        TEST_DATA_PATH = os.path.join(m_drive_folder, 'test_data')
        LOG_PATH = data_folder
        EXPERIMENT_LOG_PATH = data_folder        
        EXPERIMENT_DATA_PATH = data_folder
        MES_OUTPUT_PATH = os.path.join(m_drive_folder, 'data')        
        MES_OUTPUT_FOLDER_WIN = 'M:\\Zoltan\\visexpman\\data'        
        
        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1024, 768))
        self._create_parameters_from_locals(locals())
        
class Main(threading.Thread):
    def run(self):
        run_gui()

def run_gui():
    config = GuiConfig()    
    if ENABLE_NETWORK:
        cr = network_interface.CommandRelayServer(config)
    else:
        cr = None
    app = Qt.QApplication(sys.argv)
    gui = Gui(config, cr)
    app.exec_()
    
if __name__ == '__main__':
#    m = Main()
#    m.start()
    run_gui()
    
    
#TODO: send commands to visexpman
