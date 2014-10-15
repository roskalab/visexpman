import zipfile
from pylab import plot,show,title,figure,legend,xlabel,ylabel
import time,numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import utils, log,fileop,introspect
from visexpman.engine.generic.graphics import is_key_pressed,check_keyboard
import multiprocessing
import os.path
import tables
from visexpA.engine.datahandlers.datatypes import ImageData
from visexpA.engine.datahandlers.hdf5io import Hdf5io
import pygame
import tempfile

def measure():
    with introspect.Timer(''):
        #Sampling analog input starts
        folder = 'r:\\dataslow\\measurements\\electrode_current_temperature'
        folder = 'c:\\Data'
        ai_channels = 'Dev1/ai1:3'
        ai_record_time = 0.02
        ai_sample_rate = 30000
#        ai_sample_rate = 3000000
        complevel = 9
        pygame.display.set_mode((200, 200), pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL)
        device_name, nchannels, channel_indexes = daq_instrument.parse_channel_string(ai_channels)
        
        h = ImageData(fileop.generate_filename(os.path.join(folder, 'data.hdf5')), filelocking=False)
        raw_data = h.h5f.create_earray(h.h5f.root, 'raw_data', tables.Float32Atom((nchannels,)), (0,),filters=tables.Filters(complevel=complevel, complib='blosc', shuffle = 1), expectedrows=int(ai_record_time * ai_sample_rate))
        
        logfile = fileop.generate_filename(os.path.join(folder, 'log_recorder.txt'))
        logger = log.Logger(filename=logfile)
        instrument_name = 'recorder'
        logger.add_source(instrument_name)
        queues = {'command': multiprocessing.Queue(), instrument_name: multiprocessing.Queue(), 'data': multiprocessing.Queue(),'response': multiprocessing.Queue()}
        aio = daq_instrument.AnalogIOProcess('recorder', queues, logger, ai_channels = ai_channels)
        aio.start()
        logger.start()
        aio.start_daq(ai_sample_rate = ai_sample_rate,ai_record_time = 3.0, timeout = 10) 
        print 'recording...'
        print 'press enter to terminate'
        data = []
        i=0
        t0=time.time()
        with introspect.Timer(''):
            while True:
                r=aio.read_ai()
                if r is not None:
                    print r[-1,:]
                    raw_data.append(numpy.cast['float32'](r))
                i+=1
#                if time.time()-t0>10.0:
#                    break
                time.sleep(ai_record_time*0.5)
                if is_key_pressed('return'):
                    break
        print 'stopping...'

        data1 = aio.stop_daq()
        for r in data1[0]:
            raw_data.append(numpy.cast['float32'](r))
        aio.terminate()
        logger.terminate()
        h.close()
        if 0:
            print 'zipping'
            zipfile_handler = zipfile.ZipFile(h.filename.replace('.hdf5','.zip'), 'a',compression=zipfile.ZIP_DEFLATED)
            zipfile_handler.write(h.filename, os.path.split(h.filename)[1])
            zipfile_handler.close()
        if time.time()-t0<100.0:
            print 'check file'
            h=Hdf5io(h.filename,filelocking=False)
            h.load('raw_data')
            print h.raw_data.shape[0]/float(ai_sample_rate)
            plot(h.raw_data,'-')
            h.close()
        pygame.quit()
        print 'done'
        show()
        pass

def evaluate():
    '''
    Data order: voltage command, current, temperature
    '''
    folder = '/mnt/rzws/measurements/electrode_current_temperature'
    folder = '/tmp/test'
