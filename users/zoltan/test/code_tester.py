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
from visexpman.engine.generic import introspect

def cut2vids():
    folder = '/mnt/datafast/debug/recordings2video/cuts'
    outfolder = os.path.join(folder,  'out')
    if not os.path.exists(outfolder):
        os.mkdir(outfolder)
    else:
        shutil.rmtree(outfolder)
        os.mkdir(outfolder)
    for framefolder in file.listdir_fullpath(os.path.join(folder, 'raw')):
        frames = file.listdir_fullpath(framefolder)
        frames.sort()
        newfolder = os.path.join(outfolder, os.path.split(framefolder)[1])
        if not os.path.exists(newfolder):
            os.mkdir(newfolder)
        for i in range(len(frames)):
            newpath = os.path.join(newfolder,  'r{0:9}.png'.format(i).replace(' ',  '0'))
            shutil.copy(frames[i], newpath)
            pass
        videofile = os.path.join(outfolder, os.path.split(framefolder)[1] + '.mov')
        fps = 25
        command = 'avconv -y -r {0} -i {1} -map 0 -c:v mjpeg -b 5M {2}'.format(fps, os.path.join(newfolder, 'r%9d.png'), videofile)
        os.system(command)

#def plot(curve1,  curve2, block):
#    block.setdata(curve1, penwidth=3, color=Qt.Qt.darkRed)
#    block.adddata(curve2, penwidth=3,  color=Qt.Qt.black)
#    tempfilepath = mkstemp('.pdf')
#    block.exportPDF(tempfilepath, width=1600,  height=500)
#    block_im = imaged.pdf2numpy(tempfilepath.split('.pdf')[0])
#    return block_im

def stimulus_cadata2videoframes(path,  filter_rawdata = False,  export_rawdata = False,  stim_frame_folder = None):
    extension = 'png'
    tag = 'f'
    working_folder = os.path.join(os.path.split(path)[0],  'output')
    if not os.path.exists(working_folder):
        os.mkdir(working_folder)
    working_folder = os.path.join(working_folder,  os.path.split(path)[1])
    if not os.path.exists(working_folder):
        os.mkdir(working_folder)
    else:
        shutil.rmtree(working_folder)
        os.mkdir(working_folder)
    cfg = Config()
    h = hdf5io.Hdf5io(path, filelocking = False)
    ss = h.findvar('sync_signal')
    last_frame = ss['data_frame_start_ms'][-1] + ss['data_frame_duration_ms']
    last_stimulus = ss['stimulus_pulse_end_ms'][-1]
    xz_acpect_ratio = 5.0
    #rawdata to images
    rawdata1 = h.findvar('rawdata')
    rawdata_subset = rawdata1[:,:,:,0]
    if filter_rawdata:
        from scipy.signal import wiener, detrend
        factor = 1.0
        dr = detrend(rawdata_subset)
        with introspect.Timer('filtering'):
            dr = wiener(dr)
        dr = numpy.where(dr<0,  0.0,  dr)
        hist,bins = numpy.histogram(dr.flatten(),32)
        threshold = dr.shape[0]*dr.shape[1]*dr.shape[2]*1e-5
        maxthreshold = bins[numpy.nonzero(numpy.where(hist<threshold,  0,  1))[0].max()]
        dr = numpy.where(dr>maxthreshold,  maxthreshold,  dr)
        dr = numpy.exp(1e-6*dr)
        dr = generic.normalize(dr, numpy.uint8)
        rawdata = dr
    else:
        hist,bins = numpy.histogram(rawdata_subset.flatten(),32)
        threshold = rawdata_subset.shape[0]*rawdata_subset.shape[1]*rawdata_subset.shape[2]*1e-5
        maxthreshold = bins[numpy.nonzero(numpy.where(hist<threshold,  0,  1))[0].max()]
        rawdata_subset = numpy.where(rawdata_subset>maxthreshold,  maxthreshold,  rawdata_subset)
        rawdata = generic.normalize(rawdata_subset,  outtype = numpy.uint8)
        
    if export_rawdata:
        framedir = os.path.join(working_folder, 'rawdata')
        os.mkdir(framedir)
        nframes = rawdata.shape[2]
        for frame_i in range(nframes):
            frame = rawdata[:, :, frame_i]
