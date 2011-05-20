import time
import os

from OpenGL.GL import *

import psychopy.visual
import psychopy.event
import psychopy.monitors
import generic.utils

class UserInterface():
    '''
    UserInterface is responsible for handling keystrokes and displaying messages on screen. Display handling is taken over by StimulationControl when software leaves idle state       
    '''
    def __init__(self,  config):
        
        self.config = config
        #Initializing display, setting screen resolution, background color, hiding mouse cursor, quantities are interpreted in pixels        
        self.screen = psychopy.visual.Window(self.config.SCREEN_RESOLUTION, color = utils.convert_color(self.config.BACKGROUND_COLOR), colorSpace = 'rgb',  fullscr = self.config.FULLSCR, allowGUI = False,  units="pix") #create a window
        #Set acceptable framerate and give warning when frame drop occurs
        self.screen._refreshThreshold=1/float(self.config.EXPECTED_FRAME_RATE)+float(self.config.FRAME_DELAY_TOLERANCE) * 1e-3
        self.screen.setGamma(self.config.GAMMA)        
        
        #shortcuts to stimulus files
        n_stimulus_files = len(os.listdir(self.config.STIMULATION_FOLDER_PATH))
        if n_stimulus_files > 10:
            n_stimulus_files = 10
        stimulus_file_shortcut = []
        for i in range (n_stimulus_files):
            stimulus_file_shortcut.append(str(i))        
        self.accepted_keys = self.config.KEYS + stimulus_file_shortcut 
        
        self.clear_stimulus = True
        
        #Display menu
        position = (0, 0)   
        if self.config.TEXT_ENABLE:
            self.menu = psychopy.visual.TextStim(self.screen,  text = self.config.MENU_TEXT + self.listStimulusFiles(),  pos = position,  color = self.config.TEXT_COLOR,  height = self.config.TEXT_SIZE) 
            position = (0,  int(-0.4 * self.config.SCREEN_RESOLUTION[1]))
            self.message = psychopy.visual.TextStim(self.screen,  text = '',  pos = position,  color = self.config.TEXT_COLOR,  height = self.config.TEXT_SIZE)
            self.user_interface_items = [self.menu,  self.message]             
        
        self.update_user_interface_items()
        
        self.command = ''
        self.message_text = ''

    def update_user_interface_items(self):
        '''
        Update Psychopy items that make the user interface
        '''
        if self.config.TEXT_ENABLE and self.clear_stimulus:            
            for user_interface_item in self.user_interface_items:
                user_interface_item.draw()
            self.screen.flip()

    def display_message(self,  txt):
        '''
        Instant display  of message on the screen
        '''
        self.message_text = self.message_text + '\n' + txt
        if len(self.message_text) > self.config.MAX_MESSAGE_LENGTH:
            self.message_text = self.message_text[len(self.message_text) - self.config.MAX_MESSAGE_LENGTH:len(self.message_text)]
        if self.config.TEXT_ENABLE and self.clear_stimulus:            
            self.message.setText(self.message_text)
            self.message.draw()        
            self.screen.flip()
            
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
            command = keys_pressed[0]
        else:
            command = ''
            
        if message != '':
            self.display_message(message)
            self.update_user_interface_items()
            
        self.command = command
        return command
        
    def listStimulusFiles(self):
        '''
        Lists and displays stimulus files that can be found in the default stimulus file folder
        '''
        stimulus_files = utils.filtered_file_list(self.config.STIMULATION_FOLDER_PATH,  ['stimulus',  'example'])
        stimulus_files.sort()
        stimulus_files_string = '\n\n'
        index = 0        
        for stimulus_file in stimulus_files:            
            stimulus_files_string = stimulus_files_string + str(index) + ' ' + stimulus_file + '\n'
            index = index + 1
        return stimulus_files_string
        
    def close(self):        
        self.screen.close()        
        
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
    
