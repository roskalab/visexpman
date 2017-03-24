from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import numpy

class ApproachConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.INITIAL_WAIT=2.0
        self.MASK_SIZE=400.
        self.BAR_WIDTH=60.
        self.SPEED=80#um/s
        self.COLOR=1.0
        self.MOTION='expand' #'expand','shrink','left','right'
        self.REPEATS=1
        self.runnable = 'ApproachExp'
        self._create_parameters_from_locals(locals())

class ApproachExp(experiment.Experiment):
    def run(self):
        for r in range(self.experiment_config.REPEATS):
            self.show_approach_stimulus(self.experiment_config.MOTION, self.experiment_config.BAR_WIDTH, self.experiment_config.SPEED,
                            self.experiment_config.COLOR,self.experiment_config.INITIAL_WAIT, self.experiment_config.MASK_SIZE)
            

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('keisuke', 'StimulusDevelopment', 'ApproachConfig')
