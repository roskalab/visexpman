from pylab import *
import time,numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import utils, log,fileop,introspect
import multiprocessing
import os.path
import tables
from visexpA.engine.datahandlers.datatypes import ImageData
from visexpA.engine.datahandlers.hdf5io import Hdf5io


if __name__ == "__main__":
    with introspect.Timer(''):
        #Sampling analog input starts
        folder = 'r:\\dataslow\\measurements\\electrode_current_temperature'
        ai_channels = 'Dev1/ai3:5'
        ai_channels = 'Dev1/ai0:2'
        ai_record_time = 0.2
        ai_sample_rate = 300000
        complevel = 0
        
        device_name, nchannels, channel_indexes = daq_instrument.parse_channel_string(ai_channels)
        
        h = ImageData(fileop.generate_filename(os.path.join(folder, 'data.hdf5')), filelocking=False)
        raw_data = h.h5f.create_earray(h.h5f.root, 'raw_data', tables.Float32Atom((nchannels,)), (0,),filters=tables.Filters(complevel=complevel, complib='lzo', shuffle = 1), expectedrows=int(ai_record_time * ai_sample_rate))
        
        logfile = fileop.generate_filename(os.path.join(folder, 'log_recorder.txt'))
        logger = log.Logger(filename=logfile)
        instrument_name = 'recorder'
        logger.add_source(instrument_name)
        queues = {'command': multiprocessing.Queue(), instrument_name: multiprocessing.Queue(), 'data': multiprocessing.Queue(),'response': multiprocessing.Queue()}
        aio = daq_instrument.AnalogIOProcess('recorder', queues, logger, ai_channels = ai_channels)
        aio.start()
        logger.start()
        aio.start_daq(ai_sample_rate = ai_sample_rate,ai_record_time = 3.0, timeout = 10) 
        print 'recording...'
        print 'press enter twice to terminate'
        data = []
        i=0
        t0=time.time()
        with introspect.Timer(''):
            while not utils.enter_hit():
                r=aio.read_ai()
                if r is not None:
                    raw_data.append(numpy.cast['float32'](r))
                i+=1
                if time.time()-t0>30.0:
                    break
                time.sleep(0.1)
        print 'stopping...'

        data1 = aio.stop_daq()
        for r in data1[0]:
            raw_data.append(numpy.cast['float32'](r))
        aio.terminate()
        logger.terminate()
        h.close()
        print 'done'
        import zipfile
        zipfile_handler = zipfile.ZipFile(h.filename.replace('.hdf5','.zip'), 'a',compression=zipfile.ZIP_DEFLATED)
        zipfile_handler.write(h.filename, os.path.split(h.filename)[1])
        zipfile_handler.close()
        h=Hdf5io(h.filename,filelocking=False)
        h.load('raw_data')
        print h.raw_data.shape[0]/float(ai_sample_rate)
#        plot(h.raw_data[:1000],'x-')
        h.close()
#        show()
        pass
