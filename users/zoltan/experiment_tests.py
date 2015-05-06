from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NaturalBarsConfig1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False
        self.runnable = 'NaturalBarsExperiment1'
        self._create_parameters_from_locals(locals())

class NaturalBarsExperiment1(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        for rep in [0]:
            if self.abort:
                break
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR, flip=False)
            for directions in [0]:
                if self.abort:
                    break
                for speeds in self.experiment_config.SPEED:
                    if self.abort:
                        break
                    if self.experiment_config.ALWAYS_FLY_IN_OUT:
                        fly_in = True
                        fly_out = True
                    else:
                        if self.experiment_config.SPEED.index(speeds) == 0:
                            fly_in = True
                            fly_out = False
                        elif self.experiment_config.SPEED.index(speeds) == len(self.experiment_config.SPEED)-1:
                            fly_in = False
                            fly_out = True
                        else:
                            fly_in = False
                            fly_out = False
#                    fly_in = False
#                    fly_out = False
                    self.show_natural_bars(speed = speeds, duration=self.experiment_config.DURATION, minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out)
                    
                    


if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'NaturalBarsConfig1')
