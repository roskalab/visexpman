import  random
from visexpman.engine.vision_experiment import experiment,experiment_data
from visexpman.engine.generic import utils

class ObjectStim(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.OBJECTS=['grating','pizza 5 arms', 'concentric', 'hyperbolic','spiral', 'hyperbolic 20 degrees']
        self.ON_TIME=2.0
        self.OFF_TIME=5.0
        self.REPEAT_PER_OBJECT=3
        self.SPATIAL_FREQUENCY=0.05#cycle per degree.
        self.SIZE=2000.#um
        self.COLOR_MIN=0.0
        self.COLOR_MAX=1.0
        self.GRAY=0.5
        #Object specific:
        self.OBJECT_ORDER=self.OBJECTS*self.REPEAT_PER_OBJECT
        random.shuffle(self.OBJECT_ORDER)
        self.runnable='ObjectExperiment'
        self._create_parameters_from_locals(locals())
            
class ObjectExperiment(experiment.Experiment):
    '''
    Displays circular objects in a randomized order:
        grating in circular mask
        two armed spiral
        hyperbolic grating
        pizza slices
        concentric circles
        
    Each is shown REPEAT_PER_OBJECT times, order is shuffled.
    '''
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
        for o in ec.OBJECT_ORDER:
            self.block_start((o,))
            words=o.split(' ')
            name=words[0]
            arm_i=[i for i in range(len(words)) if 'arm' in words[i]]
            if len(arm_i)>0:
                narms=int(words[arm_i[0]-1])
            else:
                narms=4
            ori_i=[i for i in range(len(words)) if 'degree' in words[i]]
            if len(ori_i)>0:
                ori=float(words[ori_i[0]-1])
            else:
                ori=0
            if name=='grating':
                bw=0.5*experiment_data.cpd2um(ec.SPATIAL_FREQUENCY,self.machine_config.MOUSE_1_VISUAL_DEGREE_ON_RETINA)
                period=2*bw
                starting_phase=-(ec.SIZE/period-int(ec.SIZE/period*2)*0.5)*360/2
                self.show_grating(duration=ec.ON_TIME, 
                                                velocity=0, 
                                                orientation=ori,
                                                mask_size=ec.SIZE,
                                                mask_color=ec.GRAY,
                                                white_bar_width=bw,
                                                display_area=utils.rc((ec.SIZE,ec.SIZE)),
                                                starting_phase=starting_phase)
            else:
                self.show_object(name=name,
                                                size=ec.SIZE,
                                                spatial_frequency=ec.SPATIAL_FREQUENCY,
                                                duration=ec.ON_TIME,
                                                orientation=ori,
                                                color_min=ec.COLOR_MIN,
                                                color_max=ec.COLOR_MAX,
                                                narms=narms)
            self.block_end((o,))
            self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
            if self.abort:
                break
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'ObjectStim',ENABLE_FRAME_CAPTURE=not True)
