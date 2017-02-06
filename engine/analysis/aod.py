import scipy.io,traceback
import numpy,os,hdf5io,unittest
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import utils,signal,fileop
from pylab import plot,show,figure, imshow  

class AOData(experiment_data.CaImagingData):
    '''
    Addon to CaImagingData. Mes data is merged into this file
    '''
    def __init__(self, filename):
        self.mesfilename=filename.replace('.hdf5','.mat')
        if not os.path.exists(self.mesfilename):
            raise RuntimeError('No mes file found for {0}'.format(self.filename))
        experiment_data.CaImagingData.__init__(self,filename)
        self.process_mes_file()
        self.datatype='ao'
        self.save('datatype')

    def tomat(self):
        experiment_data.hdf52mat(self.filename)

    def process_mes_file(self):
        nchannels=1
        import h5py
        mesdata=h5py.File(self.mesfilename,)
        datatype=''.join(map(chr, mesdata[mesdata['DATA/Type'][0][0]].value.flatten()))
        if datatype=='Line2':
            raise NotImplementedError('Line scan data processing is not supported')
        elif datatype!='FF':
            raise NotImplementedError('Only checkerboard scanning is supported')
        self.image=mesdata[mesdata['DATA/IMAGE'][0][0]].value
        vert_size=int(mesdata[mesdata['DATA/TransversePixNum'][0][0]].value.flatten()[0])
        horiz_size=48
        nrois=[item2 for item2 in [item for item in mesdata[mesdata['DATA/info_Linfo'][0][0]].values() if 'lines' in item.name][0].values() if 'line1' in item2.name][0].shape[1]
        nframes=int([item for item in mesdata[mesdata['DATA/FoldedFrameInfo'][0][0]].values() if 'numFrames' in item.name][0][0][0])
        xoffset=1
        toffset=int([item for item in mesdata[mesdata['DATA/FoldedFrameInfo'][0][0]].values() if 'firstFramePos' in item.name][0][0][0])
        self.raw_data=numpy.zeros((nframes, nchannels, nrois, vert_size, horiz_size),dtype=self.image.dtype)
        for i in range(nrois):
            for j in range(nframes):
                self.raw_data[j,0,i]=\
                        self.image[horiz_size*i+xoffset:horiz_size*(i+1)+xoffset,vert_size*j+toffset:vert_size*(j+1)+toffset].T
              
        
        
        self.image=numpy.copy(mesdata['DATA']['IMAGE'][0][0])
        self.ao_drift=mesdata['DATA']['AO_collection_usedpixels'][0][0][0][0]
        nrois=self.image.shape[0]/self.ao_drift
        if self.image.shape[0]%self.ao_drift!=0:
            raise RuntimeError('Image data cannot be processed')
        nframes=mesdata['DATA']['FoldedFrameInfo'][0][0]['numFrames'][0][0][0][0]
        xsize=mesdata['DATA']['FoldedFrameInfo'][0][0]['numFrameLines'][0][0][0][0]
        offset=mesdata['DATA']['FoldedFrameInfo'][0][0]['firstFramePos'][0][0][0][0]
        scale=mesdata['DATA']['WidthStep'][0][0][0][0]#um/pixel
        img=self.image[:,offset:offset+float(xsize)*float(nframes)].reshape(self.image.shape[0], xsize, nframes,1, order='A')
        img=img.swapaxes(0,2).swapaxes(1,3)
        self.raw_data=img
        #Save mesfile content to hdf5 file
        mesdata['DATA']['IMAGE']=0
        self.mesdata=utils.object2array(mesdata['DATA'])
        self.save('raw_data')
        self.save('mesdata')
        self.sync_pulses_to_skip=int(mesdata['DATA']['Clipping'][0][0]['savedHeightBegin'][0][0][0][0])
        self.save('sync_pulses_to_skip')
        self.load('parameters')
        self.parameters['nrois']=nrois
        self.parameters['resolution_unit']='pixel/um'
        self.parameters['pixel_size']=1.0/scale
        self.save('parameters')
        
class TestAODData(unittest.TestCase):
    #@unittest.skip('')         
    def test_01(self):
        fn='v:\\experiment_data_ao\\adrian\\test\\data_GrayBackgndOnly5min_201609141833241.hdf5'
        fn='v:\\experiment_data_ao\\adrian\\test\\data_MovingGratingAdrian_201609141828279.hdf5'
        fn='/mnt/rzws/temp/0_aodev/data_GrayBackgndOnly5min_201612132042235.hdf5'
        a=AOData(fn)
        a.load('sync')
        #plot(a.sync[::10,0]);show()
        a.prepare4analysis()
        a.close()
        
if __name__ == '__main__':
    unittest.main()
