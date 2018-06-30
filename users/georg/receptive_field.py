from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldExploreNew(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.DISPLAY_SIZE=self.machine_config.SCREEN_SIZE_UM
        self.NROWS = 8
        self.NCOLUMNS = 14
        self.ON_TIME = 0.5
        self.OFF_TIME = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  True
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
