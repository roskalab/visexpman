import unittest,serial,time,numpy
from pylab import plot,show
class TestIOboard(unittest.TestCase):
    def line2digital_input(self,l):
        v=int(l.split('ms:')[1],16)
        bitpos=[2,3,4]
        res={}
        for bp in bitpos:
            res[bp]=v&(1<<bp)!=0
        return res
        
    def line2timestamp(self,l):
        return int(l.split(' ms:')[0])
        
    def setUp(self):
        self.s=serial.Serial('/dev/ttyACM0', 115200, timeout = 1)
        time.sleep(2.5)
        
    def tearDown(self):
        self.s.close()
        
    def execute_command(self,cmd):
        self.s.write(cmd+'\r\n')
        time.sleep(0.05)
        
    def parse_read(self,s):
        values=numpy.array([map(int,l.split(' ms: '), 2*[10]) for l in s.split('\r\n') if ' ms: ' in l])
        values[:,0]-=values[0,0]
        pins=[numpy.where(values[:,1]&(2**i)>0,1,0) for i in [2,3,4]]
        pins=numpy.array(pins).T
        values=numpy.concatenate((numpy.array([values[:,0]]).T, pins),axis=1)
        return values[:,0], pins
        
    def test_01_ioboard_identification(self):
        self.execute_command('ioboard')
        self.assertEqual(self.s.read(1000), 'ioboard\r\n')
    
    def test_02_digital_io(self):
        ontime=0.2
        set_pin_tolerance=60
        pulse_tolerance=2
        pulse_width=50
        print 'Connect pin 5 to pin 2 and pin 6 to pin 3'
        self.execute_command('reset')
        self.execute_command('read_pins')
        self.execute_command('set_pin,5,0')
        self.execute_command('set_pin,6,0')
        self.execute_command('start_read_pins')
        time.sleep(0.2)
        self.execute_command('set_pin,5,1')
        time.sleep(ontime)
        self.execute_command('set_pin,5,0')
        time.sleep(0.2)
        res=self.s.read(1000)
        t,p=self.parse_read(res)
        self.assertTrue(all(p[:,0]==numpy.array([0,1,0])))
        self.assertTrue(abs(numpy.diff(t)[1]-1e3*ontime)<set_pin_tolerance)
        self.execute_command('set_pin,6,1')
        time.sleep(ontime)
        self.execute_command('set_pin,6,0')
        time.sleep(0.2)
        res=self.s.read(1000)
        t,p=self.parse_read(res)
        self.assertTrue(all(p[:,1]==numpy.array([1,0])))
        self.assertTrue(abs(numpy.diff(t)[0]-1e3*ontime)<set_pin_tolerance)
        self.execute_command('pulse,5,{0}'.format(pulse_width))
        time.sleep(0.2)
        res=self.s.read(1000)
        t,p=self.parse_read(res)
        self.assertTrue(all(p[:,0]==numpy.array([1,0])))
        self.assertTrue(abs(numpy.diff(t)[0]-pulse_width)<pulse_tolerance)
        self.execute_command('set_pin,6,1')
        time.sleep(0.05)
        self.execute_command('set_pin,5,1')
        time.sleep(ontime)
        self.execute_command('set_pin,6,0')
        self.execute_command('set_pin,5,0')
        time.sleep(0.2)
        self.execute_command('stop_read_pins')
        time.sleep(0.1)
        res=self.s.read(1000)
        t,p=self.parse_read(res)
        self.assertTrue(all(p[:,1]==numpy.array([1,1,0,0])))
        self.assertTrue(all(p[:,0]==numpy.array([0,1,1,0])))

    def test_03_waveform(self):
        self.execute_command('reset')
        self.execute_command('set_pin,6,0')
        self.execute_command('set_pin,5,0')
        #fixed frequency waveform
        self.execute_command('waveform,1000,0,0')
        time.sleep(0.3)
        self.execute_command('stop')
        time.sleep(0.2)
        response1=self.s.read(10000)
        self.assertTrue('1000.00 Hz signal on pin 9' in response1)
        self.assertTrue('Stop waveform' in response1)
        #frequency modulated waveform
        self.execute_command('waveform,20000,5000,0.5')
        time.sleep(0.3)
        self.execute_command('stop')
        time.sleep(0.1)
        self.execute_command('stop')
        response2=self.s.read(10000)
        self.assertTrue('20000.00 Hz signal on pin 9' in response2)
        self.assertTrue('Stop waveform' in response2)
        #waveform cannot be started while one is already running
        self.execute_command('waveform,20000,5000,1')
        time.sleep(0.1)
        self.execute_command('waveform,20000,5000,10')
        time.sleep(1.0)
        self.execute_command('stop')
        time.sleep(0.5)
        self.execute_command('stop')
        response3=self.s.read(10000)
        self.assertTrue('Waveform is running' in response3)
        self.assertTrue('Stop waveform' in response3)
                
if __name__=='__main__':
    unittest.main()
