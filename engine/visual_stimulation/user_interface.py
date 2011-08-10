import time
import os
from visexpman.engine.generic import utils
import visexpman.engine.generic.graphics as graphics
from OpenGL.GL import *
from OpenGL.GLUT import *

class VisexpmanScreen(graphics.Screen):
    def initialization(self):
        self.clear_screen(color = self.config.BACKGROUND_COLOR)
        #enable blending for overlaying text
#        glEnable(GL_BLEND)
#        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
#        glBlendFunc(GL_ONE, GL_ONE)
        
    
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
        
def experiment_choices(experiment_list):
    '''
    Lists and displays stimulus files that can be found in the default stimulus file folder
    '''
    return '\n'.join([str(i)+' '+experiment_list[i][1].__name__ for i in range(len(experiment_list))])
        
        
if __name__ == "__main__":
#    print '------------------------------start------------------------------'
    ui = UserInterface()    
    while 1:
        cmd = ui.user_interface_handler()
        if cmd != '':
            ui.user_interface_handler(cmd)
        if cmd == 'q':
            break            
        
    time.sleep(1)
#    print '------------------------------end------------------------------'
    
