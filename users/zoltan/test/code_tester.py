import shutil
import tables
import os.path
import os
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpA.engine.datahandlers import hdf5io
import cPickle as pickle
import visexpA.engine.component_guesser as cg
from visexpA.users.zoltan.configuration import Config
#from visexpA.engine.datadisplay.plot import Qt4Plot
#import PyQt4.Qt as Qt
import Image
from visexpman.engine.generic.file import mkstemp
from visexpman.engine import generic as generic_visexpman
from visexpA.engine.datadisplay import imaged
from visexpA.engine.dataprocessors import generic
from visexpman.engine.vision_experiment import command_handler
from visexpman.engine import visexp_runner
from visexpA.engine.datahandlers import importers

#def plot(curve1,  curve2, block):
#    block.setdata(curve1, penwidth=3, color=Qt.Qt.darkRed)
#    block.adddata(curve2, penwidth=3,  color=Qt.Qt.black)
#    tempfilepath = mkstemp('.pdf')
#    block.exportPDF(tempfilepath, width=1600,  height=500)
#    block_im = imaged.pdf2numpy(tempfilepath.split('.pdf')[0])
#    return block_im
    
if __name__=='__main__':
    path = '/mnt/datafast/debug/fragment_xy_farbottom_-549_481_-130.0_MovingGratingNoMarching_1344865580_0.hdf5'
#    path = 'V:\\debug\\fragment_xy_farbottom_-549_481_-130.0_MovingGratingNoMarching_1344865580_0.hdf5'
    cfg = Config()
#    block = Qt4Plot(None, visible=False)
    h = hdf5io.iopen(path,  cfg)
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
    rawdata_subset = rawdata[:,:,:350,:]
    if False:
        from scipy.signal import wiener, detrend
        dr = detrend(rawdata_subset)
        rawdata=wiener(dr)
    
    rawdata = generic.normalize(rawdata,  outtype = numpy.uint8, std_range = 4)[:, :, :, 0]
    if True:        
        framedir = '/mnt/datafast/debug/f'
        if os.path.exists(framedir):
            shutil.rmtree(framedir)
        os.mkdir(framedir)
        nframes = max(rawdata.shape)
        for frame_i in range(nframes):
            frame = rawdata[:, :, frame_i]
            framepath = os.path.join(framedir,  'f{0:9}.png'.format(frame_i)).replace(' ', '0')
            Image.fromarray(frame).save(framepath)
    data_frame_indexes = []

    #Generate stimulus frames
    if False:
        machine_config, loaded_experiment_config = importers.load_configs(h)
        v = visexp_runner.VisionExperimentRunner('daniel',  'Stim2Bmp',  autostart = True)
        v.run_experiment(loaded_experiment_config)

    stim_frames = file.listdir_fullpath('/mnt/datafast/debug/cc')
    out_folder = '/mnt/datafast/debug/out'
    for stimulus_frame_i in  range(ss['stimulus_pulse_start_ms'].shape[0]-1):
        stim_t0 = ss['stimulus_pulse_start_ms'][stimulus_frame_i]
        stim_t1 = ss['stimulus_pulse_start_ms'][stimulus_frame_i+1]
        data_frame_start = ss['data_frame_start_ms']
        index = numpy.nonzero(numpy.where(stim_t1 >= data_frame_start,  1,  0))[0].max()
        data_frame_indexes.append(index)
        #Put stimulus and Ca image frames together
        if stimulus_frame_i%2 == 0:
            aspect_ratio = 16.0/9
            frame = rawdata[:, :, index]
            ca_frame = generic_visexpman.vertical_flip_array_image(frame)
            ca_frame = generic_visexpman.rescale_numpy_array_image(ca_frame,  2,  Image.BICUBIC,  normalize = False)
            stim_frame = numpy.asarray(Image.open(stim_frames[stimulus_frame_i]))
            image_size = [max(ca_frame.shape[0],  stim_frame.shape[0]),  ca_frame.shape[1] + stim_frame.shape[1]]
            if image_size[1]/float(image_size[0]) < aspect_ratio:
                image_size[1] = int(image_size[0]*aspect_ratio)
            else:
                image_size[0] = int(image_size[1]/aspect_ratio)
            
            frame = numpy.zeros((image_size[0], image_size[1], 3),  dtype = numpy.uint8)
            frame[0:ca_frame.shape[0], 0:ca_frame.shape[1],  1] = ca_frame
            frame[0:stim_frame.shape[0], ca_frame.shape[1]:,  :] = stim_frame
        
            framepath = os.path.join(out_folder,  'f{0:9}.png'.format(int(stimulus_frame_i/2))).replace(' ', '0')
            im = Image.fromarray(frame)
            im = im.resize((1920, 1080),  Image.ANTIALIAS)
            im.save(framepath)
        if stimulus_frame_i == 1200:
            break
        
        
        
    h.close()
