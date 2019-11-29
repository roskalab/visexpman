import copy,os,multiprocessing
import socket
import time
import numpy
import unittest
import scipy.ndimage.filters

from visexpman.engine.generic import utils,colors,graphics,fileop,signal
from PIL import Image

def experiment_choices(experiment_list):
    '''
    Lists and displays stimulus files that can be found in the default stimulus file folder
    '''
    return '\n'.join([str(i)+' '+experiment_list[i][1].__name__ for i in range(len(experiment_list))])
    
class CaImagingScreen(graphics.Screen):#OBSOLETE
    '''
    Graphical screen of ca-imaging application
    '''
    def __init__(self, config=None):
        if config is not None:
            self.config=config
        if self.config.FULLSCREEN:
            screen_resolution = graphics.get_screen_size()
        else:
            screen_resolution = utils.cr((1024, 768))
        graphics.Screen.__init__(self, self.config, screen_resolution = screen_resolution, graphics_mode = 'external')
        self.clear_screen()
        self.display_configuration = {}
        self.ca_activity = []
        
    def prepare_screen_for_live_imaging(self):
        self.ca_activity = []

    def refresh(self):
        '''
        Images to be displayed must be in a 0..1 range
        '''
        self.clear_screen(color = colors.convert_color(0.0))
        number_of_displays = len(self.display_configuration.keys())
        spacing = 10
        frame_color = numpy.array([0.3, 0.0, 0.0]) if self.laser_on else 0.3
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
            display_names = self.display_configuration.keys()
            display_names.sort()
            for col in range(ncols):
                for row in range(nrows):
                    if self.images.has_key('display'):
                        image2subdisplay = copy.deepcopy(self.images['display'])
                        #Select displayable channels
                        channel2display = self.display_configuration[display_names[display_id]]['channel_select']
                        if channel2display in self.config.PMTS.keys():
                            keep_channel=colors.colorstr2channel(self.config.PMTS[channel2display]['COLOR'])
                            for col_channel in range(3):
                                if col_channel != keep_channel:
                                    image2subdisplay[:,:,col_channel] = 0
                        #Select image filter
                        filter = self.display_configuration[display_names[display_id]]['recording_mode_options' if self.experiment_running else 'exploring_mode_options']
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
                        elif filter == 'Histogram shift':
                            for cch in range(3):
                                image2subdisplay[:,:,cch] = signal.histogram_shift(image2subdisplay[:,:,cch],[0.0,1.0],resolution=64)
                        elif filter == 'Half scale':
                            image2subdisplay *= 2
                        elif filter == 'Quater scale':
                            image2subdisplay *= 4
                        elif filter == '1/8th scale':
                            image2subdisplay *= 8
                            
                        if 'scale' in filter:
                            image2subdisplay = numpy.where(image2subdisplay>1,1,image2subdisplay)
                            
                            
                        pos = utils.rc(((row-0.5*(nrows-1))*(self.imsize['row']+spacing), (col-0.5*(ncols-1))*(self.imsize['col']+spacing)))
                        self.render_image(colors.addframe(image2subdisplay, frame_color), position = pos, stretch = stretch,position_in_pixel=True)
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
        from OpenGL.GLUT import GLUT_BITMAP_8_BY_13
        self.text_style = GLUT_BITMAP_8_BY_13
        self.max_lines = int(self.config.SCREEN_RESOLUTION['row']/13.0)
        self.max_chars =  int(self.config.SCREEN_RESOLUTION['col']/(8+13.0))
        self.menu_text = 'cursors - adjust screen center, '
        commands = self.config.KEYS.keys()
        if hasattr(commands,  'sort'):
            commands.sort()
        else:
            sorted(commands)
        for k in commands:
            self.menu_text+= '\n{0} - {1} '.format(self.config.KEYS[k], k)
        if self.config.PLATFORM in ['behav', 'epos', 'hi_mea', 'standalone', 'intrinsic']:
            ct = 0
            for ec in self.experiment_configs:
                self.menu_text+= '\n{0} - {1} '.format(ct, ec)
                ct +=1
            self.experiment_select_commands = map(str, range(ct))
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
        self.bullseye_size = 100.0
        self.bullseye_type = 'bullseye'
        self.bullseye_image = numpy.cast['float'](numpy.asarray(Image.open(os.path.join(fileop.visexpman_package_path(), 'data', 'images', 'bullseye.bmp'))))/255
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION=='down':
            self.bullseye_image = numpy.flipud(self.bullseye_image)
        self.bullseye_stretch_factor = self.config.SCREEN_UM_TO_PIXEL_SCALE/float(self.bullseye_image.shape[0])
        self.text_color = colors.convert_color(self.config.TEXT_COLOR, self.config)
        self.text_position = copy.deepcopy(self.config.UPPER_LEFT_CORNER)
        self.text_position['row'] -= 13
        self.text_position['col'] += 13
        
        self.refresh_non_experiment_screen()
        
    def clear_screen_to_background(self):
        self.clear_screen(color = colors.convert_color(self.stim_context['background_color'], self.config))
        
    def _display_bullseye(self):
        if self.show_bullseye:
            try:
                sc=utils.cr((self.stim_context['screen_center'][0], self.stim_context['screen_center'][1]))
            except:
                sc=utils.rc((0,0))
            if self.config.SCREEN_MODE=='psychopy':
                if not hasattr(self, 'be'):
                    from psychopy import visual
                    fn=os.path.join(fileop.visexpman_package_path(), 'data', 'images', 'bullseye.bmp')
                    pixel_size=self.config.SCREEN_WIDTH/float(self.config.SCREEN_RESOLUTION['col'])
                    s=self.bullseye_size*1e-4/pixel_size
                    self.be=visual.ImageStim(self.screen, image=fn, units='pix', pos=(sc['col'],0), size=s)#convert um to cm
                    self.be.setAutoDraw(True)
            else:
                if self.bullseye_type == 'L':
                    self.draw_L(self.bullseye_size*self.config.SCREEN_UM_TO_PIXEL_SCALE, sc)
                elif self.bullseye_type == 'square':
                    self.draw_square(self.bullseye_size*self.config.SCREEN_UM_TO_PIXEL_SCALE, sc)
                elif self.bullseye_type == 'bullseye':
                    self.render_image(self.bullseye_image, position = sc, stretch = self.bullseye_stretch_factor*self.bullseye_size)
                elif self.bullseye_type == 'spot':
                    self.draw_circle(self.bullseye_size*self.config.SCREEN_UM_TO_PIXEL_SCALE, position = sc)
        else:
            if hasattr(self, 'be'):
                self.be.setAutoDraw(False)
                del self.be
                
            
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

