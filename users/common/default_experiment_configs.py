from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldExploreDefaultConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.0
        self.SHAPE_SIZE = 200.0
        self.MESH_SIZE = None
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_ZOOM = False
        self.SELECTED_POSITION = 0
        self.ZOOM_MESH_SIZE = utils.rc((3,3))
        self.ENABLE_RANDOM_ORDER = False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
