from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random

class fingerPrint2P(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.CONTRAST = [1]
        self.FREQUENCY = [0.5, 5]                           
        self.STIMULATION_LENGTH = 8 #s
        self.REP= 5 
        self.BACKGRD_MID_COLOR = 0.5
        
        self.SPATIAL_FREQUENCY = [0.004, 0.0013] #[0.0013, 0.0025, 0.004, 0.01, 0.02] [0.0013,  0.0025,  0.004,  0.01,  0.02,  0.0398,  0.0794,  0.156] 0.01   
        self.TEMPORAL_FREQUENCY = [0.6742,  3.03] # [0.15,  0.2475,  0.4085,  0.6742,  1.1126,  1.8361,  3.03,  5.0] 0.6742
        self.GRATING_CONTRAST = 0.999 
        self.GRATING_MID_CONTRAST = 0.5 
        self.GRATING_ANGLE = 180
        self.GRATING_SIZE = utils.cr((0, 0))
        self.GRATING_OFFSET = 1.0 #grating presented without movement
        self.GRATING_PAUSE = 0.5 #background presentation between gratings
        self.GRATING_DURATION = 6.0 #s, presentation of moving grating                           
        self.BACKGROUND_COLOR = 0.5
        
   
        self.runnable = 'fingerPrint2Experiment'        
        self._create_parameters_from_locals(locals())

class fingerPrint2Experiment(experiment.Experiment):
    def run(self):
        screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        for rep_all_size in range(self.experiment_config.REP):  
        
            for freq in(self.experiment_config.FREQUENCY):
                for backgrd_contrast in(self.experiment_config.CONTRAST):
                    backgrd_colors = utils.generate_waveform('sin', self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.STIMULATION_LENGTH,
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / freq,
                        backgrd_contrast,  self.experiment_config.BACKGRD_MID_COLOR)                        
                    for j in range(len(backgrd_colors)):
                        self.show_shape(shape = 'o',  color = backgrd_colors[j], 
                                    background_color = backgrd_colors[j],  size = 2500)
                        if self.abort:
                            break
                    if self.abort:
                        break
                if self.abort:
                    break
                    
            for spatial_frequency in self.experiment_config.SPATIAL_FREQUENCY:
                for temporal_frequency in self.experiment_config.TEMPORAL_FREQUENCY:
                    white_bar_width = screen_width/(2 * spatial_frequency * 360.0)                 
                    velocity = temporal_frequency * 2 * white_bar_width
                    
                    self.show_grating(duration = self.experiment_config.GRATING_OFFSET,  profile = 'sqr',  white_bar_width = white_bar_width,   
                            display_area = self.experiment_config.GRATING_SIZE,  orientation = self.experiment_config.GRATING_ANGLE,  
                            velocity = 0,  color_contrast = self.experiment_config.GRATING_CONTRAST, color_offset = self.experiment_config.GRATING_MID_CONTRAST)
                            
                    self.show_grating(duration = self.experiment_config.GRATING_DURATION,  profile = 'sqr',  white_bar_width = white_bar_width,   
                       display_area = self.experiment_config.GRATING_SIZE,  orientation = self.experiment_config.GRATING_ANGLE,  
                       velocity = velocity,  color_contrast = self.experiment_config.GRATING_CONTRAST, color_offset = self.experiment_config.GRATING_MID_CONTRAST) 
                       
                    self.show_fullscreen(duration = self.experiment_config.GRATING_PAUSE, color =  self.experiment_config.BACKGROUND_COLOR)
                    
                    
            
