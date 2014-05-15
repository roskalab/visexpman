from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title, xlabel,  ylabel
from visexpman.engine.hardware_interface import scanner_control
from visexpA.engine.datahandlers import hdf5io
try:
    import Image
except ImportError:
    from PIL import Image
from visexpA.engine.dataprocessors.generic import normalize
import os
import os.path
from visexpman.engine.generic import utils
import time
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import camera_interface
from visexpman.engine.generic import configuration
from visexpman.engine.generic import fileop
from visexpman.engine.generic import signal

class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.F = [20.0, 40.0, 80.0, 100.0, 150.0, 200.0, 250.0, 400.0, 500.0, 700.0, 850.0, 1000.0, 1200.0, 1500.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2400.0, 2450.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0]
        self.F = numpy.array(self.F*2).reshape((2, len(self.F))).flatten('F')
        self.F[::2] = 0
        self.F = self.F.tolist()
        self.F.append(0)
        self.A = [100/128.0*2]#100 um
        self.DURATION = 3.0
        self.CAMERA_FRAME_RATE = 30.0
        VIDEO_FORMAT = 'RGB24 (320x240)'
        self.PREPOST_DELAYS = 2.0
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 400000,
        'AO_CHANNEL' : 'Dev1/ao0:1',
        'MAX_VOLTAGE' : 8.0,
        'MIN_VOLTAGE' : -8.0,
        'DURATION_OF_AI_READ' : 2.0,
        'AO_SAMPLING_MODE' : 'finite', 
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())

class ScannerCalibration(camera_interface.ImagingSourceCamera, daq_instrument.AnalogIO):
    def __init__(self, config):
        camera_interface.ImagingSourceCamera.__init__(self, config)
        daq_instrument.AnalogIO.__init__(self, config)
#        self.generate_square_signal(self.A, self.duration)
        self.generate_signal(self.config.F, self.config.A, self.config.DURATION)
        
    def generate_signal(self, f, A, duration, two_channel = False):
        self.t = numpy.linspace(0, duration,  duration*self.ao_sample_rate, False)
        signal0 = numpy.zeros(self.t.size*len(f)*len(A))
        signal1 = numpy.zeros(self.t.size*len(f)*len(A))
        for i in range(len(A)):
            for j in range(len(f)):
                if f[j] == 0:
                    signal_i0 = numpy.zeros_like(self.t)
                    signal_i1 = numpy.zeros_like(self.t)
                else:
                    signal_i0 = 0.5*A[i]*numpy.sin(2*numpy.pi*self.t*f[j])
                    if two_channel:
                        signal_i1 = 0.5*A[i]*numpy.cos(2*numpy.pi*self.t*f[j])
                    else:
                        signal_i1 = numpy.zeros_like(self.t)
                index = len(f)*i+j
                signal0[signal_i0.size*index:signal_i0.size*(index+1)] = signal_i0
                signal1[signal_i1.size*index:signal_i1.size*(index+1)] = signal_i1
        self.waveform = numpy.array([signal0, signal1]).T
        from matplotlib.pyplot import plot, show
#        plot(self.waveform[:,0])
#        plot(self.waveform[:,1])
#        show()
        pass
        
    def generate_square_signal(self, A, duration):
        self.waveform = numpy.zeros(duration*self.ao_sample_rate)
        self.waveform[0.1*self.waveform.shape[0]:0.6*self.waveform.shape[0]] = A

    def run(self):
        camera_interface.ImagingSourceCamera.start(self)
        self.start_daq_activity()
        for i in range(int((len(self.config.A)*len(self.config.F)*self.config.DURATION+ self.config.PREPOST_DELAYS)*config.CAMERA_FRAME_RATE)):
            camera_interface.ImagingSourceCamera.save(self)
        
    def close(self):
        self.finish_daq_activity()
        self.waveform = numpy.zeros((100, 2))#Make sure that outputs are on 0V
        daq_instrument.AnalogIO.run(self)
        daq_instrument.AnalogIO.release_instrument(self)
        camera_interface.ImagingSourceCamera.stop(self)
        camera_interface.ImagingSourceCamera.close(self)
        self.process_data()
        
    def process_data(self):
        import tiffile
        tiffile.imsave(fileop.generate_filename('v:\\debug\\20130503\\camcalibs\\calib.tiff'), self.video, software = 'visexpman')
        p = fileop.generate_filename('v:\\debug\\20130503\\camcalibs\\calib.hdf5')
        hdf5io.save_item(p, 'video', self.video, filelocking = False)
        hdf5io.save_item(p, 'config', self.config.get_all_parameters(), filelocking = False)
        
def scanner_calib():
    config = TestConfig()
    sc = ScannerCalibration(config)
    sc.run()
    sc.close()
    print 'DONE'
    
def evaluate_calibdata():
    p = '/mnt/datafast/debug/20130503/calibs'
    p = '/mnt/rznb/data/20130503/calibs'
    p = '/home/rz/visexp/data/calibs'
    max_linearity_error = 10e-2
    a = []
    fi = []
    frq = []
    fs =os.listdir(p)
    fs.sort()
    fs = fs[:-2]
    fs.reverse()
    for f in fs:
        calibdata = hdf5io.read_item(os.path.join(p, f), 'calibdata', filelocking=False)
    #    pmt = calibdata['pmt']
    #    mask = utils.resample_array(calibdata['mask'], calibdata['parameters']['binning_factor'])
        res = scanner_control.scanner_bode_diagram(calibdata['pmt'], utils.resample_array(calibdata['mask'], calibdata['parameters']['binning_factor']), calibdata['parameters']['scanner_speed'], max_linearity_error)
        a.append(res['sigmas'][0])
        fi.append(res['means'][0])
        frq.append(res['frq'][0])
