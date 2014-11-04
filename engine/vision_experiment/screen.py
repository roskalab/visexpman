import pygame
import copy
import socket
import time
import numpy
import unittest
import scipy.ndimage.filters

from visexpman.engine.generic import utils,colors,graphics,fileop
from PIL import Image

from OpenGL.GL import *#TODO: perhaps this is not necessary
from OpenGL.GLUT import *

def experiment_choices(experiment_list):
    '''
    Lists and displays stimulus files that can be found in the default stimulus file folder
    '''
    return '\n'.join([str(i)+' '+experiment_list[i][1].__name__ for i in range(len(experiment_list))])
    
class CaImagingScreen(graphics.Screen):
    '''
    Graphical screen of ca-imaging application
    '''
    def __init__(self, config=None):
        if config is not None:
            self.config=config
        if self.config.FULLSCREEN:
            screen_resolution = graphics.get_screen_size()
        else:
            screen_resolution = utils.cr((800, 600))
        graphics.Screen.__init__(self, self.config, screen_resolution = screen_resolution, graphics_mode = 'external')
        self.clear_screen()
        self.display_configuration = {}
        self.ca_activity = []

    def refresh(self):
        '''
        Images to be displayed must be in a 0..1 range
        '''
        self.clear_screen(color = colors.convert_color(0.0))
        number_of_displays = len(self.display_configuration.keys())
        if not self.imaging_started:
            self.ca_activity = []
        spacing = 10
        if number_of_displays>0 and self.images.has_key('display'):
            self.imsize = utils.rc((0,0))
            if number_of_displays < 4:
                nrows = 1
                ncols = number_of_displays
            else:
                nrows = 2
                ncols = int(numpy.ceil(number_of_displays/nrows))
            self.imsize['row'] = (self.screen_resolution['row']-nrows*spacing)/nrows
            self.imsize['col'] = (self.screen_resolution['col']-ncols*spacing)/ncols
            stretch = float(min( self.imsize['row'], self.imsize['col']))/max(self.images['display'].shape)
            display_id = 0
            for col in range(ncols):
                for row in range(nrows):
                    if self.images.has_key('display'):
                        image2subdisplay = copy.deepcopy(self.images['display'])
                        #Select displayable channels
                        channel2display = self.display_configuration[str(display_id)]['channel_select']
                        if channel2display in self.config.PMTS.keys():
                            keep_channel=colors.colorstr2channel(self.config.PMTS[channel2display]['COLOR'])
                            for col_channel in range(3):
                                if col_channel != keep_channel:
                                    image2subdisplay[:,:,col_channel] = 0
                        #Select image filter
                        filter = self.display_configuration[str(display_id)]['recording_mode_options' if self.experiment_running else 'exploring_mode_options']
                        if filter == 'Ca activity':
                            if self.imaging_started:
                                self.ca_activity.append(image2subdisplay.sum())
                            if len(self.ca_activity)>image2subdisplay.shape[0]-3:
                                self.ca_activity = self.ca_activity[-(image2subdisplay.shape[0]-3):]
                            if len(self.ca_activity)>0:
                                image2subdisplay = numpy.zeros_like(image2subdisplay)
                                activity = numpy.array(self.ca_activity)
                                activity = activity/activity.max()*(image2subdisplay.shape[0]-3)
                                for pi in range(activity.shape[0]):
                                    image2subdisplay[image2subdisplay.shape[0]-int(activity[pi])-2,pi+1]=1.0
                        elif 'median filter' in filter:
                            for cch in range(3):
                                image2subdisplay[:,:,cch] = scipy.ndimage.filters.median_filter(image2subdisplay[:,:,cch],3)
                        pos = utils.rc(((row-0.5*(nrows-1))*(self.imsize['row']+spacing), (col-0.5*(ncols-1))*(self.imsize['col']+spacing)))
                        self.render_image(colors.addframe(image2subdisplay, 0.3), position = pos, stretch = stretch,position_in_pixel=True)
                        display_id += 1
            #Here comes the drawing of images, activity curves
        self.flip()
    
