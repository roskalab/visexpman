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
            
class ManipulationExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
    
        self.experiment_log_copy_path = 'G:\\User\\Antonia\\data\\<filename>'
        self.local_experiment_log_copy = 'C:\\temp\\AntoniaStim\\'
        MAX_LED_VOLTAGE = [3.0, [0.0, 20.0]]
        self.MID_GREY = 165.0/255.0
        self.stimulation_type = 'grating'#flicker, grating, spots        
        self.stimulation_length = 100.0 #s   
        self.pause_between_manipulation_and_control = 10.0 #s
        self.stimulation_protocol = 'manipulation' #control, manipulation, both
        self.PRE_EXPERIMENT_DELAY = 1.0
        
        #flash parameters
        self.enable_flash = True    
        self.flash_width = 10e-3#seconds     
        self.flash_intensity = 1.0#PU       
        self.flash_color = 'blue'
        self.delay_after_flash = 0 #s min 5 sec       
        #general stimulus parameters
        self.spot_size = 200.0 #50-1000 um           
        self.background_color = self.MID_GREY       
        #spot stimulus parameters
        self.on_time = 2.0 #s
        self.off_time = 2.0 #s
        self.spot_contrast = 0.0 #              
        #flickering stimulus parameters
        self.flicker_contrast = 1.0     
        self.flicker_mid_contrast = self.MID_GREY       
        self.flicker_frequency = 2.5 #Hz            
        self.flicker_background = True
        self.flicker_background_max_contrast = 1.0
        self.flicker_background_min_contrast = 0
        self.flicker_background_frequency = 1.0/10.0 #Hz
        self.flicker_background_waveform = 'square' #steps (not implemented), square
        #grating
        self.spatial_frequency = 0.02 #0.0013 0.0025 0.004 0.01 0.02 0.0398 0.0794 0.156 TFtuning(0.039)
        self.temporal_frequency = 0.15 #0.15 0.2475 0.4085 0.6742 1.1126 1.8361 3.03 5.0 SFtuning(1)
        self.grating_contrast = 1.0
        self.grating_mid_contrast = self.MID_GREY
        self.grating_angle = 135.0 #degrees
        self.grating_size = utils.cr((0, 0))        
        
        self.runnable = 'ManipulationExperiment'        
        self._create_parameters_from_locals(locals())

class ManipulationExperiment(experiment.Experiment):
    def run(self):
        stop = False
        self.show_fullscreen(color =  self.experiment_config.background_color)
        if self.experiment_config.enable_flash:
            #generate pulses        
            offsets = [0]
            pulse_widths = [self.experiment_config.flash_width]
            amplitudes = [self.experiment_config.MAX_LED_VOLTAGE *  self.experiment_config.flash_intensity]
            duration = self.experiment_config.delay_after_flash + self.experiment_config.flash_width
#             self.led_controller.set([[offsets, pulse_widths, amplitudes], [offsets, pulse_widths, amplitudes]], duration)
            self.led_controller.set([[offsets, pulse_widths, amplitudes]], duration)
            self.led_controller.start()
            time.sleep(duration)
            
        if self.experiment_config.stimulation_protocol == 'both':
            repetitions = 2
        else:
            repetitions = 1
        
        for i in range(repetitions):            
            #Here starts the stimulus
            if self.experiment_config.stimulation_type == 'spots':
                number_of_periods = int(round(self.experiment_config.stimulation_length / float(self.experiment_config.on_time + self.experiment_config.off_time), 0))
                for period in range(number_of_periods):
                    self.show_shape(shape = 'o',  duration = self.experiment_config.on_time,  color = self.experiment_config.spot_contrast, 
                                        background_color = self.experiment_config.background_color,  size = self.experiment_config.spot_size)
                    self.show_fullscreen(duration = self.experiment_config.on_time, color =  self.experiment_config.background_color)
                    #Break the loop
                    if self.command_buffer.find('stop') != -1:  
                        self.command_buffer = ''                     
                        stop = True
                        break
            elif self.experiment_config.stimulation_type == 'grating':
                screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
                white_bar_width = screen_width/(2*self.experiment_config.spatial_frequency * 360.0)                 
                velocity = self.experiment_config.temporal_frequency * 2 * white_bar_width
                self.show_grating(duration = 2.0,  profile = 'sin',  white_bar_width = white_bar_width,   
                                  display_area = self.experiment_config.grating_size,  orientation = self.experiment_config.grating_angle,  
                                  velocity = 0,  color_contrast = self.experiment_config.grating_contrast, color_offset = self.experiment_config.grating_mid_contrast)
                self.show_grating(duration = self.experiment_config.stimulation_length,  profile = 'sin',  white_bar_width = white_bar_width,   
                                  display_area = self.experiment_config.grating_size,  orientation = self.experiment_config.grating_angle,  
                                  velocity = velocity,  color_contrast = self.experiment_config.grating_contrast, color_offset = self.experiment_config.grating_mid_contrast)
            elif self.experiment_config.stimulation_type == 'flicker':
                contrasts = utils.generate_waveform('sin', self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.stimulation_length,
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.flicker_frequency,
                        self.experiment_config.flicker_contrast,  self.experiment_config.flicker_mid_contrast)
                if self.experiment_config.flicker_background_waveform == 'square':
                    backgrounds = utils.generate_waveform('sqr',  len(contrasts), 
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.flicker_background_frequency,
                        -(self.experiment_config.flicker_background_max_contrast-self.experiment_config.flicker_background_min_contrast),
                         (self.experiment_config.flicker_background_max_contrast + self.experiment_config.flicker_background_min_contrast)/2)                
                for j in range(len(contrasts)):
                    if self.experiment_config.flicker_background:
                        background = backgrounds[j]
                    else:
                        background = self.experiment_config.background_color
                    self.show_shape(shape = 'o',  color = contrasts[j], 
                                        background_color = background,  size = self.experiment_config.spot_size)
                    #Break the loop
                    if self.command_buffer.find('stop') != -1:  
                        self.command_buffer = ''                     
                        stop = True
                        break
            
            if stop:
                break
            self.show_fullscreen(color =  self.experiment_config.background_color)
            #End of stimulus
            if i == 0 and self.experiment_config.stimulation_protocol == 'both':
                
                self.show_fullscreen(duration = self.experiment_config.pause_between_manipulation_and_control, 
                color =  self.experiment_config.background_color)                
                
        if self.experiment_config.enable_flash:
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
