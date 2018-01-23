import unittest,serial,time,numpy
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
        
    def tearDown(self):
        self.s.close()
        
    def execute_command(self,cmd):
        self.s.write(cmd+'\n')
        
    def test_01_digital_io(self):
        print 'Connect pin 5 to pin 2 and pin 6 to pin 3'
        self.execute_command('start_read_pins')
        self.execute_command('set_pin,5,0')
        self.execute_command('set_pin,6,0')
        self.execute_command('set_pin,5,1')
        time.sleep(1)
        self.execute_command('set_pin,5,0')
        time.sleep(0.5)
        self.execute_command('set_pin,6,1')
        time.sleep(1)
        self.execute_command('set_pin,6,0')
        time.sleep(0.5)
        self.execute_command('pulse,5,100')
        self.execute_command('stop_read_pins')
        time.sleep(0.5)
        response=self.s.read(10000)
        #TODO: separate command responses from digital IO readout
        
    def test_02_square_wave(self):
        self.execute_command('set_pin,6,0')
        self.execute_command('set_pin,5,0')
        print '10 Hz on Pin 5 '
        self.execute_command('square_wave,5,10')
        time.sleep(0.5)
        self.execute_command('stop_waveform,5')
        time.sleep(1)
        response1=self.s.read(10000)
        print '10 Hz on pin 6'
        self.execute_command('square_wave,6,10')
        time.sleep(0.5)
        self.execute_command('stop_waveform,6')
        time.sleep(0.5)
        response2=self.s.read(10000)
        print '2 and 10 Hz on both pins'
        self.execute_command('square_wave,5,2')
        self.execute_command('square_wave,6,10')
        time.sleep(0.5)
        self.execute_command('stop_waveform,6')
        time.sleep(0.5)
        self.execute_command('stop_waveform,5')
        time.sleep(0.5)
        response3=self.s.read(10000)
    @unittest.skip('')
    def test_01(self):
        s=serial.Serial('/dev/ttyACM0', 115200, timeout = 1)
        npulses=20
        t1=0.2
        t2=0.3
        time.sleep(3)
        s.write('r')
        time.sleep(0.2)
        buf1 = s.read(100)
        res=self.line2digital_input(buf1.split('\r\n')[0])
        self.assertFalse(res[2])
        self.assertFalse(res[3])
        s.write('p{0}'.format(chr(1<<6)))
        time.sleep(0.2)
        time.sleep(1)
        for i in range(npulses):
            s.write('o{0}'.format(chr(1<<5)))
            time.sleep(t1)
            s.write('o{0}'.format(chr(0)))
            time.sleep(t2)
        buf2= s.read(1000)
        lines=buf2.split('\r\n')[:-1]
        self.assertTrue(self.line2digital_input(lines[0])[3])
        self.assertFalse(self.line2digital_input(lines[1])[3])
        self.assertTrue(self.line2timestamp(lines[1])-self.line2timestamp(lines[0])<2)
        t=[self.line2timestamp(l) for l in lines[2:]]
        v=[self.line2digital_input(l)[2] for l in lines[2:]]
        self.assertTrue(all(v[::2]))
        self.assertFalse(any(v[1::2]))
        self.assertEqual(len(lines[2:]), 2*npulses)
        numpy.testing.assert_array_almost_equal(numpy.diff(numpy.array(t))[::2], numpy.array([int(1000*t1)]*npulses),-1)
        numpy.testing.assert_array_almost_equal(numpy.diff(numpy.array(t))[1::2], numpy.array([int(1000*t2)]*(npulses-1)),-1)
        s.close()
                
if __name__=='__main__':
    unittest.main()
