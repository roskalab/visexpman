import socket,subprocess,psutil,time,json,unittest,os,sys
from visexpman.engine.generic import fileop
if 1:
    try:
        import mescapi
        import PyQt5.QtCore as QtCore
        use_proxy=False
    except ImportError:
        use_proxy=True
else:
    use_proxy=True

class MescapiInterface(object):
    def __init__(self, mesc_address='localhost', port=11000, command_buffer_size=1024*512, timeout=1.0,debug=False):
        if use_proxy:
            self.command_buffer_size=command_buffer_size
            apiserverpath=os.path.join(fileop.visexpman_package_path(), 'engine', 'external', 'mesc', 'MEScApiServer.exe')
            self.serverp=subprocess.Popen([apiserverpath, str(port)],shell=not debug)
            self.serverpp=psutil.Process(self.serverp.pid)
            self.clientsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self.clientsocket.settimeout(timeout)
            try:
                self.clientsocket.connect((mesc_address, port))
            except:
                self.serverpp.kill()
                raise IOError('Cannot connect to MEScApiServer')
        else:
            self.connected=False
            self.manager = mescapi.APIClientManager()
            done=self.manager.webSocketConnect(QtCore.QUrl('ws://{0}:8888'.format(mesc_address)))
            if not done:
                return#Subsequent exception is not raised and main_ui freezes
                raise IOError('Cannot connect to MEScApiServer')
            self.client=self.manager.getClientListModel().getClient(0)
            loginParser=self.client.login('default','defaultpw')
            resultCode=loginParser.getResultCode()
            if resultCode > 0:
                raise RuntimeError (loginParser.getErrorText())
            self.connected=True

    def request(self,cmd):
        if use_proxy:
            try:
                if sys.version_info.major==3:
                    cmd=bytearray(cmd,'utf-8')
                self.clientsocket.send(cmd)
            except:
                self.serverpp.kill()
                raise IOError('Command cannot be sent to MEScApiServer')
            try:
                data = self.clientsocket.recv(self.command_buffer_size)
            except:
                self.serverpp.kill()
                raise IOError('MEScApiServer does not respond')
        else:
            parser=self.client.sendJSCommand(cmd)
            res=parser.getResultCode()
            if res > 0:
                raise RuntimeError(parser.getErrorText())
            else:	
                data=parser.getJSEngineResult()
        self.data=data
        if isinstance(data, bool) or isinstance(data, int):
            return data
        elif not isinstance(data, str):
            data=data.decode('utf-8')
        try:
            return json.loads(data.replace('\xb5','u'))#unicode is used for um
        except ValueError:
            return data
            
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
        return self.request('MEScMicroscope.startResonantScanAsync()')
        
    def stop(self):
        '''
        Terminate running measurement
        '''
        state=self.get_state()
        if state!='Working':
            raise IOError('Acquisition is not running, current state: {0}\r\nCheck MESc, error might have happened during recording'.format(state))
        return self.request('MEScMicroscope.stopResonantScanAsync()')
        
    def get_state(self):
        '''
        get microscope state
        '''
        return self.request('MEScMicroscope.getAcquisitionState()')['Common']['microscopeState']
    
    def save(self, filename):
        '''
        Saves last recording to file
        '''
        
    def terminate(self):
        self.serverpp.kill()
    
    def close(self):
        if use_proxy:
            self.clientsocket.close()
            try:
                self.serverpp.kill()
            except psutil.NoSuchProcess:
                pass
        else:
            if self.connected:
                self.manager.closeConnection(self.client)
        
class TestMesc(unittest.TestCase):
    def test_01_simple_use(self):
        from visexpman.engine.generic import introspect
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
