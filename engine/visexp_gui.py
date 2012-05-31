import sys
import os
import time
import socket
import Queue
import os.path
import tempfile
import Image
import numpy
import shutil
import traceback
import re
import cPickle as pickle
import unittest
import ImageDraw
import ImageFont

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpA.engine.datadisplay import imaged
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine import generic
from visexpman.engine.generic import log
from visexpman.users.zoltan.test import unit_test_runner
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.dataprocessors import generic as generic_visexpA

parameter_extract = re.compile('EOC(.+)EOP')

################### Main widget #######################
class VisionExperimentGui(QtGui.QWidget):
    def __init__(self, user, config_class):
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig)[0][1]()
        self.config.user = user
        self.console_text = ''
        self.log = log.Log('gui log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'gui_log.txt')), local_saving = True) 
        self.poller = gui.Poller(self)
        self.queues = self.poller.queues
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI - {0} - {1}' .format(user,  config_class))
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        self.create_layout()
        self.connect_signals()
        self.init_variables()
        self.poller.start()
        self.show()
        self.poller.init_job()
        
    def create_gui(self):
        self.main_widget = gui.MainWidget(self, self.config)
        self.animal_parameters_widget = gui.AnimalParametersWidget(self, self.config)
        self.images_widget = gui.ImagesWidget(self, self.config)
        self.overview_widget = gui.OverviewWidget(self, self.config)
        self.roi_widget = gui.RoiWidget(self, self.config)
        self.helpers_widget = gui.HelpersWidget(self, self.config)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Main')
        self.main_tab.addTab(self.roi_widget, 'ROI')
        self.main_tab.addTab(self.animal_parameters_widget, 'Animal parameters')
        self.main_tab.addTab(self.helpers_widget, 'Helpers')
        self.main_tab.setCurrentIndex(0)
        #Image tab
        self.image_tab = QtGui.QTabWidget(self)
        self.image_tab.addTab(self.images_widget, 'Regions')
        self.image_tab.addTab(self.overview_widget, 'Overview')
        self.standard_io_widget = gui.StandardIOWidget(self, self.config)
        experiment_config_list = utils.fetch_classes('visexpman.users.' + self.config.user,  required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig)
        experiment_config_names = []
        for experiment_config in experiment_config_list:
            experiment_config_names.append(experiment_config[1].__name__)
        self.main_widget.experiment_control_groupbox.experiment_name.addItems(QtCore.QStringList(experiment_config_names))
        self.main_widget.experiment_control_groupbox.experiment_name.setCurrentIndex(experiment_config_names.index('ShortMovingGratingConfig'))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.main_tab, 0, 0, 1, 1)
        self.layout.addWidget(self.standard_io_widget, 1, 0, 1, 1)
        self.layout.addWidget(self.image_tab, 0, 1, 2, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(2, 1)
        self.setLayout(self.layout)
        
    def init_variables(self):
        self.mouse_files = []
        
    def periodic_gui_update(self):
        #Check for new mouse files
        if self.update_mouse_files_combobox():
            self.update_region_names_combobox()
            self.update_scan_regions()
        
    ####### Signals/functions ###############
    def connect_signals(self):
        #Poller control
        self.connect(self, QtCore.SIGNAL('abort'), self.poller.abort_poller)
        #GUI events
        self.connect(self.main_widget.scan_region_groupbox.select_mouse_file, QtCore.SIGNAL('currentIndexChanged(int)'),  self.mouse_file_changed)
        self.connect(self.main_widget.scan_region_groupbox.scan_regions_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.region_name_changed)
        
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.animal_parameters_widget.new_mouse_file_button, 'save_animal_parameters')
        #Experiment control
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.stop_experiment_button, 'stop_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.graceful_stop_experiment_button, 'graceful_stop_experiment')
        #Data processing
        self.connect_and_map_signal(self.main_widget.run_fragment_process_button, 'run_fragment_process')
        self.connect_and_map_signal(self.main_widget.show_fragment_process_status_button, 'show_fragment_process_status')
        #ROI
        self.connect(self.roi_widget.next_button, QtCore.SIGNAL('clicked()'),  self.tbd)
        self.connect(self.roi_widget.select_cell_button, QtCore.SIGNAL('clicked()'),  self.tbd)
        self.connect(self.roi_widget.skip_cell_button, QtCore.SIGNAL('clicked()'),  self.tbd)
        self.connect(self.roi_widget.previous_button, QtCore.SIGNAL('clicked()'),  self.tbd)
        self.connect(self.roi_widget.select_measurement_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.tbd)
        #Network debugger tools
        self.connect_and_map_signal(self.helpers_widget.show_connected_clients_button, 'show_connected_clients')
        self.connect_and_map_signal(self.helpers_widget.show_network_messages_button, 'show_network_messages')
        self.connect_and_map_signal(self.helpers_widget.send_command_button, 'send_command')
        #Helpers
        self.connect_and_map_signal(self.helpers_widget.help_button, 'show_help')
        self.connect(self.helpers_widget.save_xy_scan_button, QtCore.SIGNAL('clicked()'),  self.poller.save_xy_scan)
        self.connect(self.standard_io_widget.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        self.connect(self.standard_io_widget.clear_console_button, QtCore.SIGNAL('clicked()'),  self.clear_console)
        #Blocking functions, run by poller
        self.connect_and_map_signal(self.main_widget.read_stage_button, 'read_stage')
        self.connect_and_map_signal(self.main_widget.set_stage_origin_button, 'set_stage_origin')
        self.connect_and_map_signal(self.main_widget.move_stage_button, 'move_stage')
        self.connect_and_map_signal(self.main_widget.stop_stage_button, 'stop_stage')
        self.connect_and_map_signal(self.main_widget.set_objective_button, 'set_objective')
#        self.connect_and_map_signal(self.main_widget.set_objective_value_button, 'set_objective_relative_value')
        self.connect_and_map_signal(self.main_widget.z_stack_button, 'acquire_z_stack')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.get_xy_scan_button, 'acquire_xy_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.xz_scan_button, 'acquire_xz_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.add_button, 'add_scan_region')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.remove_button, 'remove_scan_region')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.move_to_button, 'move_to_region')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.create_xz_lines_button, 'create_xz_lines')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.start_experiment_button, 'start_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.next_depth_button, 'next_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.redo_depth_button, 'redo_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.previous_depth_button, 'previous_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.identify_flourescence_intensity_distribution_button, 'identify_flourescence_intensity_distribution')
        #connect mapped signals to poller's pass_signal method that forwards the signal IDs.
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        if hasattr(self.poller, mapped_signal_parameter):
            self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
            getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
        else:
            self.printc('{0} method does not exists'.format(mapped_signal_parameter))
            
    ############ GUI events ############
    def mouse_file_changed(self):
        #Update mouse file path and animal parameters
        self.poller.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.main_widget.scan_region_groupbox.select_mouse_file.currentText()))
        if os.path.isfile(self.poller.mouse_file):
            self.poller.set_mouse_file()
            h = hdf5io.Hdf5io(self.poller.mouse_file)
            varname = h.find_variable_in_h5f('animal_parameters', regexp=True)[0]
            h.load(varname)
            self.poller.animal_parameters = getattr(h, varname)
            h.close()
            self.update_animal_parameter_display()
            
    def region_name_changed(self):
        self.update_scan_regions()
        
    ################### GUI updaters #################
    def update_mouse_files_combobox(self, set_to_value = None):
        new_mouse_files = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH,  'mouse')
        new_mouse_files = [mouse_file for mouse_file in new_mouse_files if '_copy' not in mouse_file]
        if self.mouse_files != new_mouse_files:
            self.mouse_files = new_mouse_files
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.select_mouse_file, self.mouse_files)
            if set_to_value != None:
                self.main_widget.scan_region_groupbox.select_mouse_file.setCurrentIndex(self.mouse_files.index(set_to_value))
            return True
                
    def update_position_display(self):
        display_position = numpy.round(self.poller.stage_position - self.poller.stage_origin, 2)
        if hasattr(self.poller, 'objective_position'):
            display_position[-1] = self.poller.objective_position
        self.main_widget.current_position_label.setText('{0:.2f}, {1:.2f}, {2:.2f}' .format(display_position[0], display_position[1], display_position[2]))
        
    def update_animal_parameter_display(self):
        if hasattr(self.poller, 'animal_parameters'):
            animal_parameters = self.poller.animal_parameters
            self.animal_parameters_str = '{2}, birth date: {0}, injection date: {1}, punch lr: {3},{4}, {5}, {6}'\
            .format(animal_parameters['mouse_birth_date'], animal_parameters['gcamp_injection_date'], animal_parameters['strain'], 
                    animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], animal_parameters['gender'],  animal_parameters['anesthesia_protocol'])
            self.main_widget.scan_region_groupbox.animal_parameters_label.setText(self.animal_parameters_str)
            
    def update_region_names_combobox(self, selected_region = None):
        #Update combobox containing scan region names
        if hasattr(self.poller.scan_regions, 'keys'):
            region_names = self.poller.scan_regions.keys()
            region_names.sort()
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.scan_regions_combobox, region_names, selected_item = selected_region)
        
    def update_scan_regions(self, selected_region = None):
        if selected_region == None:
            selected_region = self.get_current_region_name()
        no_scale = utils.rc((1.0, 1.0))
        if utils.safe_has_key(self.poller.scan_regions, selected_region):
            scan_regions = self.poller.scan_regions
            line = []
            #Update xz image if exists and collect xy line(s)
            if scan_regions[selected_region].has_key('xz'):
                line = [[ scan_regions[selected_region]['xz']['p1']['col'] ,  scan_regions[selected_region]['xz']['p1']['row'] , 
                             scan_regions[selected_region]['xz']['p2']['col'] ,  scan_regions[selected_region]['xz']['p2']['row'] ]]
                self.show_image(scan_regions[selected_region]['xz']['scaled_image'], 3,
                                     scan_regions[selected_region]['xz']['scaled_scale'], 
                                     origin = scan_regions[selected_region]['xz']['origin'])
            else:
                self.show_image(self.images_widget.blank_image, 3, no_scale)
            #Display xy image
            image_to_display = scan_regions[selected_region]['xy']
            self.show_image(image_to_display['image'], 1, image_to_display['scale'], line = line, origin = image_to_display['origin'])
            #update overwiew
            image, scale = imaged.merge_brain_regions(scan_regions, region_on_top = selected_region)
            self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
            #Update region info
            if scan_regions[selected_region].has_key('add_date'):
                region_add_date = scan_regions[selected_region]['add_date']
            else:
                region_add_date = 'unknown'
            self.main_widget.scan_region_groupbox.region_info.setText(\
                                                                           '{3}\n{0:.2f}, {1:.2f}, {2:.2f}' \
                                                                           .format(scan_regions[selected_region]['position']['x'][0], 
                                                                                   scan_regions[selected_region]['position']['y'][0], 
                                                                                   scan_regions[selected_region]['position']['z'][0], 
                                                                                   region_add_date))
        else:
                self.show_image(self.images_widget.blank_image, 1, no_scale)
                self.show_image(self.images_widget.blank_image, 3, no_scale)
                self.show_image(self.images_widget.blank_image, 'overview', no_scale)
                self.main_widget.scan_region_groupbox.region_info.setText('')
    
    def show_image(self, image, channel, scale, line = [], origin = None):
        if origin != None:
            division = numpy.round(min(image.shape) *  scale['row']/ 5.0, -1)
        else:
            division = 0
        image_in = {}
        image_in['image'] = image
        image_in['scale'] = scale
        image_in['origin'] = origin
        if channel == 'overview':
            image_with_sidebar = generate_gui_image(image_in, self.config.OVERVIEW_IMAGE_SIZE, self.config, lines  = line, sidebar_division = division)
            self.overview_widget.image_display.setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.OVERVIEW_IMAGE_SIZE))
            self.overview_widget.image_display.image = image_with_sidebar
            self.overview_widget.image_display.raw_image = image
            self.overview_widget.image_display.scale = scale
        elif channel == 'roi_curve':
            self.roi_widget.roi_info_image_display.setPixmap(imaged.array_to_qpixmap(image, self.config.ROI_INFO_IMAGE_SIZE))
            self.roi_widget.roi_info_image_display.image = image
            self.roi_widget.roi_info_image_display.raw_image = image
            self.roi_widget.roi_info_image_display.scale = scale
        else:
            image_with_sidebar = generate_gui_image(image_in, self.config.IMAGE_SIZE, self.config, lines  = line, sidebar_division = division)
            self.images_widget.image_display[channel].setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.IMAGE_SIZE))
            self.images_widget.image_display[channel].image = image_with_sidebar
            self.images_widget.image_display[channel].raw_image = image
            self.images_widget.image_display[channel].scale = scale
        
    def update_combo_box_list(self, widget, new_list,  selected_item = None):
        current_value = widget.currentText()
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
        items_list = QtCore.QStringList(new_list)
        widget.clear()
        widget.addItems(QtCore.QStringList(new_list))
        if selected_item != None and selected_item in new_list:
            widget.setCurrentIndex(new_list.index(selected_item))
        else:
            widget.setCurrentIndex(current_index)
            
    ######## GUI widget readers ###############
    def get_current_region_name(self):
        return str(self.main_widget.scan_region_groupbox.scan_regions_combobox.currentText())
        
    def update_current_mouse_path(self):
        self.poller.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.main_widget.scan_region_groupbox.select_mouse_file.currentText()))
            
    ########## GUI utilities, misc functions #############
    def show_verify_add_region_messagebox(self):
        utils.empty_queue(self.poller.gui_thread_queue)
        reply = QtGui.QMessageBox.question(self, 'Are you sure that line scan is set back to xy?', "Do you want to continue?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            self.poller.gui_thread_queue.put(False)
        else:
            self.poller.gui_thread_queue.put(True)
            
    def show_overwrite_region_messagebox(self):
        utils.empty_queue(self.poller.gui_thread_queue)
        reply = QtGui.QMessageBox.question(self, 'Overwriting scan region', "Do you want to overwrite scan region?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            self.poller.gui_thread_queue.put(False)
        else:
            self.poller.gui_thread_queue.put(True)
            
    def tbd(self):
        pass
            
    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        try:
            self.log.info(text)
        except:
            print 'gui: logging error'

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())

    def closeEvent(self, e):
        e.accept()
        self.log.copy()
        self.emit(QtCore.SIGNAL('abort'))
        #delete files:
        for file_path in self.poller.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        time.sleep(5.0) #Enough time to close network connections
        sys.exit(0)
        
class VisionExperimentGui1(QtGui.QWidget):

    def new_mouse_file_selected(self, index):
        '''
        Selected mouse file changed
        '''
        self.poller.stage_origin_set = False
        self.update_animal_parameter_display()
        self.update_scan_regions_groupbox()
        self.poller.set_roi_file()
        
    def new_scan_region_selected(self, index):
        self.update_scan_regions_groupbox()
        
    def selected_measurement_changed(self, index):
        self.cell_index = 0
        
    def select_next_roi(self, select = None):
        self.cell_index += 1
        self.register_roi_selection(select)
        
    def select_prev_roi(self):
        self.cell_index -= 1
        self.register_roi_selection(None)
            
    def select_cell(self):
        self.select_next_roi(select=True)
        
    def skip_cell(self):
        self.select_next_roi(select=False)
        
    def register_roi_selection(self, select):
        if hasattr(self.poller, 'animal_parameters'):
            roi_file_full_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.poller.generate_animal_filename('rois', self.poller.animal_parameters))
            if os.path.exists(roi_file_full_path):
                rois = hdf5io.read_item(roi_file_full_path, 'rois', safe=True)
            mouse_file = self.poller.generate_animal_filename('mouse', self.poller.animal_parameters)
            mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH,  mouse_file)
            if not os.path.exists(mouse_file):
                return
            else:
                h = hdf5io.Hdf5io(mouse_file)
                selected_rois = h.findvar('selected_rois')
                if selected_rois == None:
                    selected_rois = {}
            region_name = self.get_current_region_name()
            if not selected_rois.has_key(region_name):
                selected_rois[region_name] = {}
            measurement_id = str(self.select_roi_widget.select_measurement_combobox.currentText()).split('um/')[1]
            if not selected_rois[region_name].has_key(measurement_id):
                selected_rois[region_name][measurement_id] = numpy.cast['bool'](numpy.zeros(len(rois[region_name][measurement_id]['soma_rois'])))
            if self.cell_index < 0 or self.cell_index > selected_rois[region_name][measurement_id].shape[0]:
                self.cell_index = 0
            if select is not None:
                selected_rois[region_name][measurement_id][self.cell_index-1] = select
            h.selected_rois = selected_rois
            h.save('selected_rois', overwrite = True)
            h.close()
            self.printc('Loading image...')
            self.update_roi_info(rois, selected_rois)

    def save_animal_parameters(self):
        '''
        Saves the following parameters of a mouse:
        - birth date
        - gcamp injection date
        - anesthesia protocol
        - ear punch infos
        - strain
        - user comments

        The hdf5 file is closed.
        '''
        if self.realignment_tab.currentIndex() == 0:
            widget = self.debug_widget
        
        mouse_birth_date = widget.animal_parameters_groupbox.mouse_birth_date.date()
        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = widget.animal_parameters_groupbox.gcamp_injection_date.date()
        gcamp_injection_date = '{0}-{1}-{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())                

        animal_parameters = {
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'anesthesia_protocol' : str(widget.animal_parameters_groupbox.anesthesia_protocol.currentText()),
            'gender' : str(widget.animal_parameters_groupbox.gender.currentText()),
            'ear_punch_l' : str(widget.animal_parameters_groupbox.ear_punch_l.currentText()), 
            'ear_punch_r' : str(widget.animal_parameters_groupbox.ear_punch_r.currentText()),
            'strain' : str(widget.animal_parameters_groupbox.mouse_strain.currentText()),
            'comments' : str(widget.animal_parameters_groupbox.comments.currentText()),
        }        
        name = '{0}_{1}_{2}_{3}_{4}' .format(animal_parameters['strain'], animal_parameters['mouse_birth_date'] , animal_parameters['gcamp_injection_date'], \
                                         animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'])

        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.poller.generate_animal_filename('mouse', animal_parameters))
        
        if os.path.exists(mouse_file_path):
            self.printc('Animal parameter file already exists')
        else:
            self.poller.animal_parameters = animal_parameters
            self.hdf5_handler = hdf5io.Hdf5io(mouse_file_path)
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))        
            setattr(self.hdf5_handler,  variable_name, animal_parameters)
            self.hdf5_handler.save(variable_name)
            self.printc('Animal parameters saved')
            self.hdf5_handler.close()
            #set selected mouse file to this one
            self.update_mouse_files_combobox(set_to_value = os.path.split(mouse_file_path)[-1])
            #Clear image displays showing regions
            self.images_widget.clear_image_display(1)
            self.images_widget.clear_image_display(3)
            
    def update_mouse_files_combobox(self, set_to_value = None):
        new_mouse_files = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH,  'mouse')
        if self.mouse_files != new_mouse_files:
            self.mouse_files = new_mouse_files
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.select_mouse_file, self.mouse_files)
            if set_to_value != None:
                self.main_widget.scan_region_groupbox.select_mouse_file.setCurrentIndex(self.mouse_files.index(set_to_value))
                
    def periodic_gui_update(self):
        self.update_mouse_files_combobox()
        
    def update_scan_regions_groupbox(self):
        scan_regions = hdf5io.read_item(self.selected_mouse_file, 'scan_regions')
        displayable_region_names = []
        if scan_regions is None:
            return
        for region in scan_regions.keys():
            displayable_region_names.append(region)
        displayable_region_names.sort()
        self.update_combo_box_list(self.debug_widget.scan_region_groupbox.scan_regions_combobox, displayable_region_names)
        #Display image of selected region
        selected_region = self.get_current_region_name()
        if hasattr(scan_regions, 'has_key'):
            if scan_regions.has_key(selected_region):
                line = []
                if scan_regions[selected_region].has_key('vertical_section'):
                    line = [[ scan_regions[selected_region]['vertical_section']['p1']['col'] ,  scan_regions[selected_region]['vertical_section']['p1']['row'] , 
                             scan_regions[selected_region]['vertical_section']['p2']['col'] ,  scan_regions[selected_region]['vertical_section']['p2']['row'] ]]
                    self.show_image(scan_regions[selected_region]['vertical_section']['scaled_image'], 3,
                                     scan_regions[selected_region]['vertical_section']['scaled_scale'], 
                                     origin = scan_regions[selected_region]['vertical_section']['origin'])
                else:
                    no_scale = utils.rc((1.0, 1.0))
                    self.show_image(self.images_widget.blank_image, 3, no_scale)
                image_to_display = scan_regions[selected_region]['brain_surface']
                self.show_image(image_to_display['image'], 1, image_to_display['scale'], line = line, origin = image_to_display['origin'])
                #update overwiew
                image, scale = imaged.merge_brain_regions(scan_regions, region_on_top = selected_region)
                self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
                if scan_regions[selected_region].has_key('add_date'):
                    region_add_date = scan_regions[selected_region]['add_date']
                else:
                    region_add_date = 'unknown'
                self.debug_widget.scan_region_groupbox.region_info.setText(\
                                                                           '{3}\n{0:.2f}, {1:.2f}, {2:.2f}' \
                                                                           .format(scan_regions[selected_region]['position']['x'][0], 
                                                                                   scan_regions[selected_region]['position']['y'][0], 
                                                                                   scan_regions[selected_region]['position']['z'][0], 
                                                                                   region_add_date))
            else:
                no_scale = utils.rc((1.0, 1.0))
                self.show_image(self.images_widget.blank_image, 1, no_scale)
                self.show_image(self.images_widget.blank_image, 3, no_scale)
                self.show_image(self.images_widget.blank_image, 'overview', no_scale)
                self.debug_widget.scan_region_groupbox.region_info.setText('')
        

    def update_gui_items(self, index = 0, active_region = None):
        '''
        Update comboboxes with file lists
        '''
        self.update_roi_info()
        if self.realignment_tab.currentIndex() == 1:#No GUI update if Select Roi tab used
            return
        self.update_mouse_files_combobox()
        selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
        mouse_file_full_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file)
        scan_regions = hdf5io.read_item(mouse_file_full_path, 'scan_regions')
        if scan_regions == None:
            scan_regions = {}
        #is mouse file changed recently?
        if not hasattr(self, 'mouse_file_last_change_time'):
            self.mouse_file_last_change_time = 0
        mouse_file_last_change_time = os.stat(mouse_file_full_path).st_mtime
        if mouse_file_last_change_time != self.mouse_file_last_change_time:
            self.mouse_file_last_change_time = mouse_file_last_change_time
            displayable_region_names = []
            for region in scan_regions.keys():
                    displayable_region_names.append(region)
            displayable_region_names.sort()
            self.update_combo_box_list(self.debug_widget.scan_region_groupbox.scan_regions_combobox, displayable_region_names,  selected_item = active_region)
            mouse_file_changed = True
        else:
            mouse_file_changed = False    
        self.poller.scan_regions = scan_regions
        #Display image of selected region
        selected_region = self.get_current_region_name()
        if hasattr(scan_regions, 'has_key'):
            if scan_regions.has_key(selected_region):
                line = []
                if scan_regions[selected_region].has_key('vertical_section'):
                    line = [[ scan_regions[selected_region]['vertical_section']['p1']['col'] ,  scan_regions[selected_region]['vertical_section']['p1']['row'] , 
                             scan_regions[selected_region]['vertical_section']['p2']['col'] ,  scan_regions[selected_region]['vertical_section']['p2']['row'] ]]
                    self.show_image(scan_regions[selected_region]['vertical_section']['scaled_image'], 3,
                                     scan_regions[selected_region]['vertical_section']['scaled_scale'], 
                                     origin = scan_regions[selected_region]['vertical_section']['origin'])
                else:
                    no_scale = utils.rc((1.0, 1.0))
                    self.show_image(self.images_widget.blank_image, 3, no_scale)
                image_to_display = scan_regions[selected_region]['brain_surface']
                self.show_image(image_to_display['image'], 1, image_to_display['scale'], line = line, origin = image_to_display['origin'])
                #update overwiew
                image, scale = imaged.merge_brain_regions(scan_regions, region_on_top = selected_region)
                self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
            else:
                no_scale = utils.rc((1.0, 1.0))
                self.show_image(self.images_widget.blank_image, 1, no_scale)
                self.show_image(self.images_widget.blank_image, 3, no_scale)
                self.show_image(self.images_widget.blank_image, 'overview', no_scale)
        #Display coordinates of selected region
        if scan_regions.has_key(selected_region):
            if scan_regions[selected_region].has_key('add_date'):
                region_add_date = scan_regions[selected_region]['add_date']
            else:
                region_add_date = 'unknown'
            self.debug_widget.scan_region_groupbox.region_info.setText(\
                                                                           '{3}\n{0:.2f}, {1:.2f}, {2:.2f}' \
                                                                           .format(scan_regions[selected_region]['position']['x'][0], 
                                                                                   scan_regions[selected_region]['position']['y'][0], 
                                                                                   scan_regions[selected_region]['position']['z'][0], 
                                                                                   region_add_date))
        else:
            self.debug_widget.scan_region_groupbox.region_info.setText('')
        

    def update_roi_info(self, rois = None, selected_rois = None):
        '''
        rois,selected_rois -  if provided, not read from file
        '''
        if hasattr(self.poller, 'animal_parameters'):
            roi_file_full_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.poller.generate_animal_filename('rois', self.poller.animal_parameters))
            mouse_file_full_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.poller.generate_animal_filename('mouse', self.poller.animal_parameters))
            if os.path.exists(roi_file_full_path):
                if rois == None:
                    rois = hdf5io.read_item(roi_file_full_path, 'rois', safe=True)
                selected_region = self.get_current_region_name()
                if utils.safe_has_key(rois, selected_region):
                    #Update scan regions groupbox with roi info/processing state
                    roi = rois[selected_region]
                    info = '{0} file(s); id, depth, status, n cells, n pixels: '.format(len(roi.keys()))
                    row = 0
                    ids = roi.keys()
                    ids.sort()
                    id_labels = []
                    for i in range(len(roi.keys())):
                        id = ids[i]
                        if roi[id].has_key('cell_locations'):
                            n_cells = roi[id]['cell_locations'].shape[0]
                        else:
                            n_cells = 0
                        responding_pixels = 0
                        if roi[id].has_key('soma_rois'):
                            for soma_roi in roi[id]['soma_rois']:
                                responding_pixels +=  soma_roi.shape[0]
                        if roi[id].has_key('depth'):
                            depth = roi[id]['depth'][0]
                        else:
                            depth = 0
                        if roi[id].has_key('measurement_only'):
                            measurement_only = int(roi[id]['measurement_only'])
                        else:
                            measurement_only = 'x'
                        if measurement_only == False:
                            id_labels.append('{0}um/{1}'.format(depth, id))
                        info +='{0}, {6}, {1}{2}{3}{7}, {4}/{5};  '.format(id, int(roi[id]['fragment_check_ready']), int(roi[id]['mesextractor_ready']), int(roi[id]['find_cells_ready']), n_cells, responding_pixels,  depth, measurement_only)
                        if i%2==0:
                            info += '\n'
                    self.debug_widget.scan_region_groupbox.cell_info_label.setText(info)
                    #Update Select roi tab
                    id_labels.sort()
                    if (not hasattr(self, 'id_labels') or len(id_labels) != len(self.id_labels)):
                        self.update_combo_box_list(self.select_roi_widget.select_measurement_combobox, id_labels)
                        self.id_labels = id_labels
                    current_measurement_id  = str(self.select_roi_widget.select_measurement_combobox.currentText()).split('um/')[1]
                    if roi[current_measurement_id].has_key('roi_curves_info'):
                        roi_curve = roi[current_measurement_id]['roi_curves_info'][self.cell_index,:,:self.config.ROI_CURVE_IMAGE_CUTOUT,:][::3, ::3]
                    if selected_rois == None:
                        selected_rois = hdf5io.read_item(mouse_file_full_path, 'selected_rois')
                    if not selected_rois[selected_region].has_key(current_measurement_id):
                        selected_rois[selected_region][current_measurement_id] = numpy.cast['bool'](numpy.zeros(len(rois[selected_region][current_measurement_id]['soma_rois'])))
                    if selected_rois is not None and not selected_rois[selected_region][current_measurement_id][self.cell_index]:
                        line_indexes = numpy.arange(0, min(roi_curve.shape[0], roi_curve.shape[1]))
                        line_indexes = numpy.array([line_indexes, line_indexes])
                        roi_curve[line_indexes,line_indexes] = 0
                        enabled_cells = numpy.cast['int'](selected_rois[selected_region][current_measurement_id])
                    else:
                        enabled_cells = ''
                    self.show_image(roi_curve, 'roi_curve', utils.rc((1, 1)))
                    self.select_roi_widget.cell_id_display_label.setText('{0}   {1}' .format(self.cell_index, enabled_cells))
            else:
                self.debug_widget.scan_region_groupbox.cell_info_label.setText('')
                self.select_roi_widget.cell_id_display_label.setText('')
                self.update_combo_box_list(self.select_roi_widget.select_measurement_combobox, [])
                self.show_image(self.images_widget.blank_image, 'roi_curve', utils.rc((1, 1)))

    def update_animal_parameter_display(self):
        mouse_file = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
        self.selected_mouse_file  = os.path.join(self.config.EXPERIMENT_DATA_PATH, mouse_file)
        if os.path.exists(self.selected_mouse_file) and '.hdf5' in self.selected_mouse_file:
            h = hdf5io.Hdf5io(self.selected_mouse_file)
            varname = h.find_variable_in_h5f('animal_parameters', regexp=True)[0]
            h.load(varname)
            animal_parameters = getattr(h, varname)
            self.animal_parameters_str = '{2}, birth date: {0}, injection date: {1}, punch lr: {3},{4}, {5}, {6}'\
            .format(animal_parameters['mouse_birth_date'], animal_parameters['gcamp_injection_date'], animal_parameters['strain'], 
                    animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], animal_parameters['gender'],  animal_parameters['anesthesia_protocol'])
            h.close()
            self.debug_widget.scan_region_groupbox.animal_parameters_label.setText(self.animal_parameters_str)
            self.poller.animal_parameters = animal_parameters
            
    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        
    ####### Helpers ###############
    
    def show_image(self, image, channel, scale, line = [], origin = None):
        if origin != None:
            division = numpy.round(min(image.shape) *  scale['row']/ 5.0, -1)
        else:
            division = 0
        image_in = {}
        image_in['image'] = image
        image_in['scale'] = scale
        image_in['origin'] = origin
        if channel == 'overview':
            image_with_sidebar = generate_gui_image(image_in, self.config.OVERVIEW_IMAGE_SIZE, self.config, lines  = line, sidebar_division = division)
            self.overview_widget.image_display.setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.OVERVIEW_IMAGE_SIZE))
            self.overview_widget.image_display.image = image_with_sidebar
            self.overview_widget.image_display.raw_image = image
            self.overview_widget.image_display.scale = scale
        elif channel == 'roi_curve':
            self.select_roi_widget.roi_info_image_display.setPixmap(imaged.array_to_qpixmap(image, self.config.ROI_INFO_IMAGE_SIZE))
            self.select_roi_widget.roi_info_image_display.image = image
            self.select_roi_widget.roi_info_image_display.raw_image = image
            self.select_roi_widget.roi_info_image_display.scale = scale
        else:
            image_with_sidebar = generate_gui_image(image_in, self.config.IMAGE_SIZE, self.config, lines  = line, sidebar_division = division)
            self.regions_images_widget.image_display[channel].setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.IMAGE_SIZE))
            self.regions_images_widget.image_display[channel].image = image_with_sidebar
            self.regions_images_widget.image_display[channel].raw_image = image
            self.regions_images_widget.image_display[channel].scale = scale
        
    
            
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        try:
            self.log.info(text)
        except:
            print 'gui: logging error'

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())
        
    def update_combo_box_list(self, widget, new_list,  selected_item = None):
        current_value = widget.currentText()
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
        items_list = QtCore.QStringList(new_list)
        widget.clear()
        widget.addItems(QtCore.QStringList(new_list))
        if selected_item != None and selected_item in new_list:
            widget.setCurrentIndex(new_list.index(selected_item))
        else:
            widget.setCurrentIndex(current_index)
        
    def get_current_region_name(self):
        return str(self.debug_widget.scan_region_groupbox.scan_regions_combobox.currentText())
        
    def show_overwrite_region_messagebox(self):
        utils.empty_queue(self.poller.gui_thread_queue)
        reply = QtGui.QMessageBox.question(self, 'Overwriting scan region', "Do you want to overwrite scan region?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            self.poller.gui_thread_queue.put(False)
        else:
            self.poller.gui_thread_queue.put(True)

    def closeEvent(self, e):
        e.accept()
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.log.copy()
        self.emit(QtCore.SIGNAL('abort'))
        #delete files:
        for file_path in self.poller.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)        
        self.command_relay_server.shutdown_servers()            
        time.sleep(2.0) #Enough time to close network connections
        sys.exit(0)
        
