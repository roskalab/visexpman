import zmq,unittest,time, psutil, numpy, os, json, pdb
import matplotlib.pyplot as plt
from visexpman.engine.generic import signal
PORT=5556
IP='127.0.0.1'

def start_recording(ip=None,  tag=""):
    try:
        if ip is None:
            ip=IP
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s:%s" % (ip, PORT))
        time.sleep(0.5)
        socket.send(b"StartAcquisition")
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        if tag == "":
            socket.send(b"StartRecord CreateNewDir=1")
        else:
            socket.send_string(f"StartRecord CreateNewDir=1 AppendText={tag}")
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        return True
    except:
        import traceback
        print(traceback.format_exc())
        return False
    
    
def stop_recording(ip=None):
    try:
        if ip is None:
            ip=IP
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s:%s" % (ip, PORT))
        socket.send(b"StopRecord")
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        socket.send(b"StopAcquisition")
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        return True
    except:
        return False
    
def read_sync(in_folder):
    #in_folder=os.path.join(in_folder, 'experiment1', 'recording1')
    json_file = open(os.path.join(in_folder, "structure.oebin"))
    json_data = json.load(json_file)
    json_file.close()
    sample_rate = json_data['continuous'][0]['sample_rate']

    sync_ch_index = -1
    for ch in json_data['continuous'][0]['channels']:
        if(ch['channel_name'] == 'AP_SYNC'):
            sync_ch_index = ch['source_processor_index']
            break
    if(sync_ch_index == -1):
        raise RuntimeError('sync CH not found error!')
        
    ch_count = len(json_data['continuous'][0]['channels'])
     
    data_file_path = os.path.join(in_folder, "continuous","Neuropix-PXI-100.0","continuous.dat") #fix folder structure?
    data = numpy.fromfile(data_file_path, dtype='<i2')
    deinterleaved_data = [data[idx::ch_count] for idx in range(ch_count)]
    sync_data = deinterleaved_data[sync_ch_index]
    return sync_data, sample_rate
    
class Test(unittest.TestCase):
    @unittest.skip('')
    def test(self):
        res1=start_recording()
        time.sleep(20)
        res2=stop_recording()
        self.assertTrue(res1)
        self.assertTrue(res2)
    
    def test_check_data(self):
        in_folder=r'H:\rz_organoid\oe_data\experiment1\recording1'
        in_folder='/tmp/oe/experiment1/recording1'
        in_folder=r'C:\data\2021-09-08_12-08-49_sep8_DG_20deg_20degsec_AP3900_ML1300_DV3900_202109081208476\Record Node 103\experiment1\recording1'
        sync, fs=read_sync(in_folder)
        import scipy.io
        sync2=scipy.io.loadmat(r'C:\data\lefteye_202109081208476_sep8_DG_20deg_20degsec_AP3900_ML1300_DV3900.mat')['sync'][:, 1]
        fs2=scipy.io.loadmat(r'C:\data\lefteye_202109081208476_sep8_DG_20deg_20degsec_AP3900_ML1300_DV3900.mat')['machine_config']['SYNC_RECORDER_SAMPLE_RATE'][0][0][0][0]
        from pylab import subplot, plot, show, title, legend
        t2=numpy.arange(sync2.shape[0])/fs2
        t=numpy.arange(sync.shape[0])/fs
        plot(t2, sync2)
        plot(t, sync)
        legend(['sync pulse recorded by NI board',  'sync pulse recorded by NP (low pass filtered)'])
        show()
        pass

        

if __name__ == "__main__":
    unittest.main()
