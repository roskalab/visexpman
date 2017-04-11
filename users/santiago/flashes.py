from visexpman.engine.vision_experiment import experiment
import numpy
        
class FlashConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.PRE_TIME=10.0
        self.OFFTIME=5.0
        self.ONTIME=5.0
        self.NFLASHES = 1
        self.REPETITIONS=6
        self.POLARITY=-1#-1
#### EDIT UNTIL HERE
        self.OUTPATH='#OUTPATH'
        self.runnable = 'FlashStimulation'
        self._create_parameters_from_locals(locals())
        
class FlashStimulation(experiment.Experiment):
    def prepare(self):
        intensity_range=[0.38,1.0]#specific for Santiago's setup
        delta=0.5*(intensity_range[1]-intensity_range[0])
        mid=intensity_range[0]+delta
        self.mid=mid
        if self.experiment_config.NFLASHES==1:
            self.intensities=numpy.array([mid+self.experiment_config.POLARITY*delta])
        else:
            self.intensities=numpy.linspace(mid, mid+self.experiment_config.POLARITY*delta, self.experiment_config.NFLASHES)
        self.duration=self.experiment_config.PRE_TIME+self.experiment_config.REPETITIONS*(self.intensities.shape[0]*(self.experiment_config.ONTIME+self.experiment_config.OFFTIME)+self.experiment_config.OFFTIME)

    def run(self, fragment_id = 0):
        self.show_fullscreen(color=self.mid, duration=self.experiment_config.PRE_TIME)
        for r in range(self.experiment_config.REPETITIONS):
            self.show_fullscreen(color=self.mid, duration=self.experiment_config.OFFTIME)
            for i in self.intensities:
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self.show_fullscreen(color=i, duration=self.experiment_config.ONTIME)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                self.show_fullscreen(color=self.mid, duration=self.experiment_config.OFFTIME)
        
            
    

