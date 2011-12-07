#TODO: Load animal parameters, select ref image should come from that
#TODO: rename to visexp_gui.py
#TODO: log
#TODO:Execute experiment
#TODO: timestamp to gui.hdf5 and string_timestamp node
#TODO: string parsing: re
#TODO: string to binary array: numpy.loadtext, loadfile or struct.struct
ENABLE_NETWORK = not True
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

#class Gui(Qt.QMainWindow):
class Gui(QtGui.QWidget):
    def __init__(self, config, command_relay_server):
        self.config = config
        self.command_relay_server = command_relay_server
        self.init_network()
        self.init_files()
        self.console_text = ''
        #=== Init GUI ===
#        Qt.QMainWindow.__init__(self)
        QtGui.QWidget.__init__(self)        
        self.setWindowTitle('Vision Experiment Manager GUI')        
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_user_interface()
        self.show()
        self.print_console('init done')
        
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
        
        self.animal_parameters_gui(0, (0, 0))
        self.mes_control_gui(3, (0, 100))
        self.experiment_control_gui(3, (700, 100))        
        self.realignment_gui(4, (0, 200))
        self.visexpa_control_gui(None, None)
        self.text_io_gui(9, (0, self.config.GUI_SIZE['row']-200))

        
    def animal_parameters_gui(self, row, pos):
        self.animal_parameters_box = QtGui.QGroupBox ('Animal parameters', self)
        self.animal_parameters_box.move(pos[0], pos[1])
        layout = QtGui.QGridLayout()
        date_format = QtCore.QString('dd-mm-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])

        self.save_animal_parameters_button = QtGui.QPushButton('Save animal parameters',  self)
        layout.addWidget(self.save_animal_parameters_button,  row, 0)
        self.connect(self.save_animal_parameters_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)
        layout.addWidget(self.mouse_birth_date_label,  row + 1,0)
        self.mouse_birth_date = QtGui.QDateEdit(self)
        layout.addWidget(self.mouse_birth_date,  row + 1, 1)
        self.mouse_birth_date.setDisplayFormat(date_format)

        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        layout.addWidget(self.gcamp_injection_date_label, row + 1, 2)
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        layout.addWidget(self.gcamp_injection_date,  row + 1, 3)     
        
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        layout.addWidget(self.ear_punch_l_label,  row + 1, 4)     
        self.ear_punch_l = QtGui.QComboBox(self)        
        self.ear_punch_l.addItems(ear_punch_items)
        layout.addWidget(self.ear_punch_l,  row + 1, 5)             
        
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        layout.addWidget(self.ear_punch_r_label,  row + 1,6)     
        self.ear_punch_r = QtGui.QComboBox(self)                
        self.ear_punch_r.addItems(ear_punch_items)
        layout.addWidget(self.ear_punch_r,  row + 1, 7)     
        
        self.anesthesia_protocol_label = QtGui.QLabel('Anesthesia protocol',  self)
        layout.addWidget(self.anesthesia_protocol_label,  row + 1, 8)
        self.anesthesia_protocol = QtGui.QComboBox(self)        
        self.anesthesia_protocol.addItems(QtCore.QStringList(['isoflCP 1.0', 'isoflCP 0.5', 'isoflCP 1.5']))
        layout.addWidget(self.anesthesia_protocol,  row + 1, 9)
                
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        layout.addWidget(self.mouse_strain_label,  row + 1, 10)
        self.mouse_strain = QtGui.QComboBox(self)      
        layout.addWidget(self.mouse_strain,  row + 1, 11)
        self.mouse_strain.addItems(QtCore.QStringList(['bl6', 'chat', 'chatdtr']))
        
        self.animal_parameters_box.setLayout(layout)
    
    def mes_control_gui(self, row, pos):        
        self.mes_box = QtGui.QGroupBox ('MES', self)        
        self.mes_box.move(pos[0], pos[1])
        layout = QtGui.QGridLayout()     
               
        
        self.acquire_z_stack_button = QtGui.QPushButton('Acquire z stack',  self)
        layout.addWidget(self.acquire_z_stack_button, row, 0)
        self.connect(self.acquire_z_stack_button, QtCore.SIGNAL('clicked()'),  self.acquire_z_stack)
        
        self.line_scan_button = QtGui.QPushButton('Line scan',  self) 
        layout.addWidget(self.line_scan_button, row, 1)
        self.connect(self.line_scan_button, QtCore.SIGNAL('clicked()'),  self.line_scan)
        
        self.rc_scan_button = QtGui.QPushButton('RC scan',  self)
        layout.addWidget(self.rc_scan_button, row, 2)
        self.connect(self.rc_scan_button, QtCore.SIGNAL('clicked()'),  self.rc_scan)
        
        self.rc_set_points_button = QtGui.QPushButton('Set RC points',  self)
        layout.addWidget(self.rc_set_points_button, row, 3)
        self.connect(self.rc_set_points_button, QtCore.SIGNAL('clicked()'),  self.rc_set_points)
        
        self.echo_button = QtGui.QPushButton('Echo MES', self)
        layout.addWidget(self.echo_button, row, 4)
        self.connect(self.echo_button, QtCore.SIGNAL('clicked()'), self.echo)

        self.reference_settings_label = QtGui.QLabel('Use reference settings', self)
        layout.addWidget(self.reference_settings_label, row, 5)
        self.reference_settings_checkbox = QtGui.QCheckBox(self)
        layout.addWidget(self.reference_settings_checkbox, row, 6)
        self.connect(self.reference_settings_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.update_mes_command_parameter_file_names)
       
        self.mes_box.setLayout(layout)
        
        
    def experiment_control_gui(self, row, pos):       
        self.experiment_control_box = QtGui.QGroupBox ('Experiment control', self)
        self.experiment_control_box.move(pos[0], pos[1])
        layout = QtGui.QGridLayout()
    
        self.select_experiment = QtGui.QComboBox(self)      
        layout.addWidget(self.select_experiment,  row, 0)
        self.select_experiment.addItems(QtCore.QStringList(['moving_dot', 'grating']))
        
        self.execute_experiment_button = QtGui.QPushButton('Execute experiment',  self)
        layout.addWidget(self.execute_experiment_button, row, 1)
        self.connect(self.execute_experiment_button, QtCore.SIGNAL('clicked()'),  self.execute_experiment)        
        
        self.experiment_control_box.setLayout(layout)
        
    def visexpa_control_gui(self, row, pos):
        pass        
        
    def text_io_gui(self, row, pos):            
        self.text_io_box = QtGui.QGroupBox ('Console', self)
        self.text_io_box.move(pos[0], pos[1])
        self.text_io_box.resize(int(0.5 * self.config.GUI_SIZE['col']), 200)
        layout = QtGui.QGridLayout()        
        self.text_o = QtGui.QTextEdit(self)
        layout.addWidget(self.text_o, row, 0)
        self.text_o.setPlainText('')
        self.text_o.setReadOnly(True)
        self.text_o.ensureCursorVisible()
        self.text_o.setCursorWidth(5)
        self.text_io_box.setLayout(layout)
        
        self.text_i_box = QtGui.QGroupBox ('', self)
        layout_i = QtGui.QGridLayout()  
        self.text_i_box.move(pos[0]+int(0.5 * self.config.GUI_SIZE['col']), pos[1])
        self.text_i_box.resize(int(0.5 * self.config.GUI_SIZE['col']), 100)
        self.text_i = QtGui.QTextEdit(self)
        layout_i.addWidget(self.text_i, row, 1) 
        
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        layout_i.addWidget(self.execute_python_button, row+1, 1)
        self.connect(self.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)        
        self.text_i_box.setLayout(layout_i)
        
    def realignment_gui(self, row, pos):
        self.realignment_box = QtGui.QGroupBox ('Realign', self)
        self.realignment_box.move(pos[0], pos[1])
        file_list = file_list = self.get_z_stack_file_list()        
        select_reference_mat_items = QtCore.QStringList(file_list)
        select_acquired_mat_items = QtCore.QStringList(file_list)
        layout = QtGui.QGridLayout()

        self.realign_button = QtGui.QPushButton('Realign',  self)        
        self.connect(self.realign_button, QtCore.SIGNAL('clicked()'),  self.realign)
        layout.addWidget(self.realign_button, row, 0)
        
        self.select_reference_mat = QtGui.QComboBox(self)
        layout.addWidget(self.select_reference_mat, row, 3)      
        self.select_reference_mat.addItems(select_reference_mat_items)
        self.connect(self.select_reference_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list)
        
        self.select_acquired_mat = QtGui.QComboBox(self)
        layout.addWidget(self.select_acquired_mat, row+1, 3)   
        self.select_acquired_mat.addItems(select_acquired_mat_items)
        self.connect(self.select_acquired_mat, QtCore.SIGNAL('activated(int)'), self.update_z_stack_list) 
        
        self.read_stage_button = QtGui.QPushButton('Read stage',  self)        
        self.connect(self.read_stage_button, QtCore.SIGNAL('clicked()'),  self.read_stage)
        layout.addWidget(self.read_stage_button, row + 2, 0) 
        
        self.move_stage_button = QtGui.QPushButton('Move stage',  self)
        self.connect(self.move_stage_button, QtCore.SIGNAL('clicked()'),  self.move_stage)
        layout.addWidget(self.move_stage_button, row + 2, 1)    
        
        self.realignment_box.setLayout(layout)
        
    def init_files(self):   
        
        #create hdf5io
        #TODO: File name generation shall depend on config class
        self.hdf5_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'gui_MovingDot_{0}.hdf5'.format(int(time.time())))
        self.hdf5_handler = hdf5io.Hdf5io(self.hdf5_path , config = self.config, caller = self)
        
    def print_console(self, text):
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.text_o.setPlainText(self.console_text)      
        self.text_o.moveCursor(QtGui.QTextCursor.End)
        
    def scan_console(self):
        return self.text_i.toPlainText()
        
    def execute_python(self):
        exec(str(self.scan_console()))
        
    def read_stage(self):
        self.visexpman_out_queue.put('SOCstageEOCreadEOP')
        self.print_console('reads x, y, z, objective z,  rotation x,  rotation y')
        while not True:
            if not self.visexpman_in_queue.empty():
                response = self.visexpman_in_queue.get()
                if 'SOCstageEOC' in response:
                    position = response.split('EOC')[-1].replace('EOP', '')
                    self.print_console([map(int, i) for i in position.split(',')])
                    break
                    
    def move_stage(self):
        self.print_console('moves to {0}'.format(self.scan_console()))
        
    def rc_set_points(self):
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
            file_list = utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter = filter)[-1]
        else:
            file_list = utils.filtered_file_list(self.config.EXPERIMENT_DATA_PATH, filter = filter,  fullpath = True)
        return file_list

        
    def get_win_path_of_parameter_file(self,file):        
        #Obsolete
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
    def save_animal_parameters(self):
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
        self.print_console('Animal parameters saved')
