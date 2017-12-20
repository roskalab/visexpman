import itertools,random,numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import sound
from visexpman.engine.generic import signal

class SoundAndGratingC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS=[200,600,1200]
        self.CONDITIONS=['sound', 'grating', 'both']
        self.RANDOMIZE=False #true
        self.BLOCK_DURATION=8.0
        self.PAUSE=4.0
        self.SOUND_BASE_FREQUENCY=14000
        self.FREQUENCY_STEP=1000#Hz
        self.MODULATION='am'#'fm'
        self.BAR_WIDTH=300
        self.GRATING_DUTY_CYCLE=0.5
        self.GRAY=0.5
        self.MASK_SIZE=1500.0#um
        self.AUDIO_SAMPLING_RATE=44.1e3
        self.runnable='SoundAndGratingE'
        self._create_parameters_from_locals(locals())
        
class SoundAndGratingShort(SoundAndGratingC):
    def _create_parameters(self):
        SoundAndGratingC._create_parameters(self)
        self.SPEEDS=[1200]
        
class SoundAndGratingE(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        self.protocol=[[s,c] for s, c in itertools.product(ec.SPEEDS, ec.CONDITIONS)]
        if ec.RANDOMIZE:
            random.shuffle(self.protocol)
        self.duty_cycle=1/ec.GRATING_DUTY_CYCLE-1
        self.experiment_config.PROTOCOL=self.protocol
        self.experiment_config.PROTOCOL1=[[p[0], int(p[1]=='grating' or p[1]=='both'), int(p[1]=='sound' or p[1]=='both')] for p in self.protocol]
        self.experiment_config.GRATING_FREQUENCY=1.0/(ec.BAR_WIDTH/ec.GRATING_DUTY_CYCLE/numpy.array(ec.SPEEDS))
        self.sound_filenames={}
        self.s=[]
        for i in range(len(ec.GRATING_FREQUENCY)):
            self.s.append(sound.SoundGenerator())
            self.s[-1].sample_rate=ec.AUDIO_SAMPLING_RATE
            if ec.MODULATION=='fm':
                self.s[-1].array2mp3(signal.generate_frequency_modulated_waveform(ec.BLOCK_DURATION,ec.SOUND_BASE_FREQUENCY,ec.FREQUENCY_STEP, ec.GRATING_FREQUENCY[i],ec.AUDIO_SAMPLING_RATE, step=True))
            elif ec.MODULATION=='fmsmooth':
                self.s[-1].array2mp3(signal.generate_frequency_modulated_waveform(ec.BLOCK_DURATION,ec.SOUND_BASE_FREQUENCY,ec.FREQUENCY_STEP, ec.GRATING_FREQUENCY[i],ec.AUDIO_SAMPLING_RATE, step=False))
            elif ec.MODULATION=='am':
                self.s[-1].generate_modulated_sound(ec.BLOCK_DURATION,ec.SOUND_BASE_FREQUENCY,ec.GRATING_FREQUENCY[i])
            self.sound_filenames[ec.SPEEDS[i]]=self.s[-1].mp3fn
            #import shutil;shutil.copy(self.s[-1].mp3fn,'c:\\temp')
        self.orientation=0
        self.block_boundaries=[]
        
    def block(self, speed, condition):
        block_sig=(condition, speed)
        self.block_start(block_sig)
        self.block_boundaries.append(self.frame_counter)
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
                               velocity=speed,
                               mask_size=ec.MASK_SIZE,
                               mask_color=ec.GRAY)
        self.block_boundaries.append(self.frame_counter-1)
        self.block_end(block_sig)
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
        if not self.abort:
            #save block boundaries
            for i in range(len(self.experiment_config.PROTOCOL1)):
                self.experiment_config.PROTOCOL1[i].extend([self.block_boundaries[2*i],self.block_boundaries[2*i+1]])
            self.experiment_config.PROTOCOL1=numpy.array(self.experiment_config.PROTOCOL1)
            print self.experiment_config.PROTOCOL1
        
                
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'SoundAndGratingC')