def generate_gui_image(images, size, config, lines  = [], sidebar_division = 0):
    '''
    Combine images with widgets like lines, sidebars. 
    
    Inputs:
    images: images to display. These will be overlaid using coloring, scaling and origin information.
    size: size of output image in pixels in row, col format
    lines: lines to draw on images, containing line endpoints in um
    sidebar_division: the size of divisions on the sidebar
    
    config: the following parameters are expected: 
                                LINE_WIDTH, LINE_COLOR
                                SIDEBAR_COLOR, SIDEBAR_SIZE

    Ouput: image_to_display
    '''
    out_image = 255*numpy.ones((size['row'], size['col'], 3), dtype = numpy.uint8)
    if not isinstance(images,  list):
        images = [images]
    if len(images) == 1:
        merged_image = images[0]
    else:
        #here the images are merged: 1. merge with coloring different layers, 2. merge without coloring
        pass
    image_area = utils.rc_add(size,  utils.cr((2*config.SIDEBAR_SIZE, 2*config.SIDEBAR_SIZE)), '-')
    #calculate scaling factor for rescaling image to required image size
    rescale = (numpy.cast['float64'](utils.nd(image_area)) / merged_image['image'].shape).min()
    rescaled_image = generic.rescale_numpy_array_image(merged_image['image'], rescale)
    #Draw lines
    image_with_line = numpy.array([rescaled_image, rescaled_image, rescaled_image])
    image_with_line = numpy.rollaxis(image_with_line, 0, 3)
    for line in lines:
        #Line: x1,y1,x2, y2 - x - col, y = row
        #Considering MES/Image origin
        line_in_pixel  = [(line[0] - merged_image['origin']['col'])/merged_image['scale']['col'],
                            (-line[1] + merged_image['origin']['row'])/merged_image['scale']['row'],
                            (line[2] - merged_image['origin']['col'])/merged_image['scale']['col'],
                            (-line[3] + merged_image['origin']['row'])/merged_image['scale']['row']]
        line_in_pixel = (numpy.cast['int32'](numpy.array(line_in_pixel)*rescale)).tolist()
        image_with_line = generic.draw_line_numpy_array(image_with_line, line_in_pixel)
    #create sidebar
    if sidebar_division != 0:
        image_with_sidebar = draw_scalebar(image_with_line, merged_image['origin'], utils.rc_multiply_with_constant(merged_image['scale'], 1.0/rescale), sidebar_division, frame_size = config.SIDEBAR_SIZE)
    else:
        image_with_sidebar = image_with_line
    out_image[0:image_with_sidebar.shape[0], 0:image_with_sidebar.shape[1], :] = image_with_sidebar
    return out_image

