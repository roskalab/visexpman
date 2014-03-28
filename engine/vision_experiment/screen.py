import pygame
import copy
import socket
import time

from visexpman.engine.generic import utils
from visexpman.engine.generic import colors
from visexpman.engine.generic import graphics
from visexpman.engine.generic import fileop
try:
    import Image
except ImportError:
    from PIL import Image

from OpenGL.GL import *#TODO: perhaps this is not necessary
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
        self.max_lines = int(self.config.SCREEN_RESOLUTION['row']/13.0)
        self.max_chars =  int(self.config.SCREEN_RESOLUTION['col']/(8+13.0))
        self.menu_text = 'ESCAPE - exit, b - toggle bullseye, h - Hide text, w - white, d - black, g - mid grey, u - user defined color, cursors - adjust screen center'
        #Split menu text to lines
        parts = [[]]
        self.menu_lines = 0
        char_count = 0
        for item in self.menu_text.split(','):
            char_count += len(item)
            if char_count > self.max_chars:
                char_count = 0
                self.menu_lines += 1
                parts.append([])
            parts[self.menu_lines].append(item)
        self.menu_text = '\n'
        for part in parts:
            self.menu_text = self.menu_text + ', '.join(part) + '\n'
        self.max_print_lines = self.max_lines-self.menu_lines-6
        self.screen_text = ''
        self.show_text = True
        self.show_bullseye = False
        self.bullseye_size = None
        self.text_color = colors.convert_color(self.config.TEXT_COLOR, self.config)
        self.text_position = copy.deepcopy(self.config.UPPER_LEFT_CORNER)
        self.text_position['row'] -= 13
        self.text_position['col'] += 13
        self.refresh_non_experiment_screen()
        
    def clear_screen_to_background(self):
        self.clear_screen(color = colors.convert_color(self.stim_context['background_color'], self.config))
        
    def _display_bullseye(self):
        if self.show_bullseye:
            if self.bullseye_size is None:
                bullseye_path = os.path.join(self.config.PACKAGE_PATH, 'data', 'images', 'bullseye.bmp')
            else:
                self.bullseye_size_in_pixel = int(float(self.bullseye_size) * self.config.SCREEN_UM_TO_PIXEL_SCALE)
                bullseye_path = fileop.get_tmp_file('bmp')
                im = Image.open(os.path.join(self.config.PACKAGE_PATH, 'data', 'images', 'bullseye.bmp'))
                im = im.resize((self.bullseye_size_in_pixel, self.bullseye_size_in_pixel))
                im.save(bullseye_path)
            self.render_imagefile(bullseye_path, position = utils.rc_multiply_with_constant(self.stim_context['screen_center'], self.config.SCREEN_UM_TO_PIXEL_SCALE))
            
    def refresh_non_experiment_screen(self, flip = True):
        '''
        Render menu and message texts to screen
        '''
        self.clear_screen_to_background()
        self._display_bullseye()
        if self.show_text and self.config.ENABLE_TEXT:
            self.render_text(self.menu_text +'\n\n\n' + self.screen_text, color = self.text_color, position = self.text_position, text_style = self.text_style)
        self.flip()

    def run_preexperiment(self):
        pass

class ScreenAndKeyboardHandler(VisionExperimentScreen):
    '''
    VisexpmanScreen is amended with keyboard handling
    '''
    def __init__(self):
        VisionExperimentScreen.__init__(self)
        self.command_domain = 'keyboard'
        import Queue
        self.keyboard_command_queue = Queue.Queue()
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
    keys_pressed = []
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            key_pressed = pygame.key.name(event.key)                
            keys_pressed.append(key_pressed)
    return keys_pressed
    
if __name__ == "__main__":
    pass
