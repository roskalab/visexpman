from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.daniel import grating

class MyGrating(grating.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating.MovingGratingNoMarchingConfig._create_parameters(self)
        self.REPEATS = 1
        self._create_parameters_from_locals(locals())