#        figure(len(frq))
#        t = numpy.linspace(0, 1, res['signals'][0].shape[0])
#        plot(t, res['signals'][0])
#        plot(t, scanner_control.gauss(t, res['gauss_amplitudes'][0], fi[-1], a[-1]))
#        title('{0} Hz, {1}, {2}'.format(frq[-1], fi[-1], a[-1]))
    #print frq
    phase = 2*utils.sinus_linear_range(max_linearity_error)*(fi-fi[-1])
    figure(len(frq)+1)
    plot(frq, a/a[-1])
    plot(frq, phase)
    
    import scipy.optimize
    p0 = [1.0/2500,0.0]
    frq = numpy.array(frq)
    coeff, var_matrix = scipy.optimize.curve_fit(linear, frq, phase, p0=p0)
#    plot(frq, p0[0]*frq+p0[1])
    plot(frq, coeff[0]*frq+coeff[1])
    legend(('gain', 'phase', 'fitted'))
    print coeff#[ 0.00043265 -0.02486131]
    
    #    show()
    
def evaluate_videos():
    '''
    Strategy:
    First approach:
    1 .Find segment indexes in video
    2. Add frames within one segment
    3. Plot accumulated fragments to tiff sequence
    '''
    p = '/mnt/datafast/debug/20130503/camcalibs'
    i=0
    for pp in ['x', 'y']:
        i+=1
        for fn in os.listdir(os.path.join(p, pp)):
            if 'hdf5' in fn:
                evaluate_video(os.path.join(p, pp, fn),pp)
#    show()
    
def evaluate_video(p, axis):
    h=hdf5io.Hdf5io(p,filelocking=False)
    h.load('video')
    rvideo = h.video
    h.load('config')
    h.close()
    frqs = h.config['F'][1::2]
    mask = numpy.where(rvideo<2*rvideo.min(),False, True)
    masked_video = rvideo*mask
    sizes = []
    for fri in range(rvideo.shape[0]):
        frame = masked_video[fri,:,:]
        sizes.append(numpy.nonzero(frame)[0].shape[0])
    sizes = numpy.array(sizes)
    #calculate segment indexes
    diffs = abs(numpy.diff(sizes))
    indexes = numpy.nonzero(numpy.where(diffs > diffs.max()/3, True, False))[0]
    indexes = indexes[numpy.nonzero(numpy.where(numpy.diff(indexes) == 1, 0, 1))[0]]
    indexes = indexes[:-1]
    masked_video = normalize(masked_video,outtype=numpy.uint8)
    segments = numpy.split(masked_video, indexes)[1::2]
    mean_images = numpy.zeros((len(segments), masked_video.shape[1], masked_video.shape[2]))
    curves = numpy.zeros((len(segments), masked_video.shape[2]))
    for segment_i in range(len(segments)):
        segment_mean = segments[segment_i].mean(axis=0)
        curves[segment_i] = segment_mean.mean(axis=0)
#        dim_order = [0, 1]
#        from visexpA.engine.dataprocessors import signal
#        sigma = 2
#        positions = signal.regmax(segment_mean,dim_order, sigma = sigma)
#        for pos in positions:
#            segment_mean[pos['row'],pos['col']] = 255
        mean_images[segment_i, :, :] = segment_mean
    #Beam profile over frequencies
    Image.fromarray(normalize(curves,outtype=numpy.uint8)).show()
#    mean_images = normalize(mean_images,outtype=numpy.uint8)
    import tiffile
    tiffile.imsave(fileop.generate_filename('/mnt/rznb/1.tiff'), numpy.cast['uint8'](mean_images), software = 'visexpman')
    pass
    return

def generate_delay_curve():
    if False:
        #1. method
        folder1 = '/home/rz/visexp/data/calibs'
        fns = os.listdir(folder1)
        fns.sort()
        fns = fns[:-2]
        resolutions = []
        delays = []
        for fn in fns:
            calibdata = hdf5io.read_item(os.path.join(folder1, fn),  'calibdata',  filelocking=False)
            signal = calibdata['pmt']
            mask = utils.resample_array(calibdata['mask'], calibdata['parameters']['binning_factor'])
            scanner = utils.resample_array(calibdata['waveform'][:, 0], calibdata['parameters']['binning_factor'])
            #Calculate scan size and resolution
            npoints = numpy.diff(numpy.nonzero(numpy.diff(mask))[0][:2])[0]
            scan_range = ((scanner*mask).max() - (scanner*mask).min())*128/2
            resolutions.append(npoints/scan_range)
            #Extract peak delay
            indexes = numpy.nonzero(numpy.diff(mask))[0]
            indexes = indexes[:indexes.shape[0]/2]
            signal = numpy.array((numpy.split(signal, indexes)[1::2])).mean(axis=0)[:,0]
            p0 = [1., signal.argmax(), 1.]
            import scipy.optimize
            coeff, var_matrix = scipy.optimize.curve_fit(scanner_control.gauss, numpy.arange(signal.shape[0]), signal, p0=p0)
            delays.append(coeff[1]/signal.shape[0])
    #        plot(signal)
    #        plot(scanner_control.gauss(numpy.arange(signal.shape[0]),  *coeff))
            pass
    #2. method
    folder2 = '/home/rz/visexp/data/shift_size_calib'
    folder2 = 'V:\\debug\\data\\2013-06-02'
    output_folder = 'V:\\debug\\out'
    fns = os.listdir(folder2)
    fns.sort()
