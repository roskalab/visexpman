from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class GratingParametersWilson(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPATIAL_FREQUENCY = 0.06#CPD
        self.SWEEP_TIME=3.0
        self.CONTRAST=0.125
        self.SPEED=4#cycles/sec
        self.BLANK_TIME=3
        self.TRIALS=8
        self.DIRECTIONS=16
        
        self.DRUG_CONC = 0.0  
        self.BACKGROUND_COLOR=0.0
        self.runnable = 'GratingExperimentWilson'        
        self._create_parameters_from_locals(locals())

class GratingExperimentWilson(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        self.orientations=numpy.arange(0, 360, 360./ec.DIRECTIONS)
        self.period=1.0/ec.SPATIAL_FREQUENCY*30.0 #Assuming that 1 visual degree corresponds to 30 um on mouse retina
        self.white_bar_width=0.5*self.period
        self.speed=ec.SPEED*self.period
        self.offset=ec.CONTRAST*0.5
        self.contrast=ec.CONTRAST*0.5
        
    def run(self):
        ec=self.experiment_config
        for t in range(ec.TRIALS):
            for o in self.orientations:
                self.show_grating(duration = ec.SWEEP_TIME,  profile = 'sin',  white_bar_width = self.white_bar_width,   
                                    orientation = o, velocity = self.speed,  color_contrast = self.contrast, color_offset = self.offset)
                self.show_fullscreen(duration =ec.BLANK_TIME, color =  self.offset)
                if self.abort:
                    break
            if self.abort:
                break
                
