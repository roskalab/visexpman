import  random
from visexpman.engine.vision_experiment import experiment,experiment_data

class ObjectStim(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.OBJECTS=['grating','pizza', 'concentric',]#  'hyperbolic','spiral']
        self.ON_TIME=2.0
        self.OFF_TIME=2.0
        self.REPEAT_PER_OBJECT=2
        self.SPATIAL_FREQUENCY=0.05
        self.ORIENTATION=0
        self.SIZE=1000.#um
        self.COLOR_MIN=0.0
        self.COLOR_MAX=1.0
        self.GRAY=0.5
        #Object specific:
        self.NARMS=4
        self.OBJECT_ORDER=self.OBJECTS*self.REPEAT_PER_OBJECT
        random.shuffle(self.OBJECT_ORDER)
        self.runnable='ObjectExperiment'
        self._create_parameters_from_locals(locals())
                
class ObjectExperiment(experiment.Experiment):
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
        for o in ec.OBJECT_ORDER:
            self.block_start((o,))
            if o=='grating':
                bw=0.5*experiment_data.cpd2um(ec.SPATIAL_FREQUENCY,self.machine_config.MOUSE_1_VISUAL_DEGREE_ON_RETINA)
                self.show_grating(duration=ec.ON_TIME, 
                                                velocity=0, 
                                                mask_size=ec.SIZE,
                                                mask_color=ec.GRAY,
                                                white_bar_width=bw)
            else:
                self.show_object(name=o,
                                                size=ec.SIZE,
                                                spatial_frequency=ec.SPATIAL_FREQUENCY,
                                                duration=ec.ON_TIME,
                                                orientation=ec.ORIENTATION,
                                                color_min=ec.COLOR_MIN,
                                                color_max=ec.COLOR_MAX,
                                                narms=ec.NARMS)
            self.block_end((o,))
            self.show_fullscreen(color=ec.GRAY, duration=ec.OFF_TIME)
            if self.abort:
                break
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'ObjectStim',ENABLE_FRAME_CAPTURE=not True)
