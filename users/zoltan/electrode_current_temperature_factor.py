import zipfile
import time,numpy
try:
    from visexpman.engine.hardware_interface import daq_instrument
    from visexpman.engine.generic import utils, log,fileop,introspect
    from visexpman.engine.generic.graphics import is_key_pressed,check_keyboard
    from visexpA.engine.datahandlers.datatypes import ImageData
    from visexpA.engine.datahandlers.hdf5io import Hdf5io
    import tables
    import pygame
    from pylab import plot,show,title,figure,legend,xlabel,ylabel,savefig
except:
    pass

import multiprocessing
import os.path


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
    folder = 'c:\\temp'
    current_scale = 0.5 #mV/pA, 750 mV at 1500 pA
    voltage_command_scale = 0.1 #100 mV/V
    ai_sample_rate = 30000
    fs = os.listdir(folder)
    fs.sort()
    figct = 1
    legendtxt=[]
    zipped = len([f for f in fs if 'zip' in f])>0
    hout=Hdf5io('/mnt/rzws/temp/out.hdf5',filelocking=False)
    hout.data={}
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
            results.append([voltage,current,temperature_,resistance,current_baseline])
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
        current_baseline = results[:,4]/1000#nA
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
            i_interval = current[boundary[0]:boundary[1]]
            i_b_interval = current_baseline[boundary[0]:boundary[1]]
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
            hout.data[legendtxt[-1]]={}
            hout.data[legendtxt[-1]]['t']=t_interval
            hout.data[legendtxt[-1]]['r']=r_interval
            hout.data[legendtxt[-1]]['i']=i_interval
            hout.data[legendtxt[-1]]['ib']=i_b_interval
#            figure(figct)
#            figct +=1
#            title('{0}, temp-resistance [MOhm], {1}'.format(os.path.split(f)[1],intervali))
#            plot(temps[:-1],resistance_sorted)
        
    figure(100)
    legend(legendtxt)
    xlabel('temperature [Celsius degree]')
    ylabel('resistance [MOhm]')
    title('Temperature dependency of electrode resistance')
    hout.save('data')
    hout.close()
    show()
    import pdb
#    pdb.set_trace()
    pass
    
def variable_transformation(data, target, target_resolution):
    bins = numpy.arange(target.min(),target.max(),target_resolution)
    transformed = []
    for i in range(bins.shape[0]-1):
        transformed.append(data[numpy.nonzero(numpy.where(target>bins[i],1,0)*numpy.where(target<bins[i+1],1,0))[0]].mean())
    return bins[:-1]+0.5*target_resolution, numpy.array(transformed)
        
def electrode_current_calc(t, *p):
    import scipy.constants
    Ea = p[1]
    A = p[0]
    return A*numpy.exp(-Ea/(scipy.constants.R*t))
   
def evaluate1():
    import scipy.constants
    f = '/tmp/test'
    current_scale = 0.5*2 #mV/pA, 750 mV at 1500 pA
    voltage_command_scale = 0.1 #100 mV/V
    ai_sample_rate = 30000
    i0 = -500#pA
    t0 = scipy.constants.C2K(24.0)
    figct=1
    l = []
    coeffs = []
    for fi in fileop.listdir_fullpath(f):
        h=Hdf5io(fi, filelocking=False)
        h.load('raw_data')
        import copy
        data = copy.deepcopy(h.raw_data)
        data *= numpy.array([voltage_command_scale, current_scale*1e3,10.0])
        h.close()
        voltage_command = data[:,0]
        electrode_current = data[:,1]
        temperature = scipy.constants.C2K(data[:,2])
        if '00001' in fi:
            boundaries = [17757, 177472, 209415, 266129, 534274, 575917, 686876, 747984]
#        elif '00002'in fi:
#            boundaries = [25323, 127036, 147210, 315330]
        else:
#            figure(figct+100)
#            plot(voltage_command[::100])
#            plot(electrode_current[::100])
#            plot(temperature[::100])
#            legend(['voltage_command','electrode_current','temperature'])
#            title(fi)
            continue
        boundaries = numpy.array(boundaries)*100
        hh=numpy.histogram(voltage_command)
        voltage = numpy.round(hh[1][hh[0].argmax()]*1000,-1)
        figure(figct)
        plot(voltage_command[::100])
        plot(electrode_current[::100])
        plot(temperature[::100])
        legend(['voltage_command','electrode_current','temperature'])
        title('{0}, {1} mV' .format(fi,voltage))
        figct+=1
        
        for ii in range(boundaries.shape[0]/2):
            t, i = variable_transformation(electrode_current[boundaries[ii*2]:boundaries[ii*2+1]], temperature[boundaries[ii*2]:boundaries[ii*2+1]], 1)
            figure(0)
            k=i/i0
            plot(1.0/t,numpy.log(k))
            l.append('{0}, {1}, {2} mV'.format(fi, ii%2, voltage))
            import scipy.optimize
            p0 = [1, -4000.0]
            coeff, var_matrix = scipy.optimize.curve_fit(poly, 1/t, numpy.log(i/i0), p0=p0)
            coeffs.append(coeff)
