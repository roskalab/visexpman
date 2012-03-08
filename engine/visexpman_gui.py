#TODO: Load animal parameters, select ref image should come from that
#TODO: rename to visexp_gui.py
#TODO: log
#TODO:Execute experiment
#TODO: timestamp to gui.hdf5 and string_timestamp node
#TODO: string parsing: re

ENABLE_NETWORK = True

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

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from visexpA.engine.datadisplay import imaged
import visexpman.engine.generic.utils as utils
import visexpman.engine.vision_experiment.configuration as configuration
import visexpman.engine.vision_experiment.gui as gui
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.generic.utils as utils
from visexpman.engine.generic import file
import visexpman.engine.generic as generic
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import visexpA.engine.datahandlers.hdf5io as hdf5io
try:
    import visexpA.engine.dataprocessors.itk_image_registration as itk_image_registration
    import visexpA.engine.dataprocessors.itk_versor_rigid_registration as itk_versor_rigid_registration
except:
    print 'itk not installed'
import visexpA.engine.datahandlers.matlabfile as matlabfile
import visexpman.engine.generic.log as log
from visexpman.engine.vision_experiment import experiment_data
try:
    import visexpA.engine.dataprocessors.signal as signal
except:
    pass
    
parameter_extract = re.compile('EOC(.+)EOP')