#    fns = fns[:10]
    offsets = {}
    delays_pix = {}
    bead_sizes = {}#Useless, relative position matters
    figct = 0
    for fn in fns:
        rawdata = hdf5io.read_item(os.path.join(folder2,  fn),  'raw_data',  filelocking=False)
        scan_parameters = hdf5io.read_item(os.path.join(folder2,  fn),  'scan_parameters',  filelocking=False)
        resolution = 1/scan_parameters['resolution']
        scan_range = scan_parameters['scan_size']['col']
        curve = rawdata.mean(axis=2).mean(axis=0)[:,0]
        p0 = [1., curve.argmax(), 1.]
        import scipy.optimize
        try:
            coeff, var_matrix = scipy.optimize.curve_fit(scanner_control.gauss, numpy.arange(curve.shape[0]), curve, p0=p0)
            delay = coeff[1]/curve.shape[0]
            delay_pix = coeff[1]
            size_pix = coeff[2]
        except:
            delay = 0
            delay_pix = 0
            size_pix = 0
        size = size_pix / resolution
        if not offsets.has_key(scan_range):
            offsets[scan_range] = []
            delays_pix[scan_range] = []
            bead_sizes[scan_range] = []
        offsets[scan_range].append([resolution, delay])
        delays_pix[scan_range].append([resolution, delay_pix])
        bead_sizes[scan_range].append([resolution, size])
        figure(figct)
        plot(curve)
        plot(scanner_control.gauss(numpy.arange(curve.shape[0]),  *coeff))
        t = '{0} um {1} pixel um {2:0.3f} {3:2.1f} pix {4:2.1f} um'.format(scan_range,  resolution, delay, size_pix, size)
        title(t)
        figct += 1
        fn = os.path.join(output_folder, t+'.png')
        savefig(fn)
        fig = numpy.asarray(Image.open(fn))
        pic = normalize(rawdata[:,:,0,0], numpy.uint8)
        ima = numpy.zeros((fig.shape[0]+pic.shape[0],  max(fig.shape[1],  pic.shape[1]), 3 ),  dtype = numpy.uint8)
        ima[0:fig.shape[0],  0:fig.shape[1],  :] = fig[:, :, 0:3]
        ima[fig.shape[0]: fig.shape[0] + pic.shape[0], 0:pic.shape[1],  1] = pic
        os.remove(fn)
        Image.fromarray(ima).save(fn)
        pass
    fn = fileop.generate_filename(os.path.join(output_folder, 'ca_image_offset_calibration.hdf5'))
    for vn in ['offsets',  'bead_sizes']:
        hdf5io.save_item(fn, vn, utils.object2array(locals()[vn]), filelocking=False)
    return fn

def plot_delay_curve(fn):
    delays = utils.array2object(hdf5io.read_item(fn,  'delays', filelocking=False))
    bead_sizes = utils.array2object(hdf5io.read_item(fn,  'bead_sizes', filelocking=False))
    fn = os.path.join(os.path.split(fn)[0], 'plot.png')
    srs = delays.keys()
    srs.sort()
    alldata = []
    #Generate scan_range, resolution, relative position table
    for scan_range in srs:
        data = numpy.array(delays[scan_range])
        data[:,1] -= data[-1,1]
        scan_range_vector = scan_range*numpy.ones(data.shape[0])
        alldata_item = numpy.zeros((scan_range_vector.shape[0],  3))
        alldata_item[:, 0] = scan_range_vector
        alldata_item[:, 1:] = data
        alldata.extend(alldata_item)
    alldata = numpy.array(alldata)
    figure(200)
    for scan_range in srs:
        data = numpy.array(bead_sizes[scan_range])
        plot(data[:, 0],  data[:, 1],  '*-')
    legend(map(str, srs))
    xlabel('resolution [pixel/um]')
    ylabel('bead size [um]')
    savefig(fileop.generate_filename(fn))
    #Plot bead position over resolution
    figure(201)
    for scan_range in srs:
        data = numpy.array([item for item in alldata if item[0] == scan_range])
        plot(data[:,1],  data[:,2], '*-')
    legend(map(str, srs))
    xlabel('resolution [pixel/um]')
    ylabel('bead position [PU]')
    savefig(fileop.generate_filename(fn))
    #Plot bead position over scan range
    figure(202)
    resolutions = set(alldata[:,1])
    resolutions = list(resolutions)
    resolutions.sort()
#    resolutions = [res for res in resolutions if int(res) == res]
    for resolution in resolutions:
        data = numpy.array([item for item in alldata if item[1] == resolution])
        plot(data[:,0],  data[:,2], '*-')
    legend(map(str, resolutions))
    xlabel('scan range [um]')
    ylabel('bead position [PU]')
    savefig(fileop.generate_filename(fn))
    resolutions.reverse()
    resolution_axis, scan_range_axis = numpy.meshgrid(resolutions, srs)
    offset = []
    for scan_range_axis_flattened, resolution_axis_flattened in zip(scan_range_axis.flatten(),  resolution_axis.flatten()):
        value = [item[2] for item in alldata if item[0] == scan_range_axis_flattened and item[1] == resolution_axis_flattened]
        if len(value) == 0:
            if len(offset)>0:
                value = offset[-1]
            else:
                value = numpy.NaN
        else:
            value = value[0]
        offset.append(value)
    offset = numpy.array(offset).reshape(scan_range_axis.shape)
    from scipy import interpolate
    f = interpolate.interp2d(scan_range_axis, resolution_axis, offset, kind='linear')#CONTINUE HERE
    
    
    import mpl_toolkits.mplot3d.axes3d as p3
    fig=figure(203)
    ax = p3.Axes3D(fig)
    ax.plot_wireframe(scan_range_axis, resolution_axis, offset)
    ax.set_xlabel('scan range [um]')
    ax.set_ylabel('resolution [pixel/um]')
    ax.set_zlabel('bead position [PU]')    
    pass
#    show()
    
