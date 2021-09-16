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

def check_data(in_folder):
    in_folder=os.path.join(in_folder, 'experiment1', 'recording1')
    json_file = open(os.path.join(in_folder, "structure.oebin"))
    json_data = json.load(json_file)
    json_file.close()
    sample_rate = json_data['continuous'][0]['sample_rate']

    camera_sync_ch_index = -1
    for ch in json_data['continuous'][0]['channels']:
        if(ch['channel_name'] == 'ADC2'):
            camera_sync_ch_index = ch['source_processor_index']
            break
    if(camera_sync_ch_index == -1):
        print('Camera sync CH(ADC2) not found error!')
        return -1
        
    ch_count = len(json_data['continuous'][0]['channels'])
     
    data_file_path = os.path.join(in_folder, "continuous","Rhythm_FPGA-100.0","continuous.dat") #fix folder structure?
    data = numpy.fromfile(data_file_path, dtype='<i2')
    deinterleaved_data = [data[idx::ch_count] for idx in range(ch_count)]
    sync_data = deinterleaved_data[camera_sync_ch_index]
    sync_data_raw=numpy.copy(sync_data)
    #sync_data = sync_data[180000:]  #skip start transiens ??
    
    #calc pulse widths, r_edge
    min_amplitude = 10000;
#    pulse_widths=[]
#    rising_edges=[]
#    found=False;
#    width_cnt=0;
#    for i in range(len(sync_data)):
#        if(sync_data[i] > min_amplitude):
#            if(width_cnt == 0): #rising edge
#                width_cnt = width_cnt +1
#                rising_edges.append(i)
#            else:
#                width_cnt = width_cnt +1
#        else:
#            if(width_cnt > 0): #falling edge
#                pulse_widths.append(width_cnt)
#                width_cnt = 0
#    rising_edges = numpy.array(rising_edges) 
    rising_edges=signal.detect_edges(sync_data, min_amplitude)[::2]
    periods = rising_edges[1:] - rising_edges[0:-1]  #samples
    periods = periods * (1.0/sample_rate);  #sec 
    period = periods.mean()
    frequency = 1.0/period  #Hz
    frequency_std = (1.0/periods).std();
    
    print("period(mean)",period*1000, "ms") 
    print("Frequency(mean):",frequency,"Hz")
    print("Frequency deviation:",frequency_std,"Hz")
    #plt.plot(sync_data)
    #plt.show()
    return frequency, frequency_std, rising_edges, sync_data_raw
    
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
        check_data(in_folder)

        

if __name__ == "__main__":
    unittest.main()
