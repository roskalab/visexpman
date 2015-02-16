import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class AngleTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'AngleStimulus'        
        self._create_parameters_from_locals(locals())

class AngleStimulus(experiment.Experiment):
    def run(self):
        self.moving_cross(speeds = [400,200], sizes = [20,20], position = utils.rc((0,0)), movement_directions = [45,0], contrasts = 1.0, background = 0.0)
        return
        for i in range(1):
            self.show_shape(shape='L', duration = 100, orientation = 0,L_shape_config = \
                                            {'shorter_side':100, 'longer_side':100, 'shorter_position': 'middle', 'angle' : 135, 'width': 20})#,
                                            #pos = utils.rc((2*numpy.arange(200), numpy.zeros(200))))
        return
        self.show_shape(shape='L', duration = 1, orientation = 0,L_shape_config = \
                                            {'shorter_side':100, 'longer_side':200, 'shorter_position': 'start', 'angle' : 10, 'width': 10})
        for angle in [45,90]:
            self.show_shape(shape='L', duration = 100, orientation = 0,L_shape_config = \
                                            {'shorter_side':100, 'longer_side':200, 'shorter_position': 'end', 'angle' : angle, 'width': 10})
        return
        i=200
        self.moving_comb(speed=100, orientation=10, bar_width=100, tooth_size=10, tooth_type='square', contrast=1.0, background=0.0)
        self.moving_comb(speed=100, orientation=10, bar_width=100, tooth_size=10, tooth_type='sawtooth', contrast=1.0, background=0.0)
        return
        self.show_shape(shape='star',size=i,ncorners=5,duration=10,inner_radius = i/2,orientation = 0)
        return
        for i in range(1,500):
            self.show_shape(shape='star',size=i,ncorners=5,duration=0,inner_radius = i/2,orientation = 0)
        
        return
        self.show_shape(shape='triangle',size=100,duration=2.0,orientation = 0)        
        for i in range(2,11):
            for ori in range(100):

                self.show_shape(shape='star',size=100,ncorners=i,duration=0,inner_radius = 40,orientation = ori)
        
#        self.show_shape(shape='star',size=100,ncorners=6,duration=200,inner_radius = 50,orientation = ori)
        
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('adrian', 'StimulusDevelopment', 'AngleTest')