def recordings2calibdata(datafolder,  output_folder, enable_plot=False):
    '''
    Reads and sorts recordings from the same fluorescent bead with different scan ranges and resolutions.
    The relative horizontal position of the bead are calculated and from this data a 3d calibration curve is generated where scan range [um]
    and resolution [pixel/um] are the two axes. The highest resolution is considered a position with 0 offset.
    '''
    filenames = os.listdir(datafolder)
    filenames.sort()
#    filenames = filenames[:10]#TMP
    offsets = []
    figct = 0
    for fn in filenames:
        #read rawdata and scan parameters from file
        h= hdf5io.Hdf5io(os.path.join(datafolder,  fn), filelocking=False)
        rawdata = h.findvar('rawdata')
        if rawdata is None:
            rawdata = h.findvar('raw_data')
        scan_parameters = h.findvar('scan_parameters')
        h.close()
        #get resolution, scan range and convert image to curve
        resolution = 1/scan_parameters['resolution']
        scan_range = scan_parameters['scan_size']['col']
        curve = rawdata.mean(axis=2).mean(axis=0)[:,0]
        #Fit gaussian on the curve, its mean is the position of the bead
        p0 = [1., curve.argmax(), 1.]
        import scipy.optimize
        try:
            coeff, var_matrix = scipy.optimize.curve_fit(scanner_control.gauss, numpy.arange(curve.shape[0]), curve, p0=p0)
            offset = coeff[1]/curve.shape[0]
        except:
            offset = 0
        offsets.append([scan_range, resolution, offset])
        if enable_plot:
            figure(figct)
            plot(curve)
            plot(scanner_control.gauss(numpy.arange(curve.shape[0]),  *coeff))
            t = '{0} um {1} pixel um {2:0.3f}'.format(scan_range,  resolution, offset)
            title(t)
            figct += 1
            fn = os.path.join(output_folder, t+'.png')
            savefig(fn)
            fig = numpy.asarray(Image.open(fn))
            pic = normalize(rawdata[:,:,0,0], numpy.uint8)
            ima = numpy.zeros((fig.shape[0]+pic.shape[0],  max(fig.shape[1],  pic.shape[1]), 3 ),  dtype = numpy.uint8)
            ima[0:fig.shape[0],  0:fig.shape[1],  :] = fig[:, :, 0:3]
            ima[fig.shape[0]: fig.shape[0] + pic.shape[0], 0:pic.shape[1],  1] = pic
            os.remove(fn)
            Image.fromarray(ima).save(fn)
    offsets = numpy.array(offsets)
    #Convert [scan_range, resolution, offset] data to meshgrid order
    scan_ranges = list(set(offsets[:,0].tolist()))
    scan_ranges.sort()
    scan_ranges.reverse()
    resolutions = list(set(offsets[:,1].tolist()))
    resolutions.sort()
    resolutions.reverse()
    resolutions, scan_ranges = numpy.meshgrid(resolutions, scan_ranges)
    offsets_mg = []
    for scan_range, resolution in zip(scan_ranges.flatten(),  resolutions.flatten()):
        value = [item[2] for item in offsets if item[0] == scan_range and item[1] == resolution]
        if len(value) == 0:
            if len(offsets_mg)>0:
                value = offsets_mg[-1]
            else:
                value = numpy.NaN
        else:
            value = value[0]
        offsets_mg.append(value)
    offsets_mg = numpy.array(offsets_mg).reshape(scan_ranges.shape)
    import mpl_toolkits.mplot3d.axes3d as p3
    fig=figure(203)
    ax = p3.Axes3D(fig)
    ax.plot_wireframe(scan_ranges, resolutions, offsets_mg)
    ax.set_xlabel('scan range [um]')
    ax.set_ylabel('resolution [pixel/um]')
    ax.set_zlabel('bead position [PU]')
    savefig(os.path.join(output_folder, 'curve.png'))
    
    
    
    
    from scipy import interpolate
    f = interpolate.interp2d(scan_ranges, resolutions, offsets_mg, kind='linear')
    
    fn = fileop.generate_filename(os.path.join(output_folder, 'image_offset_calibration.hdf5'))
    hdf5io.save_item(fn, 'offsets', offsets, filelocking=False)
    hdf5io.save_item(fn, 'scan_ranges', scan_ranges, filelocking=False)
    hdf5io.save_item(fn, 'resolutions', resolutions, filelocking=False)
    hdf5io.save_item(fn, 'offsets_mg', offsets_mg, filelocking=False)
    return fn
    
def calculate_bead_size(folder):
    data = []
    for fn in os.listdir(folder):
        h=hdf5io.Hdf5io(os.path.join(folder, fn), filelocking=False)
        cadata = h.findvar('cadata')
        resolution = 1/h.findvar('scan_parameters')['resolution']
        h.close()
        vertical_profile = cadata[:,:,:,0].mean(axis=2).mean(axis=0)
        horizontal_profile = cadata[:,:,:,0].mean(axis=2).mean(axis=1)
        sizes = []
        positions = []
        import scipy.optimize
        for profile in [vertical_profile, horizontal_profile]:
            p0 = [1., profile.argmax(), 1.]
            try:
                coeff, var_matrix = scipy.optimize.curve_fit(scanner_control.gauss, numpy.arange(profile.shape[0]), profile, p0=p0)
                size = 4*coeff[2]/resolution
                position = numpy.round(coeff[1]/profile.shape[0], 2)
            except:
                size = 0
                position = 0
            sizes.append(size)
            positions.append(position)
        data.append([positions[0], resolution, sizes[0]])
        data.append([positions[1], resolution, sizes[1]])
        if False:
            print sizes
            print positions
            print 1/resolution, sizes[0]/sizes[1]
    pass
    data=numpy.array(data)
    positions_h, resolutions_h, values_h = data23dplot(data[0::2])
    positions_v, resolutions_v, values_v = data23dplot(data[1::2])
    #plots:
    #3d plot: position, resolution, size x; size y
    import mpl_toolkits.mplot3d.axes3d as p3
    fig=figure(203)
    ax = p3.Axes3D(fig)
    ax.plot_wireframe(positions_v, resolutions_v, values_v)
