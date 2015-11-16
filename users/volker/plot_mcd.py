import numpy,os
from pylab import *
from visexpman.engine.vision_experiment.elphys_viewer import mcd2raw,read_raw
import scipy.io

################ Change parameters here ##################
filenames=['e:\\ME64 Data\\test1\\mm0042.mcd','e:\\ME64 Data\\test1\\mm0037.mcd']
nsamples2display=1e6
channel2display=[66,77]
enable_save2mat=True#Or False
################ End of parameters ##################


for i in range(len(filenames)):
    fn=filenames[i]
    rawfile=mcd2raw(fn, nchannels=62,outfolder='c:\\temp',header_separately=True)
    t,analog,digital,elphys,channel_names,sample_rate,ad_scaling=read_raw(rawfile)
    if enable_save2mat:
        channel_numbers=[int(cn.split('_')[1]) for cn in channel_names[2:]]
        data2save={'time':t,'analog':analog, 'digital': digital, 'elphys': elphys, 'channel_names':channel_names, 'sample_rate' :sample_rate, 'ad_scaling':ad_scaling,'channel_numbers':channel_numbers}
        

        scipy.io.savemat(fn.replace('.mcd','.mat'),data2save, oned_as = 'row', long_field_names=True,do_compression=True)
    os.remove(rawfile)
    os.remove(rawfile.replace('.raw','h.raw'))
    if 0:
        for rng in range(60):
            clf()
            plot(elphys[rng, 1e6:1.1e6][::4])
            plot(digital[1e6:1.1e6][::4]*1000-1000)
            savefig('c:\\temp\\{0}.png'.format(rng))
        import pdb
        pdb.set_trace()
    t=t[:nsamples2display]
    
    for ch in channel2display:
        digitalp=(digital[:nsamples2display]&2)*0.5#bit 1 is the sync channel
        channel=[str(ch) in chn  for chn in channel_names]
        selected_electrode=elphys[channel.index(True)-2][:nsamples2display]
        analogp=analog[:nsamples2display]
        analogp-=analogp.mean()
        analogp*=selected_electrode.max()/analogp.max()
        figure(len(channel2display)*i+channel2display.index(ch))
        title('{0}, channel {1}'.format(fn,ch))
        plot(t,selected_electrode);plot(t,analogp);plot(t,digitalp*selected_electrode.max())
show()
