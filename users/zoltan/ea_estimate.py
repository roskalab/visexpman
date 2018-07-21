import numpy
import os
import os.path
from visexpman.users.zoltan import electrode_current_temperature_factor
import scipy.constants
import time

if __name__ == "__main__":  
    root = 'c:\\Data\\tamas\\IR laser'
    root = ''
    time.sleep(3)
    fns = os.listdir(root)
    d = 0
    most_recent_file = ''
    for fn in fns:
        fn=os.path.join(root,fn)
        if '.csv' in fn and os.stat(fn).st_ctime>d:
            d = os.stat(fn).st_ctime
            most_recent_file = fn
    with open(most_recent_file, 'rt') as fp:
        txt = fp.read()
    dataseries = txt.split('\n')
    data = []
    for i in range(len(dataseries)-1):
        data.append(map(float,dataseries[i].split('\t')))
    d = numpy.array(data, dtype=numpy.float32).T
    repetitions = float(most_recent_file.split('_')[2])
    
    laser_pulse = d[1]
    current = d[2]*2000#pA
    temperature = scipy.constants.C2K(d[3])
    #print d.shape, temperature.mean(), current.min(),current.max()
    chunksize=temperature.shape[0]/repetitions
    Eas = []
    for r in range(int(repetitions)):
        Eas.append(electrode_current_temperature_factor.calculate_activation_energy(current[r*chunksize:(r+1)*chunksize], temperature[r*chunksize:(r+1)*chunksize], laser_pulse[r*chunksize:(r+1)*chunksize]))
    Eas_mean=numpy.array(Eas).mean(axis=0)
    print('Ea, Ea cal', list(Eas_mean))
    print(Eas)
    print(most_recent_file)
