import sys,scipy.io,time,os,numpy
from PIL import Image
from visexpman.engine.generic import signal

def raw2mat(id, folder, recording_duration):
    cleanup=True
    res=(600,960)
    gain=18
    exposure=1
    recording_duration=float(recording_duration)
    filename=os.path.join(folder, id+'.mat')
    filenamemip=os.path.join(folder, id+'_mip.png')
    files=[f for f in os.listdir(folder) if id in f and os.path.splitext(f)[1]=='.raw']
    files.sort()
    frames=[]
    t0=time.time()
    for f in files:
        pixels=numpy.fromfile(os.path.join(folder,f),numpy.uint16)
        frames.append(pixels.reshape(res))
    t1=time.time()
    frames=numpy.array(frames)
    mip=frames.max(axis=0)
    data={}
    data['mip']=mip
    data['rawdata']=frames
    data['recording_duration']=recording_duration
    data['fps']=frames.shape[0]/recording_duration
    print data['fps'], 'Hz'
    data['gain']=gain
    data['exposure']=exposure
    scipy.io.savemat(filename,data,do_compression=False)
    print 'Saved to {0}'.format(filename)
    Image.fromarray(numpy.cast['uint8'](signal.scale(mip)*255)).save(filenamemip)
    t2=time.time()
    if cleanup:
        [os.remove(os.path.join(folder,f)) for f in files]
    t3=time.time()
    print t1-t0,t2-t1,t3-t2
    
    
    
    

if __name__ == "__main__":
    raw2mat(*sys.argv[1:])
    
