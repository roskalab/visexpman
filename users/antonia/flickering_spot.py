import numpy
from visexpman.engine.vision_experiment import experiment

class FlickeringSpotParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE=1000#um
        self.GAUSSIAN_STD=0.167
        self.GAUSSIAN_MEAN=0.5
        self.DURATION=10.0#s
        self.BACKGROUND=0.5
        self.WAIT_BEFORE_AFTER=5#s
        self.runnable='FlickeringSpotExperiment'
        
class FlickeringSpotExperiment(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        nframes=int(ec.DURATION*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.intensities=numpy.array([numpy.random.normal(ec.GAUSSIAN_MEAN,ec.GAUSSIAN_STD,nframes)]).T
        
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(duration=ec.WAIT_BEFORE_AFTER,color=ec.BACKGROUND)
        self.show_shape(shape='spot', size=ec.SPOT_SIZE,color=self.intensities,background_color=ec.BACKGROUND)
        self.show_fullscreen(duration=ec.WAIT_BEFORE_AFTER,color=ec.BACKGROUND)

if __name__ == "__main__":
    
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'FlickeringSpotParameters')
    