#    folder = 'c:\\temp\\test'
    current_scale = 0.5 #mV/pA, 750 mV at 1500 pA
    voltage_command_scale = 0.1 #100 mV/V
    ai_sample_rate = 30000
    fs = os.listdir(folder)
    fs.sort()
    figct = 1
    legendtxt=[]
    zipped = len([f for f in fs if 'zip' in f])>0
    for f in fs:
        if 'zip' not in f and zipped:
            continue
        print f
        f=os.path.join(folder,f)
        if zipped:
            z = zipfile.ZipFile(f)
            extracted_file = z.extract(os.path.split(f)[1].replace('zip','hdf5'), tempfile.gettempdir())
        else:
            if 'hdf5' not in f:
                continue
            extracted_file = f
        h=Hdf5io(extracted_file, filelocking=False)
        h.load('raw_data')
        import copy
        data = copy.deepcopy(h.raw_data)
        h.close()
        if zipped:
            os.remove(extracted_file)
        z.close()
        #convert data to physical units:
        scale = numpy.array([voltage_command_scale, current_scale*1e3,10.0])
        data *= scale
        voltage_command = data[:,0]
        electrode_current = data[:,1]
        temperature = data[:,2]
        t = numpy.arange(voltage_command.shape[0],dtype=numpy.float)/ai_sample_rate
#        plot(t[:1e5],voltage_command[:1e5])
        from scipy.signal import wiener,medfilt
        #Find out when voltage pulses took place
        filtered_voltage_command = (medfilt(voltage_command,[5]))
        edges = numpy.nonzero(numpy.where(abs(numpy.diff(filtered_voltage_command))>5e-3,1,0))[0]
        on_pulses = []
        for i in range(1,edges.shape[0]-1):
            prev_interval = [edges[i-1]+1,edges[i]-1]
            if prev_interval[1]-prev_interval[0]<1:
                continue
            current_interval = [edges[i]+1,edges[i+1]-1]
            if current_interval[1]-current_interval[0]<1:
                continue
            current_interval_voltage = filtered_voltage_command[current_interval[0]:current_interval[1]].mean()
            if filtered_voltage_command[prev_interval[0]:prev_interval[1]].mean() < current_interval_voltage:
                on_pulses.append([current_interval,current_interval_voltage])
        results = []
        removable_items = []
        print 'analyse pulses'
        for i in range(len(on_pulses)):
            on_pulse = on_pulses[i]
            boundaries = on_pulse[0]
            voltage = voltage_command[boundaries[0]:boundaries[1]].mean()
            if i ==0:
                baseline_first_index = boundaries[0]/2
            else:
                baseline_first_index = on_pulses[i-1][0][1]+0.25*(boundaries[0]-on_pulses[i-1][0][1])
            current_baseline = electrode_current[baseline_first_index:boundaries[0]-1].mean()
            current = electrode_current[boundaries[0]+0.1*(boundaries[1]-boundaries[0]):boundaries[1]].mean()
            current -= current_baseline
            temperature_ = temperature[boundaries[0]:boundaries[1]].mean()
            if current==0:
                resistance = 0
            else:
                resistance = voltage/(current*1e-12)
            if i>1:
                if voltage*0.5>results[i-1][0] and results[i-1][0]<0.5*results[i-2][0]:
                    removable_items.append(i-1)
            results.append([voltage,current,temperature_,resistance])
        print 'pulse analysis done'
        results = [results[i] for i in range(len(results)) if i not in removable_items]
        results = numpy.array(results)
        if '006' in f:
            results = results[200:3300,:]
        elif '008' in f:
            results = results[110:,:]
        if 0:
            numpy.savetxt(f.replace('zip','txt'), results, '%10.5f')
        voltage = results[:,0]*1000#mV
        current = results[:,1]/1000#nA
        temperature = results[:,2]#Celsius
        resistance = results[:,3]/1e6#MOhm
        if 0:
            figure(figct)
            figct +=1
            plot(voltage)
            plot(current)
            plot(temperature)
            legend(['voltage','current','temperature'])
            title(os.path.split(f)[1])
            figure(figct)
            figct +=1
            plot(temperature)
    #        plot(current*100)
            plot(resistance)
    #        plot(temperature/resistance)
            legend(['temperature', 'resistance'])
            title(os.path.split(f)[1])
        #Notes: at cooling there is some fluctuance in resistance
        #1. plot raw current values with temperature to see if it is true
        #2. cut out temp up and temp down sections and make a plot(temp, resistance)
