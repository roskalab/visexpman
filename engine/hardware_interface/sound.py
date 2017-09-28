import playsound,subprocess,platform,numpy,scipy.io.wavfile,unittest,tempfile,os,threading

class SoundGenerator(threading.Thread):
    def __init__(self):
        if platform.system()!='Windows':
            raise NotImplementedError()
        threading.Thread.__init__(self)
        self.sample_rate=44100
        self.amplitude=2**16-1
        self.wavfn=os.path.join(tempfile.gettempdir(), 'sound.wav')
        self.mp3fn=os.path.join(tempfile.gettempdir(), 'sound.mp3')
        for fn in [self.wavfn, self.mp3fn]:
            if os.path.exists(fn):
                os.remove(fn)
        
    def generate_modulated_sound(self, duration, frequency, modulation_frequency):
        indexes=numpy.arange(int(duration*self.sample_rate))/float(self.sample_rate)
        base_signal=numpy.sin(indexes*2*numpy.pi*frequency)
        modulated_signal=numpy.sin(indexes*2*numpy.pi*modulation_frequency)
        signal=base_signal*modulated_signal*self.amplitude
        self.array2mp3(signal)
        
    def array2mp3(self,array):
        scipy.io.wavfile.write(self.wavfn, self.sample_rate, array)
        cmd='ffmpeg -i {0} {1}'.format(self.wavfn, self.mp3fn)
        subprocess.call(cmd, shell=True)
        
    def play(self):
        playsound.playsound(self.mp3fn)
        
    def run(self):
        self.play()
        
        
        
        
class TestSound(unittest.TestCase):
    def test_01(self):
        s=SoundGenerator()
        s.generate_modulated_sound(10,1000,10)
        s.start()
        
if __name__ == "__main__":    
    unittest.main()
