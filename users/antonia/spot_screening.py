from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy,itertools,time,inspect,random


class SpotScreeningParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [200,2000]
        self.AREA=utils.rc((500,500))
        self.COLORS=[0.0,1.0]
        self.BACKGROUND=0.5
        self.SPACING=50
        self.REPEATS=5
        self.ON_TIME=0.5
        self.OFF_TIME=0.5
        self.runnable = 'SpotScreeningExp'        
        self._create_parameters_from_locals(locals())
        
class SpotScreeningExp(experiment.Experiment):
    def generate_positions(self):
        npos=utils.rc_multiply_with_constant(self.experiment_config.AREA, 1.0/self.experiment_config.SPACING)
        rowvalues=(numpy.arange(npos['row'])-0.5*(npos['row']-1))*self.experiment_config.SPACING
        colvalues=(numpy.arange(npos['col'])-0.5*(npos['col']-1))*self.experiment_config.SPACING
        y,x=numpy.meshgrid(rowvalues,colvalues)
        return zip(x.flatten(),y.flatten())

    def run(self):
        self.show_fullscreen(color=self.experiment_config.BACKGROUND,duration=0)
        positions = self.generate_positions()
        spot_params=[[p,s,c] for p,s,c in itertools.product(positions, self.experiment_config.SIZES, self.experiment_config.COLORS)]*self.experiment_config.REPEATS
        random.seed(0)
        random.shuffle(spot_params)
        for pos, size, color in spot_params:
            self.show_shape(shape='spot', size=size,color=color,background_color=self.experiment_config.BACKGROUND, pos=utils.rc(pos),duration=self.experiment_config.ON_TIME)
            self.show_fullscreen(color=self.experiment_config.BACKGROUND,duration=self.experiment_config.ON_TIME)
            if self.abort:
                break

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'SpotScreeningParameters')


