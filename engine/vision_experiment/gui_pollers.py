import time
import numpy
import os.path
import os
if os.name == 'nt':
    import winsound
else:
    winsound = None
from visexpman.engine.vision_experiment import gui
from visexpman.engine.hardware_interface import flowmeter
from visexpman.engine.generic import file

class FlowmeterPoller(flowmeter.Flowmeter, gui.Poller):
    def __init__(self, parent, config):
        gui.Poller.__init__(self, parent)
        flowmeter.Flowmeter.__init__(self, config)
        self.recording = []
        self.timeseries = []
        self.path = file.generate_filename(os.path.join(self.config.LOG_PATH, 'recording.txt'))
        self.file = open(self.path, 'at')
        self.file.write('time[s]\tflow rate[ul/min\n')
        self.last_file_write = time.time()
        self.last_flowrate_check = time.time()
        
    def periodic(self):
        #Update status
        if self.running:
            status = 'running'
        elif self.init_ready:
            status = 'initialized'
        else:
            status = 'not initialized' 
        data = self.read(self.config.GUI_REFRESH_PERIOD * 7)
        if not data[0]:
            self.parent.update_status(status)
        else:
            self.parent.update_status(status, data[1][0])
            recording_chunk = data[1]
            timeseries_chunk = numpy.arange(len(self.recording), len(self.recording) + data[1].shape[0], dtype = numpy.float) / self.config.FLOWMETER['SAMPLING_RATE']
            rec_str = ''
            for i in range(recording_chunk.shape[0]):
                rec_str += '{0}\t{1:2.2f}\n'.format(timeseries_chunk[i], recording_chunk[i])
            self.file.write(rec_str)
            now = time.time()
            if now - self.last_file_write > self.config.FILEWRITE_PERIOD:
                self.file.flush()
                self.last_file_write = now
            self.recording.extend(data[1].tolist())
            #Sound alarm
            if now - self.last_flowrate_check > self.config.FLOW_STUCKED_CHECK_PERIOD and abs(data[1]).mean() < self.config.FLOW_STUCKED_LIMIT and hasattr(winsound, 'PlaySound'):
                self.last_flowrate_check = now
                self.printc('Low flowrate')
                winsound.PlaySound('SystemHand',winsound.SND_ALIAS)
        
    def close(self):
        self.stop_measurement()
        self.file.close()
    