#            try:
#                coeff, var_matrix = scipy.optimize.curve_fit(electrode_current_calc, t, k, p0=[1,3.84e3*scipy.constants.calorie])
#                print coeff[1]/scipy.constants.calorie/1e3
#                figure(300+figct)
#                plot(t, k)
#                plot(t, electrode_current_calc(t, *coeff))
#            except:
#                pass
            figct+=1
            
    coeff_ = numpy.array(coeffs).mean(axis=0)
    print -numpy.array(coeffs)[:,1]* scipy.constants.R/scipy.constants.calorie/1e3
    Ea = -coeff_[1] * scipy.constants.R
    Ea_cal = Ea/scipy.constants.calorie/1e3
    print Ea_cal
    figure(0)
    t=scipy.constants.C2K(numpy.arange(20,50,1))
    plot(1/t,poly(1/t,*coeff_),'x-')
    l.append('fit')
    legend(l)
    xlabel('1/temperature [K]')
    ylabel('ln(i/i0), where i0=500 pA at 297 K')
    
    
    
    show()
    
def poly(x, *p):
    res = []
    for o in range(len(p)):
        res.append(p[o]*x**o)
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
        figure(100)
        plot(1/numpy.array(c[0]),numpy.log(1/numpy.array(c[1])))
        xlabel('1/temperature [Celsius degree]')
        ylabel('ln(1/resistance) [MOhm]')
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
    
def arrhenius():
    p='c:\\temp\\out.hdf5'
    h=Hdf5io(p,filelocking=False)
    h.load('data')
    p0=[40,-1]
    import scipy.optimize
    ct=0
    for n,d in h.data.items():
#        ct+=1
        figure(ct)
#        if '20' in n:
#            
#        else:
#            figure(2)
        figure(1)
        plot(1/d['t'],numpy.log(d['i']))
        figure(2)
        plot(d['t'],d['ib'])
#        coeff, var_matrix = scipy.optimize.curve_fit(poly, numpy.array(c[0]), numpy.array(c[1]), p0=p0)
#        title(n)
    figure(1)
    legend(h.data.keys())
    figure(2)
    legend(h.data.keys())
    show()
    
def plot_rawdata():
    folder = 'c:\\temp'
    current_scale = 0.5 #mV/pA, 750 mV at 1500 pA
    voltage_command_scale = 0.1 #100 mV/V
    ai_sample_rate = 30000
    fs = os.listdir(folder)
    fs.sort()
    figct = 1
    legendtxt=[]
    zipped = len([f for f in fs if 'zip' in f])>0
    figct = 1
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
        figure(figct)
        plot(electrode_current)
        plot(temperature)
        figct+=1
        title(f)
    show()
    
def merge_datafiles():
    folder = '/home/rz/rzws/measurements/electrode_current_temperature/20141128'
    folders = map(os.path.join, len(os.listdir(folder))*[folder], os.listdir(folder))
    h = Hdf5io(os.path.join(os.path.split(folder)[0], '20141128.hdf5'),filelocking=False)
    h.names = []
    for f in folders:
        alldata = []
        h.names.append(os.path.split(f)[1])
        files = map(os.path.join, len(os.listdir(f))*[f], os.listdir(f))
        for fn in files:
            parameters = {}
            parameters['name'] = os.path.split(f)[1]
            tags = os.path.split(fn)[1].replace('.csv','').split('_')
            parameters['repetitions'] = int(tags[1])
            parameters['pulse_duration'] = float(tags[4])
            parameters['laser_power'] = float(tags[5])
            with open(fn, 'rt') as fp:
                txt = fp.read()
            dataseries = txt.split('\r\n')
            data = []
            for i in range(len(dataseries)-1):
                data.append(map(float,dataseries[i].split(',')))
            data = numpy.array(data, dtype=numpy.float32)
            alldata.append([parameters, data])
        setattr(h, h.names[-1], utils.object2array(alldata))
        h.save(h.names[-1])
    h.save('names')
    h.close()
    pass
    
