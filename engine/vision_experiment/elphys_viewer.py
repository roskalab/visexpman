import subprocess,tempfile,os,unittest,numpy,scipy.io,scipy.signal
from pylab import *

from visexpman.engine.generic import fileop,introspect

def mcd2raw(filename):
    cmdfile=os.path.join(fileop.visexpman_package_path(), 'data', 'mcd2raw16.cmd')
    cmdfiletxt=fileop.read_text_file(cmdfile)
    outfile=os.path.join(tempfile.gettempdir(),os.path.basename(filename).replace('.mcd','.raw'))
    cmdfiletxt=cmdfiletxt.replace('infile', filename).replace('outfile', outfile)
    tmpcmdfile=os.path.join(tempfile.gettempdir(), 'cmd.cmd')
    fileop.write_text_file(tmpcmdfile, cmdfiletxt)
    mcdatatoolpath='c:\\Program Files (x86)\\Multi Channel Systems\\MC_DataTool\MC_DataTool'
    cmd='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile)
    if subprocess.call(cmd, shell=True) == 0:
        return outfile
        
def read_raw(filename):
    header=[]
    with open(filename) as f:
        for line in f:
            header.append(line)
            if 'EOH' in line:
                headerlen=len(''.join(header))
                f.seek(headerlen)
                data=numpy.fromfile(f,dtype=numpy.int16)
                break
    sample_rate=float([item for item in header if 'Sample rate = ' in item][0].split('=')[1])
    ad_scaling=float([item for item in header if 'El = ' in item][0].split('=')[2].split('\xb5V')[0])*1e-6
    channel_names=[item for item in header if 'Streams = ' in item][0].split('=')[1].strip().split(';')
    if data.shape[0]%len(channel_names) != 0:
        raise IOError('Invalid data in {0}. Datapoints: {1}, Channels: {2}'.format(filename, data.shape[0], nchannels))
    data=data.reshape((data.shape[0]/len(channel_names),len(channel_names))).T
    digital=data[0]+2**15
    elphys=data[1:]
    t=numpy.linspace(0,digital.shape[0]/sample_rate,digital.shape[0])
    return t,digital,elphys,channel_names,sample_rate,ad_scaling
    
def extract_repetitions(digital,elphys):
    edges=numpy.nonzero(numpy.diff(digital))[0]
    fragments = numpy.split(elphys,edges,axis=1)[::2][1:]
    fragment_length=min([f.shape[1] for f in fragments])
    repetitions = [f[:,:fragment_length] for f in fragments]
    return repetitions
    
def save2mat(filename,**datafields):
    field_names=['t','digital','elphys','channel_names','sample_rate','ad_scaling,repetitions']
    scipy.io.savemat(filename,datafields,oned_as='column',do_compression=True)
    
def filter_trace(pars):
    lowpass, highpass,signal=pars
    lowpassfiltered=scipy.signal.filtfilt(lowpass[0],lowpass[1], signal).real
    highpassfiltered=scipy.signal.filtfilt(highpass[0],highpass[1], signal).real
    return lowpassfiltered, highpassfiltered
    
def filter(elphys, cutoff,order,fs):
    lowpass=scipy.signal.butter(order,cutoff/fs,'low')
    highpass=scipy.signal.butter(order,cutoff/fs,'high')
    lowpassfiltered=numpy.zeros_like(elphys)
    highpassfiltered=numpy.zeros_like(elphys)
    import multiprocessing
    p=multiprocessing.Pool(introspect.get_available_process_cores())
    pars=[(lowpass,highpass,elphys[i]) for i in range(elphys.shape[0])]
    res=p.map(filter_trace,pars)
    for i in range(len(res)):
        lowpassfiltered[i]=res[i][0]
        highpassfiltered[i]=res[i][1]
    return lowpassfiltered, highpassfiltered
       
    
class ElphysViewerFunctions(unittest.TestCase):
    @unittest.skipIf(os.name!='nt', 'Works only on Windows')
    def test_01_mcd2raw(self):
        from visexpman.users.test import unittest_aggregator
        wf=unittest_aggregator.prepare_test_data('mcd')
        for f in fileop.listdir_fullpath(wf):
            outfile=mcd2raw(f)
            self.assertTrue(os.path.exists(outfile))
            self.assertEqual(int(numpy.log10(os.path.getsize(f))),int(numpy.log10(os.path.getsize(outfile))))
            
    def test_02_raw2mat(self):
        from visexpman.users.test import unittest_aggregator
        wf=unittest_aggregator.prepare_test_data('mcdraw')
        for f in fileop.listdir_fullpath(wf):
            t,digital,elphys,channel_names,sample_rate,ad_scaling = read_raw(f)
            self.assertEqual(t.shape[0],digital.shape[0])
            self.assertEqual(elphys.shape[0]+1,len(channel_names))
            repetitions=extract_repetitions(digital,elphys)
            self.assertTrue(all([r.shape[1] for r in repetitions]))#All elements equal
            data2mat={}
            data2mat['t']=t
            data2mat['digital']=digital
            data2mat['elphys']=elphys
            data2mat['channel_names']=channel_names
            data2mat['sample_rate']=sample_rate
            data2mat['ad_scaling']=ad_scaling
            data2mat['repetitions']=repetitions
            
            l,h=filter(elphys, 300,3,sample_rate)
            
            save2mat(os.path.join('/tmp',os.path.basename(f)).replace('.raw','.mat'),**data2mat)

if __name__=='__main__':
    unittest.main()