class CaptureImagingTrigger(multiprocessing.Process):
    '''
    With the help of IOboard it measures imaging frquency
    Captures imaging triggers
    '''
    def __init__(self, port, std_limits,  buffer_size=16, fps=40):
        multiprocessing.Process.__init__(self)
        self.port=port
        self.tfps=fps
        self.std_limits=std_limits
        self.command=multiprocessing.Queue()
        self.trigger=multiprocessing.Queue()
        self.fps=multiprocessing.Queue()
        self.log=multiprocessing.Queue()
        self.buffer_size=buffer_size
        
    def run(self):
        import serial
        self.s=serial.Serial(self.port, 1000000,timeout=0.005)
        time.sleep(2.5)
        self.s.write('waveform,{0},0,0\r\n'.format(int(self.tfps)))
        time.sleep(1)
        self.s.write('fps_meas,1\r\n')
        time.sleep(0.1)
        r=self.s.read(100)
        frame_interval_buffer=numpy.zeros(self.buffer_size)
        buffer_index=0
        fps_sent=False
        fps_acknowledge=False
        phase_sent=False
        pulse_counter=0
        self.log.put(r)
        self.log.put('Prep done')
        while True:
            if not self.command.empty():
                command=self.command.get()
                if command=='terminate':
                    break
            else:
                command=None
            self.wait_serial(5)
            msg=self.s.read(5)
            self.log.put(msg)
            try:
                frame_interval_buffer[buffer_index]=int(msg)
            except ValueError:
                continue
            buffer_index+=1
            pulse_counter+=1
            if buffer_index==self.buffer_size:
                buffer_index=0
            frame_interval_std=frame_interval_buffer.std()
            if not fps_sent and pulse_counter>self.buffer_size:
                frame_interval_mean=frame_interval_buffer.mean()
                if frame_interval_std<self.std_limits['stable']:
                    fps_sent=True
                    self.fps.put(frame_interval_mean)
            elif not fps_acknowledge:
                if command=='fps_acknowledge':
                    fps_acknowledge=True
            elif not phase_sent:
                self.trigger.put('phase')
                phase_sent=True
        self.s.write('fps_meas,0\r\n')
        self.s.write('stop\r\n')
        time.sleep(0.1)
        self.s.close()
        
    def wait_serial(self,n):
        if os.name!='nt':
            return
        while True:
            if self.s.inWaiting()==n:
                break
            time.sleep(0)
        
    
class TestCaImagingScreen(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        self.config = GUITestConfig()
        self.config.user_interface_name = 'ca_imaging'
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
        
    @unittest.skip('')
    def test_01_image_display(self):
        frame_saving_shifted=True
        cai = CaImagingScreen(self.config)     
        cai.experiment_running=False
        cai.imaging_started=True
        cai.laser_on = False
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
        #check if frame is grey (laser off)
        image_frame_indexes=numpy.nonzero(numpy.where(numpy.logical_or(frame == int(0.3*255),frame == int(0.3*255)+1),1,0))
        self.assertGreater(image_frame_indexes[0].shape[0],0)
        [self.assertIn(i, image_frame_indexes[2]) for i in range(3)]
        cai.display_configuration =\
                {'0': {'channel_select': 'ALL', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'raw'}, 
                '1': {'channel_select': 'SIDE', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'raw'},
                '2': {'channel_select': 'SIDE', 'recording_mode_options': 'raw', 'gridline_select': 'off', 'exploring_mode_options': 'Ca activity'}}
        cai.laser_on = True
        if frame_saving_shifted:
            cai.refresh()
        cai.refresh()
        frame1=numpy.cast['int'](self._get_captured_frame())
        cai.refresh()
        frame2=numpy.cast['int'](self._get_captured_frame())
        hh=numpy.histogram(frame2-frame1,255)
        numpy.testing.assert_equal(hh[0][1:-1],0)#No values in diff image except 0 and 255
        self.assertGreater(hh[0][0],hh[0][-1])
        #check if frame is red (laser on)
        for f in [frame1,frame2]:
            image_frame_indexes=numpy.nonzero(numpy.where(numpy.logical_or(f == int(0.3*255), f == int(0.3*255)+1),1,0))
            self.assertGreater(image_frame_indexes[0].shape[0],0)
            numpy.testing.assert_equal(image_frame_indexes[2], numpy.zeros_like(image_frame_indexes[2]))
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