#== MES ==        
    def acquire_camera_image(self):
        self.update_mes_command_parameter_file_names()        
        self.mes_command_queue.put('SOCacquire_camera_imageEOC{0}EOP' .format(self.get_win_path_of_parameter_file('acquire_camera_image')))
        self.get_response_from_mes()
        
    def acquire_z_stack(self):
        self.update_mes_command_parameter_file_names()
        self.mes_command_queue.put('SOCacquire_z_stackEOC{0}EOP' .format(self.get_win_path_of_parameter_file('acquire_z_stack')))
        self.get_response_from_mes()
        
    def line_scan(self):
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
            m_drive_folder = '/home/zoltan/share'
            if not os.path.exists(m_drive_folder):
                m_drive_folder = '/media/sf_M_DRIVE/Zoltan/visexpman'
        data_folder = os.path.join(m_drive_folder, 'data')
        TEST_DATA_PATH = os.path.join(m_drive_folder, 'test_data')
        LOG_PATH = data_folder
        EXPERIMENT_LOG_PATH = data_folder        
        EXPERIMENT_DATA_PATH = data_folder
        MES_OUTPUT_PATH = os.path.join(m_drive_folder, 'data')        
        MES_OUTPUT_FOLDER_WIN = 'M:\\Zoltan\\visexpman\\data'     
        self.COMMAND_RELAY_SERVER['ENABLE'] = ENABLE_NETWORK
        
        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1200, 700))
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
