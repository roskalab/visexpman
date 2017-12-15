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
