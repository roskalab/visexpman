from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class GratParametersTemp(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPATIAL_FREQUENCY = [0.004] #[0.0013,  0.0025,  0.004,  0.01,  0.02,  0.0398,  0.0794,  0.156] 
        # random.shuffle(self.SPATIAL_FREQUENCY)      
        self.TEMPORAL_FREQUENCY = [0.15,  0.2475,  0.4085,  0.6742,  1.1126,  1.8361,  3.03,  5.0] # [0.15,  0.2475,  0.4085,  0.6742,  1.1126,  1.8361,  3.03,  5.0]
        # random.shuffle(self.TEMPORAL_FREQUENCY) 
        self.GRATING_CONTRAST = [0.9] #[0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 0.999]
        self.GRATING_MID_CONTRAST = [0.5] #[0.5,  0.4,  0.6,  0.3,  0.7,  0.2,  0.9,  0.1,  0.9,  0.01, 0.99]
        self.GRATING_ANGLE = [0] #degrees [0, 45, 90, 135, 180, 225, 270, 315]
        self.GRATING_SIZE = utils.cr((0, 0))
        self.GRATING_OFFSET = 0.0 #grating presented without movement
        self.GRATING_PAUSE = 0 #background presentation between gratings
        self.GRATING_DURATION = 10.0/2.0 #s, presentation of moving grating                           
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.REPETITIONS = 2 #s
        self.runnable = 'GratExperiment'        
        self._create_parameters_from_locals(locals())

class GratExperiment(experiment.Experiment):
    def run(self):
        screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        for repetitions in range(self.experiment_config.REPETITIONS):
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
                                self.show_grating(duration = self.experiment_config.GRATING_DURATION,  profile = 'sin',  white_bar_width = white_bar_width,   
                                    display_area = self.experiment_config.GRATING_SIZE,  orientation = angle+180,  
                                    velocity = velocity,  color_contrast = grating_contrast, color_offset = grating_mid_contrast)  
                                self.show_fullscreen(duration = self.experiment_config.GRATING_PAUSE, color =  self.experiment_config.BACKGROUND_COLOR)
                            if self.abort:
                                break
                        if self.abort:
                            break
                    if self.abort:
                        break
                if self.abort:
                    break
            if self.abort:
                break
                
                
  
        