def draw_scalebar(image, origin, scale, division, frame_size = None, fill = (0, 0, 0),  mes = True):
    if frame_size == None:
        frame_size = 0.05 * min(image.shape)
    if not isinstance(scale,  numpy.ndarray) and not isinstance(scale,  numpy.void):
        scale = utils.rc((scale, scale))
    #Scale = unit (um) per pixel
    frame_color = 255
    fontsize = int(frame_size/3)
    if len(image.shape) == 3:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size, image.shape[2])
    else:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size)
    image_with_frame = frame_color*numpy.ones(image_with_frame_shape, dtype = numpy.uint8)
    if len(image.shape) == 3:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1], :] = generic_visexpA.normalize(image,numpy.uint8)
    else:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1]] = generic_visexpA.normalize(image,numpy.uint8)
    im = Image.fromarray(image_with_frame)
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    if os.name == 'nt':
        font = ImageFont.truetype("arial.ttf", fontsize)
    else:
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", fontsize)
    image_size = utils.cr((image.shape[0]*float(scale['row']), image.shape[1]*float(scale['col'])))
    if mes:
        number_of_divisions = int(image_size['row'] / division)
    else:
        number_of_divisions = int(image_size['col'] / division)
    col_labels = numpy.linspace(numpy.round(origin['col'], 1), numpy.round(origin['col'] + number_of_divisions * division, 1), number_of_divisions+1)
    if mes:
        number_of_divisions = int(image_size['col'] / division)
        row_labels = numpy.linspace(numpy.round(origin['row'], 1),  numpy.round(origin['row'] - number_of_divisions * division, 1), number_of_divisions+1)
    else:
        number_of_divisions = int(image_size['row'] / division)
        row_labels = numpy.linspace(origin['row'],  origin['row'] + number_of_divisions * division, number_of_divisions+1)
    #Overlay labels
    for label in col_labels:
        position = int((label-origin['col'])/scale['col']) + frame_size
        draw.text((position, 5),  str(int(label)), fill = fill, font = font)
        draw.line((position, int(0.75*frame_size), position, frame_size), fill = fill, width = 0)
        #Opposite side
        draw.text((position, image_with_frame.shape[0] - fontsize-5),  str(int(label)), fill = fill, font = font)
        draw.line((position,  image_with_frame.shape[0] - int(0.75*frame_size), position,  image_with_frame.shape[0] - frame_size), fill = fill, width = 0)
        
    for label in row_labels:
        if mes:
            position = int((-label+origin['row'])/scale['row']) + frame_size
        else:
            position = int((label-origin['row'])/scale) + frame_size
        draw.text((5, position), str(int(label)), fill = fill, font = font)
        draw.line((int(0.75*frame_size), position, frame_size, position), fill = fill, width = 0)
        #Opposite side
        draw.text((image_with_frame.shape[1] - int(2.0*fontsize), position),  str(int(label)), fill = fill, font = font)
        draw.line((image_with_frame.shape[1] - int(0.75*frame_size), position,  image_with_frame.shape[1] - frame_size, position), fill = fill, width = 0)
    im = numpy.asarray(im)
    return im

def run_gui():
    app = Qt.QApplication(sys.argv)
    gui = VisionExperimentGui(sys.argv[1], sys.argv[2])
    app.exec_()

if __name__ == '__main__':
    run_gui()
