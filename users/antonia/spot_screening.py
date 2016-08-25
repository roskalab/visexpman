from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy,itertools,time,inspect,random


class SpotScreeningParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [200]
        self.AREA=utils.rc((500,500))
        self.COLORS=[0.0,1.0]
        self.BACKGROUND=0.5
        self.SPACING= 50
        self.REPEATS=5
        self.ON_TIME=0.5
        self.OFF_TIME=1.0
        self.FULLFIELD_RATIO=0.1#Number of fullfields presented is 10% of the spots presented
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
        nfullfield=int(len(spot_params)*self.experiment_config.FULLFIELD_RATIO)/len(self.experiment_config.COLORS)
        for c in self.experiment_config.COLORS:
            spot_params.extend([[[0,0],-1,c]]*nfullfield)
        random.seed(0)
        random.shuffle(spot_params)
        for pos, size, color in spot_params:
            if size==-1:
                self.show_shape(shape='spot', size=2500,color=color,background_color=self.experiment_config.BACKGROUND,duration=self.experiment_config.ON_TIME*self.machine_config.TIME_CORRECTION)
                #self.show_fullscreen(color=color,duration=self.experiment_config.ON_TIME*self.machine_config.TIME_CORRECTION)
            else:
                self.show_shape(shape='spot', size=size,color=color,background_color=self.experiment_config.BACKGROUND, pos=utils.rc(pos),duration=self.experiment_config.ON_TIME*self.machine_config.TIME_CORRECTION)
            self.show_fullscreen(color=self.experiment_config.BACKGROUND,duration=self.experiment_config.OFF_TIME*self.machine_config.TIME_CORRECTION)
            if self.abort:
                break

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'SpotScreeningParameters')