#            from scipy.ndimage.filters import median_filter
#            frame = median_filter(frame, 5)
            if frame.shape[1]/frame.shape[0] > xz_acpect_ratio:
                scale = (frame.shape[1]/xz_acpect_ratio)/frame.shape[0]
                frame = generic_visexpman.rescale_numpy_array_image(frame,  utils.rc((scale,  1)),  Image.BICUBIC,  normalize = False)
            framepath = os.path.join(framedir,  'f{0:9}.png'.format(frame_i)).replace(' ', '0')
            Image.fromarray(frame).save(framepath)
    data_frame_indexes = []

    #Generate stimulus frames
    if False:
        machine_config, loaded_experiment_config = importers.load_configs(h)
        v = visexp_runner.VisionExperimentRunner('daniel',  'Stim2Bmp',  autostart = True)
        loaded_experiment_config = None
        v.run_experiment(loaded_experiment_config)
        
    if not stim_frame_folder is None:
        stim_frames = file.listdir_fullpath(stim_frame_folder)
        out_folder = os.path.join(working_folder, 'out')
        os.mkdir(out_folder)
        frame_counter = 0
        for stimulus_frame_i in  range(ss['stimulus_pulse_start_ms'].shape[0]-1):
            stim_t0 = ss['stimulus_pulse_start_ms'][stimulus_frame_i]
            stim_t1 = ss['stimulus_pulse_start_ms'][stimulus_frame_i+1]
            data_frame_start = ss['data_frame_start_ms']
            index = numpy.nonzero(numpy.where(stim_t1 >= data_frame_start,  1,  0))[0].max()
            data_frame_indexes.append(index)
            #Put stimulus and Ca image frames together
            if stimulus_frame_i%2 == 0 or True:
                stim_frame =  numpy.asarray(Image.open(stim_frames[stimulus_frame_i]))[::4, ::4]
                try:
                    frame = rawdata[:, :, index]
                except IndexError:
                    break
                ca_frame = generic_visexpman.vertical_flip_array_image(frame,  False)
                if ca_frame.shape[1]/ca_frame.shape[0] > xz_acpect_ratio:
                    scale = 0.76*stim_frame.shape[0]/float(ca_frame.shape[0])
                    ca_frame = generic_visexpman.rescale_numpy_array_image(ca_frame,  utils.rc((scale,  0.38)),  Image.BICUBIC,  normalize = False)
                else:
                    ca_frame = generic_visexpman.rescale_numpy_array_image(ca_frame,  2,  Image.BICUBIC,  normalize = False)
                image_size = [max(ca_frame.shape[0],  stim_frame.shape[0]),  ca_frame.shape[1] + 0*stim_frame.shape[1]]
                for i in range(2):#Make sure that image size is divisible by 2
                    if image_size[i] %2 != 0:
                        image_size[i] +=1
                frame = numpy.zeros((image_size[0], image_size[1], 3),  dtype = numpy.uint8)
                frame[0:ca_frame.shape[0], 0:ca_frame.shape[1], 1] = ca_frame
                white_pixels = numpy.nonzero(stim_frame)
                frame[white_pixels[0]-stim_frame.shape[0], white_pixels[1]-stim_frame.shape[1],  white_pixels[2]] = 180
                framepath = os.path.join(out_folder,  '{2}{0:9}.{1}'.format(frame_counter,  extension,  tag)).replace(' ', '0')
                frame_counter += 1
                im = Image.fromarray(frame)
#                    im = im.resize((1024, 768),  Image.ANTIALIAS)
                im.save(framepath)
                pass
        
    h.close()
    if not stim_frame_folder is None:
        fps = 60
        videofile = os.path.join(working_folder, os.path.split(path)[1].replace('hdf5', 'mp4'))
        command = 'avconv -y -r {0} -i {1} -map 0 -c:v libx264 -b 5M {2}'.format(fps, os.path.join(out_folder, '{0}%9d.{1}'.format(tag,  extension)), videofile)
#        command = 'avconv -y -r {0} -i {1} -map 0 -c:v mpeg4 -b 5M {2}'.format(fps, os.path.join(out_folder, '{0}%9d.{1}'.format(tag,  extension)), videofile)
        os.system(command)

if __name__=='__main__':
    if True:
        cut2vids()
    else:
        stim_frame_folder = '/mnt/datafast/debug/captured_2'
        for path in file.listdir_fullpath('/mnt/datafast/debug/recordings2video'):
            if 'hdf5' in path:
                with introspect.Timer('generate video'):
                    stimulus_cadata2videoframes(path,  filter_rawdata = not True,  export_rawdata = False, stim_frame_folder = stim_frame_folder)
            

    