################### Main widget #######################
class VisionExperimentGui(QtGui.QWidget):
    def __init__(self, config, command_relay_server = None):
        self.config = config
        self.command_relay_server = command_relay_server
        self.console_text = ''
        self.init_network()
        self.poller = gui.Poller(self, self.queues)
        self.poller.start()
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        self.create_layout()
        self.connect_signals()
        self.init_files()
        self.update_gui_items()
        self.show()
        
    def create_gui(self):
        self.debug_widget = gui.DebugWidget(self, self.config)
        self.regions_images_widget = gui.RegionsImagesWidget(self, self.config)
        self.overview_widget = gui.OverviewWidget(self, self.config)
        self.realignment_tab = QtGui.QTabWidget(self)
        self.realignment_tab.addTab(self.debug_widget, 'Debug')
        self.realignment_tab.setCurrentIndex(0)
        #Image tab
        self.image_tab = QtGui.QTabWidget(self)
        self.image_tab.addTab(self.regions_images_widget, 'Regions')
        self.image_tab.addTab(self.overview_widget, 'Overview')
        
        self.standard_io_widget = gui.StandardIOWidget(self, self.config)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.realignment_tab, 0, 0, 1, 1)
        self.layout.addWidget(self.standard_io_widget, 1, 0, 1, 1)
        self.layout.addWidget(self.image_tab, 0, 1, 2, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(2, 1)
        self.setLayout(self.layout)

    ############ Network, context, non-gui stuff ################
    def init_network(self):
        self.connections = {}
        self.queues = {}
        self.queues['mes'] = {}
        self.queues['mes']['out'] = Queue.Queue()
        self.queues['mes']['in'] = Queue.Queue()
        self.connections['mes'] = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.queues['mes']['in'], self.queues['mes']['out'])
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['stim'] = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.queues['stim']['in'], self.queues['stim']['out'])
        self.queues['analysis'] = {}
        self.queues['analysis']['out'] = Queue.Queue()
        self.queues['analysis']['in'] = Queue.Queue()
        self.connections['analysis'] = network_interface.start_client(self.config, 'GUI', 'GUI_ANALYSIS', self.queues['analysis']['in'], self.queues['analysis']['out'])
            
    def init_files(self):
        self.files_to_delete = []
        self.log = log.Log('gui log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'gui_log.txt'))) 
        # create folder if not exists
        self.context_file_path = os.path.join(self.config.CONTEXT_PATH, self.config.CONTEXT_NAME)
        context_hdf5 = hdf5io.Hdf5io(self.context_file_path)
        context_hdf5.load('stage_origin')
        context_hdf5.load('stage_position')
        if hasattr(context_hdf5, 'stage_position') and hasattr(context_hdf5, 'stage_origin') :
            self.stage_origin = context_hdf5.stage_origin
            self.stage_position = context_hdf5.stage_position
        else:
            self.stage_position = numpy.zeros(3)
            self.stage_origin = numpy.zeros(3)
        self.two_photon_image = context_hdf5.findvar('two_photon_image')
        if hasattr(self.two_photon_image, 'has_key'):
            if self.two_photon_image.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.show_image(self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], 0, 
                                self.two_photon_image['scale']['row'], 
                                origin = self.two_photon_image['origin'])
        self.vertical_scan = context_hdf5.findvar('vertical_scan')
        if hasattr(self.vertical_scan, 'has_key'):
            self.show_image(self.vertical_scan['scaled_image'], 2, self.vertical_scan['scale']['row'], origin = self.two_photon_image['origin'])
        context_hdf5.close()
        self.stage_position_valid = False
        self.mouse_files = []
        self.selected_mouse_file = ''
        self.scan_regions = {}
        
    def save_context(self):        
        context_hdf5 = hdf5io.Hdf5io(self.context_file_path)
        context_hdf5.stage_origin = self.stage_origin
        context_hdf5.stage_position = self.stage_position        
        context_hdf5.save('stage_origin',overwrite = True)
        context_hdf5.save('stage_position', overwrite = True)
        if hasattr(self,  'two_photon_image'):
            context_hdf5.two_photon_image = self.two_photon_image
            context_hdf5.save('two_photon_image', overwrite = True)
        if hasattr(self, 'vertical_scan'):
            context_hdf5.vertical_scan = self.vertical_scan
            context_hdf5.save('vertical_scan', overwrite = True)
        context_hdf5.close()
        
    ####### Signals/functions ###############
    def connect_signals(self):
        self.connect(self.standard_io_widget.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        self.connect(self.standard_io_widget.clear_console_button, QtCore.SIGNAL('clicked()'),  self.clear_console)
        self.connect(self.debug_widget.animal_parameters_groupbox.new_mouse_file_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        self.connect(self.debug_widget.show_connected_clients_button, QtCore.SIGNAL('clicked()'),  self.show_connected_clients)
        self.connect(self.debug_widget.show_network_messages_button, QtCore.SIGNAL('clicked()'),  self.show_network_messages)
        self.connect(self.debug_widget.z_stack_button, QtCore.SIGNAL('clicked()'),  self.acquire_z_stack)
        self.connect(self.debug_widget.stop_experiment_button, QtCore.SIGNAL('clicked()'),  self.stop_experiment)
        self.connect(self.debug_widget.graceful_stop_experiment_button, QtCore.SIGNAL('clicked()'),  self.graceful_stop_experiment)
        self.connect(self.debug_widget.start_experiment_button, QtCore.SIGNAL('clicked()'),  self.start_experiment)
        self.connect(self.debug_widget.set_stage_origin_button, QtCore.SIGNAL('clicked()'),  self.set_stage_origin)
        self.connect(self.debug_widget.read_stage_button, QtCore.SIGNAL('clicked()'),  self.read_stage)
        self.connect(self.debug_widget.move_stage_button, QtCore.SIGNAL('clicked()'),  self.move_stage)
        self.connect(self.debug_widget.send_command_button, QtCore.SIGNAL('clicked()'),  self.send_command)
        self.connect(self.debug_widget.save_two_photon_image_button, QtCore.SIGNAL('clicked()'),  self.save_two_photon_image)
        self.connect(self.debug_widget.move_stage_to_origin_button, QtCore.SIGNAL('clicked()'),  self.move_stage_to_origin)
        self.connect(self.debug_widget.scan_region_groupbox.get_two_photon_image_button, QtCore.SIGNAL('clicked()'),  self.acquire_two_photon_image)
        self.connect(self.debug_widget.scan_region_groupbox.snap_brain_surface_button, QtCore.SIGNAL('clicked()'),  self.snap_brain_surface)
        self.connect(self.debug_widget.scan_region_groupbox.add_button, QtCore.SIGNAL('clicked()'),  self.add_scan_region)
        self.connect(self.debug_widget.scan_region_groupbox.remove_button, QtCore.SIGNAL('clicked()'),  self.remove_scan_region)
        self.connect(self.debug_widget.scan_region_groupbox.scan_regions_combobox, QtCore.SIGNAL('currentIndexChanged()'),  self.update_gui_items)
        self.connect(self.debug_widget.scan_region_groupbox.realign_button, QtCore.SIGNAL('clicked()'),  self.realign_region)
        self.connect(self.debug_widget.scan_region_groupbox.move_to_button, QtCore.SIGNAL('clicked()'),  self.move_to_region)
        self.connect(self.debug_widget.scan_region_groupbox.register_button, QtCore.SIGNAL('clicked()'),  self.register)
        self.connect(self.debug_widget.scan_region_groupbox.vertical_scan_button, QtCore.SIGNAL('clicked()'),  self.acquire_vertical_scan)
#        self.connect(self.debug_widget.set_objective_button, QtCore.SIGNAL('clicked()'),  self.poller.set_objective)
        self.connect(self, QtCore.SIGNAL('abort'), self.poller.abort_poller)
        self.connect(self.debug_widget.scan_region_groupbox.select_mouse_file, QtCore.SIGNAL('currentIndexChanged(int)'),  self.update_animal_parameter_display)

        
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.signal_mapper.setMapping(self.debug_widget.set_objective_button, QtCore.QString('1'))
        self.debug_widget.set_objective_button.clicked.connect(self.signal_mapper.map)
        
        
        self.signal_mapper.mapped.connect(self.poller.convey_command)

    def acquire_vertical_scan(self):
        '''
        User have to figure out what is the correct scan time
        '''
        if self.debug_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() == 0:
            result, line_scan_path = self.mes_interface.start_line_scan(timeout = self.config.MES_TIMEOUT)
        else:
            #Load scan settings from parameter file
            parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'scan_region_parameters.mat')
            selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
            selected_region = self.get_current_region_name()
            scan_regions = hdf5io.read_item(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file), 'scan_regions')
            scan_regions[selected_region]['vertical_section']['mes_parameters'].tofile(parameter_file_path)
            result, line_scan_path = self.mes_interface.start_line_scan(timeout = self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
        self.files_to_delete.append(line_scan_path)
        if result:
            result = self.mes_interface.wait_for_line_scan_complete(timeout = self.config.MES_TIMEOUT)
            if result:
                result = self.mes_interface.wait_for_line_scan_save_complete(timeout = self.config.MES_TIMEOUT)
                if result:
                    self.vertical_scan = matlabfile.read_vertical_scan(line_scan_path)
                    #rescale image so that it could be displayed
                    self.show_image(self.vertical_scan['scaled_image'], 2, self.vertical_scan['scale']['row'], origin = self.vertical_scan['origin'])
                    self.save_context()
                else:
                    self.printc('data not saved')
            else:
                self.printc('scan complete with error')
        else:
            self.printc('scan did not start')

    def set_objective(self):
        position = float(self.scanc())
        if self.mes_interface.set_objective(position, self.config.MES_TIMEOUT):
            self.debug_widget.objective_position_label.setText(str(position))
            self.printc('objective is set to {0} um'.format(position))

    def add_scan_region(self, widget = None):
        '''
        The following data are saved:
        -two photon image of the brain surface
        -mes parameter file of two photon acquisition so that later the very same image could be taken to help realignment
        -objective positon where the data acquisition shall take place. This is below the brain surface
        -stage position. If master position is saved, the current position is set to origin. The origin of stimulation software is also 
        '''

        if widget == None:
            widget = self.debug_widget
        result,  self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
        if self.read_stage() and result:
            if hasattr(self, 'brain_surface_image'):
                mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(widget.scan_region_groupbox.select_mouse_file.currentText()))
                if os.path.exists(mouse_file_path) and '.hdf5' in mouse_file_path:
                    #Read scan regions
                    hdf5_handler = hdf5io.Hdf5io(mouse_file_path)
                    hdf5_handler.scan_regions = hdf5_handler.findvar('scan_regions')
                    if hdf5_handler.scan_regions == None:
                        hdf5_handler.scan_regions = {}
                    region_name = self.get_current_region_name()
                    #If no name provided, will be generated from the coordinates
                    if region_name == '':
                        relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
                        region_name = 'r_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
                        self.printc(region_name)
                    #Ask for confirmation to overwrite if region name already exists
                    if hdf5_handler.scan_regions.has_key(region_name):
                        reply = QtGui.QMessageBox.question(self, 'Overwriting scan region', "Are you sure?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                        if reply == QtGui.QMessageBox.No:
                            self.printc('Region not saved')
                            hdf5_handler.close()
                            return
                    #Data to be saved regardless it is a master position or not:
                    scan_region = {}
                    scan_region['add_date'] = utils.datetime_string().replace('_', ' ')
                    scan_region['brain_surface'] = {}
                    scan_region['brain_surface']['image'] = self.brain_surface_image[self.config.DEFAULT_PMT_CHANNEL]
                    scan_region['brain_surface']['scale'] = self.brain_surface_image['scale']
                    scan_region['brain_surface']['origin'] = self.brain_surface_image['origin']
                    scan_region['brain_surface']['mes_parameters']  = utils.file_to_binary_array(self.brain_surface_image['path'].tostring())
                    #Vertical section
                    if hasattr(self, 'vertical_scan'):
                        if self.vertical_scan !=  None:
                            scan_region['vertical_section'] = self.vertical_scan
                            scan_region['vertical_section']['mes_parameters'] = utils.file_to_binary_array(self.vertical_scan['path'].tostring())
                        else:
                            self.printc('No vertical scan is available')
                    else:
                        self.printc('No vertical scan is available')
                    if region_name == 'master':
                       if not self.set_stage_origin():
                            self.printc('Setting origin did not succeed')
                            hdf5_handler.close()
                            return
                    if region_name == 'master' or hdf5_handler.scan_regions.has_key('master') or region_name == 'r_0_0' or\
                    hdf5_handler.scan_regions.has_key('r_0_0'):
                        scan_region['position'] = utils.pack_position(self.stage_position-self.stage_origin, self.objective_position)
                    else:
                        self.printc('Master position has to be defined')
                        hdf5_handler.close()
                        return
                    #Save new scan region to hdf5 file
                    hdf5_handler.scan_regions[region_name] = scan_region
                    hdf5_handler.save('scan_regions', overwrite = True)
                    hdf5_handler.close()
                    self.printc('Scan region saved')
                else:
                    self.printc('mouse file not found')
            else:
                self.printc('No brain surface image is acquired')
        else:
            self.printc('Stage or objective position is not available')
                    
    def remove_scan_region(self):
        selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
        selected_region = self.get_current_region_name()
        hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file))
        scan_regions = hdf5_handler.findvar('scan_regions')
        if scan_regions.has_key(selected_region):
            del scan_regions[selected_region]
        hdf5_handler.scan_regions = scan_regions
        hdf5_handler.save('scan_regions', overwrite = True)
        hdf5_handler.close()
        
    def save_two_photon_image(self):
        hdf5_handler = hdf5io.Hdf5io(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'two_photon_image.hdf5')))
        hdf5_handler.two_photon_image = self.two_photon_image
        hdf5_handler.stage_position = self.stage_position
        hdf5_handler.save(['two_photon_image', 'stage_position'])
        hdf5_handler.close()

    def register(self):
