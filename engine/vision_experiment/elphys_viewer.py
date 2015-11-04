import subprocess,tempfile,os,unittest,numpy,scipy.io

from visexpman.engine.generic import fileop

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
        
def raw2mat(filename):
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
    ad_scaling=float([item for item in header if 'El = ' in item][0].split('=')[2].split('\xb5V')[0])
    channel_names=[item for item in header if 'Streams = ' in item][0].split('=')[1].strip().split(';')
    if data.shape[0]%len(channel_names) != 0:
        raise IOError('Invalid data in {0}. Datapoints: {1}, Channels: {2}'.format(filename, data.shape[0], nchannels))
    #TODO: separate digital and elphys data
    data2mat={}
    data2mat['data']=data
    data2mat['channel_names']=channel_names
    data2mat['sample_rate']=sample_rate
    data2mat['ad_scaling']=ad_scaling
    pass
    
    
    
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
            raw2mat(f)

if __name__=='__main__':
    unittest.main()
