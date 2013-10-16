from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class BlackPre(experiment.PreExperiment):    
    def run(self):
        self.show_fullscreen(color = 0.0, duration = 0,flip=False)

class MovingGratingPre(experiment.PreExperiment):    
    def run(self):
        if hasattr(self.experiment_config, 'PROFILE'):
            profile = self.experiment_config.PROFILE
        else:
            profile = 'sqr'
        self.show_grating(duration = 0, profile = profile,
                            orientation = self.experiment_config.ORIENTATIONS[0], 
                            velocity = 0, white_bar_width = self.experiment_config.WHITE_BAR_WIDTHS[0],
                            duty_cycle = self.experiment_config.DUTY_CYCLES[0], part_of_drawing_sequence = True)
