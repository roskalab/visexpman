import playsound,subprocess,platform,numpy,scipy.io.wavfile,unittest,tempfile,os,threading,uuid

class SoundGenerator():
    def __init__(self):
        if platform.system()!='Windows':
            raise NotImplementedError()
        self.sample_rate=44100
        self.amplitude=2**15-1
        id=str(uuid.uuid1())
        self.wavfn=os.path.join(tempfile.gettempdir(), '{0}.wav'.format(id))
        self.mp3fn=os.path.join(tempfile.gettempdir(), '{0}.mp3'.format(id))
        
    def generate_modulated_sound(self, duration, frequency, modulation_frequency):
        indexes=numpy.arange(int(duration*self.sample_rate))/float(self.sample_rate)
        base_signal=numpy.sin(indexes*2*numpy.pi*frequency)
        modulated_signal=numpy.sin(indexes*2*numpy.pi*modulation_frequency)
        signal=numpy.cast['int16'](base_signal*modulated_signal*self.amplitude)
        self.array2mp3(signal)
        
    def array2mp3(self,array):
        scipy.io.wavfile.write(self.wavfn, self.sample_rate, array)
        cmd='ffmpeg -i {0} {1}'.format(self.wavfn, self.mp3fn)
        subprocess.call(cmd, shell=True)
        os.remove(self.wavfn)
        
    def __del__(self):
        for fn in [self.wavfn, self.mp3fn]:
            if os.path.exists(fn):
                os.remove(fn)
                
class SoundPlayer(threading.Thread):
    def __init__(self, filename):
        if os.path.splitext(filename)[1]!='.mp3':
            raise NotImplementedError()
        self.filename=filename
        threading.Thread.__init__(self)
        
    def run(self):
        playsound.playsound(self.filename)
        
class TestSound(unittest.TestCase):
    def test_01(self):
        s=SoundGenerator()
        s.generate_modulated_sound(1,1000,10)
        p=SoundPlayer(s.mp3fn)
        p.start()
        p.join()
        pass
        
if __name__ == "__main__":    
    unittest.main()