class StimulationScreen(graphics.Screen):
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
        self.menu_text = 'cursors - adjust screen center, '
        commands = self.config.KEYS.keys()
        commands.sort()
        for k in commands:
            self.menu_text+= '{0} - {1}, '.format(self.config.KEYS[k], k)
        self.menu_text = self.menu_text[:-2]
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
            self.render_imagefile(bullseye_path, position = self.stim_context['screen_center'])
            
    def refresh_non_experiment_screen(self, flip = True):
        '''
        Render menu and message texts to screen
        '''
        self.clear_screen_to_background()
        self._display_bullseye()
        if self.show_text and self.config.ENABLE_TEXT:
            self.render_text(self.menu_text +'\n\n\n' + self.screen_text, color = self.text_color, position = self.text_position, text_style = self.text_style)
        #TODO: call  prerun method of pre experiment if exists
        self.flip()

#OBSOLETE
class ScreenAndKeyboardHandler(StimulationScreen):
    '''
    VisexpmanScreen is amended with keyboard handling
    '''
    def __init__(self):
        StimulationScreen.__init__(self)
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
        return self._parse_keyboard_command(graphics.check_keyboard(),  domain)
        

    def user_interface_handler(self):
        '''
        Updates menu and message on screen, takes care of handling the keyboard
        '''
        self.refresh_non_experiment_screen()
        command = self.keyboard_handler(self.command_domain)
        #Send command to queue
        if command != None:
            self.keyboard_command_queue.put(command)
    
class TestCaImagingScreen(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        self.config = GUITestConfig()
        self.config.application_name = 'ca_imaging'
        self.config.ENABLE_FRAME_CAPTURE=True
        from visexpman.users.test import unittest_aggregator
        self.config.CAPTURE_PATH = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_working_folder),'capture')
        fileop.mkdir_notexists(self.config.CAPTURE_PATH,remove_if_exists=True)
        self.config.user = 'test'
    
    def _get_captured_frame(self,remove_file=True):
        fn=fileop.listdir_fullpath(self.config.CAPTURE_PATH)
        fn.sort()
        fn_latest=fn[-1]
        frame=numpy.asarray(Image.open(fn_latest))
        if remove_file:
            [os.remove(f) for f in fn]
        return frame
        
        
    def test_01_image_display(self):
        frame_saving_shifted=True
        cai = CaImagingScreen(self.config)     
        cai.experiment_running=False
        cai.imaging_started=True
        cai.images={}
        cai.ca_activity.extend(range(10))
        cai.images['display'] = numpy.ones((50,100,3))
        cai.display_configuration =\
                {'0': {'channel_select': 'ALL', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'raw'}, }
        cai.refresh()
        if frame_saving_shifted:
            cai.refresh()
        frame=self._get_captured_frame()
        numpy.testing.assert_equal(frame[int(frame.shape[0]*0.4):int(frame.shape[0]*0.6),int(frame.shape[1]*0.4):int(frame.shape[1]*0.6)].flatten(), 255)
        cai.display_configuration =\
                {'0': {'channel_select': 'ALL', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'raw'}, 
                '1': {'channel_select': 'SIDE', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'raw'},
                '2': {'channel_select': 'SIDE', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'Ca activity'}}
        if frame_saving_shifted:
            cai.refresh()
        cai.refresh()
        frame1=numpy.cast['int'](self._get_captured_frame())
        cai.refresh()
        frame2=numpy.cast['int'](self._get_captured_frame())
        hh=numpy.histogram(frame2-frame1,255)
        numpy.testing.assert_equal(hh[0][1:-1],0)#No values in diff image except 0 and 255
        self.assertGreater(hh[0][0],hh[0][-1])
        cai.images['display'] = numpy.zeros((50,100,3))
        cai.images['display'][:,20:22,0] = 0.8
        cai.images['display'][:,30:32,1] = 0.8
        cai.images['display'][:,50:52,:] = 0.8
        noise = numpy.random.random(cai.images['display'].shape)*0.05
        cai.images['display'] += noise
        cai.display_configuration =\
                {'0': {'channel_select': 'ALL', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': '3x3 median filter'}, }
        if frame_saving_shifted:
            cai.refresh()
        cai.refresh()
        frame=self._get_captured_frame()
        #TODO: test for median filter

if __name__ == "__main__":
    unittest.main()
