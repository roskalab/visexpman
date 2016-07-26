import hdf5io,unittest,numpy,os
from visexpman.engine.generic import introspect
from pylab import *
from skimage.filter import threshold_otsu
from scipy.ndimage.filters import gaussian_filter

def extract_eyeblink(filename, baseline_length=0.5,blink_duration=0.5,threshold=0.01, debug=False, annotation=None):
    '''
    Ceiling light is reflected on mice eyeball which results a significantly bright area. When eyes are
    closed, this area turns to dark, this is used for detecting if eyeblink happened after an airpuff
    '''
    h=hdf5io.Hdf5io(filename)
    h.load('ic_frames')
    h.load('ic_timestamps')
    h.load('airpuff_values')
    frames=h.ic_frames
    h.close()
    std=frames.std(axis=0)
    std_range=std.max()-std.min()
    activity=(numpy.where(std>std_range*0.75,1,0)*frames).mean(axis=1).mean(axis=1)
    activity=gaussian_filter(activity,2)
    activity_t=h.ic_timestamps[:,0]
    if h.airpuff_values.shape[0]==0:
        return
    airpuff_t=h.airpuff_values[:,0]
    airpuff= h.airpuff_values[:,1]
    is_blinked=[]
    for rep in range(airpuff.shape[0]):
        t0=airpuff_t[rep]
        baseline=activity[numpy.where(numpy.logical_and(activity_t<t0,activity_t>t0-baseline_length))[0]].mean()
        eye_closed=activity[numpy.where(numpy.logical_and(activity_t>t0,activity_t<t0+blink_duration))[0]].mean()
        is_blinked.append(True if baseline-eye_closed>threshold else False)
        if debug:
            outfolder='/tmp/out'
            tmin=t0-1
            tmax=t0+5
            indexes1=numpy.where(numpy.logical_and(activity_t>tmin, activity_t<tmax))[0]
            indexes2=numpy.where(numpy.logical_and(airpuff_t>tmin, airpuff_t<tmax))[0]
            clf()
            cla()
            plot(activity_t[indexes1]-t0, activity[indexes1])
            plot(airpuff_t[indexes2]-t0, airpuff[indexes2]*0.05,'o')
            if annotation!=None:
                annot=annotation[os.path.basename(filename)]
                indexes3=numpy.where(numpy.logical_and(activity_t[annot]>tmin, activity_t[annot]<tmax))[0]
                if indexes3.shape[0]>0:
                    indexes3=numpy.array(annot)[indexes3]
                    plot(activity_t[indexes3]-t0, numpy.ones_like(activity_t[indexes3])*0.06, 'o')
            ylim([0,0.1])
            title(is_blinked[-1])
            savefig(os.path.join(outfolder, '{0}_{1}.png'.format(os.path.basename(filename),rep)),dpi=200)
    return airpuff_t, airpuff, is_blinked, activity_t, activity
    

class TestBehavAnalysis(unittest.TestCase):
        def test_01_blink_detect(self):
            fn='/tmp/fear/data_FearResponse_1466414204.hdf5'
            annotated = {
                    'data_FearResponse_1466413859.hdf5': [582],
                    'data_FearResponse_1466413981.hdf5': [233],
                    'data_FearResponse_1466414084.hdf5': [59, 146, 299],#, 450, 590, 756, 895, 1049],
                    'data_FearResponse_1466414204.hdf5': [41, 148, 271, 448, 743, 1056, 1272, 1303],
                    'data_FearResponse_1466414305.hdf5': [130, 408, 436, 697, 738, 1028],
                    'data_FearResponse_1466414405.hdf5': [6, 131, 338, 414, 430, 589, 681, 740, 781, 982, 1028, 1055, 1180, 1332, 1474],
                    'data_FearResponse_1466414505.hdf5': [130, 253, 429, 727, 1027, 1147],
                    'data_FearResponse_1466414606.hdf5': [123, 421, 727, 1018],
                    'data_FearResponse_1466414706.hdf5': [138, 430, 731, 1040],
                    'data_FearResponse_1466414806.hdf5': [134, 430, 730, 1034],
                    'data_FearResponse_1466414907.hdf5': [129, 429, 727, 1034],
                    'data_FearResponse_1466415007.hdf5': [120, 430, 720],
                    'data_FearResponse_1466415107.hdf5': [175],
                    }

            folder='/tmp/fear'
            #folder='/home/rz/temp/'
            out='/tmp/out/'
            fns=os.listdir(folder)
            fns.sort()
            for fn in fns:
                if fn[-4:]!='hdf5':
                    continue
                print fn
                of=None#os.path.join(out,fn)
                with introspect.Timer():
                    airpuff_t, airpuff, is_blinked, activity_t, activity = extract_eyeblink(os.path.join(folder,fn), debug=True,annotation=annotated)

if __name__ == "__main__":
    unittest.main()
