import numpy,time
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class NaturalBarsConfig1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False
        self.runnable = 'NaturalBarsExperiment1'
        self._create_parameters_from_locals(locals())

class NaturalBarsExperiment1(experiment.Experiment):
    def prepare(self):
        self.stimulus_duration = self.experiment_config.DURATION
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DURATION, color =  self.experiment_config.BACKGROUND_COLOR)

class DottestConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FILENAME=''
        self.runnable = 'DottestExperiment'
        self._create_parameters_from_locals(locals())
        
class DottestExperiment(experiment.Experiment):
    def run(self):
        duration=2
        nframes=duration*60
        ndots=50
        dot_diameters=20+10*numpy.random.random(nframes*ndots)
        positions=utils.rc((
                    numpy.random.random(ndots)*800-400,
                    numpy.random.random(ndots)*800-400,
#                    numpy.array([0,100, 0, 100]),
#                    numpy.array([0,100, 100, 0])
                    ))
        
        dot_positions=numpy.tile(positions,nframes)
        for i in range(nframes*ndots):
            dot_positions[i*ndots:(i+1)*ndots]['row']+=numpy.random.random()*500-250
            dot_positions[i*ndots:(i+1)*ndots]['col']+=numpy.random.random()*500-250
        t0=time.time()
        self.show_dots(dot_diameters, dot_positions, ndots)
        print t0-time.time()

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'DottestConfig')
