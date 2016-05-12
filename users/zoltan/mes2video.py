from pylab import *
import scipy.io
import os
import os.path
import tempfile
import numpy
import shutil
from PIL import Image
import subprocess
import multiprocessing
from visexpA.engine.datahandlers import matlabfile
from visexpman.engine.generic import signal

def mes2video(f,save2mat=False,outfolder=None):
    print f
    data = scipy.io.loadmat(f,mat_dtype=True)
    is_red_channel = data['DATA'].shape[0] == 3
    duration=data['DATA'][0]['Height'][0][0][0] * data['DATA'][0]['HeightStep'][0][0][0]*1e-3
    data = numpy.cast['float'](matlabfile.read_line_scan(f,is_red_channel))
    if outfolder is None:
        outfolder=os.path.join(os.path.split(f)[0], 'out')
        if not os.path.exists(outfolder):
            os.mkdir(outfolder)
    if save2mat:
        scipy.io.savemat(os.path.join(outfolder, os.path.split(f)[1]), {'rawdata': numpy.cast['uint16'](data)}, oned_as='column')
    frame_rate = data.shape[2]/duration
    folder=tempfile.mkdtemp()
    if data.shape[3]==2:
        red_max = data[:,:,:,1].max()
    green_max = data[:,:,:,0].max()
    for i in range(data.shape[2]):
        frame=numpy.zeros((data.shape[0],2*data.shape[1], 3),dtype=numpy.uint8)
        if data.shape[3]==2:
            frame[:,:frame.shape[1]/2,0] = signal.scale(data[:,:,i,1]/red_max*255,0,255)
        frame[:,frame.shape[1]/2:,1] = signal.scale(data[:,:,i,0]/green_max*255,0,255)
        Image.fromarray(frame).save(os.path.join(folder, '{0:0=6}.png'.format(i)))
#        if i ==5:
#            break
    fvid = os.path.join(outfolder,os.path.split(f)[1]+'.mp4')
    subprocess.call('avconv -y -r {0} -i {1}/%06d.png -map 0 -c:v libx264 -b 5M {2}'.format(frame_rate,folder, fvid),shell=True)
    shutil.rmtree(folder)

if __name__=='__main__':
    folders=['/mnt/rzws/temp/fede/20150204/rec1', '/mnt/rzws/temp/fede/20150204/rec2']
    for folder in folders:
        files=[os.path.join(folder, f) for f in os.listdir(folder) if '.mat' in f]
        ff=map(os.path.join, len(files)*[folder], files)
        p=multiprocessing.Pool(processes=3)
        p.map(mes2video,ff)
    
    






