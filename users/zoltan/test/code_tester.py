import shutil
import tables
import os.path
import os
import numpy
from visexpA.engine.datahandlers import hdf5io
from visexpman.engine.generic import utils
import cPickle as pickle
import visexpA.engine.component_guesser as cg
from visexpA.users.zoltan.configuration import Config
from visexpA.engine.datadisplay.plot import Qt4Plot
import PyQt4.Qt as Qt
import Image
from visexpman.engine.generic.file import mkstemp
from visexpA.engine.datadisplay import imaged
from visexpA.engine.dataprocessors import generic
from visexpman.engine.vision_experiment import command_handler
from visexpman.engine import visexp_runner
from visexpA.engine.datahandlers import importers

def plot(curve1,  curve2, block):
    block.setdata(curve1, penwidth=3, color=Qt.Qt.darkRed)
    block.adddata(curve2, penwidth=3,  color=Qt.Qt.black)
    tempfilepath = mkstemp('.pdf')
    block.exportPDF(tempfilepath, width=1600,  height=500)
    block_im = imaged.pdf2numpy(tempfilepath.split('.pdf')[0])
    return block_im
    
if __name__=='__main__':
    path = '/mnt/datafast/debug/fragment_xy_farbottom_-549_481_-130.0_MovingGratingNoMarching_1344865580_0.hdf5'
    cfg = Config()
    block = Qt4Plot(None, visible=False)
    h = hdf5io.Hdf5io(path)
    ss = h.findvar('sync_signal')
    last_frame = ss['data_frame_start_ms'][-1] + ss['data_frame_duration_ms']
    last_stimulus = ss['stimulus_pulse_end_ms'][-1]


#    node_name = '_'.join(cg.get_mes_name_timestamp(h))
#    sync = h.findvar('sync_data',  path = 'root.' + node_name)
#    curve1 = sync[1500000:, 0]
#    curve2 = sync[1500000:, 1]
#    Image.fromarray(plot(curve1,  curve2, block)).save('/mnt/datafast/debug/ch1.png')
    
    #rawdata to images
    rawdata = h.findvar('rawdata')
    framedir = '/mnt/datafast/debug/f'
    if os.path.exists(framedir):
        shutil.rmtree(framedir)
    os.mkdir(framedir)
    nframes = max(rawdata.shape)
    for frame_i in range(nframes):
        frame = rawdata[:, :, frame_i, 0]
        frame = generic.normalize(frame, outtype=numpy.uint8)
        framepath = os.path.join(framedir,  'f{0:9}.png'.format(frame_i)).replace(' ', '0')
        Image.fromarray(frame).save(framepath)
    #Generate stimulus frames
    machine_config, loaded_experiment_config = importers.load_configs(h)
    v = visexp_runner.VisionExperimentRunner('daniel',  'Stim2Bmp',  autostart = True)
#    v.run_loop()
    v.run_experiment(loaded_experiment_config)
    h.close()
