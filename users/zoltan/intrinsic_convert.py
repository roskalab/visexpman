import sys,scipy.io,time,os,numpy,logging,time,traceback
from PIL import Image
from visexpman.engine.generic import signal
from pylab import plot,savefig,show,xlabel,title
JOB_FOLDER='d:\\cam\\jobs'

def raw2mat(id, folder, recording_duration,averaging, gain,exposure, frame_rate):
    cleanup=True
    res=(600,960)
    recording_duration=float(recording_duration)
    averaging=int(averaging)
    gain=float(gain)
    exposure=float(exposure)
    frame_rate=float(frame_rate)
    filename=os.path.join(folder, id+'.mat')
    filenamemip=os.path.join(folder, id+'_mip.png')
    filenameplot=os.path.join(folder, id+'_mean_intensity.png')
    log('Converting {0}'.format(id))
    files=[f for f in os.listdir(folder) if id in f and os.path.splitext(f)[1]=='.raw']
    files.sort()
    frames=[]
    t0=time.time()
    log('reading frames')
    for f in files:
        pixels=numpy.fromfile(os.path.join(folder,f),numpy.uint16)
        frames.append(pixels.reshape(res))
        frames[-1]=frames[-1][res[0]/4:3*res[0]/4,res[1]/4:3*res[1]/4]#Cutting out center
    t1=time.time()
    frames=numpy.array(frames)
    mip=frames.max(axis=0)
    #mean intensity
    t=numpy.arange(frames.shape[0])/frame_rate
    mean_intensity=frames.mean(axis=1).mean(axis=1)
    plot(t,mean_intensity)
    title(id)
    xlabel('time [s]')
    savefig(filenameplot,dpi=200)
    averaged_frames=[]
    log('averaging frames')
    for i in range(frames.shape[0]/averaging):
        averaged_frames.append(frames[i*averaging:(i+1)*averaging].mean(axis=0))
    averaged_frames=numpy.array(averaged_frames)
    averaged_frames=numpy.cast['uint16'](averaged_frames)
    log('saving to {0}'.format(filename))
    data={}
    data['mip']=mip
    data['rawdata']=averaged_frames
    data['recording_duration']=recording_duration
    data['fps']=frames.shape[0]/recording_duration
    data['data_fps']=averaged_frames.shape[0]/recording_duration
    print data['fps'], '/', data['data_fps'], 'Hz'
    data['gain']=gain
    data['exposure']=exposure
    data['frame_rate']=frame_rate
    data['averaging']=averaging
    scipy.io.savemat(filename,data,do_compression=False)
    print 'Saved to {0}'.format(filename)
    Image.fromarray(numpy.cast['uint8'](signal.scale(mip)*255)).save(filenamemip)
    t2=time.time()
    if cleanup:
        log('Removing raw files')
        [os.remove(os.path.join(folder,f)) for f in files]
    t3=time.time()
    print t1-t0,t2-t1,t3-t2
    
def log(msg):
    print msg
    logging.info(msg)
    
    
def processor():
    logging.basicConfig(filename= 'd:\\cam\\log\\converter.txt',
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
    while True:
        try:
            files=[os.path.join(JOB_FOLDER, f) for f in os.listdir(JOB_FOLDER)]
            if len(files)==0:
                time.sleep(1)
                continue
            fileage=[os.path.getmtime(f) for f in files]
            oldest=min(fileage)
            if time.time()-oldest<2:
                time.sleep(2)
                continue
            oldest_file=files[fileage.index(oldest)]
            fp=open(oldest_file,'rt')
            pars= fp.read().split(',')
            fp.close()
            raw2mat(*pars)
            os.remove(oldest_file)
            log('{0} done'.format(pars[0]))
        except:
            log(traceback.format_exc())

if __name__ == "__main__":
    if len(sys.argv)==1:
        processor()
        #raw2mat(*sys.argv[1:])
    else:
        pars2save=sys.argv[1:]
        fp=open(os.path.join(JOB_FOLDER, sys.argv[1]+'.txt'), 'wt')
        fp.write(','.join(pars2save))
        fp.close()
        print 'Passed to converter'
        
    
     
