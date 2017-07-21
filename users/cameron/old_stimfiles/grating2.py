from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class GratParameters2Co(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WHITE_BAR_WIDTHS = [75.0,150.0,300.0,800.0]
        # random.shuffle(self.SPATIAL_FREQUENCY)      
        self.VELOCITIES = [300.0, 600.0, 800.0, 1100.0, 1500.0]
        # random.shuffle(self.TEMPORAL_FREQUENCY) 
        self.GRATING_DURATION = 6.0 #s, presentation of moving grating
        self.MINIMUM_PERIODS = 5
        self.GRATING_CONTRAST = [0.999] #[0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 0.999]
        self.GRATING_MID_CONTRAST = 0.5#[0.5,  0.4,  0.6,  0.3,  0.7,  0.2,  0.9,  0.1,  0.9,  0.01, 0.99]
        self.GRATING_ANGLE = [0, 90]#[0, 180, 90, 270] #degrees [0, 45, 90, 135, 180, 225, 270, 315]
        self.GRATING_SIZE = utils.cr((0, 0))
        self.GRATING_OFFSET = 1.0 #grating presented without movement
        self.GRATING_PAUSE = 4 #background presentation between gratings
        
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.REPETITIONS = 1 #s
        self.runnable = 'GratExperiment2'        
        self._create_parameters_from_locals(locals())

class GratExperiment2(experiment.Experiment):
    def run(self):
        screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        for repetitions in range(self.experiment_config.REPETITIONS):
            for angle in self.experiment_config.GRATING_ANGLE:
                for velocity in self.experiment_config.VELOCITIES:
                    #duration = 2*white_bar_width/velocity*self.experiment_config.MINIMUM_PERIODS
                    #if duration < self.experiment_config.GRATING_DURATION:
                    duration = self.experiment_config.GRATING_DURATION
                    for white_bar_width in self.experiment_config.WHITE_BAR_WIDTHS:
                        for grating_contrast in self.experiment_config.GRATING_CONTRAST:
                            
                            self.show_grating(duration = self.experiment_config.GRATING_OFFSET,  profile = 'sin',  white_bar_width = white_bar_width,   
                                    display_area = self.experiment_config.GRATING_SIZE,  orientation = angle,  
                                    velocity = 0,  color_contrast = grating_contrast, color_offset = self.experiment_config.GRATING_MID_CONTRAST)
                            self.show_grating(duration = duration,  profile = 'sin',  white_bar_width = white_bar_width,   
                                    display_area = self.experiment_config.GRATING_SIZE,  orientation = angle,  
                                    velocity = velocity,  color_contrast = grating_contrast, color_offset = self.experiment_config.GRATING_MID_CONTRAST) 
                            self.show_fullscreen(duration = self.experiment_config.GRATING_PAUSE, color =  self.experiment_config.BACKGROUND_COLOR)
                            
                            self.show_grating(duration = self.experiment_config.GRATING_OFFSET,  profile = 'sin',  white_bar_width = white_bar_width,   
                                    display_area = self.experiment_config.GRATING_SIZE,  orientation = angle+180,  
                                    velocity = 0,  color_contrast = grating_contrast, color_offset = self.experiment_config.GRATING_MID_CONTRAST)
                            self.show_grating(duration = duration,  profile = 'sin',  white_bar_width = white_bar_width,   
                                    display_area = self.experiment_config.GRATING_SIZE,  orientation = angle+180,  
                                    velocity = velocity,  color_contrast = grating_contrast, color_offset = self.experiment_config.GRATING_MID_CONTRAST) 
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
                
                
  
        
