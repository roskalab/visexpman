import socket,subprocess,psutil,time,json,unittest,os,sys
from websocket import create_connection #pip install websocket_client
try:
    from visexpman.generic import fileop
except ImportError:
    pass

class MescapiInterface(object):
    def __init__(self, mesc_address='localhost', port=11000, command_buffer_size=1024*512, timeout=1.0,debug=False, galvo=False):
        self.galvo=galvo
        self.connected=False
        self.conn=create_connection("ws://localhost:8888")
        self.conn.timeout=2
        self.connected=True

    def request(self,cmd):
        self.conn.send(cmd)
        res=self.conn.recv()
        try:
            return json.loads(res)
        except:
            return res
            
    def ping(self):
        if not self.connected:
            return False
        try:
            return self.request('a="123";')==123
        except:
            self.connected=False
            return False
        
    def start(self):
        '''
        Initiate recording
        '''
        state=self.get_state()
        if state!='Ready':
            raise IOError('Microscope is not ready for recording, current state: {0}'.format(state))
        if self.galvo:
            return self.request('MEScMicroscope.startGalvoScanAsync()')
        else:
            return self.request('MEScMicroscope.startResonantScanAsync()')
        
    def stop(self):
        '''
        Terminate running measurement
        '''
        state=self.get_state()
        if state!='Working':
            raise IOError('Acquisition is not running, current state: {0}\r\nCheck MESc, error might have happened during recording'.format(state))
        if self.galvo:
            return self.request('MEScMicroscope.stopGalvoScanAsync()')
        else:
            return self.request('MEScMicroscope.stopResonantScanAsync()')
        
    def get_state(self):
        '''
        get microscope state
        '''
        res=self.request('MEScMicroscope.getAcquisitionState()')
        try:
            return res['taskIndependentParameters']['microscopeState']
        except:
            return res
    
    def save(self, filename):
        '''
        Saves last recording to file
        '''
        return self.request('MEScFile.closeFileAndSaveAsAsync("{0}")'.format(filename.replace('\\',  '\\\\')))
        
    def close(self):
            if self.connected:
                self.conn.close()
        
class TestMesc(unittest.TestCase):
    def test_01_simple_use(self):
        from visexpman.generic import introspect
        m=MescapiInterface(debug=True)
        with introspect.Timer():
            m.request('MEScMicroscope.getAcquisitionState();')
        m.close()
        
    def test_02_multiple_commands(self):
        m=MescapiInterface(debug=True)
        for i in range(10):
            self.assertEqual([i for i in m.request('MEScMicroscope.getAcquisitionState();').values()],['Ready'])
            self.assertEqual(m.request('MEScFile.echo(\'TEST\');'), 'MEScFile:TEST')
        m.close()
        
    def test_03_reinstantiate(self):
        for i in range(10):
            m=MescapiInterface(debug=True)
            self.assertEqual(m.get_state(),'Ready')
            m.close()
            m=MescapiInterface()
            self.assertEqual(m.request('MEScFile.echo(\'TEST\');'), 'MEScFile:TEST')
            m.close()
        
    def test_04_invalid_command(self):
        m=MescapiInterface(debug=True)
        self.assertRaises(RuntimeError, m.request, 'invalidcmd();')
        m.close()
        
    @unittest.skip('')
    def test_05_high_load(self):
        '''
        Multiple commands with lot of data
        '''
        
        m=MescapiInterface(debug=True)
        import numpy
        from pylab import imshow,show
        from visexpman.generic import introspect
        nframes=3
        frame=numpy.zeros((nframes,512,512),dtype=numpy.uint16)
        nlines=32
        with introspect.Timer():
            for fr in range(nframes):
                for i in range(0, 512, nlines):
                    cmd='MEScFile.readRawChannelDataJSON(\'52,0,0,0\',\'0,{0},{2}\',\'512,{1},1\' );'.format(i,nlines,fr)
                    res=m.request(cmd)
                    frame[fr,:,i:i+nlines]=numpy.array(res).reshape(512,nlines, order='F')
        m.close()
        frame=65535-frame
        imshow(frame[0])
        show()
        
    def test_06_measurement_start(self):
        m=MescapiInterface(debug=True)
        self.assertRaises(IOError, m.stop)
        self.assertTrue(m.start())
        time.sleep(3)
        self.assertTrue(m.stop())
        m.close()
        
        
if __name__=='__main__':
    app = QtCore.QCoreApplication(sys.argv)
    unittest.main()
