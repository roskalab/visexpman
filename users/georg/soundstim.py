import itertools,random,numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import sound,digital_io
from visexpman.engine.generic import signal,utils

class SoundAndGratingC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS=[200,1200]
        self.ORIENTATION=[180, 0, 270, 90]
        self.CONDITIONS=['grating'] # 'sound' 'both'
        self.RANDOMIZE=True #true
        self.BLOCK_DURATION=8.0
        self.FLASH_DURATION=2.0
        self.PAUSE=5.0
        self.SOUND_BASE_FREQUENCY=14000
        self.FREQUENCY_STEP=1000#Hz
        self.MODULATION='fm'#'fm'
        self.BAR_WIDTH=300
        self.GRATING_DUTY_CYCLE=0.5
        self.GRAY=0.5
        self.MASK_SIZE=3000.0#um
        self.AUDIO_SAMPLING_RATE=44.1e3
        self.ARDUINO_SOUND_GENERATOR=not False
        self.ARDUINO_SOUND_GENERATOR_PORT='COM5'
        if not isinstance(self.ORIENTATION,list):
            self.ORIENTATION=[self.ORIENTATION]
        self.runnable='SoundAndGratingE'
        self._create_parameters_from_locals(locals())
        
class SoundAndGratingShort(SoundAndGratingC):
    def _create_parameters(self):
        SoundAndGratingC._create_parameters(self)
        self.SPEEDS=[1200]
        
class SoundAndGratingE(experiment.Experiment):
    def prepare(self):
        ec=self.experiment_config
        self.protocol=[[s,c,o] for s, c, o in itertools.product(ec.SPEEDS, ec.CONDITIONS, ec.ORIENTATION)]
        if ec.RANDOMIZE:
            random.shuffle(self.protocol)
        self.duty_cycle=1/ec.GRATING_DUTY_CYCLE-1
        self.experiment_config.PROTOCOL=self.protocol
        self.experiment_config.PROTOCOL1=[[p[0], int(p[1]=='grating' or p[1]=='both'), int(p[1]=='sound' or p[1]=='both')] for p in self.protocol]
        self.experiment_config.GRATING_FREQUENCY=1.0/(ec.BAR_WIDTH/ec.GRATING_DUTY_CYCLE/numpy.array(ec.SPEEDS))
        if not self.experiment_config.ARDUINO_SOUND_GENERATOR:
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
        self.block_boundaries=[]
        
    def block(self, speed, condition, orientation):
        block_sig=(condition, speed, orientation)
        self.block_start(block_sig)
        self.block_boundaries.append(self.frame_counter)
        ec=self.experiment_config
        if condition!='grating':
            if ec.ARDUINO_SOUND_GENERATOR:
                self.ioboard.set_waveform(ec.SOUND_BASE_FREQUENCY, ec.FREQUENCY_STEP, ec.GRATING_FREQUENCY[ec.SPEEDS.index(speed)])
            else:
                if hasattr(self, 'soundplayer'):
                    if self.soundplayer.is_alive():
                        raise RuntimeError('Previous block\'s sound generator have not finished')
                self.soundplayer=sound.SoundPlayer(self.sound_filenames[speed])
                self.soundplayer.start()
        if condition=='sound':
            self.show_fullscreen(color=ec.GRAY, duration=ec.BLOCK_DURATION)
        else:
            size=max(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col'])
            if ec.FLASH_DURATION>0:
                self.show_grating(orientation=orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=ec.BLOCK_DURATION-ec.FLASH_DURATION,
                               display_area=utils.rc((size, size)),
                               velocity=0,
                               mask_size=ec.MASK_SIZE,
                               mask_color=ec.GRAY)
            self.show_grating(orientation=orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=ec.BLOCK_DURATION-ec.FLASH_DURATION,
                               display_area=utils.rc((size, size)),
                               velocity=speed,
                               mask_size=ec.MASK_SIZE,
                               mask_color=ec.GRAY)
        if ec.ARDUINO_SOUND_GENERATOR:
            self.ioboard.stop_waveform()
        self.block_boundaries.append(self.frame_counter-1)
        self.block_end(block_sig)
#        if condition!='grating':
#            self.show_fullscreen(color=ec.GRAY)
        
    def run(self):
        ec=self.experiment_config
        if ec.ARDUINO_SOUND_GENERATOR:
            self.ioboard=digital_io.IOBoard(ec.ARDUINO_SOUND_GENERATOR_PORT,timeout=0.2)
        self.show_fullscreen(color=ec.GRAY, duration=ec.PAUSE)
        for p in self.protocol:
            print p
            self.block(*p)
            self.show_fullscreen(color=ec.GRAY, duration=ec.PAUSE)
            if self.abort:
                break
        if ec.ARDUINO_SOUND_GENERATOR:
            self.ioboard.close()
        if 0 and not self.abort:
            #save block boundaries
            for i in range(len(self.experiment_config.PROTOCOL1)):
                self.experiment_config.PROTOCOL1[i].extend([self.block_boundaries[2*i],self.block_boundaries[2*i+1]])
            self.experiment_config.PROTOCOL1=numpy.array(self.experiment_config.PROTOCOL1)
            print self.experiment_config.PROTOCOL1
        
                
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'SoundAndGratingC')