#    ax.plot_wireframe(positions_h, resolutions_h, values_h)
    ax.set_xlabel('positions [%]')
    ax.set_ylabel('resolution [pixel/um]')
    ax.set_zlabel('v bead size [um]')
    
    
    fig=figure(204)
    ax = p3.Axes3D(fig)
    ax.plot_wireframe(positions_h, resolutions_h, values_h)
    ax.set_xlabel('positions [%]')
    ax.set_ylabel('resolution [pixel/um]')
    ax.set_zlabel('h bead size [um]')
    show()
        
def data23dplot(data):
    '''
    [axis1, axis2, data]
    '''
    axis1=list(set(data[:, 0]))
    axis2=list(set(data[:, 1]))
    axis1.sort()
    axis2.sort()
    axis1_mg, axis2_mg = numpy.meshgrid(axis1, axis2)
    values = []
    for ax1_v, ax2_v in zip(axis1_mg.flatten(),  axis2_mg.flatten()):
        value = [item[2] for item in data if item[0] == ax1_v and item[1] == ax2_v]
        if len(value) == 0:
            if len(values) == 0:
                value = numpy.NaN
            else:
                value=values[-1]
        else:
            value = value[0]
        values.append(value)
    return axis1_mg, axis2_mg, numpy.array(values).reshape(axis1_mg.shape)

class ScannerIdentification(object):
    '''
    Concept:
    Mirror angle and angle error signal are recorded while position command signal is generated.
    Mirror angle seems to be always less than what is expected from the command voltage.
    Real mirror angle and measured angle signal corresponds to each other.
    
    1. command voltage - real angle characteristics at low frequencies
        +/- 7 V range with 0.1 V steps for 1 second, check position stability and hysteresis
        
    From this the real angle/voltage scale can be determined. 
    The angle error signal is to be validated from this data.
        
    What is the amplitude, frequency and offset range where the mirror angle has an acceptable
    or predictable error to the command signal? The scanner shall be operated within this domain. 
    
    2. Mirror delay and amplitude error characteristics
        amplitude ange: 0.1-10 V
        offset range: +/- 1.8 V, 0.1 V steps
        frequency range: 1-2000 Hz
        
    
    '''
    def __init__(self):
        self.ao_sample_rate = 100000
        self.ao_channel_name = 'Dev1/ao1'
        self.ai_channel_name = 'Dev1/ai2'
        self.angle2voltage_factor = 0.66132089075664857    
        self.voltage_correction_factor = self.angle2voltage_factor*2
        
    def command_voltage_angle_characteristics(self):
        import random
        import copy
        
        measurement_time_per_point = 0.7#sec
        repeats = 2
        voltage_range = 7
        voltage_step_size = 0.1
        voltage_up = numpy.round(numpy.arange(-voltage_range,voltage_range,voltage_step_size),3)
        voltage_down = voltage_up[::-1]#See if there is any hysteresis
        voltage_random = copy.deepcopy(voltage_down)
        random.seed(0)
#        random.shuffle(voltage_random)
        voltage_sequence = numpy.tile(numpy.concatenate((voltage_up, voltage_down)),repeats)
        voltages = []
        for v in voltage_sequence:
            voltages.append([v]*int(self.ao_sample_rate*measurement_time_per_point))
        waveform = numpy.concatenate(tuple(voltages))
        measured = self.run_measurement(waveform)
        measured = measured[:,0]
        index_of_transitions = numpy.nonzero(numpy.diff(waveform))[0]
        indexes2remove = numpy.concatenate(tuple([index_of_transitions +i for i in range(-10,20)]))
        
#        print angle2voltage_factor,(waveform/measured)[indexes].std()
        measured = measured[:waveform.shape[0]]
        ratio = waveform/measured
        ratio = numpy.where(abs(ratio) > 2 , 1.3, ratio)
        #From datasheet: 0.5 volt/degree
        angle2voltage_factor = 0.5*ratio.mean()#0.66132089075664857     
        mask = numpy.ones_like(waveform)
        mask[indexes2remove] = 0.0
        angle_command = waveform /angle2voltage_factor
        angle_measured = measured * 2
        
        from pylab import plot,show,figure
        figure(1)
        plot(ratio)
        figure(2)
        plot(measured)
        plot(waveform)
        show()
        pass
        
    def frequency_domain_characteristics(self):
        
        frequency_limit = 500
        voltage_limit = 3
        paramspace = {}
        if False:
            periods = 10
            paramspace['frequency'] = numpy.concatenate((numpy.logspace(1,3,13,False), numpy.linspace(1000, 2000, 5)))
            paramspace['voltage'] = numpy.logspace(-1, 0.7, 6)
            paramspace['offset'] = numpy.concatenate((-numpy.logspace(0.2, -1, 3), numpy.zeros(1), numpy.logspace(-1, 0.2, 3)))
        else:
            periods = 40
            paramspace['frequency'] = numpy.linspace(1000, 2500, 10)
            paramspace['voltage'] = numpy.linspace(0.5, 2, 4)
            paramspace['offset'] = numpy.linspace(1.0, -1.0, 3)
        from visexpman.engine import generic
        params = []
        for o in paramspace['offset']:
            for v in paramspace['voltage']:
                for f in paramspace['frequency']:
                    params.append({'frequency': f, 'voltage': v, 'offset': o})
                    
