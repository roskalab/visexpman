import itertools,random,numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import sound

class SoundAndGratingC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS=[200,600,1200]
        self.CONDITIONS=['sound', 'grating', 'both']
        self.RANDOMIZE=False #true
        self.BLOCK_DURATION=8.0
        self.PAUSE=4.0
        self.SOUND_BASE_FREQUENCY=14000
        self.BAR_WIDTH=300
        self.GRATING_DUTY_CYCLE=0.5
        self.GRAY=0.5
        self.runnable='SoundAndGratingE'
        self._create_parameters_from_locals(locals())
        
class SoundAndGratingE(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        self.protocol=[[s,c] for s, c in itertools.product(ec.SPEEDS, ec.CONDITIONS)]
        if ec.RANDOMIZE:
            random.shuffle(self.protocol)
        self.duty_cycle=1/ec.GRATING_DUTY_CYCLE-1
        self.experiment_config.PROTOCOL=self.protocol
        self.experiment_config.GRATING_FREQUENCY=1.0/(ec.BAR_WIDTH/ec.GRATING_DUTY_CYCLE/numpy.array(ec.SPEEDS))
        self.sound_filenames={}
        self.s=[]
        for i in range(len(ec.GRATING_FREQUENCY)):
            self.s.append(sound.SoundGenerator())
            self.s[-1].generate_modulated_sound(ec.BLOCK_DURATION,ec.SOUND_BASE_FREQUENCY,ec.GRATING_FREQUENCY[i])
            self.sound_filenames[ec.SPEEDS[i]]=self.s[-1].mp3fn
        self.orientation=0
        
        
    def block(self, speed, condition):
        ec=self.experiment_config
        if condition!='grating':
            if hasattr(self, 'soundplayer'):
                if self.soundplayer.is_alive():
                    raise RuntimeError('Previous block\'s sound generator have not finished')
            self.soundplayer=sound.SoundPlayer(self.sound_filenames[speed])
            self.soundplayer.start()
        if condition=='sound':
            self.show_fullscreen(color=ec.GRAY, duration=ec.BLOCK_DURATION)
        else:
            self.show_grating(orientation=self.orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=ec.BLOCK_DURATION,
                               display_area=self.machine_config.SCREEN_SIZE_UM,
                               velocity=speed)
#        if condition!='grating':
#            self.show_fullscreen(color=ec.GRAY)
        
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(color=ec.GRAY, duration=ec.PAUSE)
        for p in self.protocol:
            print p
            self.block(*p)
            self.show_fullscreen(color=ec.GRAY, duration=ec.PAUSE)
            if self.abort:
                break
                
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'SoundAndGratingC')
