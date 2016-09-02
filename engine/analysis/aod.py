import scipy.io,traceback
import numpy,os,hdf5io,unittest
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import utils,signal
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
        
    def tomat(self):
        experiment_data.hdf52mat(self.filename)

    def process_mes_file(self):
        mesdata=scipy.io.loadmat(self.mesfilename)
        if str(mesdata['DATA']['Type'][0][0][0])!='Line2':
            raise NotImplementedError('Only line scan data processing is supported')
        self.image=numpy.copy(mesdata['DATA']['IMAGE'][0][0])
        self.raw_data=self.image.reshape(self.image.shape[0],1,1,self.image.shape[1])#time, channel, null, roi
        #Save mesfile content to hdf5 file
        mesdata['DATA']['IMAGE']=0
        self.mesdata=utils.object2array(mesdata['DATA'])
        self.save('raw_data')
        self.save('mesdata')
        
class TestAODData(unittest.TestCase):
    def test_01(self):
        fn='v:\\experiment_data_ao\\adrian\\data_MovingGratingAdrian_201609011425405.hdf5'
        a=AOData(fn)
        a.prepare4analysis()
        a.close()
        

        
if __name__ == '__main__':
    unittest.main()
