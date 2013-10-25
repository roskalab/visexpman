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