#        self.printc((self.image_display[0].scale['row'], self.image_display[1].scale['row']))
#        self.printc((self.image_display[0].image.shape, self.image_display[1].image.shape))
#        if self.image_display[0].scale['row'] != self.image_display[1].scale['row']:
#            rescaled_image = generic.rescale_numpy_array_image(self.image_display[0].image, self.image_display[0].scale['row'] / self.image_display[1].scale['row'])
#        else:
        rescaled_image = self.regions_images_widget.image_display[0].image
#        self.printc(rescaled_image.shape)
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'))
        image_hdf5_handler.f1 = rescaled_image
        image_hdf5_handler.f2 = self.regions_images_widget.image_display[1].image
        image_hdf5_handler.save(['f1', 'f2'], overwrite = True)
        image_hdf5_handler.close()
        arguments = ''
        utils.empty_queue(self.queues['analysis']['in'])
        self.queues['analysis']['out'].put('SOCregisterEOC' + arguments + 'EOP')
        if utils.wait_data_appear_in_queue(self.queues['analysis']['in'], self.config.MAX_REGISTRATION_TIME):
            while not self.queues['analysis']['in'].empty():
                response = self.queues['analysis']['in'].get()
                if 'register' in response:
                    self.registration_result = self.parse_list_response(response) #rotation in angle, center or rotation, translation
                    self.suggested_translation = utils.cr(utils.nd(self.two_photon_image['scale']) * self.registration_result[-2:]*numpy.array([-1, 1]))
                    self.printc(self.registration_result[-2:])
                    self.printc(self.suggested_translation)
        else:
            self.printc('no response')

    def realign_region(self):
        self.move_stage_relative(-numpy.round(numpy.array([self.suggested_translation['col'], self.suggested_translation['row'], 0.0]), 2))
        self.suggested_translation = utils.cr((0, 0)) #To avoid unnecessary movements if realign button is pressed twice
        
    def move_to_region(self):
        selected_region = self.get_current_region_name()
        if (self.scan_regions.has_key('master') or self.scan_regions.has_key('r_0_0')) and self.scan_regions.has_key(selected_region):
            if self.scan_regions.has_key('master'):
                master_position_name = 'master'
            else:
                master_position_name = 'r_0_0'
            current_relative_position = self.stage_position - self.stage_origin
            master_position = numpy.array([self.scan_regions[master_position_name]['position']['x'][0], self.scan_regions[master_position_name]['position']['y'][0], current_relative_position[-1]])
            target_relative_position = numpy.array([self.scan_regions[selected_region]['position']['x'][0], self.scan_regions[selected_region]['position']['y'][0], current_relative_position[-1]])
            movement = target_relative_position - current_relative_position
            self.move_stage_relative(movement)
        else:
            self.printc('Master position is not defined')
    
    def acquire_z_stack(self):
        try:
            self.z_stack, results = self.mes_interface.acquire_z_stack(self.config.MES_TIMEOUT)
            self.printc((self.z_stack, results))
        except:
            self.printc(traceback.format_exc())
            
    def snap_brain_surface(self):
        self.acquire_two_photon_image()
        self.brain_surface_image = self.two_photon_image
            
    def acquire_two_photon_image(self):
        try:
            if self.debug_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() == 0:
                self.two_photon_image,  result = self.mes_interface.acquire_two_photon_image(self.config.MES_TIMEOUT)
            else:
                #Load scan settings from parameter file
                parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'scan_region_parameters.mat')
                selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
                selected_region = self.get_current_region_name()
                scan_regions = hdf5io.read_item(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file), 'scan_regions')
                scan_regions[selected_region]['brain_surface']['mes_parameters'].tofile(parameter_file_path)
                self.two_photon_image,  result = self.mes_interface.acquire_two_photon_image(self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
            if self.two_photon_image.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.two_photon_image['path'])
            if result:
                self.show_image(self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], 0, 
                                self.two_photon_image['scale']['row'], 
                                origin = self.two_photon_image['origin'])
                self.save_context()
            else:
                self.printc('No image acquired')
        except:
            self.printc(traceback.format_exc())
            
    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('stop_experiment')
        
    def graceful_stop_experiment(self):
        command = 'SOCgraceful_stop_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('graceful_stop_experiment')
        
    def start_experiment(self):
        params =  self.scanc()
        if len(params)>0:
            objective_positions = params.replace(',',  '<comma>')
            command = 'SOCexecute_experimentEOCobjective_positions={0}EOP' .format(objective_positions)
        else:
            command = 'SOCexecute_experimentEOCEOP'        
        self.queues['stim']['out'].put(command)
        self.printc('Experiment started')

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

        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'mouse_{0}.hdf5'\
                                            .format(name))
        
        if os.path.exists(mouse_file_path):
            self.printc('Animal parameter file already exists')
        else:        
            self.hdf5_handler = hdf5io.Hdf5io(mouse_file_path)
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))        
            setattr(self.hdf5_handler,  variable_name, animal_parameters)
            self.hdf5_handler.save(variable_name)
            self.printc('Animal parameters saved')
            self.hdf5_handler.close()
            #set selected mouse file to this one
            self.update_mouse_files_combobox(set_to_value = os.path.split(mouse_file_path)[-1])
            
    def update_mouse_files_combobox(self, set_to_value = None):
        new_mouse_files = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH,  'mouse')
        if self.mouse_files != new_mouse_files:
            self.mouse_files = new_mouse_files
            self.update_combo_box_list(self.debug_widget.scan_region_groupbox.select_mouse_file, self.mouse_files)
            if set_to_value != None:
                self.debug_widget.scan_region_groupbox.select_mouse_file.setCurrentIndex(self.mouse_files.index(set_to_value))

    def update_gui_items(self):
        '''
        Update comboboxes with file lists
        '''
        self.update_mouse_files_combobox()
        selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
        scan_regions = hdf5io.read_item(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file), 'scan_regions')
        if scan_regions == None:
            scan_regions = {}
        #is new region added?
        if scan_regions.keys() != self.scan_regions.keys():
            displayable_region_names = []
            for region in scan_regions.keys():
                if scan_regions[region].has_key('add_date'):
                    displayable_region_names.append(region + '  ' + scan_regions[region]['add_date'])
                else:
                    displayable_region_names.append(region)
            self.update_combo_box_list(self.debug_widget.scan_region_groupbox.scan_regions_combobox, displayable_region_names)
        self.scan_regions = scan_regions
        #Display image of selected region
        selected_region = self.get_current_region_name()
        if hasattr(self.scan_regions, 'has_key'):
            if self.scan_regions.has_key(selected_region):
                line = None
                if self.scan_regions[selected_region].has_key('vertical_section'):
                    #convert line info from um to pixel
                    line = numpy.array([\
                                    self.scan_regions[selected_region]['vertical_section']['p1']['col'] - self.scan_regions[selected_region]['brain_surface']['origin']['col'],\
                                    -(self.scan_regions[selected_region]['vertical_section']['p1']['row'] - self.scan_regions[selected_region]['brain_surface']['origin']['row']),\
                                    self.scan_regions[selected_region]['vertical_section']['p2']['col'] - self.scan_regions[selected_region]['brain_surface']['origin']['col'],\
                                    -(self.scan_regions[selected_region]['vertical_section']['p2']['row'] - self.scan_regions[selected_region]['brain_surface']['origin']['row'])])
                    line /= self.scan_regions[selected_region]['brain_surface']['scale']['row']
                    line = line.tolist()
                    self.show_image(self.scan_regions[selected_region]['vertical_section']['scaled_image'], 3,
                                     self.scan_regions[selected_region]['vertical_section']['scale']['row'], 
                                     origin = self.scan_regions[selected_region]['vertical_section']['origin'])
                image_to_display = self.scan_regions[selected_region]['brain_surface']
                self.show_image(image_to_display['image'], 1, image_to_display['scale']['row'], line = line, origin = image_to_display['origin'])
                #update overwiew
                image, scale = experiment_data.merge_brain_regions(self.scan_regions, region_on_top = selected_region)
                self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
                
        #Display coordinates of selected region
        if self.scan_regions.has_key(selected_region):
            if self.scan_regions[selected_region].has_key('add_date'):
                region_add_date = self.scan_regions[selected_region]['add_date']
            else:
                region_add_date = 'unknown'
            self.debug_widget.scan_region_groupbox.region_info.setText(\
                                                                           '{0:.2f}, {1:.2f}, {2:.2f}\n{3}' \
                                                                           .format(self.scan_regions[selected_region]['position']['x'][0], 
                                                                                   self.scan_regions[selected_region]['position']['y'][0], 
                                                                                   self.scan_regions[selected_region]['position']['z'][0], 
                                                                                   region_add_date))

    def update_animal_parameter_display(self, index):
        selected_mouse_file  = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText()))
        if os.path.exists(selected_mouse_file) and '.hdf5' in selected_mouse_file:
            h = hdf5io.Hdf5io(selected_mouse_file)
            varname = h.find_variable_in_h5f('animal_parameters')[0]
            h.load(varname)
            animal_parameters = getattr(h, varname)
            self.animal_parameters_str = '{2}, birth date: {0}, injection date: {1}, punch lr: {3},{4}, {5}, {6}'\
            .format(animal_parameters['mouse_birth_date'], animal_parameters['gcamp_injection_date'], animal_parameters['strain'], 
                    animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], animal_parameters['gender'],  animal_parameters['anesthesia_protocol'])
            h.close()

        self.debug_widget.scan_region_groupbox.animal_parameters_label.setText(self.animal_parameters_str)

    def set_stage_origin(self):
        result = False
        if not self.stage_position_valid:
            self.read_stage(display_coords = False)
            self.stage_position_valid = True
        self.stage_origin = self.stage_position
        self.save_context()
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCoriginEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], 10.0):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()            
                if 'SOCstageEOC' in response:
                    self.printc('origin set')
                    result = True
        self.origin_set = True
        return result

    def read_stage(self, display_coords = True):
        result = False
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCreadEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.STAGE_TIMEOUT):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()            
                if 'SOCstageEOC' in response:
                    self.stage_position = self.parse_list_response(response)
                    if display_coords:
                        self.printc('abs: ' + str(self.stage_position))
                        self.printc('rel: ' + str(self.stage_position - self.stage_origin))
                    self.save_context()
                    self.debug_widget.current_position_label.setText('rel: {0}' .format(numpy.round(self.stage_position - self.stage_origin, 2)))
                    result = True
        else:
            self.printc('stage is not accessible')
        return result
    
    def move_stage(self):
        movement = self.scanc().split(',')
        if len(movement) == 2:
            movement.append('0')
        elif len(movement) != 3:
            self.printc('invalid coordinates')
            return
        self.move_stage_relative(movement)

    def move_stage_relative(self, movement):
        if hasattr(self, 'brain_surface_image'): #to avoid saving false data at saving regions
            del self.brain_surface_image
        if hasattr(self, 'vertical_scan'):
            del self.vertical_scan
        self.debug_widget.scan_region_groupbox.scan_regions_combobox.setEditText('')
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCset,{0},{1},{2}EOP'.format(movement[0], movement[1], movement[2]))
        self.printc('movement {0}'.format(movement))
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.STAGE_TIMEOUT):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()
                if 'SOCstageEOC' in response:
                    self.stage_position = self.parse_list_response(response)
                    self.save_context()
                    self.debug_widget.current_position_label.setText('rel: {0}' .format(numpy.round(self.stage_position - self.stage_origin, 2)))
                    self.printc('abs: ' + str(self.stage_position))
                    self.printc('rel: ' + str(self.stage_position - self.stage_origin))
                    
    def move_stage_to_origin(self):
        pass

    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)

    ####### Helpers ###############
    
    def parse_list_response(self, response):
        return numpy.array(map(float,parameter_extract.findall( response)[0].split(',')))
    
    def show_image(self, image, channel, scale, line = None, origin = None):
        scale_indexed = scale
            
        if line != None:
            image_with_line = generic.draw_line_numpy_array(image, line)
        else:
            image_with_line = image
        if origin != None:
            origin_fixed = origin
            division = numpy.round(min(image_with_line.shape) *  scale_indexed/ 5.0, -1)
            image_with_sidebar = generic.draw_scalebar(image_with_line, origin_fixed, scale_indexed, division)
        else:
            image_with_sidebar = image_with_line
        if channel == 'overview':
            self.overview_widget.image_display.setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.OVERVIEW_IMAGE_SIZE))
            self.overview_widget.image_display.image = image_with_sidebar
            self.overview_widget.image_display.scale = scale_indexed
        else:
            self.regions_images_widget.image_display[channel].setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.IMAGE_SIZE))
            self.regions_images_widget.image_display[channel].image = image_with_sidebar
            self.regions_images_widget.image_display[channel].scale = scale_indexed
        
    def send_command(self):
        connection = str(self.debug_widget.select_connection_list.currentText())
        self.queues[connection]['out'].put(self.scanc())
        
    def show_connected_clients(self):
        connection_status = self.command_relay_server.get_connection_status()
        connected = []
        for k, v in connection_status.items():
            if v:
                connected.append(k)
        connected.sort()
        connected = str(connected).replace('[','').replace(']', '').replace('\'','').replace(',','\n')
        self.printc(connected)
        self.printc('\n')

    def show_network_messages(self):
        if hasattr(self, 'network_messages'):
            for info in self.command_relay_server.get_debug_info():
                self.network_messages.append(info)
        else:
            self.network_messages = self.command_relay_server.get_debug_info()
        self.network_messages = self.network_messages[-500:] #limit the number of displayed messages
        for network_message in self.network_messages:
            endpoint_name = network_message[1].split(' ')
            endpoint_name = (endpoint_name[1] + '/' + endpoint_name[3]).replace(',','')
            message = network_message[1].split('port')[1].split(': ', 1)[1]
            displayable_message = network_message[0] + ' ' + endpoint_name + '>> ' + message
            self.printc(displayable_message)
        self.printc('\n')
            
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        self.log.info(text)

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())
        
    def update_combo_box_list(self, widget, new_list):
        current_value = widget.currentText()
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
        items_list = QtCore.QStringList(new_list)
        widget.clear()
        widget.addItems(QtCore.QStringList(new_list))
        widget.setCurrentIndex(current_index)
        
    def get_current_region_name(self):
        return str(self.debug_widget.scan_region_groupbox.scan_regions_combobox.currentText()).split(' ')[0]

    def closeEvent(self, e):
        e.accept()
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.emit(QtCore.SIGNAL('abort'))
        #delete files:
        for file_path in self.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        if ENABLE_NETWORK:
            self.command_relay_server.shutdown_servers()            
            time.sleep(2.0) #Enough time to close network connections
        sys.exit(0)
        
class GuiConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        COORDINATE_SYSTEM='center'

        if self.OS == 'win':
            v_drive_folder = 'V:\\'
        elif self.OS == 'linux':                        
            v_drive_folder = '/home/zoltan/visexp'
        if len(sys.argv) >1:
            arg = sys.argv[1]
        else:
            arg = ''
        if 'dev' in arg or 'development' in self.PACKAGE_PATH:
            CONTEXT_NAME = 'gui_dev.hdf5'
            data_folder = os.path.join(v_drive_folder, 'debug', 'data')
            MES_DATA_FOLDER = 'V:\\debug\\data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'debug', 'data')            
        else:
            CONTEXT_NAME = 'gui.hdf5'
            data_folder = os.path.join(v_drive_folder, 'experiment_data')
            MES_DATA_FOLDER = 'V:\\experiment_data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'experiment_data')
        self.MES_TIMEOUT = 5.0
        self.MAX_REGISTRATION_TIME = 30.0
        LOG_PATH = os.path.join(data_folder, 'log')
        EXPERIMENT_LOG_PATH = data_folder
        EXPERIMENT_DATA_PATH = data_folder
        CONTEXT_PATH = os.path.join(v_drive_folder, 'context')
        self.GUI_REFRESH_PERIOD = 2.0
        self.COMMAND_RELAY_SERVER['ENABLE'] = ENABLE_NETWORK
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'#'172.27.26.1'#'172.27.25.220'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = ENABLE_NETWORK
#        self.COMMAND_RELAY_SERVER['TIMEOUT'] = 60.0
        DEFAULT_PMT_CHANNEL = ['pmtUGraw',  ['pmtUGraw', 'pmtURraw',  'undefined']]
        self.STAGE_TIMEOUT = 30.0

        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1200, 800))
        TAB_SIZE = utils.cr((500, 800))
        IMAGE_SIZE = utils.rc((400, 400))
        OVERVIEW_IMAGE_SIZE = utils.rc((800, 800))
        self._create_parameters_from_locals(locals())

def run_gui():
    config = GuiConfig()
    if ENABLE_NETWORK:
        cr = network_interface.CommandRelayServer(config)
    else:
        cr = None
    app = Qt.QApplication(sys.argv)
    gui2 = VisionExperimentGui(config, cr)
    app.exec_()

if __name__ == '__main__':
    run_gui()