#        params = generic.iterate_parameter_space(paramspace)
        
        
#        params = params[:10]
        params = [par for par in params if not (par['frequency'] > frequency_limit and par['voltage'] > voltage_limit)]
        test_signal = []
        from visexpman.engine.generic import signal
        nsamples = 0
        for param in params:
            duration = periods/param['frequency']
            test_signal.append(numpy.ones(0.1 * self.ao_sample_rate)*param['offset'])
            test_signal.append(signal.wf_sin(param['voltage'], param['frequency'], duration, self.ao_sample_rate, offset = param['offset']))
            nsamples += test_signal[-1].shape[0]
        print float(nsamples)/self.ao_sample_rate/60
        wf = numpy.concatenate(tuple(test_signal))
        t = numpy.arange(wf.shape[0],dtype= numpy.float)/self.ao_sample_rate
        measured = self.run_measurement(wf*self.voltage_correction_factor)
        measured = measured[:wf.shape[0],0]
        data = {}
        data['waveform'] = wf
        data['measured'] = measured
        data['ao_sample_rate'] = self.ao_sample_rate
        data['params'] = params
        data['angle2voltage_factor'] = self.angle2voltage_factor
        numpy.save('r:\\dataslow\\scanner_frq_domain_anal\\high_frequency_domain_characteristics.npy', utils.object2array(data))

    def run_measurement(self,waveform):
        from visexpman.engine.generic import log
        from visexpman.engine.hardware_interface import daq_instrument
        from visexpman.users.test import unittest_aggregator
        from visexpman.engine.generic import log
        import multiprocessing
        self.logile = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_working_folder), 'log_scanner_calibration_{0}.txt'.format(int(1000*time.time())))
        self.logger = log.Logger(filename=self.logile)
        self.instrument_name = 'aio'
        self.logger.add_source(self.instrument_name)
        self.limits = {}
        vlim = 7.1
        self.limits['min_ao_voltage'] = -vlim
        self.limits['max_ao_voltage'] = vlim
        self.limits['min_ai_voltage'] = -vlim
        self.limits['max_ai_voltage'] = vlim
        self.limits['timeout'] = 1
        self.queues = {'command': multiprocessing.Queue(), 
                                                                            'response': multiprocessing.Queue(), 
                                                                            'data': multiprocessing.Queue()}
        aio = daq_instrument.AnalogIOProcess(self.instrument_name, self.queues, self.logger,
                                ai_channels = self.ai_channel_name,
                                ao_channels= self.ao_channel_name, limits = self.limits)
        [p.start() for p in [aio,self.logger]]
        if aio.start_daq(ai_sample_rate = self.ao_sample_rate, ao_sample_rate = self.ao_sample_rate, 
                      ao_waveform = waveform.reshape((1,waveform.shape[0])),
                      timeout = 30) == 'timeout':
                          print 'did not start correctly'
                          self.stop_aio(aio)
                          return
                          
#        t0 = time.time()
#        data1 = []
#        while True:
#            res = aio.read_ai()
#            if res is not None:
#                if res.shape[0]*res.shape[1] != 0:
#                    data1.append(res)
#            if time.time()-t0 > 1.5*float(waveform.shape[0])/self.ao_sample_rate:
#                break
#            time.sleep(1e-3)
        time.sleep(float(waveform.shape[0])/self.ao_sample_rate*1.3)
        data = aio.stop_daq()
        self.stop_aio(aio)
        return data[0]
        
    def stop_aio(self,aio):
        aio.terminate()
        daq_instrument.set_voltage(self.ao_channel_name, 0)
        if self.logger.is_alive():
            self.logger.terminate()
        [utils.empty_queue(q) for q in self.queues.values()]
        
    def load_measurement(self,filename):
        varnames = ['angle2voltage_factor', 'waveform', 'measured', 'ao_sample_rate', 'params']
        self.outfolder = os.path.join(os.path.split(filename)[0],'out')
        fileop.mkdir_notexists(self.outfolder, remove_if_exists=True)
        d = utils.array2object(numpy.load(filename))
        [setattr(self, vn, d[vn]) for vn in varnames]
        gap_indexes = numpy.nonzero(numpy.diff(self.waveform))[0]
        gap_sizes = numpy.diff(gap_indexes)
        gap_indexes = numpy.nonzero(numpy.where(gap_sizes>1, gap_sizes, 0))[0]
        limiter = numpy.zeros(0.1*self.ao_sample_rate)
        mask=numpy.ones_like(self.waveform)
        mask[numpy.nonzero(numpy.diff(self.waveform))[0]]=0#Has to be filtered
        rising_edge_indexes = numpy.nonzero(numpy.where(numpy.diff(mask)==1,1,0))[0][:-1]
        rising_edge_indexes = rising_edge_indexes.tolist()
        rising_edge_indexes.insert(0,0)
        rising_edge_indexes = numpy.array(rising_edge_indexes)
        falling_edge_indexes = numpy.nonzero(numpy.where(numpy.diff(mask)==-1,1,0))[0]
        indexes = [[rising_edge_indexes[i], falling_edge_indexes[i]] for i in range(rising_edge_indexes.shape[0]) if falling_edge_indexes[i] - rising_edge_indexes[i] >100]
        mask=numpy.zeros_like(self.waveform)
        for i in indexes:
            mask[i[0]:i[1]]=1
        edges = numpy.nonzero(numpy.diff(mask))[0]
        edges = edges.tolist()
        edges.append(len(mask)-1)
        edges = numpy.array(edges)
        mask=numpy.zeros_like(self.waveform)
        for i in range(edges.shape[0]/2):
            mask[edges[0::2][i]:edges[1::2][i]]=1
        for i in range(len(self.params)):
            self.params[i]['rising'] = edges[0::2][i]
            self.params[i]['falling'] = edges[1::2][i]
        
    def eval_frequency_characteristics(self,filename):
        self.load_measurement(filename)
        res = [self.eval_single(p) for p in self.params]
        #gain, phase and offset change over frequency, amplitude and offset
        from mpl_toolkits.mplot3d import Axes3D
        parameter_ranges = {}
        for pname in ['frequency', 'voltage', 'offset']:
            parameter_ranges[pname] = list(set([p[pname] for p in res]))
            parameter_ranges[pname].sort()
        fig_ct = 1
        curves = []
        legend_items = []
        for offset in parameter_ranges['offset']:
            X, Y = numpy.meshgrid(parameter_ranges['frequency'], parameter_ranges['voltage'])
            phase = numpy.zeros_like(X)
            gain = numpy.zeros_like(X)
            for fi in range(len(parameter_ranges['frequency'])):
                for vi in range(len(parameter_ranges['voltage'])):
                    record = [r['measured'] for r in res if r['frequency'] == parameter_ranges['frequency'][fi] and r['voltage'] == parameter_ranges['voltage'][vi] and r['offset'] == offset]
                    if len(record)==0:
                        phase[vi,fi] = numpy.nan
                        gain[vi,fi] = numpy.nan
                        continue
                    record = record[0]
                    phase[vi,fi] = record['phase']
                    gain[vi,fi] = record['gain']
