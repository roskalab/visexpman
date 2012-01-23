from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import shutil
import random
            
class ManipulationExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
    
        self.experiment_log_copy_path = 'G:\\User\\Antonia\\data\\<filename>'
        self.local_experiment_log_copy = 'C:\\temp\\AntoniaStim\\'
        MAX_LED_VOLTAGE = [3.0, [0.0, 20.0]]
        self.MID_GREY = 165.0/255.0
        self.STIMULATION_TYPE = 'spots'#flicker, grating, spots        
        self.STIMULATION_LENGTH = 12.0 #s   
        self.PAUSE_BETWEEN_MANIPULATION_AND_CONTROL = 10.0 #s
        self.STIMULATION_PROTOCOL = 'control' #control, manipulation, both
        self.PRE_EXPERIMENT_DELAY = 1.0 #important for trigger of electrophys computer?
        
        #flash parameters
        self.ENABLE_FLASH = True    
        self.FLASH_WIDTH = 10e-3#seconds     
        self.FLASH_INTENSITY = 1.0#PU       
        self.FLASH_COLOR = 'blue'
        self.DELAY_AFTER_FLASH = 0 #s min 5 sec       
        #general stimulus parameters           
        self.BACKGROUND_COLOR = self.MID_GREY       
        #general spot stimulus parameters
        self.SPOT_SIZE = [200] # [100,  200,  300,  400,  500,  1000] # 
        self.ON_TIME = 2.0 #s
        self.OFF_TIME = 2.0 #s
        self.SPOT_CONTRAST = [168,  188,  255] # [168,  175,  177,  180,  185,  188,  195,  205,  209,  255]            
        #flickering stimulus parameters
        self.FLICKER_CONTRAST = 1.0     
        self.FLICKER_MID_CONTRAST = self.MID_GREY       
        self.FLICKER_FREQUENCY = 2.5 #Hz            
        self.FLICKER_BACKGROUND = True
        self.FLICKER_BACKGROUND_MAX_CONTRAST = 1.0
        self.FLICKER_BACKGROUND_MIN_CONTRAST = 0
        self.FLICKER_BACKGROUND_FREQUENCY = 1.0/10.0 #Hz
        self.FLICKER_BACKGROUND_WAVEFORM = 'square' #steps (not implemented), square
        #grating parameters
        self.SPATIAL_FREQUENCY = [0.0398] #[0.0013,  0.0025,  0.004,  0.01,  0.02,  0.0398,  0.0794,  0.156]  # TFtuning(0.039)
        random.shuffle(self.SPATIAL_FREQUENCY)      
        self.TEMPORAL_FREQUENCY = [1] # [0.15,  0.2475,  0.4085,  0.6742,  1.1126,  1.8361,  3.03,  5.0] # SFtuning(1)
        random.shuffle(self.TEMPORAL_FREQUENCY) 
        self.GRATING_CONTRAST = 1
        self.GRATING_MID_CONTRAST = self.MID_GREY
        self.GRATING_ANGLE = 135.0 #degrees
        self.GRATING_SIZE = utils.cr((0, 0))
        self.GRATING_OFFSET = 2.0 #grating presented without movement
        self.GRATING_PAUSE = 2.0 #background presentation between gratings
        
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
                for spatial_frequency in self.experiment_config.SPATIAL_FREQUENCY:
                    for temporal_frequency in self.experiment_config.TEMPORAL_FREQUENCY:
                        white_bar_width = screen_width/(2 * spatial_frequency * 360.0)                 
                        velocity = temporal_frequency * 2 * white_bar_width
                        self.show_grating(duration = self.experiment_config.GRATING_OFFSET,  profile = 'sin',  white_bar_width = white_bar_width,   
                                  display_area = self.experiment_config.GRATING_SIZE,  orientation = self.experiment_config.GRATING_ANGLE,  
                                  velocity = 0,  color_contrast = self.experiment_config.GRATING_CONTRAST, color_offset = self.experiment_config.GRATING_MID_CONTRAST)
                        self.show_grating(duration = (self.experiment_config.stimulation_length - len(self.experiment_config.SPATIAL_FREQUENCY) * len(self.experiment_config.TEMPORAL_FREQUENCY) * self.experiment_config.GRATING_OFFSET * self.experiment_config.GRATING_PAUSE) / (len(self.experiment_config.SPATIAL_FREQUENCY) * len(self.experiment_config.TEMPORAL_FREQUENCY)) ,  profile = 'sin',  white_bar_width = white_bar_width,   
                                  display_area = self.experiment_config.GRATING_SIZE,  orientation = self.experiment_config.GRATING_ANGLE,  
                                  velocity = velocity,  color_contrast = self.experiment_config.GRATING_CONTRAST, color_offset = self.experiment_config.GRATING_MID_CONTRAST)  
                        self.show_fullscreen(duration = self.experiment_config.GRATING_PAUSE, color =  self.experiment_config.BACKGROUND_COLOR)     
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
                                        background_color = background,  size = self.experiment_config.SPOT_SIZE)
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
