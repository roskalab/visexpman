#TODO: Rename this module

import pygame
import socket
#import threading
import time
#import os#?
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.graphics as graphics
from OpenGL.GL import *#?
from OpenGL.GLUT import *
import copy

def experiment_choices(experiment_list):
    '''
    Lists and displays stimulus files that can be found in the default stimulus file folder
    '''
    return '\n'.join([str(i)+' '+experiment_list[i][1].__name__ for i in range(len(experiment_list))])

class VisexpmanScreen(graphics.Screen):
    '''
    graphics.Screen is amended with vision experiment specific features: menu&message displaying
    '''    
    def __init__(self, config, caller):
        self.caller = caller
        graphics.Screen.__init__(self, config, graphics_mode = 'external')
        self.clear_screen()
        #== Initialize displaying text ==
        self.text_style = GLUT_BITMAP_8_BY_13
        self.menu_position = utils.cr(( int(self.config.MENU_POSITION['col'] * self.config.SCREEN_RESOLUTION['col']), int(self.config.MENU_POSITION['row'] * self.config.SCREEN_RESOLUTION['row'])))
        self.message_position = utils.cr(( int(self.config.MESSAGE_POSITION['col'] * self.config.SCREEN_RESOLUTION['col']), int(self.config.MESSAGE_POSITION['row'] * self.config.SCREEN_RESOLUTION['row'])))
        self.message = 'no message'
        self.hide_menu = False
        self.show_bullseye = False
        #== Update text to screen ==
#        self.refresh_non_experiment_screen()
        
    def clear_screen_to_background(self):
        color = self.config.BACKGROUND_COLOR
        if self.caller.command_handler.presentinator_interface['command'] == 'color':
            color = utils.convert_color(self.caller.command_handler.presentinator_interface['color'])
        graphics.Screen.clear_screen(self, color = color)
        
    def display_bullseye(self):
        if self.show_bullseye:
            #TODO: bullseye size
            #TODO: consider coordinate system type
            self.render_imagefile(os.path.join(self.config.PACKAGE_PATH, 'data', 'images', 'bullseye.bmp'))
            
        
    def _show_menu(self, flip = False):
        '''
        Show menu text on screen:
         - possible keyboard commands
         - available experiment configurations
        '''
        self.menu_text = self.config.MENU_TEXT + experiment_choices(self.caller.experiment_config_list) + '\nSelected experiment config: ' + self.caller.experiment_config_list[int(self.caller.command_handler.selected_experiment_config_index)][1].__name__
        self.render_text(self.menu_text, color = self.config.TEXT_COLOR, position = self.menu_position, text_style = self.text_style)
        if flip:
            self.flip()

    def _show_message(self, message, flip = False):
        '''
        Display messages coming from command handler
        '''
        #count number of message rows and limit their number
        lines = message.split('\n')
        lines = lines[-self.config.NUMBER_OF_MESSAGE_ROWS:]
        limited_message = ''
        for line in lines:
            limited_message += line + '\n'
        
        self.render_text(limited_message, color = self.config.TEXT_COLOR, position = self.message_position, text_style = self.text_style)
        if flip:
            self.flip()

    def refresh_non_experiment_screen(self, flip = True):
        '''
        Render menu and message texts to screen
        '''
        
        #TODO: when ENABLE_TEXT = False, screen has to be cleared to background color, self.clear_screen_to_background()
        if self.config.ENABLE_TEXT:# and not self.hide_menu:#TODO: menu is not cleared - Seems like opengl does not clear 2d text with glclear command
            self._show_menu()
            self._show_message(self.message, flip = flip)

    def run_preexperiment(self):
        pass

class ScreenAndKeyboardHandler(VisexpmanScreen):
    '''
    VisexpmanScreen is amended with keyboard handling
    '''
    def __init__(self, config, caller, keyboard_command_queue):
        VisexpmanScreen.__init__(self, config, caller)
        self.keyboard_command_queue = keyboard_command_queue
        self.experiment_config_shortcuts = ['{0}'.format(i) for i in range(len(caller.experiment_config_list))]#stimulus_file_shortcut
        self.command_domain = 'keyboard'
        self.keyboard_commands = copy.deepcopy(self.config.COMMANDS)
        self.separator = '@'
        for shortcut in self.experiment_config_shortcuts:
            self.keyboard_commands['select_experiment' + self.separator + shortcut] = {'key': shortcut, 'domain' : [self.command_domain]}

    def _check_keyboard(self):
        '''
        Get pressed key
        '''        
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                key_pressed = pygame.key.name(event.key)                
                return key_pressed
        return

    def _parse_keyboard_command(self, key_pressed, domain):
        '''
        If pressed key valid, generate command string.
        '''
        command = None
        parameter = None
        for k, v in self.keyboard_commands.items():
            if v['key'] == key_pressed and utils.is_in_list(v['domain'], domain) :
                command_and_parameters = k.split(self.separator)
                command = command_and_parameters[0]
                if len(command_and_parameters) == 2:
                    parameter = command_and_parameters[1]
                break
        if command != None:
            command = 'SOC' + command + 'EOC'
            if parameter != None:
                command += parameter + 'EOP'        
        return command
        
    def keyboard_handler(self, domain):
        '''
        Registers pressed key and generates command string for command handler.
        '''
        return self._parse_keyboard_command(self._check_keyboard(),  domain)
        
    def experiment_user_interface_handler(self):
        '''
        Keyboard commands accepted during running experiment are handled here
        '''        
        return self.keyboard_handler('running experiment')

    def user_interface_handler(self):
        '''
        Updates menu and message on screen, takes care of handling the keyboard
        '''
        self.refresh_non_experiment_screen()
        command = self.keyboard_handler(self.command_domain)
        #Send command to queue
        if command != None:
            self.keyboard_command_queue.put(command)
        
if __name__ == "__main__":
    pass
