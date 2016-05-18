from visexpman.engine.vision_experiment import experiment
import numpy,itertools,time,inspect

class ChirpParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE = 3500
        self.TEMPORAL_FREQUENCIES=[5.0]
        self.DURATIONS=[2.0]
        self.REPEATS=3
        self.SWITCH_TIME=0.4
        self.PAUSE=2
        self.runnable = 'ChirpExp'
        self._create_parameters_from_locals(locals())
        
class ChirpExp(experiment.Experiment):
    def generate_chirp_waveform(self):
        nperiods=[[d,f,d*f] for d,f in itertools.product(self.experiment_config.DURATIONS,self.experiment_config.TEMPORAL_FREQUENCIES)]
        waveforms=[]
        for d,frq in itertools.product(self.experiment_config.DURATIONS,self.experiment_config.TEMPORAL_FREQUENCIES):
            frq*=1.0/self.machine_config.TIME_CORRECTION
            nperiod=d*frq
            amplitudes=numpy.arange(nperiod)/(nperiod-1)
            t=numpy.linspace(0,1.0/frq-1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE,1.0/frq*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            waveform=numpy.concatenate([a*numpy.sin(t*numpy.pi*2*frq) for a in amplitudes])
            waveforms.append([d,frq,waveform])
        return waveforms
            
    def switch_filter(self,filterid, block_duration, chirp_frequency):
        self._save_stimulus_frame_info(inspect.currentframe())
        self.parallel_port.set_data_bit(6, filterid, log = False)
        time.sleep(self.experiment_config.SWITCH_TIME)

    def run(self):
        self.show_fullscreen(color=0.5,duration=0)
        for r in range(self.experiment_config.REPEATS):
            for duration, frq, waveform in self.generate_chirp_waveform():
                for filterid in [0,1]:
                    self.switch_filter(filterid,duration, frq)
                    self.show_shape(shape='spot', size=self.experiment_config.SIZE,color=waveform.reshape((waveform.shape[0],1)),background_color=0.5)
                    self.show_fullscreen(color=0.5,duration=self.experiment_config.PAUSE*self.machine_config.TIME_CORRECTION)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'ChirpParameters')