def calculate_activation_energy(current, temperature, trigger):
    current_transient, temperature_transient, t0, temperature_step, max_measured_temperature, i0, max_current,current_step,heat_up_transient,cooling_transient = \
                    extract(trigger, current, temperature)
    index = numpy.nonzero(numpy.where(trigger>trigger.max()/2,1,0))[0].max()
    current=current[index:]
    temperature=temperature[index:]
    t, i = variable_transformation(current, temperature, (temperature.max()-temperature.min())/10.0)
    if numpy.isnan(i).any() or numpy.where(i/i0<0,1,0).sum()>0:
        return 0,0
    p0 = [1, -4000.0]
    import scipy.optimize,scipy.constants
    coeff, var_matrix = scipy.optimize.curve_fit(poly, 1/t, numpy.log(i/i0), p0=p0)
    Ea = -coeff[1] * scipy.constants.R
    Ea_cal = Ea/scipy.constants.calorie/1e3
    return Ea, Ea_cal
    
def estimate_electrode_temperature(i, i0, t0, Ea):
    import scipy.constants
    t=1/(1/t0-scipy.constants.R/Ea*numpy.log(i/i0))
    return t
    
def extract(laser_pulse, current, temperature):
    '''
    Extract current and temp baseline and transient
    '''
    laser_on_indexes = numpy.nonzero(numpy.where(laser_pulse>0.5*laser_pulse.max(), 1, 0))[0]
    pre_pulse_temperature = temperature[:0.95*laser_on_indexes.min()].mean()
    pre_pulse_current = current[:0.95*laser_on_indexes.min()].mean()
    current_transient = current[laser_on_indexes.min():]
    temperature_transient = temperature[laser_on_indexes.min():]
    max_measured_temperature = temperature.max()
    max_current = current.min()
    current_step = abs(max_current-pre_pulse_current)
    temperature_step = abs(max_measured_temperature-pre_pulse_temperature)
    cooling_current = current[laser_on_indexes.max():]
    cooling_temperature = temperature[laser_on_indexes.max():]
    heat_up_transient = current[laser_on_indexes.min():laser_on_indexes.max()]
    cooling_transient = current[laser_on_indexes.max():]
    return current_transient, temperature_transient, pre_pulse_temperature, temperature_step, max_measured_temperature, pre_pulse_current, max_current,current_step,heat_up_transient,cooling_transient
    
def exp(t, *p):
    return p[0]*numpy.exp(p[1]*t)+p[2]
       
def evaluate_laser_triggered_currents():
    '''
    Temperature estimation from current: 1/(1/T0-R/Ea*log(I/I0))
    
    Ea = ?
    '''
    import scipy.constants
    fn = '/home/rz/rzws/measurements/electrode_current_temperature/20141128.hdf5'
    h= Hdf5io(fn, filelocking=False)
    currents_at_100deg = []
    Eaall = {}
    for n in h.findvar('names'):
        Ea_per_measurement = []
        data = utils.array2object(h.findvar(n))
        for par, d in data:
            laser_pulse = d[0]
            current = d[1]*2000#pA
            temperature = scipy.constants.C2K(d[2])
