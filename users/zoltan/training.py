from visexpman.engine.vision_experiment import experiment
class FlashParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FLASH_TIME=0.5
        self.FLASH_PERIOD=3
        self.NFLASHES=10
        self.DOT_SIZE=100#um
        self.runnable = 'FlashExperiment'

class FlashExperiment(experiment.Experiment):
    def run(self):
        
        import numpy
        frquency=0.5#Hz
        duration=10
        tseries=numpy.linspace(0,duration,duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        waveform=0.5*(numpy.sin(tseries*numpy.pi*2*frquency)+1)
        self.show_shape(shape='spot', size=300, color=waveform.reshape(waveform.shape[0],1))
        
        wait_before_after_flash = (self.experiment_config.FLASH_PERIOD-self.experiment_config.FLASH_TIME)/2
        for i in range(self.experiment_config.NFLASHES):
            self.show_fullscreen(color=0.0,duration=wait_before_after_flash)
            self.show_shape(shape='spot', size=self.experiment_config.DOT_SIZE, color=1.0,duration=self.experiment_config.FLASH_TIME,background_color=0.0)
            self.show_fullscreen(color=0.0,duration=wait_before_after_flash)
        self.show_grating(duration=10,velocity=2000,white_bar_width=100,orientation=90)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'FlashParameters')
