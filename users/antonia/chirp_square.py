from visexpman.engine.vision_experiment import experiment
import numpy,itertools,time,inspect

class ChirpSquareParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE = 3000
        self.CONTRAST_STEP=0.1
        self.ON_TIME=0.2
        self.OFF_TIME=0.5 
        self.DURATION= 5.0
        self.REPEATS= 5
        self.SWITCH_TIME=2#0.4
        self.runnable = 'ChirpSquareExp'
        self._create_parameters_from_locals(locals())
        
class ChirpSquareExp(experiment.Experiment):
    def generate_pattern(self):
        intensities=numpy.linspace(0.0,1.0,1.0/self.experiment_config.CONTRAST_STEP+1)
        intensities=intensities[numpy.where(intensities!=0.5)[0]]
        numpy.random.shuffle(intensities)
        nflashes=int(numpy.ceil(self.experiment_config.DURATION/(self.experiment_config.ON_TIME+self.experiment_config.OFF_TIME)))
        intensities=intensities[:nflashes]
        return intensities
            
    def switch_filter(self,filterid):
        self._save_stimulus_frame_info(inspect.currentframe())
        self.parallel_port.set_data_bit(6, filterid, log = False)
        time.sleep(self.experiment_config.SWITCH_TIME)

    def run(self):
        self.show_fullscreen(color=0.5,duration=0)
        for r in range(self.experiment_config.REPEATS):
            pattern=self.generate_pattern()
            print pattern
            for filterid in [0,1]:
                self.switch_filter(filterid)
                t0=time.time()
                for intensity in pattern:
                    self.show_fullscreen(color=0.5,duration=self.experiment_config.OFF_TIME*0.5*self.machine_config.TIME_CORRECTION)
                    self.show_shape(shape='spot', size=self.experiment_config.SIZE,color=intensity,background_color=0.5,duration=self.experiment_config.ON_TIME*self.machine_config.TIME_CORRECTION)
                    self.show_fullscreen(color=0.5,duration=self.experiment_config.OFF_TIME*0.5*self.machine_config.TIME_CORRECTION)
                    if self.abort: break
                if self.abort: break
                print time.time()-t0
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'ChirpParameters')


