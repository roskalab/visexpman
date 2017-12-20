import playsound,subprocess,numpy,scipy.io.wavfile,unittest,tempfile,os,threading,uuid
import time

class SoundGenerator():
    def __init__(self):
        self.sample_rate=44100
        self.amplitude=2**15-1
        id=str(uuid.uuid1())
        self.wavfn=os.path.join(tempfile.gettempdir(), '{0}.wav'.format(id))
        self.mp3fn=os.path.join(tempfile.gettempdir(), '{0}.mp3'.format(id))
        
    def generate_modulated_sound(self, duration, frequency, modulation_frequency):
        indexes=numpy.arange(int(duration*self.sample_rate))/float(self.sample_rate)
        base_signal=numpy.sin(indexes*2*numpy.pi*frequency)
        modulated_signal=numpy.sin(indexes*2*numpy.pi*modulation_frequency)
        self.signal=numpy.cast['int16'](base_signal*modulated_signal*self.amplitude)
        self.array2mp3(self.signal)
        
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
    def __init__(self,filename,sample_rate=None,waveforms=None ):
        self.waveforms=waveforms
        if hasattr(waveforms, 'put'):
            self.s=SoundGenerator()
            self.s.sample_rate=sample_rate
        elif hasattr(filename,'dtype'):
            self.s=SoundGenerator()
            self.s.sample_rate=sample_rate
            self.s.array2mp3(filename)
            self.filename=self.s.mp3fn
        else:
            if os.path.splitext(filename)[1]!='.mp3':
                raise NotImplementedError()
            self.filename=filename
        threading.Thread.__init__(self)
        
    def run(self):
        if hasattr(self.waveforms, 'get'):
            while True:
                time.sleep(0.05)
                if not self.waveforms.empty():
                    msg=self.waveforms.get()
                    if msg=='terminate':
                        break
                    elif hasattr(msg, 'dtype'):
                        if os.path.exists(self.s.mp3fn):
                            os.remove(self.s.mp3fn)
                        self.s.array2mp3(msg)
                        playsound.playsound(self.s.mp3fn)
        else:
            playsound.playsound(self.filename)
        
class TestSound(unittest.TestCase):
    @unittest.skip('')
    def test_01_modulated_sound(self):
        s=SoundGenerator()
        s.generate_modulated_sound(1,1000,10)
        p=SoundPlayer(s.mp3fn)
        p.start()
        p.join()
        
    def test_02_waveform(self):
        sample_rate=44100
        waveform=numpy.random.random(40000)
        import time,Queue
        wf=Queue.Queue()
        sp=SoundPlayer(waveform, sample_rate,wf)
        
        #playsound.playsound(sp.filename)
        sp.start()
        for i in range(3):
            wf.put(waveform)
            time.sleep(0.0)
        wf.put('terminate')
        sp.join()
        
if __name__ == "__main__":    
    unittest.main()
