import socket,subprocess,psutil,time,json,unittest,os
from visexpman.engine.generic import fileop
p=subprocess.Popen('c:\\Users\\mouse\\Documents\\build\\release\\MEScApiConsole.exe')
pp=psutil.Process(p.pid)
HOST='localhost'
PORT=27015
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
for i in range(1):
#    s.send('a=100;b=20;c=a+b;')
    s.send('MEScFile.getMescState();')
    data = s.recv(1024*1024)
    print data
s.close()


#Parse json
resp=json.loads(data.replace('\xb5','u'))#unicode is used for um
#TODO: make sure that process is terminated, time.sleep(1.5)
if 0 and pp.status()=='running':
    print 'kill'
    pp.kill()
pass

class MescapiInterface(object):
    def __init__(self, port=11000, command_buffer_size=1024*512, timeout=1.0):
        self.command_buffer_size=command_buffer_size
        apiserverpath=os.path.join(fileop.visexpman_package_path(), 'engine', 'external', 'mesc', 'MEScApiServer.exe')
        self.serverp=subprocess.Popen([apiserverpath, str(port)])
        self.serverpp=psutil.Process(self.serverp.pid)
        self.clientsocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.settimeout=timeout
        try:
            self.clientsocket.connect(('localhost', port))
        except:
            raise IOError('Cannot connect to MEScApiServer')

    def request(self,cmd):
        try:
            self.clientsocket.send(cmd)
        except:
            raise IOError('Command cannot be sent to MEScApiServer')
        try:
            data = self.clientsocket.recv(self.command_buffer_size)
        except:
            raise IOError('MEScApiServer does not respond')
        return json.loads(data.replace('\xb5','u'))#unicode is used for um
        
    def start(self):
        '''
        Initiate recording
        '''
        
    def stop(self):
        '''
        Terminate running measurement
        '''
        
    def microscope_state(self):
        '''
        get microscope state
        '''
    
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
        m=MescapiInterface()
        with introspect.Timer():
            m.request('MEScFile.getMescState();')
        m.close()
        
    def test_02_multiple_commands(self):
        m=MescapiInterface()
        m.request('MEScFile.getMescState();')
        m.request('MEScFile.echo(\'TEST\');')
        m.close()
        
    def test_03_reinstantiate(self):
        m=MescapiInterface()
        m.request('MEScFile.getMescState();')
        m.close()
        m=MescapiInterface()
        m.request('MEScFile.echo(\'TEST\');')
        m.close()
        
    def test_04_invalid_command(self):
        m=MescapiInterface()
        m.request('invalidcmd();')
        m.close()
        
    def test_05_high_load(self):
        '''
        Multiple commands with lot of data
        '''
        
if __name__=='__main__':
    unittest.main()