#            #TODO: This calculation does not consider repeptitions!!!!!!!!!!!!!!!!!!
            current_transient, temperature_transient, t0, temperature_step, max_measured_temperature, i0, max_current,current_step,heat_up_transient,cooling_transient = \
                    extract(laser_pulse, current, temperature)
            Ea_per_file = []
            for r in range(par['repetitions']):
                i1 = r*current.shape[0]/par['repetitions']
                i2 = (r+1)*current.shape[0]/par['repetitions']
                Ea_per_file.append(calculate_activation_energy(current[i1:i2], temperature[i1:i2], laser_pulse[i1:i2]))
                if Ea_per_file[-1] == (0,0):
                    Ea_per_file.remove((0,0))
            if par['laser_power'] > 5.0 and par['pulse_duration'] > 0.1 and len(Ea_per_file)>0:
                Ea_per_measurement.append(numpy.array(Ea_per_file).mean(axis=0))
            if 'boil' in n:
                pulse_widths = 1e-3*numpy.array([10, 12, 13, 15,16, 17])
                if par['pulse_duration'] in pulse_widths:
                    Ea = Eaall['rapidtemp_pipette2_200um_deeper'][0]*scipy.constants.calorie*1e3
                    currents_at_100deg.append([par['pulse_duration'], temperature.max(), estimate_electrode_temperature(current, i0, t0, Ea).max()])
        if len(Ea_per_measurement)>0:
            Eaall[n] = numpy.array(Ea_per_measurement)[:,1]
            Eaall[n] = [Eaall[n].mean(), Eaall[n].std(), Eaall[n]]
        pass
    #Ea-s calculated, estimate temp from current
    figct=1
    timing = []
    for n in h.findvar('names'):
        diff = []
        if 'boil' in n or 'pipettaX' in n:
            continue
        data = utils.array2object(h.findvar(n))
        Ea = Eaall[n][0]
        Ea_SI = Ea*scipy.constants.calorie*1e3
        for par, d in data:
            cool2_10percent_time = []
            heat_50percent_time = []
            for r in range(par['repetitions']):
                i1 = r*d[0].shape[0]/par['repetitions']
                i2 = (r+1)*d[0].shape[0]/par['repetitions']
                laser_pulse = d[0,i1:i2]
                current = d[1,i1:i2]*2000#pA
                temperature = scipy.constants.C2K(d[2,i1:i2])
                current_transient, temperature_transient, t0, temperature_step, max_measured_temperature, i0, max_current,current_step,heat_up_transient,cooling_transient = \
                        extract(laser_pulse, current, temperature)
                if 0:
                    cool2_10percent_time.append(numpy.nonzero(numpy.where(cooling_transient < cooling_transient[-1]+0.1*(cooling_transient[0] - cooling_transient[-1]),1,0))[0].max())
                    heat_50percent_time.append(numpy.nonzero(numpy.where(heat_up_transient>heat_up_transient[0]-di,1,0))[0].max())
                else:
                    di = 100#pA Absolute current step is better for comparing effect of different laser pulses
                    cool2_10percent_time.append(numpy.nonzero(numpy.where(cooling_transient < cooling_transient[0]+di,1,0))[0].max())
                    heat_50percent_time.append(numpy.nonzero(numpy.where(heat_up_transient>heat_up_transient[0]-di,1,0))[0].max())
                if par['laser_power']<6 and par['pulse_duration']<0.3:
                    continue
                try:
                    figure(figct)
                    plot(temperature)
                    #t=1/(1/t0-scipy.constants.R/Ea*numpy.log(i/i0))
                    estimated_temp = estimate_electrode_temperature(current, i0, t0, Ea_SI)
                    plot(estimated_temp)
                    indexes = numpy.nonzero(numpy.where(laser_pulse.max()*0.5<laser_pulse,1,0))[0]
                    trg=t0*numpy.ones_like(estimated_temp)
                    trg[indexes] = estimated_temp.max()
                    plot(trg)
#                    plot(current)
                    legend(['measured', 'estimated', 'pulse on/off', 'current'])
                    diff.append(abs(estimated_temp-temperature).max())
                    title('max diff between measured and estimated: {0}'.format(diff[-1]))
                    savefig('/tmp/fig/{0}_{1}_{2}_{3}_{4}.png'.format(n,par['laser_power'], par['pulse_duration'], figct, int(diff[-1])))
                    figct+=1
                except:
                    pass
            cool2_10percent_time = numpy.array(cool2_10percent_time)
            heat_50percent_time = numpy.array(heat_50percent_time)
            timing.append([par['name'], par['laser_power'], par['pulse_duration'], cool2_10percent_time.mean(), 100*cool2_10percent_time.std()/cool2_10percent_time.mean(), heat_50percent_time.mean(), 100*heat_50percent_time.std()/heat_50percent_time.mean()])
        figure(figct)
        plot(diff)
        savefig('/tmp/fig/max_error_{0}.png'.format(n))
#            print timing[-1]
    h.close()
    
    for n in h.findvar('names'):
        sel = [t for t in timing if t[0] == n]
        laser_powers = set([t[1] for t in timing])
        laser_powers = list(laser_powers)
        laser_powers.sort()
        pulse_durations = list(set([t[2] for t in timing]))
        pulse_durations.sort()
        pulse_durations.remove(0.0)
        for pulse_duration in pulse_durations:
            if pulse_duration == 0:
                continue
            pd = [[t[1], t[3], t[5]] for t in timing if t[2] == pulse_duration]
            pd_sorted = []
            for lp in laser_powers:
                pd_sorted.append([pdi for pdi in pd if pdi[0] == lp][0])
            pd = numpy.array(pd_sorted)
            figure(figct)
            plot(pd[:,0],pd[:,1]/1e4*1e3)
            title('{0}, cooling time'.format(n))
            legend(pulse_durations)
            ylabel('ms')
            xlabel('W')
            figure(figct+1)
            plot(pd[:,0],pd[:,2]/1e4*1e3)
            title('{0}, heating time'.format(n))
            legend(pulse_durations)
            ylabel('ms')
            xlabel('W')
        figct += 2
    pass
    show()
    
    

if __name__ == "__main__":
    evaluate_laser_triggered_currents()
#    merge_datafiles()
#    plot_rawdata()
#    arrhenius()
#    measure()
#    evaluate1()
#    fit()

    
