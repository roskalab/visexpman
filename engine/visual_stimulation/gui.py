import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.utils as utils

################### New mouse widget #######################
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
        self.comments.setToolTip('Add comment')
        
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
        
class MouseFileGroupBox(QtGui.QGroupBox):
    '''
    The mouse file contains the parameters of the mouse and the scanning regions
    '''
    def __init__(self, parent, config):
        self.config = config
        QtGui.QGroupBox.__init__(self, 'mouse file', parent)                    
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):        
        self.new_mouse_file_button = QtGui.QPushButton('Create new mouse file',  self)
#        self.redefine_mouse_file_button = QtGui.QPushButton('Redefine mouse file',  self)
#        self.select_mouse_file_label = QtGui.QLabel('Mouse file',  self)
#        self.select_mouse_file = QtGui.QComboBox(self)
#        self.select_mouse_file.addItems(utils.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH, filter = 'gui')[-1])
#        self.select_mouse_file.setEditable(True)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.new_mouse_file_button, 0, 0, 1, 2)
#        self.layout.addWidget(self.redefine_mouse_file_button, 0, 2, 1, 2)
#        self.layout.addWidget(self.select_mouse_file_label, 1, 0)
#        self.layout.addWidget(self.select_mouse_file, 1, 1, 1, 3)
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
        self.mouse_file_groupbox = MouseFileGroupBox(self, self.config)
        self.master_position_groupbox = MasterPositionGroupBox(self)
        self.new_scan_region_groupbox = NewScanRegion(self, ['moving_dot', 'grating'])        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.animal_parameters_groupbox, 0, 0, 1, 2)
        self.layout.addWidget(self.mouse_file_groupbox, 0, 2, 1, 2)
        self.layout.addWidget(self.master_position_groupbox, 2, 0, 1, 3)
        self.layout.addWidget(self.new_scan_region_groupbox, 3, 0, 1, 3)        
#        self.layout.setRowStretch(3, 300)
        self.setLayout(self.layout)

################### Registered mouse widget #######################
class FindMasterPositionGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):        
        QtGui.QGroupBox.__init__(self, 'Find master position', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.z_stack_button = QtGui.QPushButton('Create Z stack',  self)        
        self.calculate_position_offset_button = QtGui.QPushButton('Calculate position offset',  self)
        self.position_offset_display = QtGui.QComboBox(self)
        self.position_offset_display.setEditable(True)
        self.move_mouse_button = QtGui.QPushButton('Move mouse',  self)
        self.save_master_position_button = QtGui.QPushButton('Save master position',  self)        
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.z_stack_button, 0, 1)
        self.layout.addWidget(self.calculate_position_offset_button, 0, 2)
        self.layout.addWidget(self.position_offset_display, 0, 3, 1, 1)
        self.layout.addWidget(self.move_mouse_button, 0, 4)
        self.layout.addWidget(self.save_master_position_button, 0, 5)
        self.setLayout(self.layout)
       
class FindScanRegion(QtGui.QGroupBox):
    def __init__(self, parent, experiment_names):
        QtGui.QGroupBox.__init__(self, 'Find scan region', parent)
        self.experiment_names = QtCore.QStringList(experiment_names)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.select_scan_region = QtGui.QComboBox(self)
        self.select_scan_region.setEditable(True)
        self.move_mouse_button = QtGui.QPushButton('Move mouse',  self)
        self.add_button = QtGui.QPushButton('Add new',  self)
        self.z_stack_button = QtGui.QPushButton('Create Z stack',  self)
        self.calculate_position_offset_button = QtGui.QPushButton('Calculate position offset',  self)
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(self.experiment_names)
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop experiment',  self)
        self.save_experiment_results_button = QtGui.QPushButton('Save experiment results',  self)
        self.save_region_info_button = QtGui.QPushButton('Save region info',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.select_scan_region, 0, 0)
        self.layout.addWidget(self.add_button, 0, 1)
        self.layout.addWidget(self.save_region_info_button, 0, 3)
        self.layout.addWidget(self.move_mouse_button, 0, 2, 2, 1)
        self.layout.addWidget(self.z_stack_button, 1, 0)
        self.layout.addWidget(self.calculate_position_offset_button, 1, 1)
        self.layout.addWidget(self.experiment_name, 2, 0)
        self.layout.addWidget(self.start_experiment_button, 2, 1)
        self.layout.addWidget(self.stop_experiment_button, 2, 2)
        self.layout.addWidget(self.save_experiment_results_button, 2, 3)       
        self.setLayout(self.layout)
       
class RegisteredMouseWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        
    def create_widgets(self):
        self.select_mouse_file_label = QtGui.QLabel('Select mouse file', self)
        self.select_mouse_file = QtGui.QComboBox(self)
        self.find_master_position_groupbox = FindMasterPositionGroupBox(self)
        self.find_scan_region = FindScanRegion(self, ['moving_dot', 'grating'])
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.select_mouse_file_label, 0, 0, 1, 1)
        self.layout.addWidget(self.select_mouse_file, 0, 1, 1, 1)
        self.layout.addWidget(self.find_master_position_groupbox, 1, 0, 1, 2)
        self.layout.addWidget(self.find_scan_region, 2, 0, 1, 3)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
################### Debug/helper widgets #######################
class DebugWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        
    def create_widgets(self):
        #MES related
        self.z_stack_button = QtGui.QPushButton('Create Z stack', self)
        self.line_scan_button = QtGui.QPushButton('Line scan', self)
        self.rc_scan_button = QtGui.QPushButton('RC scan point', self)
        self.rc_scan_point = QtGui.QComboBox(self)
        self.rc_scan_point.setEditable(True)
        #Stimulation/experiment control related
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList(['moving_dot', 'grating']))
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.stop_experiment_button = QtGui.QPushButton('Stop experiment',  self)
        #Stage related
        self.read_stage_button = QtGui.QPushButton('read stage', self)
        self.move_stage_button = QtGui.QPushButton('move stage', self)        
        #Network related
        self.network_connection_status_button = QtGui.QPushButton('Read network connection status',  self)
        self.server_debug_info_button = QtGui.QPushButton('Read server debug info',  self)        
        self.select_connection_list = QtGui.QComboBox(self)        
        self.select_connection_list.addItems(QtCore.QStringList(['','mes', 'stimulation', 'analysis']))
        self.send_command_button = QtGui.QPushButton('Send command',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.z_stack_button, 0, 0, 1, 1)
        self.layout.addWidget(self.line_scan_button, 0, 1, 1, 1)
        self.layout.addWidget(self.rc_scan_button, 0, 2, 1, 1)
        self.layout.addWidget(self.rc_scan_point, 0, 3, 1, 2)
        self.layout.addWidget(self.experiment_name, 1, 0, 1, 1)
        self.layout.addWidget(self.start_experiment_button, 1, 1, 1, 1)
        self.layout.addWidget(self.stop_experiment_button, 1, 2, 1, 1)
        self.layout.addWidget(self.read_stage_button, 2, 0, 1, 1)
        self.layout.addWidget(self.move_stage_button, 2, 1, 1, 1)
        self.layout.addWidget(self.network_connection_status_button, 3, 0, 1, 1)
        self.layout.addWidget(self.server_debug_info_button, 3, 1, 1, 1)
        self.layout.addWidget(self.select_connection_list, 3, 2, 1, 1)
        self.layout.addWidget(self.send_command_button, 3, 3, 1, 1)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)
        
class StandardIOWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.GUI_SIZE['col'], 0.5*self.config.GUI_SIZE['row'])
        
    def create_widgets(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        self.text_in = QtGui.QTextEdit(self)
        self.text_in.setToolTip('self.printc()')
        
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        self.clear_console_button = QtGui.QPushButton('Clear console',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.text_out, 0, 0, 3, 3)
        self.layout.addWidget(self.text_in, 1, 3, 1, 2)
        self.layout.addWidget(self.execute_python_button, 0, 3, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.clear_console_button, 0, 4, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.setRowStretch(300, 300)
        self.layout.setColumnStretch(0, 100)
        self.setLayout(self.layout)
        
if __name__ == '__main__':
    pass
    
