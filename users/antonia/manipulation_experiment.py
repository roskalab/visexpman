from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.users.test.unittest_aggregator as unittest_aggregator
import shutil
import random
            
class ManipulationExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.experiment_log_copy_path = 'G:\\User\\Antonia\\data\\<filename>'
        self.local_experiment_log_copy = 'C:\\temp\\AntoniaStim\\'
        MAX_LED_VOLTAGE = [3.0, [0.0, 20.0]]
        self.PAUSE_BETWEEN_MANIPULATION_AND_CONTROL = 10.0 #s
        self.STIMULATION_PROTOCOL = 'control' #control, manipulation, both
        self.PRE_EXPERIMENT_DELAY = 1.0 #important for trigger of electrophys computer?
        self.MID_GREY = 162.0/255.0       
        self.BACKGROUND_COLOR = self.MID_GREY
        
        self.DRUG_CONC = 0.0 
        self.STIMULATION_TYPE = 'grating'#flicker, grating, spots, grating_switch        
        self.STIMULATION_LENGTH = 30.0 #s       
         
              
        # spots parameters
        self.SPOT_SIZE = [200] # [100,  200,  300,  400,  500,  1000] # 
        self.ON_TIME = 2.0 #s
        self.OFF_TIME = 2.0 #s
        self.SPOT_CONTRAST = [163.5,  167,  173,  174,  179,  182,  187,  198,  204,  255] # ON [163.5,  167,  173,  174,  179,  182,  187,  198,  204,  255]  OFF  [159,  154,  149,  144,  139,  134,  126,  109,  95,  0]         
        
        #grating parameters
        self.SPATIAL_FREQUENCY = [0.0398] #[0.0013,  0.0025,  0.004,  0.01,  0.02,  0.0398,  0.0794,  0.156]  # TFtuning(0.039)
        # random.shuffle(self.SPATIAL_FREQUENCY)      
        self.TEMPORAL_FREQUENCY = [1.1126] # [0.15,  0.2475,  0.4085,  0.6742,  1.1126,  1.8361,  3.03,  5.0] # SFtuning(1)
        # random.shuffle(self.TEMPORAL_FREQUENCY) 
        self.GRATING_CONTRAST = [1] #[0.5,  0.4,  0.6,  0.3,  0.7,  0.2,  0.9,  0.1,  0.9,  0.01, 0.99]
        self.GRATING_MID_CONTRAST = [162.0/255.0] #[162.0/255.0,  154.0/255.0,  167.0/255.0,  144.0/255.0,  174.0/255.0,   134.0/255.0,   182.0/255.0,  109.0/255.0,  198.0/255.0]  #10% -90%, 162 50% is mid grey value
        self.GRATING_ANGLE = [0, 180, 315] #degrees [0, 45, 90, 135, 180, 225, 270, 315]
        self.GRATING_SIZE = utils.cr((0, 0))
        self.GRATING_OFFSET = 2.0 #grating presented without movement
        self.GRATING_PAUSE = 2.0 #background presentation between gratings
        self.GRATING_DURATION = 4.0 #s, presentation of moving grating
        
        #grating switch parameters
        self.GRATING_SWITCH_CONTRAST = [109.0/255.0,  198.0/255.0]#
        self.GRATING_DURATION_SWITCH = 2 #s
           
        #flicker parameters
        self.FLICKER_CONTRAST = 1.0     
        self.FLICKER_MID_CONTRAST = self.MID_GREY       
        self.FLICKER_FREQUENCY = 1.0 #Hz            
        self.FLICKER_BACKGROUND = True
        self.FLICKER_BACKGROUND_MAX_CONTRAST = 1.0
        self.FLICKER_BACKGROUND_MIN_CONTRAST = 0
        self.FLICKER_BACKGROUND_FREQUENCY = 1/10.0 #Hz
        self.FLICKER_BACKGROUND_WAVEFORM = 'square' #steps (not implemented), square
             
        #flash parameters
        self.ENABLE_FLASH = True    
        self.FLASH_WIDTH = 10e-3#seconds     
        self.FLASH_INTENSITY = 1.0#PU       
        self.FLASH_COLOR = 'blue'
        self.DELAY_AFTER_FLASH = 0 #s min 5 sec   
        
        self.runnable = 'ManipulationExperiment'        
        self._create_parameters_from_locals(locals())

