from visexpman.engine.vision_experiment import experiment

class SmallAndLargeSpotInitialWaitParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SMALL_SPOT_SIZE=120
        self.LARGE_SPOT_SIZE=3900
        self.SPOT_TIME=2
        self.INITIAL_WAIT=10
        self.PRE_WAIT=6
        self.POST_WAIT=5
        self.runnable='SmallAndLargeSpotInitialWaitE'
        self._create_parameters_from_locals(locals())
        
class SmallAndLargeSpotInitialWaitE(experiment.Experiment):
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(color=0.0, duration=ec.INITIAL_WAIT)
        self.show_shape(color=1.0, size=ec.SMALL_SPOT_SIZE, duration=ec.PRE_WAIT)
        self.show_shape(color=1.0, size=ec.LARGE_SPOT_SIZE, duration=ec.SPOT_TIME)
        self.show_shape(color=1.0, size=ec.SMALL_SPOT_SIZE, duration=ec.POST_WAIT)
        
if __name__ == "__main__":
    from visexpman.applications.visexp_app import stimulation_tester
    stimulation_tester('rei', 'StimulusDevelopment', 'SmallAndLargeSpotInitialWaitParameters',ENABLE_FRAME_CAPTURE=not True)
