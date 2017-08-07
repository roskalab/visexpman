from visexpman.engine.vision_experiment import experiment


class PlaidConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.INITIAL_WAIT=2.0
        self.MASK_SIZE=400.
        self.DURATION=10
        self.DIRECTION=45
        self.RELATIVE_ANGLE=45
        self.VELOCITY=800
        self.LINE_WIDTH=10
        self.LINE_SPACING_RATIO=20
        self.CONTRAST=1.0
        self.BACKGROUND_COLOR=0.5
        self.REPEATS=1
        self.SINUSOID=False
        self.runnable = 'PlaidExp'
        self._create_parameters_from_locals(locals())

class PlaidExp(experiment.Experiment):
    def run(self):
        self.show_fullscreen(color=self.experiment_config.BACKGROUND_COLOR, duration=self.experiment_config.INITIAL_WAIT)
        for r in range(self.experiment_config.REPEATS):
            self.show_moving_plaid(self.experiment_config.DURATION,
                                    self.experiment_config.DIRECTION,
                                    self.experiment_config.RELATIVE_ANGLE,
                                    self.experiment_config.VELOCITY,
                                    self.experiment_config.LINE_WIDTH,
                                    self.experiment_config.LINE_SPACING_RATIO,
                                    self.experiment_config.MASK_SIZE,
                                    self.experiment_config.CONTRAST,
                                    self.experiment_config.BACKGROUND_COLOR,
                                    self.experiment_config.SINUSOID)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('keisuke', 'StimulusDevelopment', 'PlaidConfig')
