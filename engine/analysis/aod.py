import numpy,os,unittest
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import introspect
from pylab import plot,show,figure, imshow  

class AOData(experiment_data.CaImagingData):
    '''
    Addon to CaImagingData. Mes data is merged into this file
    '''
    def __init__(self, filename):
        self.mesfilename=filename.replace('.hdf5','.mat')
        if not os.path.exists(self.mesfilename):
            raise RuntimeError('No mes file found for {0}'.format(filename))
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
        height=int(mesdata[mesdata['DATA/TransversePixNum'][0][0]].value.flatten()[0])
        width=48
        nrois=mesdata[[item2 for item2 in [item for item in mesdata[mesdata['DATA/info_Linfo'][0][0]].values() if 'lines' in item.name][0].values() if 'line1' in item2.name][0].value[0,1]].shape[0]
        nframes=int([item for item in mesdata[mesdata['DATA/FoldedFrameInfo'][0][0]].values() if 'numFrames' in item.name][0][0][0])
        xoffset=1*0
        toffset=int([item for item in mesdata[mesdata['DATA/FoldedFrameInfo'][0][0]].values() if 'firstFramePos' in item.name][0][0][0])
        self.raw_data=numpy.zeros((nframes, nchannels, nrois, height, width),dtype=self.image.dtype)
        for roiid in range(nrois):#1.5-2 second, does not need to speed it up
            for framei in range(nframes):
                self.raw_data[framei,0,roiid]=\
                        self.image[height*framei+toffset:height*(framei+1)+toffset,width*roiid+xoffset:width*(roiid+1)+xoffset]
        scale=mesdata[mesdata['DATA/WidthStep'][0][0]][0][0]#um/pixel
        self.save('raw_data')
        self.sync_pulses_to_skip=[item for item in mesdata[mesdata['DATA/Clipping'][0][0]].values() if 'savedHeightBegin' in item.name][0][0][0]/width
        self.save('sync_pulses_to_skip')
        self.load('parameters')
        self.parameters['nrois']=nrois
        self.parameters['resolution_unit']='pixel/um'
        self.parameters['pixel_size']=1.0/scale
        self.save('parameters')
        
class TestAODData(unittest.TestCase):
    #@unittest.skip('')         
    def test_01(self):
        fn='v:\\experiment_data_ao\\adrian\\test\\dpixel_sizeata_GrayBackgndOnly5min_201609141833241.hdf5'
        fn='v:\\experiment_data_ao\\adrian\\test\\data_MovingGratingAdrian_201609141828279.hdf5'
        fn='/mnt/rzws/temp/0_aodev/data_GrayBackgndOnly5min_201612132042235.hdf5'
        fn='/home/rz/mysoftware/data/ao/data_GrayBackgndOnly5min_201612132042235.hdf5'
        fn='/home/rz/mysoftware/data/ao/data_MovingGratingMid_201612131953459.hdf5'
        folder='/home/rz/mysoftware/data/ao'
        folder='/home/rz/test'
        folder='v:\\experiment_data_ao\\zoltan\\20170714'
        folder='/tmp/processed'
        folder='c:\\temp\\1'
        #folder='v:\\debug\\0'
        for fn in os.listdir(folder):
            if os.path.splitext(fn)[1]=='.hdf5':
                with introspect.Timer(1):
                    print fn
                    fn=os.path.join(folder,fn)
                    a=AOData(fn)
                    a.get_image('mip')
                with introspect.Timer(2):
                    a.sync2time(True)
                    a.check_timing()
                    a.close()
        
if __name__ == '__main__':
    unittest.main()
