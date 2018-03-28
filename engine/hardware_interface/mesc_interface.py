import socket,subprocess,psutil,time,json,unittest,os
from visexpman.engine.generic import fileop

class MescapiInterface(object):
    def __init__(self, port=11000, command_buffer_size=1024*512, timeout=1.0,debug=False):
        self.command_buffer_size=command_buffer_size
        apiserverpath=os.path.join(fileop.visexpman_package_path(), 'engine', 'external', 'mesc', 'MEScApiServer.exe')
        self.serverp=subprocess.Popen([apiserverpath, str(port)],shell=not debug)
        self.serverpp=psutil.Process(self.serverp.pid)
        self.clientsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.clientsocket.settimeout(timeout)
        try:
            self.clientsocket.connect(('localhost', port))
        except:
            self.serverpp.kill()
            raise IOError('Cannot connect to MEScApiServer')

    def request(self,cmd):
        try:
            self.clientsocket.send(cmd)
        except:
            self.serverpp.kill()
            raise IOError('Command cannot be sent to MEScApiServer')
        try:
            data = self.clientsocket.recv(self.command_buffer_size)
        except:
            self.serverpp.kill()
            raise IOError('MEScApiServer does not respond')
        self.data=data
        try:
            return json.loads(data.replace('\xb5','u'))#unicode is used for um
        except ValueError:
            return data
        
    def start(self):
        '''
        Initiate recording
        '''
        return self.request('MEScMicroscope.startResonantScanAsync()')
        
    def stop(self):
        '''
        Terminate running measurement
        '''
        return self.request('MEScMicroscope.stopResonantScanAsync()')
        
    def microscope_state(self):
        '''
        get microscope state
        '''
        return self.request('MEScMicroscope.getAcquisitionState()')
    
    def save(self, filename):
        '''
        Saves last recording to file
        '''
        
    def terminate(self):
        self.serverpp.kill()
    
    def close(self):
        self.clientsocket.close()
        try:
            self.serverpp.kill()
        except psutil.NoSuchProcess:
            pass
        
class TestMesc(unittest.TestCase):
    def test_01_simple_use(self):
        from visexpman.engine.generic import introspect
        m=MescapiInterface(debug=True)
        with introspect.Timer():
            m.request('MEScFile.getMescState();')
        m.close()
        
    def test_02_multiple_commands(self):
        m=MescapiInterface(debug=True)
        for i in range(10):
            self.assertEqual(m.request('MEScMicroscope.getAcquisitionState();').values(),['Ready'])
            self.assertEqual(m.request('MEScFile.echo(\'TEST\');'), 'MEScFile:TEST')
        m.close()
        
    def test_03_reinstantiate(self):
        for i in range(10):
            m=MescapiInterface(debug=True)
            self.assertEqual(m.request('MEScMicroscope.getAcquisitionState();').values(),['Ready'])
            m.close()
            m=MescapiInterface()
            self.assertEqual(m.request('MEScFile.echo(\'TEST\');'), 'MEScFile:TEST')
            m.close()
        
    def test_04_invalid_command(self):
        m=MescapiInterface(debug=True)
        self.assertEqual(m.request('invalidcmd();')['MESc Error code'],4)
        m.close()
        
    def test_05_high_load(self):
        '''
        Multiple commands with lot of data
        '''
        
        m=MescapiInterface(debug=True)
        import numpy
        from pylab import imshow,show
        from visexpman.engine.generic import introspect
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
        
if __name__=='__main__':
    unittest.main()
