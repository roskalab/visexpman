
import pygame
import copy
import socket
import time

from visexpman.engine.generic import utils
from visexpman.engine.generic import colors
from visexpman.engine.generic import graphics
from visexpman.engine.generic import file
import Image

from OpenGL.GL import *
from OpenGL.GLUT import *

def experiment_choices(experiment_list):
    '''
    Lists and displays stimulus files that can be found in the default stimulus file folder
    '''
    return '\n'.join([str(i)+' '+experiment_list[i][1].__name__ for i in range(len(experiment_list))])

class VisionExperimentScreen(graphics.Screen):
    '''
    graphics.Screen is amended with vision experiment specific features: menu&message displaying
    '''    
    def __init__(self):
        graphics.Screen.__init__(self, self.config, graphics_mode = 'external')
        self.clear_screen()
        #== Initialize displaying text ==
        self.text_style = GLUT_BITMAP_8_BY_13
        self.menu_position = utils.cr(( int(self.config.MENU_POSITION['col'] * self.config.SCREEN_RESOLUTION['col']), int(self.config.MENU_POSITION['row'] * self.config.SCREEN_RESOLUTION['row'])))
        self.message_position = utils.cr(( int(self.config.MESSAGE_POSITION['col'] * self.config.SCREEN_RESOLUTION['col']), int(self.config.MESSAGE_POSITION['row'] * self.config.SCREEN_RESOLUTION['row'])))
        self.message_to_screen = ['no message']
        self.hide_menu = False
        self.show_bullseye = False
        self.bullseye_size = None
        #== Update text to screen ==
#        self.refresh_non_experiment_screen()
        
    def clear_screen_to_background(self):
        color = self.config.BACKGROUND_COLOR
        if hasattr(self, 'user_background_color'):
            color = colors.convert_color(self.user_background_color)
        self.clear_screen(color = color)
        
    def _display_bullseye(self):
        if self.show_bullseye:
            if self.bullseye_size is None:
                bullseye_path = os.path.join(self.config.PACKAGE_PATH, 'data', 'images', 'bullseye.bmp')
            else:
                self.bullseye_size_in_pixel = int(float(self.bullseye_size) * self.config.SCREEN_UM_TO_PIXEL_SCALE)
                bullseye_path = file.get_tmp_file('bmp')
                im = Image.open(os.path.join(self.config.PACKAGE_PATH, 'data', 'images', 'bullseye.bmp'))
                im = im.resize((self.bullseye_size_in_pixel, self.bullseye_size_in_pixel))
                try:
                    im.save(bullseye_path)
                    self.render_imagefile(bullseye_path, position = self.config.SCREEN_CENTER)
                except:
                    pass
            
        
    def _show_menu(self, flip = False):
        '''
        Show menu text on screen:
         - possible keyboard commands
         - available experiment configurations
        '''
        self.menu_text = self.config.MENU_TEXT + experiment_choices(self.experiment_config_list) + '\nSelected experiment config: '
        if len(self.experiment_config_list) > 0:
            self.menu_text += self.experiment_config_list[int(self.selected_experiment_config_index)][1].__name__
        self.render_text(self.menu_text, color = self.config.TEXT_COLOR, position = self.menu_position, text_style = self.text_style)
        if flip:
            self.flip()

    def _show_message(self, message, flip = False):
        '''
        Display messages coming from command handler
        '''
        #count number of message rows and limit their number
        lines = ''
        for line in message:
            if line is not None and len(line) > 0:
                lines += line + '\n'
        lines = lines.split('\n')
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
        self._display_bullseye()
        if self.config.ENABLE_TEXT:# and not self.hide_menu:#TODO: menu is not cleared - Seems like opengl does not clear 2d text with glclear command     
            self._show_menu()
            self._show_message(self.message_to_screen, flip = flip)

    def run_preexperiment(self):
        pass

class ScreenAndKeyboardHandler(VisionExperimentScreen):
    '''
    VisexpmanScreen is amended with keyboard handling
    '''
    def __init__(self):
        VisionExperimentScreen.__init__(self)
        self.command_domain = 'keyboard'
        self.load_keyboard_commands()
            
    def load_keyboard_commands(self):        
        self.keyboard_commands = copy.deepcopy(self.config.COMMANDS)
        self.separator = '@'
        if hasattr(self, 'experiment_config_list'):
            self.experiment_config_shortcuts = ['{0}'.format(i) for i in range(len(self.experiment_config_list))]#stimulus_file_shortcut
            for shortcut in self.experiment_config_shortcuts:
                self.keyboard_commands['select_experiment' + self.separator + shortcut] = {'key': shortcut, 'domain' : [self.command_domain]}
        else:
            self.experiment_config_shortcuts = []
        
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
        return self._parse_keyboard_command(check_keyboard(),  domain)
        

    def user_interface_handler(self):
        '''
        Updates menu and message on screen, takes care of handling the keyboard
        '''
        self.refresh_non_experiment_screen()
        command = self.keyboard_handler(self.command_domain)
        #Send command to queue
        if command != None:
            self.keyboard_command_queue.put(command)

def check_keyboard():
    '''
    Get pressed key
    '''        
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            key_pressed = pygame.key.name(event.key)                
            return key_pressed
    return
    
if __name__ == "__main__":
    pass
