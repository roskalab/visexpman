
#TODO: log
#TODO: command with previous setting
#TODO:Execute experiment

import time
import socket
import sys
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.utils as utils
import visexpman.engine.visual_stimulation.configuration as configuration
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.generic.utils as utils
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import Queue
import os.path
import visexpA.engine.datahandlers.hdf5io as hdf5io

class Gui(Qt.QMainWindow):
    def __init__(self, config):
        self.config = config
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
        self.mes_server = network_interface.CommandServer(self.mes_command_queue, self.mes_response_queue, self.config.GUI_MES['PORT'])
        self.mes_server.start()
        
    def create_user_interface(self):
        self.panel_size = utils.cr((150, 35))
        
        self.experiment_identification_gui(50)
        self.mes_control(50 + 4 * self.panel_size['row'])
        self.visexpman_control(50 + 6.5 * self.panel_size['row'])
        self.visexpa_control(50 + 9 * self.panel_size['row'])       
        
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
        generate_id = {'size' : self.panel_size,  'position' : utils.cr((0, row + 3.1 * self.panel_size['row']))}
        
        id = {'size' : utils.cr((self.config.GUI_SIZE['col'] - self.panel_size['col'], 40)),  'position' : utils.cr((1.1 * self.panel_size['col'], row + 3.1 * self.panel_size['row']))}       
        
        #== Create gui items ==
        self.experiment_identification_title = QtGui.QLabel(title['title'],  self)
        self.experiment_identification_title.resize(title['size']['col'],  title['size']['row'])
        self.experiment_identification_title.move(title['position']['col'],  title['position']['row'])
        self.experiment_identification_title.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.generate_id_button = QtGui.QPushButton('Generate ID',  self)
        self.generate_id_button.resize(generate_id['size']['col'],  generate_id['size']['row'])
        self.generate_id_button.move(generate_id['position']['col'],  generate_id['position']['row'])
        self.connect(self.generate_id_button, QtCore.SIGNAL('clicked()'),  self.generate_id)
        
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
        
        self.id = QtGui.QLabel('',  self)
        self.id.resize(id['size']['col'],  id['size']['row'])
        self.id.move(id['position']['col'],  id['position']['row'])
        
        
    
    def mes_control(self, row):
        #== Params ==
        title = {'title' : '---------------------    MES    ---------------------', 'size' : utils.cr((self.config.GUI_SIZE['col'], 40)),  'position' : utils.cr((0, row))}
        acquire_camera_image = {'size' : self.panel_size,  'position' : utils.cr((0,  row + 1.1 *  self.panel_size['row']))}
        acquire_z_stack = {'size' : self.panel_size,  'position' : utils.cr((self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        single_two_photon_recording = {'size' : self.panel_size,  'position' : utils.cr((2*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        two_photon_recording = {'size' : self.panel_size,  'position' : utils.cr((3*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        rc_scan = {'size' : self.panel_size,  'position' : utils.cr((4*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        echo = {'size' : self.panel_size,  'position' : utils.cr((5*self.panel_size['col'],  row + 1.1 *  self.panel_size['row']))}
        
        #== gui items ==        
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
        
        self.echo_button = QtGui.QPushButton('Echo MES',  self)
        self.echo_button.resize(echo['size']['col'],  echo['size']['row'])
        self.echo_button.move(echo['position']['col'],  echo['position']['row'])
        self.connect(self.echo_button, QtCore.SIGNAL('clicked()'),  self.echo)
        
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
        
    def init_files(self):
        self.acquire_camera_image_parameters = os.path.join(self.config.MAT_PATH, 'acquire_camera_image_parameters.mat').replace('/', '\\')
        self.acquire_z_stack_parameters = os.path.join(self.config.MAT_PATH, 'acquire_z_stack_parameters.mat')
        self.two_photon_parameters = os.path.join(self.config.MAT_PATH, 'two_photon_parameters.mat').replace('/', '\\')
        self.single_two_photon_parameters = os.path.join(self.config.MAT_PATH, 'single_two_photon_parameters.mat').replace('/', '\\')
        self.rc_scan_parameters = os.path.join(self.config.MAT_PATH, 'rc_scan_parameters.mat')
        
        #create hdf5io
        self.hdf5_path = utils.generate_filename(os.path.join(self.config.ARCHIVE_PATH, 'gui.hdf5'))
        self.hdf5_handler = hdf5io.Hdf5io(self.hdf5_path , config = self.config, caller = self)
        
#        Mat file handling
#        data = scipy.io.loadmat('test.mat')
#        data = {}
#        data['x'] = x
#        scipy.io.savemat('test.mat',data)

    def execute_experiment(self):
        print 'SOCexecute_experimentEOC{0}EOP'.format(self.experiment_config_input.toPlainText())
        
    def generate_id(self):
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
        experiment_class_name = 'tbd'
        experiment_config_name = 'tbd'
        #[mouse strain](b[birth date] i[injection date] [stagex] [stagey] [zpos])-r[i]-[data type]-[stim class name]-[stimcfgname]-[anesthesia]-[earpunch]
        id_text = '{0}(b{1}i{2}{3}{4}{5})-r{6}-{7}-{8}-{9}-{10}-{11}{12}' .format(
                                                                                   self.mouse_strain.currentText(),  
                                                                                   mouse_birth_date, 
                                                                                   gcamp_injection_date, 
                                                                                   stagex, stagey, stagez, 
                                                                                   i, data_type, 
                                                                                   experiment_class_name, experiment_config_name, 
                                                                                   self.anesthesia_protocol.currentText(), 
                                                                                   self.ear_punch_l.currentText(), self.ear_punch_r.currentText(), 
                                                                                   )
        self.hdf5_handler.id = id_text
        self.hdf5_handler.save('id')
        self.id.setText(id_text)        
        
    def acquire_camera_image(self):
        self.mes_command_queue.put('SOCacquire_camera_imageEOC{0}EOP' .format(self.acquire_camera_image_parameters))        
        
    def acquire_z_stack(self):
        self.mes_command_queue.put('SOCacquire_z_stackEOC{0}EOP' .format(self.acquire_z_stack_parameters))
        
    def two_photon_recording(self):
        self.mes_command_queue.put('SOCacquire_line_scanEOC{0}EOP'.format(self.two_photon_parameters))
        
    def single_two_photon_recording(self):
        self.mes_command_queue.put('SOCacquire_xy_imageEOC{0}EOP'.format(self.single_two_photon_parameters))

    def rc_scan(self):
        self.mes_command_queue.put('SOCrc_scanEOC{0}EOP'.format(self.rc_scan_parameters))
        
    def echo(self):
        self.mes_command_queue.put('SOCechoEOCguiEOP')
        
    def closeEvent(self, e):
        e.accept()
        self.mes_command_queue.put('SOCclose_connectionEOCEOP')
        self.hdf5_handler.close()
        time.sleep(1.0) #Enough time to close connection with MES
        self.mes_server.terminate()
        sys.exit(0)
        
class GuiConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        COORDINATE_SYSTEM='center'
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        MAT_PATH= unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1024, 768))
        self._create_parameters_from_locals(locals())
        
if __name__ == '__main__':
    config = GuiConfig()    
    app = Qt.QApplication(sys.argv)
    gui = Gui(config)
    app.exec_()
#TODO: send commands to visexpman