#            fig = figure(fig_ct)
#            fig_ct += 1
#            ax = fig.gca(projection='3d')
#            surf = ax.plot_surface(X, Y, phase, rstride=1, cstride=1, linewidth=0, antialiased=True)
#            title('phase, offset {0}'.format(offset))
#            fig = figure(fig_ct)
#            fig_ct += 1
#            ax = fig.gca(projection='3d')
#            surf = ax.plot_surface(X, Y, gain, rstride=1, cstride=1, linewidth=0, antialiased=True)
#            title('gain, offset {0}'.format(offset))
            for v in parameter_ranges['voltage']:
                c = numpy.array([[r['measured']['frequency'], r['measured']['gain'], r['measured']['phase'],r['voltage']] for r in res if r['voltage'] == v and r['offset'] == offset])
                curves.append(c)
                legend_items.append('{0:2.2f},{1:2.2f}'.format(v,offset))
                figure(fig_ct)
                plot(c[:,0],c[:,1])
                figure(fig_ct+1)
                plot(c[:,0],c[:,2]*180/numpy.pi)
#            figure(fig_ct)
#            legend(map(str, numpy.round(parameter_ranges['voltage'],2)))
#            figure(fig_ct+1)
#            legend(map(str, numpy.round(parameter_ranges['voltage'],2)))
#            fig_ct += 2
        figure(fig_ct)
        title('gain')
#        legend(legend_items)
#        savefig(os.path.join(outfolder, 'v_gain_{0:0=5}.png'.format(fig_ct)))
        figure(fig_ct+1)
        title('phase')
