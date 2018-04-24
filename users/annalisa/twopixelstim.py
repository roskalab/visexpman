import numpy, copy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class TwoPixelFullField(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CONTRASTS=[0.625, 0.75, 0.87, 1.0]
        self.ONTIME=2#seconds
        self.OFFTIME=2#seconds
        self.TIMESHIFT=-1.5#seconds
        self.PIXEL_RATIO=0.5
        self.runnable='TwoPixelFullFieldE'
        self._create_parameters_from_locals(locals())
        
        
class TwoPixelFullFieldE(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        mc=self.machine_config
        self.duration=len(ec.CONTRASTS)*(ec.OFFTIME+ec.ONTIME)+abs(ec.TIMESHIFT)+ec.OFFTIME
        self.left_contrasts=numpy.zeros(int(self.duration*mc.SCREEN_EXPECTED_FRAME_RATE))
        self.right_contrasts=numpy.zeros_like(self.left_contrasts)
        off=numpy.zeros(int(mc.SCREEN_EXPECTED_FRAME_RATE*ec.OFFTIME))
        contrast_segments=[off]
        for c in ec.CONTRASTS:
            contrast_segments.append(numpy.ones_like(off)*c)
            contrast_segments.append(off)
        contrasts=numpy.concatenate(contrast_segments)
        shift=abs(int(mc.SCREEN_EXPECTED_FRAME_RATE*ec.TIMESHIFT))
        if ec.TIMESHIFT>0:
            self.left_contrasts[:contrasts.shape[0]]=contrasts
            self.right_contrasts[shift:]=contrasts
        else:
            self.left_contrasts[shift:]=contrasts
            self.right_contrasts[:contrasts.shape[0]]=contrasts
        left_width=mc.SCREEN_SIZE_UM['col']*ec.PIXEL_RATIO
        right_width=mc.SCREEN_SIZE_UM['col']*(1-ec.PIXEL_RATIO)
        self.sizes=numpy.array([[left_width, mc.SCREEN_SIZE_UM['row']], [left_width, mc.SCREEN_SIZE_UM['row']]])
        self.positions=utils.rc(numpy.array([numpy.zeros(2), numpy.array([left_width*0.5, left_width+right_width*0.5])-0.5*mc.SCREEN_SIZE_UM['col']]).T)
        self.colors=numpy.array([self.left_contrasts,self.right_contrasts]).T
        
    def run(self):
        self.show_shapes('rect', self.sizes, self.positions, 2, color = self.colors,
                            are_same_shapes_over_frames = True, colors_per_shape = False)
        
if __name__ == "__main__":
    from visexpman.applications.visexp_app import stimulation_tester
    stimulation_tester('annalisa', 'StimulusDevelopment', 'TwoPixelFullField',ENABLE_FRAME_CAPTURE=not True)
