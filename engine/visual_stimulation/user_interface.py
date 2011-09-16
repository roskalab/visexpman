#TODO: Rename this module

import pygame
import socket
import threading
import time#?
import os#?
from visexpman.engine.generic import utils
import visexpman.engine.generic.graphics as graphics
from OpenGL.GL import *#?
from OpenGL.GLUT import *

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
        self.menu_text = self.config.MENU_TEXT + experiment_choices(self.caller.experiment_config_list)
        self.message_position = utils.cr(( int(self.config.MESSAGE_POSITION['col'] * self.config.SCREEN_RESOLUTION['col']), int(self.config.MESSAGE_POSITION['row'] * self.config.SCREEN_RESOLUTION['row'])))
        self.message = 'no message'
        self.hide_menu = False
        #== Update text to screen ==
#        self.refresh_non_experiment_screen()
        
    def clear_screen_to_background(self):
        graphics.Screen.clear_screen(self, color = self.config.BACKGROUND_COLOR)        
        
    def _show_menu(self, flip = False):
        '''
        Show menu text on screen:
         - possible keyboard commands
         - available experiment configurations
        '''        
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
        if self.config.TEXT_ENABLE:# and not self.hide_menu:#TODO: menu is not cleared - Seems like opengl does not clear 2d text with glclear command
            self._show_menu()
            self._show_message(self.message, flip = flip)

    def run_preexperiment(self):
        pass
            
class ScreenAndKeyboardHandler(VisexpmanScreen):
    '''
    VisexpmanScreen is amended with keyboard handling
    '''
    def __init__(self, config, caller):
        VisexpmanScreen.__init__(self, config, caller)
        self.experiment_config_shortcuts = ['{0}'.format(i) for i in range(len(caller.experiment_config_list))]#stimulus_file_shortcut         
        self.keyboard_commands = self.config.KEYBOARD_COMMANDS
        self.separator = '@'
        for shortcut in self.experiment_config_shortcuts:
            self.keyboard_commands['select_experiment' + self.separator + shortcut] = {'key': shortcut}

    def _check_keyboard(self):
        '''
        Get pressed key
        '''
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                key_pressed = pygame.key.name(event.key)
                return key_pressed
        return
        
    def _parse_keyboard_command(self, key_pressed):
        '''
        If pressed key valid, generate command string.
        '''
        command = None
        parameter = None
        if key_pressed == 'escape':
            command = 'quit'
        else:
            for k, v in self.keyboard_commands.items():
                if v['key'] == key_pressed:
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
        
    def keyboard_handler(self):
        '''
        Registers pressed key and generates command string for command handler.
        '''        
        return self._parse_keyboard_command(self._check_keyboard())

    def user_interface_handler(self):
        '''
        Updates menu and message on screen, takes care of handling the keyboard
        '''
        self.refresh_non_experiment_screen()
        command = self.keyboard_handler()
        #Send command to command handler via tcp ip        
        if command != None:
            sock = socket.create_connection(('localhost',  self.config.COMMAND_INTERFACE_PORT))
            sock.sendall(command)                                
    
class UserInterface():
    '''
    UserInterface is responsible for handling keystrokes and displaying messages on screen. Display handling is taken over by StimulationControl when software leaves idle state       
    '''
    def __init__(self,  config,  caller):
        
        self.config = config
        #Initializing display, setting screen resolution, background color, hiding mouse cursor, quantities are interpreted in pixels
        self.screen = VisexpmanScreen(self.config, graphics_mode = 'external') #create a window
        #Set acceptable framerate and give warning when frame drop occurs
        #TODO: self.screen._refreshThreshold=1/float(self.config.SCREEN_EXPECTED_FRAME_RATE)+float(self.config.FRAME_DELAY_TOLERANCE) * 1e-3
        #TODO: self.screen.setGamma(self.config.GAMMA)
        
        #shortcuts to experiment classes, max 10
        self.accepted_keys = self.config.KEYS + ['{0}'.format(i) for i in range(len(caller.experiment_config_list))]#stimulus_file_shortcut 
        
        #Display menu        
        if self.config.TEXT_ENABLE:
            self.text_style = GLUT_BITMAP_8_BY_13
            self.menu_position = utils.cr(( int(-0.2 * self.config.SCREEN_RESOLUTION['col']), 0))
            self.menu_text = self.config.MENU_TEXT + experiment_choices(caller.experiment_config_list)
            self.screen.render_text(self.menu_text, color = self.config.TEXT_COLOR, position = self.menu_position, text_style = self.text_style)
            self.message_position = utils.cr((int(-0.2 * self.config.SCREEN_RESOLUTION['col']),  int(-0.3 * self.config.SCREEN_RESOLUTION['row'])))
            self.message_text = ''
            self.screen.render_text(self.message_text, color = self.config.TEXT_COLOR, position = self.message_position, text_style = self.text_style)
        
        self.update_user_interface_items()
        
        self.command = ''
        self.message_text = 'no message'

    def update_user_interface_items(self):
        '''
        Update Psychopy items that make the user interface
        '''
        if self.config.TEXT_ENABLE:            
            self.screen.render_text(self.menu_text, color = self.config.TEXT_COLOR, position = self.menu_position, text_style = self.text_style)
            self.screen.render_text(self.message_text, color = self.config.TEXT_COLOR, position = self.message_position, text_style = self.text_style)
            self.screen.flip()

    def display_message(self,  txt):
        '''
        Instant display  of message on the screen
        '''
        self.message_text = self.message_text + '\n' + txt
        if len(self.message_text) > self.config.MAX_MESSAGE_LENGTH:
            self.message_text = self.message_text[len(self.message_text) - self.config.MAX_MESSAGE_LENGTH:len(self.message_text)]
        if self.config.TEXT_ENABLE and not self.config.ENABLE_PRE_EXPERIMENT:            
            self.update_user_interface_items()
            
    def is_next_pressed(self):
        '''
        Checks if abort  or next segment can come pressed. This check is performed when stimulation runs
        '''
        
        key_pressed = psychopy.event.getKeys([self.config.CMD_NEXT_SEGMENT])       

        if len(key_pressed) > 0:            
            return True
        else:
            return False
        
        
    def isAbortPressed(self):
        '''
        Checks if abort ('a') is pressed. This check is performed when stimulation runs
        '''
        key_pressed = psychopy.event.getKeys([self.config.CMD_ABORT_STIMULUS])
        if len(key_pressed) > 0:            
            return True
        else:
            return False
        
    def user_interface_handler(self,  message = ''):
        """
        Checks if button pressed and updates display if necessary. The pressed buttons are returned so that Command handler could parse
        """        
        keys_pressed = psychopy.event.getKeys(self.accepted_keys)
        if len(keys_pressed) > 0:
            command = 'SOC'+self.config.COMMANDS[keys_pressed[0]]+'EOC' #replace pressed key with command from command lookup table defined for the machine running the user interface
        else:
            command = ''
            
        if message != '':
            self.display_message(message)
            self.update_user_interface_items()
            
        self.command = command
        return command
                
    def close(self):
        pass
        self.screen.close()        
        

        
        
if __name__ == "__main__":
    pass