#        legend(legend_items)
#        savefig(os.path.join(outfolder, 'v_phase_{0:0=5}.png'.format(fig_ct+1)))
#        show()
        #phase fitting
        phase_steepness = []#rad/Hz
        for c in [c[:,2] for c in curves]:
            p0 = [-1.0, 0.0]
            import scipy.optimize
            coeff, var_matrix = scipy.optimize.curve_fit(linear, numpy.array(parameter_ranges['frequency'])[:c.shape[0]], c, p0=p0)
            phase_steepness.append(coeff)
        phase_params = numpy.array(phase_steepness).mean(axis=0)
        #gain fitting
        coeffs = []
        for c in [c[:,1] for c in curves]:
            p0 = [1,1,1]
            coeff, var_matrix = scipy.optimize.curve_fit(poly, numpy.array(parameter_ranges['frequency'])[:c.shape[0]], c, p0=p0)
            coeffs.append(coeff)

        gain_params = numpy.array(coeffs).mean(axis=0)
        pass
        
    def eval_single(self,param):
        '''
        Gain and phase shift has to be calculated
        '''
        command = self.waveform[param['rising']:param['falling']]
        measured = self.measured[param['rising']:param['falling']]
        import scipy.optimize
        p0 = [param['voltage'], param['frequency'], 0.0,  param['offset']]
        coeff, var_matrix = scipy.optimize.curve_fit(sinus, numpy.arange(measured.shape[0], dtype=numpy.float)/self.ao_sample_rate, measured, p0=p0)
        import copy
        res = copy.deepcopy(param)
        res['measured'] = {}
        res['measured']['voltage'] = coeff[0]*2
        res['measured']['frequency'] = coeff[1]
        res['measured']['phase'] = coeff[2]
        if res['measured']['phase'] > numpy.pi:
            res['measured']['phase'] = res['measured']['phase'] - numpy.pi
        res['measured']['offset'] = coeff[3]
        res['measured']['gain'] = abs(res['measured']['voltage']/param['voltage'])
        res['measured']['offset_change'] = param['offset'] - res['measured']['offset']
        return res
        
    def y_mirror_test(self):
        periods = 5
        paramspace = {}
        paramspace['voltage'] = numpy.logspace(-0.3,0.5,4)
        paramspace['offset'] = numpy.array([-1.0,0.0,1.0])
        paramspace['frame_rate'] = numpy.array([3.0, 5.0, 10.0, 20.0])
        paramspace['flyback_time'] = numpy.array([1.0/1500, 2/1500.0, 5.0/1500, 10.0/1500])
        params = []
        for o in paramspace['offset']:
            for v in paramspace['voltage']:
                for f in paramspace['frame_rate']:
                    for fb in paramspace['flyback_time']:
                        params.append({'frame_rate': f, 'voltage': v, 'offset': o, 'flyback_time': fb})
        test_signal = []
        nsamples = 0
        for param in params:
            test_signal.append(numpy.ones(0.1 * self.ao_sample_rate)*param['offset'])
            t_up = 1.0/param['frame_rate'] - param['flyback_time']
            test_signal.append(signal.wf_triangle(param['voltage'], t_up, param['flyback_time'], periods/param['frame_rate'], self.ao_sample_rate, offset = param['offset']))
            nsamples += test_signal[-2].shape[0] + test_signal[-1].shape[0]
        wf = numpy.concatenate(tuple(test_signal))
        print wf.shape[0]/self.ao_sample_rate
        measured = self.run_measurement(wf*self.voltage_correction_factor)
        measured = measured[:wf.shape[0],0]
        data = {}
        data['waveform'] = wf
        data['measured'] = measured
        data['ao_sample_rate'] = self.ao_sample_rate
        data['params'] = params
        data['angle2voltage_factor'] = self.angle2voltage_factor
        numpy.save('r:\\dataslow\\scanner_frq_domain_anal\\y_mirror.npy', utils.object2array(data))
        pass
        
    def eval_y_scanner(self,filename):
        self.load_measurement(filename)
        res = []
        plots = {}
        figct = 1
        for param in self.params:
            res.append(param)
            command = self.waveform[param['rising']:param['falling']]
            measured = self.measured[param['rising']:param['falling']]
            #linearity in scan range: this also gives information about the effect of flyback
            accel = numpy.diff(numpy.diff(command))
            accel = numpy.where(abs(accel)<1e-10,0,accel)
            boundaries = numpy.nonzero(accel)[0][1::2]
            command_mean = numpy.array(numpy.split(command,boundaries)[1::2]).mean(axis=0)
            measured_mean = numpy.array(numpy.split(measured,boundaries)[1::2]).mean(axis=0)
            res[-1]['command_mean'] = command_mean
            res[-1]['measured_mean'] = measured_mean
            import scipy.optimize
            p0 = [1.0,0.0]
            t = numpy.arange(measured_mean.shape[0])/float(self.ao_sample_rate)
            coeff, var_matrix = scipy.optimize.curve_fit(linear, t, measured_mean, p0=p0)
            res[-1]['measured'] = coeff
            coeff, var_matrix = scipy.optimize.curve_fit(linear, t, command_mean, p0=p0)
            res[-1]['command'] = coeff
            
            error = res[-1]['command']/res[-1]['measured']
            error = numpy.where(error<1e-2,1.0,error)
            res[-1]['error']=error
            if not plots.has_key(param['flyback_time']):
                plots[param['flyback_time']] = {}
                if not plots[param['flyback_time']].has_key(param['frame_rate']):
                    plots[param['flyback_time']][param['frame_rate']] = {}
                    if not plots[param['flyback_time']][param['frame_rate']].has_key(param['voltage']):
                        plots[param['flyback_time']][param['frame_rate']][param['voltage']] = []
            plots[param['flyback_time']][param['frame_rate']][param['voltage']].append(error)
        
        leg1 = []
        leg2 = []
        for fbtime in plots.keys():
            for framerate in plots[fbtime].keys():
                for v in plots[fbtime][framerate].keys():
                    dat= numpy.array(plots[fbtime][framerate][v])
                    figure(1)
                    plot(dat[:,0])
                    leg1.append('speed, {0}, {1}, {2}'.format(1/fbtime, framerate,v))
                    figure(2)
                    plot(dat[:,1])
                    leg2.append('offset, {0}, {1}, {2}'.format(1/fbtime, framerate,v))
                    
                    
            
        figure(1)
        legend(leg1)
        figure(2)
        legend(leg2)
        show()
#            fgct+=2
             
        pass
            
def sinus(x, *p):
    A, f, ph, o = p
    return A*numpy.sin(numpy.pi*2*x*f+ph)+o
    
def linear(x, *p):
    A,b = p
    return A*x+b
    
def poly(x, *p):
    res = []
    for o in range(len(p)):
        res .append(p[o]*x**o)
    return numpy.array(res).sum(axis=0)
        
def scanner_control_signal():
    error = 10e-2
    f = 1500
    fs = 400e3
    duration = 1.0/f
    a =1
    xscanner = signal.wf_sin(a, f, duration, fs,phase = 0)
    yscanner = signal.wf_sin(a, f/10, duration, fs,phase = 0)
    xlin = numpy.arange(xscanner.shape[0],dtype=numpy.float)*numpy.diff(xscanner)[0]
#    plot(xlin)
    plot(xscanner)
    plot(yscanner)
#    plot(abs(xscanner-xlin))
#    plot(numpy.ones_like(xscanner)*error)
    samples_per_x_period = 2*numpy.where(numpy.ones_like(xscanner)*error-abs(xscanner-xlin)>0,1,0).sum()
    pass
    
if __name__ == "__main__":
    s=ScannerIdentification()

    if False:
        s.y_mirror_test()
        s.command_voltage_angle_characteristics()
#    s.frequency_domain_characteristics()
#    scanner_control_signal()
#    s.eval_frequency_characteristics('r:\\dataslow\\scanner_frq_domain_anal\\high_frequency_domain_characteristics.npy')
#        s.eval_frequency_characteristics('/mnt/rzws/dataslow/scanner_frq_domain_anal/high_frequency_domain_characteristics.npy')
#    s.eval_y_scanner('/mnt/rzws/dataslow/scanner_frq_domain_anal/y_mirror.npy')
    s.eval_y_scanner('/home/zoltan/codes/data/y_mirror.npy')