class ManipulationExperiment(experiment.Experiment):
    def run(self):
        stop = False
        self.show_fullscreen(color =  self.experiment_config.BACKGROUND_COLOR)
        if self.experiment_config.ENABLE_FLASH:
            #generate pulses        
            offsets = [0]
            pulse_widths = [self.experiment_config.FLASH_WIDTH]
            amplitudes = [self.experiment_config.MAX_LED_VOLTAGE *  self.experiment_config.FLASH_INTENSITY]
            duration = self.experiment_config.DELAY_AFTER_FLASH + self.experiment_config.FLASH_WIDTH
#             self.led_controller.set([[offsets, pulse_widths, amplitudes], [offsets, pulse_widths, amplitudes]], duration)
            self.led_controller.set([[offsets, pulse_widths, amplitudes]], duration)
            self.led_controller.start()
            time.sleep(duration)
            
        if self.experiment_config.STIMULATION_PROTOCOL == 'both':
            repetitions = 2
        else:
            repetitions = 1
        
        for i in range(repetitions):            
            #Here starts the stimulus
            if self.experiment_config.STIMULATION_TYPE == 'spots':
                number_of_periods = int(round(self.experiment_config.STIMULATION_LENGTH / (float(self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME)*len(self.experiment_config.SPOT_SIZE)*len(self.experiment_config.SPOT_CONTRAST)), 0))
                for period in range(number_of_periods):
                    for spot_size in self.experiment_config.SPOT_SIZE:  
                        for spot_contrast in self.experiment_config.SPOT_CONTRAST:
                            self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = float(spot_contrast)/float(255), 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = spot_size)
                            self.show_fullscreen(duration = self.experiment_config.OFF_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                    #Break the loop
                    if self.command_buffer.find('stop') != -1:  
                        self.command_buffer = ''                     
                        stop = True
                        break
            elif self.experiment_config.STIMULATION_TYPE == 'grating':
                screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
                number_of_periods = int(round(self.experiment_config.STIMULATION_LENGTH / (float(self.experiment_config.GRATING_OFFSET + self.experiment_config.GRATING_DURATION + self.experiment_config.GRATING_PAUSE)*len(self.experiment_config.GRATING_MID_CONTRAST)*len(self.experiment_config.GRATING_CONTRAST)*len(self.experiment_config.TEMPORAL_FREQUENCY)*len(self.experiment_config.SPATIAL_FREQUENCY)*len(self.experiment_config.GRATING_ANGLE)), 0))
                print number_of_periods
                for period in range(number_of_periods):
                    for spatial_frequency in self.experiment_config.SPATIAL_FREQUENCY:
                        for temporal_frequency in self.experiment_config.TEMPORAL_FREQUENCY:
                           white_bar_width = screen_width/(2 * spatial_frequency * 360.0)                 
                           velocity = temporal_frequency * 2 * white_bar_width
                           for grating_mid_contrast in self.experiment_config.GRATING_MID_CONTRAST:
                                for grating_contrast in self.experiment_config.GRATING_CONTRAST:
                                    for angle in self.experiment_config.GRATING_ANGLE:
                                        self.show_grating(duration = self.experiment_config.GRATING_OFFSET,  profile = 'sin',  white_bar_width = white_bar_width,   
                                            display_area = self.experiment_config.GRATING_SIZE,  orientation = angle,  
                                            velocity = 0,  color_contrast = grating_contrast, color_offset = grating_mid_contrast)
                                        self.show_grating(duration = self.experiment_config.GRATING_DURATION,  profile = 'sin',  white_bar_width = white_bar_width,   
                                            display_area = self.experiment_config.GRATING_SIZE,  orientation = angle,  
                                            velocity = velocity,  color_contrast = grating_contrast, color_offset = grating_mid_contrast)  
                                        self.show_fullscreen(duration = self.experiment_config.GRATING_PAUSE, color =  self.experiment_config.BACKGROUND_COLOR)                       
            elif self.experiment_config.STIMULATION_TYPE == 'grating_switch':
                screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
                number_of_periods = int(round(self.experiment_config.STIMULATION_LENGTH / (float(self.experiment_config.GRATING_DURATION_SWITCH)*len(self.experiment_config.GRATING_SWITCH_CONTRAST)*len(self.experiment_config.GRATING_CONTRAST)*len(self.experiment_config.TEMPORAL_FREQUENCY)*len(self.experiment_config.SPATIAL_FREQUENCY)*len(self.experiment_config.GRATING_ANGLE)), 0))
                for period in range(number_of_periods):
                    for spatial_frequency in self.experiment_config.SPATIAL_FREQUENCY:
                        for temporal_frequency in self.experiment_config.TEMPORAL_FREQUENCY:
                            white_bar_width = screen_width/(2 * spatial_frequency * 360.0)                 
                            velocity = temporal_frequency * 2 * white_bar_width
                            for grating_switch_contrast in self.experiment_config.GRATING_SWITCH_CONTRAST:
                                for grating_contrast in self.experiment_config.GRATING_CONTRAST: 
                                    for angle in self.experiment_config.GRATING_ANGLE:
                                        self.show_grating(duration = self.experiment_config.GRATING_DURATION_SWITCH,  profile = 'sin',  white_bar_width = white_bar_width,   
                                            display_area = self.experiment_config.GRATING_SIZE,  orientation = angle,  
                                            velocity = velocity,  color_contrast = grating_contrast, color_offset = grating_switch_contrast)                        
            elif self.experiment_config.STIMULATION_TYPE == 'flicker':
                contrasts = utils.generate_waveform('sin', self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.STIMULATION_LENGTH,
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.FLICKER_FREQUENCY,
                        self.experiment_config.FLICKER_CONTRAST,  self.experiment_config.FLICKER_MID_CONTRAST)
                if self.experiment_config.FLICKER_BACKGROUND_WAVEFORM == 'square':
                    backgrounds = utils.generate_waveform('sqr',  len(contrasts), 
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.FLICKER_BACKGROUND_FREQUENCY,
                        -(self.experiment_config.FLICKER_BACKGROUND_MAX_CONTRAST-self.experiment_config.FLICKER_BACKGROUND_MIN_CONTRAST),
                         (self.experiment_config.FLICKER_BACKGROUND_MAX_CONTRAST + self.experiment_config.FLICKER_BACKGROUND_MIN_CONTRAST)/2)                
                for j in range(len(contrasts)):
                    if self.experiment_config.FLICKER_BACKGROUND:
                        background = backgrounds[j]
                    else:
                        background = self.experiment_config.BACKGROUND_COLOR
                    self.show_shape(shape = 'o',  color = contrasts[j], 
                                        background_color = background,  size = self.experiment_config.SPOT_SIZE[0])
                    #Break the loop
                    if self.command_buffer.find('stop') != -1:  
                        self.command_buffer = ''                     
                        stop = True
                        break
            
            if stop:
                break
            self.show_fullscreen(color =  self.experiment_config.BACKGROUND_COLOR)
            #End of stimulus
            if i == 0 and self.experiment_config.STIMULATION_PROTOCOL == 'both':
                
                self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_MANIPULATION_AND_CONTROL, 
                color =  self.experiment_config.BACKGROUND_COLOR)                
                
        if self.experiment_config.ENABLE_FLASH:
            self.led_controller.release_instrument()
            
    def cleanup(self):
        self.log.flush()
        path = self.experiment_config.experiment_log_copy_path.replace('G:\\User\\Antonia\\data\\', self.experiment_config.local_experiment_log_copy)
        print path
        try:
            shutil.copyfile(self.logfile_path, path)
#             shutil.copyfile(self.logfile_path, self.experiment_config.experiment_log_copy_path)
        except:
            print self.logfile_path, self.experiment_config.experiment_log_copy_path
            print 'not copied for some reason'
