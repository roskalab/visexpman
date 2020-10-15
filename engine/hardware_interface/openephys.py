import zmq,unittest,time, psutil, numpy, os, json, pdb
import matplotlib.pyplot as plt
PORT=5556
IP='127.0.0.1'

def start_recording():
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s:%s" % (IP, PORT))
        time.sleep(1)
        socket.send(b"StartRecord CreateNewDir=1")
        time.sleep(1)
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
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        socket.send(b"StopAcquisition")
        time.sleep(1)
        socket.recv(flags=zmq.NOBLOCK)
        return True
    except:
        return False

def file_quality_check(in_folder):
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
    sync_data = sync_data[180000:]  #skip start transiens ??
    
    #calc pulse widths, r_edge
    min_amplitude = 10000;
    pulse_widths=[]
    rising_edges=[]
    found=False;
    width_cnt=0;
    for i in range(len(sync_data)):
        if(sync_data[i] > min_amplitude):
            if(width_cnt == 0): #rising edge
                width_cnt = width_cnt +1
                rising_edges.append(i)
            else:
                width_cnt = width_cnt +1
        else:
            if(width_cnt > 0): #falling edge
                pulse_widths.append(width_cnt)
                width_cnt = 0
                
    rising_edges = numpy.array(rising_edges)          
    periods = rising_edges[1:] - rising_edges[0:-1]  #samples
    periods = periods * (1.0/sample_rate);  #sec 
    period = periods.mean()
    frequency = 1.0/period  #Hz
    frequency_dev = (1.0/periods).std();
    
    print("period(mean)",period*1000, "ms") 
    print("Frequency(mean):",frequency,"Hz")
    print("Frequency deviation:",frequency_dev,"Hz")
    #plt.plot(sync_data)
    #plt.show()
    
    
    
    pdb.set_trace()
    
class Test(unittest.TestCase):
    @unittest.skip('')
    def test(self):
        res1=start_recording()
        time.sleep(20)
        res2=stop_recording()
        self.assertTrue(res1)
        self.assertTrue(res2)
    
    def test_file_quality_check(self):
        in_folder=r'H:\rz_organoid\oe_data\experiment1\recording1'
        in_folder='/tmp/oe/experiment1/recording1'
        file_quality_check(in_folder)

        

if __name__ == "__main__":
    unittest.main()
