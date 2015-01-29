'''
Helpers for ngspice analysis
'''
from visexpman.engine.generic import utils,signal
import subprocess
import os
import os.path
import numpy
import time
from pylab import plot,legend,show,title,xlim,ylim
if __name__ == "__main__":
    folder = '/mnt/rzws/dataslow/documents/temperature_controller'
    os.chdir(folder)
    vrefs=numpy.arange(1.6,1.8,0.1)
    hyst_steps = []
    for vrefi in range(len(vrefs)):
        #Generate netlist file
        subprocess.call('gnetlist -g spice-sdb -o comparator.net comparator.sch',shell=True)
        #overwrite vref
        modifications = 0
        os.remove('comparator1.net')
        with open('comparator.net','r+') as f:
            netlist=f.read()
            for line in netlist.split('\n'):
                if 'VREF' in line:
                    items=line.split(' ')
                    items[-1] = str(vrefs[vrefi])+'V'
                    with open('comparator1.net','wt') as f1:
                        f1.write(netlist.replace(line, ' '.join(items)))
                    break
                
        #Run analysis
        if os.path.exists('result.txt'):
            os.remove('result.txt')
        time.sleep(0.1)
        subprocess.call('ngspice -b comparator1.net > result.txt',shell=True)
        with open('result.txt','rt') as f:
            res=f.read().split('\n')
            for line in range(len(res)):
                if 'Transient Analysis' in res[line]:
                    break
            for line2 in range(line,len(res)):
                if 'elapsed time since last call' in res[line2]:
                    break
            data=[]
            for l in range(line+1,line2-1):
                if '\t' not in res[l]:
                    continue
                data.append(map(float,res[l].split('\t')[1:-1]))
        data=numpy.array(data)
        t=data[:,0]
        vout=data[:,1]
        vin=data[:,2]
        vref=data[:,3]
        if 1:
            figure(vrefi+1)
            plot(t,vin)
            plot(t,vout)
            plot(t,vref)
            legend(['vin','vout','vref'])
        #expected threshold voltages:
        R1=float([l.split(' ')[-3].replace('k','000') for l in netlist.split('\n') if 'R1' == l.split(' ')[0]][0])
        R2=float([l.split(' ')[-3].replace('k','000') for l in netlist.split('\n') if 'R2' == l.split(' ')[0]][0])
        Vh=vout[numpy.nonzero(signal.signal2binary(vout))[0]].mean()
        Vl=vout[numpy.nonzero(signal.signal2binary(vout)^1)[0]].mean()
        Vs=vref.mean()*R2/(R1+R2)
        Vtu=Vs+Vh*R1/(R1+R2)
        Vtl=Vs+Vl*R1/(R1+R2)
        #Calculate threshold values from simulation results
        thresholds=vin[numpy.nonzero(numpy.diff(signal.signal2binary(vout)))[0]]
        Vtu_sim=thresholds[0::2].mean()
        Vtl_sim=thresholds[1::2].mean()
    #    plot(t,1000*(vout-vref)/R2)
        title('vref = {0}, calculated thresholds: {1:.2f}, {2:.2f}, simulated thresholds: {3:.2f}, {4:.2f}\n{5:.2}, {6:.2}'
                        .format(vrefs[vrefi],Vtu,Vtl,Vtu_sim,Vtl_sim, abs(vrefs[vrefi]-Vtu_sim),abs(vrefs[vrefi]-Vtl_sim)))
        hyst_steps.append([Vtu_sim,Vtl_sim,Vtu,Vtl,Vs])
    hyst_steps=numpy.array(hyst_steps)    
    figure(100)
    for i in range(2):
        plot(vrefs,abs(hyst_steps[:,i]-vrefs),'o-')
    legend(['Vtu_sim','Vtl_sim'])   

    figure(101)
    plot(vrefs,(abs(hyst_steps[:,0]-vrefs)-abs(hyst_steps[:,1]-vrefs)))

    figure(102)
    for i in range(2):
        plot(vrefs,hyst_steps[:,i],'o-')
    plot(vrefs,vrefs,'o-')
    xlim([vrefs[0],vrefs[-1]])
    ylim([1.0,2.5])
    #savefig('/tmp/c1/{0}k-{1}k.png'.format(R1/1000,R2/1000))
    legend(['Vtu_sim','Vtl_sim', 'vref'])


    #for i in range(2,4):
    #    plot(vrefs,hyst_steps[:,i])
    #plot(vrefs,vrefs)

    show()
    pass
