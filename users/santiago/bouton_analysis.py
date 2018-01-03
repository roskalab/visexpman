import numpy,unittest,os
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment_data


class TestFileops(unittest.TestCase):
    def test(self):
        #TODO: test for baseline and response n_frames=1 too
        #TODO: handle multiple datafolders
        #TODO: Aggregate to excel
        from pylab import plot,show
        folder='/tmp/20170711'
        preflash_nframes=5
        respone_nframes=5
        response_threshold = 3
        response_calculation_method='mean'
        files=fileop.listdir(folder)
        files.sort()
        for f in files:
            print f
            if os.path.splitext(f)[1]!='.hdf5':
                continue
            e=experiment_data.CaImagingData(f)
            #Determine flash frames
            e.load('raw_data')
            saturated_frames_1=numpy.where(e.raw_data.mean(axis=2)==255)[0]
            saturated_frames_2=numpy.where(e.raw_data.mean(axis=3)==255)[0]
            #It is considered saturated if a row or a column has max values
            saturated_frame_indexes=list(set(numpy.concatenate((saturated_frames_1,saturated_frames_2))))
            expected_nflashes=e.findvar('stimulus_parameters')['NUMBER_OF_FLASHES']
            detected_nflashes=numpy.where(numpy.diff(saturated_frame_indexes)>1)[0].shape[0]+1
            if expected_nflashes != detected_nflashes:
                raise RuntimeError('Number of expected ({0}) and detected ({1}) flashes do not match'.format(expected_nflashes, detected_nflashes))
            mask=numpy.zeros(e.raw_data.shape[0])
            mask[saturated_frame_indexes]=1
            boundaries=numpy.nonzero(numpy.diff(mask))[0]
            boundaries+=1
            #Extract pre and post flash std values
            e.load('rois')
            if not hasattr(e,'rois'):
                e.close()
                continue
            for roii in range(len(e.rois)):
                for flashi in range(detected_nflashes):
                    preflash_end=boundaries[flashi*2]
                    preflash_start=preflash_end-preflash_nframes
                    response_start=boundaries[flashi*2+1]
                    response_end=response_start+respone_nframes
                    preflash_std=e.rois[roii]['raw'][preflash_start:preflash_end].std()
                    response=getattr(numpy,response_calculation_method)(e.rois[roii]['raw'][response_start:response_end])
                    e.rois[roii]['bouton_analysis']={'preflash_end':preflash_end,
                                                                            'preflash_start':preflash_start,
                                                                            'response_start':response_start,
                                                                            'response_end':response_end,
                                                                            'preflash_std':preflash_std,
                                                                            'response':response,
                                                                            'is_response': response>response_threshold*preflash_std,
                                                                            }
                
            e.close()
            

if __name__=='__main__':
        unittest.main()
