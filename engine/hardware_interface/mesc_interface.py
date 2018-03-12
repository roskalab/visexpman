import socket,subprocess,psutil,time,json
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
