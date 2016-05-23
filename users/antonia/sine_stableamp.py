from visexpman.engine.vision_experiment import experiment
import numpy,itertools,time,inspect

class SineStableAmplitudeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE = 2000
        self.CONTRASTS=[0.5, 0.4, 0.3, 0.2, 0.1]
        self.TEMPORAL_FREQUENCY=3.0
        self.NPERIODS=6
        self.REPEATS= 5
        self.SWITCH_TIME=1.0
        self.PAUSE=5
        self.runnable = 'SineStableAmplitudeExp'
        self._create_parameters_from_locals(locals())
        
class SineStableAmplitudeExp(experiment.Experiment):
            
    def switch_filter(self,filterid):
        self._save_stimulus_frame_info(inspect.currentframe())
        self.parallel_port.set_data_bit(6, filterid, log = False)
        time.sleep(self.experiment_config.SWITCH_TIME)

    def run(self):
        self.show_fullscreen(color=0.5,duration=0)
        sine_duration=float(self.experiment_config.NPERIODS)/(self.experiment_config.TEMPORAL_FREQUENCY/self.machine_config.TIME_CORRECTION)
        t=numpy.linspace(0,sine_duration-1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE,int(sine_duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE))
        waveform=numpy.sin(t*numpy.pi*2*self.experiment_config.TEMPORAL_FREQUENCY/self.machine_config.TIME_CORRECTION)
        for r in range(self.experiment_config.REPEATS):
            for contrast in self.experiment_config.CONTRASTS:
                for filterid in [0,1]:
                    self.switch_filter(filterid)
                    waveform_scaled=waveform*contrast+0.5
                    self.show_shape(shape='spot', size=self.experiment_config.SIZE,color=waveform_scaled.reshape((waveform_scaled.shape[0],1)),background_color=0.5)
                    self.show_fullscreen(color=0.5,duration=0)
                    if self.abort: break
                if self.abort: break
            self.show_fullscreen(color=0.5,duration=self.experiment_config.PAUSE*self.machine_config.TIME_CORRECTION)
            if self.abort: break

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'ChirpParameters')


