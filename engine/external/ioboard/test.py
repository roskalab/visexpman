import unittest,serial,time
class TestIOboard(unittest.TestCase):
    def test_01(self):
        s=serial.Serial('/dev/ttyACM0', 115200, timeout = 1)
        s.write('r')
        time.sleep(0.2)
        #print s.read(100)
        s.write('p{0}'.format(chr(1<<6)))
        time.sleep(0.2)
        #print s.read(100)
        time.sleep(1)
        for i in range(3):
            s.write('o{0}'.format(chr(1<<5)))
            time.sleep(0.2)
            s.write('o{0}'.format(chr(0)))
            time.sleep(0.3)
        print s.read(1000)
        s.close()
        
if __name__=='__main__':
    unittest.main()