#        cut_indexes = numpy.nonzero(numpy.where(voltage>15,1,0))[0]
#        temperature = temperature[cut_indexes]
#        resistance = resistance[cut_indexes]
#        if temperature.shape[0]==0:
#            continue
        #1e-3
        #5e-3, 10e-3
        if '008' in f:
            boundaries = [600,2300,2950,6600,6990,8250,9100,12900]
        elif '007' in f:
            boundaries = [0,1450,2800, 6200]
        elif '006' in f:
            boundaries = [0,2500]
        for intervali in range(len(boundaries)/2):
            boundary=boundaries[2*intervali:2*intervali+2]
            t_interval = temperature[boundary[0]:boundary[1]]
            r_interval = resistance[boundary[0]:boundary[1]]
            temps = numpy.arange(t_interval.min(), t_interval.max(),0.1)
            resistance_sorted = []
            resistance_sorted_std = []
            
            
            for step in range(temps.shape[0]-1):
                indexes = numpy.nonzero(numpy.where(t_interval>temps[step],1,0) * numpy.where(t_interval<=temps[step+1],1,0))[0]
                resistance_sorted.append(r_interval[indexes].mean())
                resistance_sorted_std.append(r_interval[indexes].std())
            if intervali%2 ==0:
                tag='heating'
            else:
                tag='cooling'
            figure(100)
            plot(temps[:-1],resistance_sorted)
            legendtxt.append('{0}, {1}, {2:.0f} mV'.format(os.path.split(f)[1],tag, voltage[boundary[0]+1]))
#            figure(figct)
#            figct +=1
#            title('{0}, temp-resistance [MOhm], {1}'.format(os.path.split(f)[1],intervali))
#            plot(temps[:-1],resistance_sorted)
        
        
        
        
    figure(100)
    legend(legendtxt)
    xlabel('temperature [Celsius degree]')
    ylabel('resistance [MOhm]')
    title('Temperature dependency of electrode resistance')
    show()
    import pdb
#    pdb.set_trace()
    pass
    
def evaluate1():
    f = '/home/rz/codes/data/electrode_current_temperature/20141010/data_00003.hdf5'
    current_scale = 0.5 #mV/pA, 750 mV at 1500 pA
    voltage_command_scale = 0.1 #100 mV/V
    ai_sample_rate = 30000    
    h=Hdf5io(f, filelocking=False)
    h.load('raw_data')
    print h.raw_data.shape
    data = copy.deepcopy(h.raw_data)
    h.close()
    voltage_command = data[:,0]
    electrode_current = data[:,1]
    temperature = data[:,2]
    pass
    
def poly(x, *p):
    res = []
    for o in range(len(p)):
        res .append(p[o]*x**o)
    return numpy.array(res).sum(axis=0)
    
def fit():
    f = '/home/rz/codes/data/electrode_current_temperature/aggregated.hdf5'
    h=Hdf5io(f,filelocking=False)
    legendtxt = h.findvar('legendtxt')
    rt_curves = h.findvar('rt_curves')
    h.close()
    figct=1
    for c in rt_curves:
        figure(0)
        plot(c[0],c[1])
        figure(figct)
        plot(c[0],c[1])
        p0=[40,-1]
        import scipy.optimize
        coeff, var_matrix = scipy.optimize.curve_fit(poly, numpy.array(c[0]), numpy.array(c[1]), p0=p0)
        plot(c[0],poly(numpy.array(c[0]), *coeff))
        plot(numpy.arange(10,45,1), poly(numpy.arange(10,45,1), 40,-0.44), 'x-')
        title(legendtxt[figct-1]+', {0:.3f} + {1:.3f}*T'.format(coeff[0],coeff[1]))
        xlabel('temperature [Celsius degree]')
        ylabel('resistance [MOhm]')
        figct+=1
    figure(0)
    plot(numpy.arange(10,45,1), poly(numpy.arange(10,45,1), 40,-0.44), 'x-')
    legend(legendtxt)
    xlabel('temperature [Celsius degree]')
    ylabel('resistance [MOhm]')
    show()

if __name__ == "__main__":
#    measure()
#    evaluate()
    fit()

    
