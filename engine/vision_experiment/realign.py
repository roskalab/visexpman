class Realign():
    def __init__(self, config, printc, mes_interface):
        self.config = config
        self.printc = printc
        self.mes_interface = mes_interface

def realign_to_region(self, scan_region, config, protocol, printc, mes_interface):
    '''
    '''
    if protocol['stage_realign'] :
        printc('Realign stage')
        printc('Acquire xy image')
        xy_image, result = mes_interface.acquire_xy_image(scan_region['brain_surface']['mes_parameters'])
        if not result:
            printc('Acquire xy does not succeed')
        printc('Register with saved image.')
        #calculate translation between current and saved brain surface image
        if not self.register_images(self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['brain_surface']['image'], self.two_photon_image['scale']):
            return
        if abs(self.suggested_translation['col'])  > self.config.MAX_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.MAX_REALIGNMENT_OFFSET:
            self.printc('Suggested translation is not plausible')
            return
        #Translate stage with suggested values
        stage_translation = -numpy.round(numpy.array([self.suggested_translation['col'], self.suggested_translation['row'], 0.0]), 2)
        if abs(self.suggested_translation['col'])  > self.config.REALIGNMENT_XY_THRESHOLD or abs(self.suggested_translation['row']) > self.config.REALIGNMENT_XY_THRESHOLD:
            self.move_stage_relative(stage_translation)
        else:
            self.printc('Suggested translation is small, stage is not moved')
        if self.parent.debug_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_origin_adjust'] .checkState() != 0:
            self.printc('Stage origin was corrected with detected offset')
            self.stage_origin = self.stage_origin + stage_translation
        #Get a two photon image and register again, to see whether realignment was successful
        if not self.acquire_xy_image(use_region_parameters = True):
            return
        if not self.register_images(self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['brain_surface']['image'], self.two_photon_image['scale']):
            return
        if abs(self.suggested_translation['col']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
            self.printc('Realignment was not successful {0}' .format(self.suggested_translation)) #Process not interrupted, but moves to vertical realignment
        self.printc('XY offset {0}' .format(self.suggested_translation))
    if self.parent.debug_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_realign'] .checkState() != 0 and\
            'vertical_section' in self.scan_regions[selected_region]:
        self.printc('Realign objective')
        result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
        if not result:
            self.printc('MES does not respond')
            return
        if not self.acquire_vertical_scan(use_region_parameters = True):
            self.printc('Vertical scan was not successful')
            return
        #calculate z offset between currently acquired vertical scan and reference data
        if not self.register_images(self.vertical_scan['scaled_image'], self.scan_regions[selected_region]['vertical_section']['scaled_image'], self.vertical_scan['scaled_scale']):
            return
        vertical_offset = self.suggested_translation['row']
        if abs(vertical_offset)  > self.config.MAX_REALIGNMENT_OFFSET:
            self.printc('Suggested movement is not plausible')
            return
        new_objective_position = self.objective_position + vertical_offset#self.objective_position was updated by vertical scan
        #Move objective
        if abs(vertical_offset)  > self.config.REALIGNMENT_Z_THRESHOLD:
            if not self.mes_interface.set_objective(new_objective_position, self.config.MES_TIMEOUT):
                self.printc('Setting objective did not succeed')
                return
            else:
                self.printc('Objective moved to {0}'.format(new_objective_position))
                #Change origin when full realignment is done with moving both objective and stage and realign both devices
                if self.parent.debug_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_origin_adjust'] .checkState() != 0:
                    if not self.mes_interface.overwrite_relative_position(self.objective_position, self.config.MES_TIMEOUT):
                        self.printc('Setting objective relative value did not succeed')
                        return
                    else:
                        self.printc('Objective relative origin was corrected with detected offset')
                result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
                if not result:
                    self.printc('MES did not respond')
                    return
        else:
            self.printc('Suggested translation is small, objective is not moved.')
        #Verify vertical realignment
        if not self.acquire_vertical_scan(use_region_parameters = True):
            self.printc('Vertical scan was not successful')
            return
        if not self.register_images(self.vertical_scan['scaled_image'], self.scan_regions[selected_region]['vertical_section']['scaled_image'], self.vertical_scan['scaled_scale']):
            return
        vertical_offset = self.suggested_translation['row']
        if abs(vertical_offset) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
            self.printc('Realignment was not successful {0}'.format(vertical_offset))
            return
        self.printc('Vertical offset {0}' .format(vertical_offset))
    self.update_position_display()
    self.suggested_translation = utils.cr((0, 0))
    self.printc('Move to region complete')
        
def register_images(f1, f2, scale,  print_result = True):
        from PIL import Image
#        from visexpA.engine.dataprocessors import generic
#        Image.fromarray(generic.normalize(f1,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f1.png')))
#        Image.fromarray(generic.normalize(f2,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f2.png')))
        self.create_image_registration_data_file(f1, f2)
        utils.empty_queue(self.queues['analysis']['in'])
        arguments = ''
        self.queues['analysis']['out'].put('SOCregisterEOC' + arguments + 'EOP')
        if not utils.wait_data_appear_in_queue(self.queues['analysis']['in'], 10.0):
            self.printc('Analysis not connected')
            return False
        if 'SOCregisterEOCstartedEOP' not in self.queues['analysis']['in'].get():
            self.printc('Image registration did not start')
            return False
        if utils.wait_data_appear_in_queue(self.queues['analysis']['in'], timeout = self.config.MAX_REGISTRATION_TIME):#TODO: the content of the queue also need to be checked
            while not self.queues['analysis']['in'].empty():
                    response = self.queues['analysis']['in'].get()
                    if 'error' in response:
                        self.printc('Image registration resulted error')
                        return False
                    elif 'register' in response:
                        self.registration_result = self.parse_list_response(response) #rotation in angle, center or rotation, translation
                        self.suggested_translation = utils.cr(utils.nd(scale) * self.registration_result[-2:]*numpy.array([-1, 1]))
                        if print_result:
                            self.printc(self.registration_result[-2:])
                            self.printc('Suggested translation: {0}'.format(self.suggested_translation))
                        return True
        else:
            self.printc('Analysis does not respond')
        return False

def create_image_registration_data_file(f1, f2):
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'),filelocking=False)
        image_hdf5_handler.f1 = f1
        image_hdf5_handler.f2 = f2
        image_hdf5_handler.save(['f1', 'f2'], overwrite = True)
        image_hdf5_handler.close()
