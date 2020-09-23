import zmq,unittest,time
PORT=5556
IP='127.0.0.1'

def start_recording():
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s:%s" % (IP, PORT))
        socket.send(b"StartRecord CreateNewDir=1")
        socket.recv(flags=zmq.NOBLOCK)
        return True
    except:
        return False
    
    
def stop_recording():
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s:%s" % (IP, PORT))
        socket.send(b"StopRecord")
        socket.recv(flags=zmq.NOBLOCK)
        socket.send(b"StopAcquisition")
        socket.recv(flags=zmq.NOBLOCK)
        return True
    except:
        return False
    
class Test(unittest.TestCase):
    def test(self):
        res1=start_recording()
        time.sleep(10)
        res2=stop_recording()
        self.assertTrue(res1)
        self.assertTrue(res2)


if __name__ == "__main__":
    unittest.main()
