from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class SinusoidalSpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FREQUENCIES = [8, 4, 2, 1, 0.5, 0.25]
        self.DURATION = 8.0
        self.PAUSE = 2.0
        self.BACKGROUND = 0.5
        self.AMPLITUDES = [1.0]
        self.SPOT_DIAMETERS = [300]
        self.WAVEFORM = 'sin'
        self.runnable = 'SpotWaveform'
        self._create_parameters_from_locals(locals())

class MovingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.rc((300, 900)) #um
        self.SPEEDS = [50, 100, 200,400,800,1200] #um/s
        self.SPEEDS = self.SPEEDS[2:]#TMP
        self.AXIS_ANGLE = 0.0
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE_BACKGROUND = 0.5
        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
        self.REPETITIONS = 1
        if self.AXIS_ANGLE >= 180.0:
            null_dir = self.AXIS_ANGLE-180.0
        else:
            null_dir = self.AXIS_ANGLE+180.0
        self.DIRECTIONS = [self.AXIS_ANGLE, null_dir]
        self.SHAPE = 'rect'
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
