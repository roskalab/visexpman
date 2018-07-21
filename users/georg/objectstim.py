import  random
from visexpman.engine.vision_experiment import experiment,experiment_data
from visexpman.engine.generic import utils,introspect

class ObjectStim(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.OBJECTS=['pizza 3 arms','pizza 3 arms invert',
        'pizza 5 arms','pizza 5 arms invert',
        'pizza 11 arms', 'pizza 11 arms invert'
        'concentric','concentric invert', 
         'concentric 0.05 cpd','concentric 0.05 cpd invert', 
        'hyperbolic','hyperbolic invert', 
        'hyperbolic 45 degrees','hyperbolic 45 degrees invert',
        'spiral','spiral invert', 
        'spiral 45 degrees','spiral 45 degrees invert']
        self.ON_TIME=2.0
        self.OFF_TIME=5.0
        self.REPEAT_PER_OBJECT=1
        self.SPATIAL_FREQUENCY=0.1#cycle per degree.
        self.SIZE=3000.0#um
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
    def prepare(self):
        ec=self.experiment_config
        self.duration=len(ec.OBJECTS)*(ec.ON_TIME+ec.OFF_TIME)+ec.OFF_TIME

    def run(self):
        self.check_frame_rate=False
        ec=self.experiment_config
        self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
        for o in ec.OBJECT_ORDER:
            self.printl(o)
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
            spatial_frq_i=[i for i in range(len(words)) if 'cpd' in words[i]]
            if len(spatial_frq_i)>0:
                spatial_frq=float(words[spatial_frq_i[0]-1])
            else:
                spatial_frq=ec.SPATIAL_FREQUENCY
            invert='invert' in words
            if name=='grating':
                bw=0.5*experiment_data.cpd2um(spatial_frq,self.machine_config.MOUSE_1_VISUAL_DEGREE_ON_RETINA)
                period=2*bw
                if int(ec.SIZE/period*2)%2==0:
                    starting_phase=-(ec.SIZE/period-int(ec.SIZE/period*2)*0.5-0.5)*360/2
                else:
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
                                                spatial_frequency=spatial_frq,
                                                duration=ec.ON_TIME,
                                                orientation=ori,
                                                color_min=ec.COLOR_MIN,
                                                color_max=ec.COLOR_MAX,
                                                narms=narms,
                                                invert=invert)
            self.block_end((o,))
            self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
            if self.abort:
                break
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'ObjectStim',ENABLE_FRAME_CAPTURE=not True)
