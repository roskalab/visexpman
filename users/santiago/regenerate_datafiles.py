import os,numpy,hdf5io,zipfile
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import utils,fileop
from visexpman.users.zoltan import legacy

def timing2csv(filename):
        h = experiment_data.CaImagingData(filename)
        output_folder=os.path.join(os.path.dirname(filename), 'output', os.path.basename(filename))
        from PIL import Image
        h.load('raw_data')
        h.load('parameters')
        #Fn: 1_0__rect_64.00_64.00_0.00_0.00_2.00_top_0000000.png
        for framei in range(h.raw_data.shape[0]):
            for chi in range(h.raw_data.shape[1]):
                base=os.path.splitext(os.path.basename(h.parameters['imaging_filename']))[0]
                base='_'.join(base.split('_')[:-1])+'_'+h.parameters['channels'][chi]+'_{0:0=5}'.format(framei)
                fn=os.path.join(output_folder, base+'.png')
                Image.fromarray(h.raw_data[framei,chi]).rotate(90).save(fn)
        h.load('tstim')
        h.load('timg')
        if 'Led2' in filename:
            h.load('generated_data')
            channels = utils.array2object(h.generated_data)#,len(utils.array2object(h.generated_data))
            real_events=h.tstim[numpy.where(numpy.diff(h.tstim)>2e-3)[0]]
            real_events=numpy.append(real_events, h.tstim[-1])
            tstim_sep={}
            for ch in ['stim','led']:
                tstim_sep[ch]=real_events[[i for i in range(len(channels)) if channels[i]==ch or channels[i]=='both']]
        h.close()
        if 'Led2' in filename:
            txtlines1=','.join(map(str,numpy.round(tstim_sep['stim'],3)))
            txtlines2=','.join(map(str,numpy.round(tstim_sep['led'],3)))
        else:
            txtlines2=','.join(map(str,numpy.round(h.tstim,3)))
        txtlines3 =','.join(map(str,numpy.round(h.timg,3)))
        csvfn3=os.path.join(output_folder, os.path.basename(filename).replace('.hdf5', '_img.csv'))
        csvfn2=os.path.join(output_folder, os.path.basename(filename).replace('.hdf5', '_lgnled.csv'))
        csvfn1=os.path.join(output_folder, os.path.basename(filename).replace('.hdf5', '_stim.csv'))
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if 'Led2' in filename:
            fileop.write_text_file(csvfn1, txtlines1)
        fileop.write_text_file(csvfn2, txtlines2)
        fileop.write_text_file(csvfn3, txtlines3)
        
if __name__=='__main__':
    folder='/data/santiago-setup/debug/rescale'
    outfolder='/data/santiago-setup/debug/output'
    for fn in os.listdir(folder):
        if os.path.splitext(fn)[1]=='.hdf5':
            print fn
            hdf5fn=os.path.join(folder, fn)
            pars=hdf5io.read_item(hdf5fn, 'parameters')
            zipf=hdf5fn.replace('.hdf5', '.zip')
            zip_ref = zipfile.ZipFile(zipf, 'r')
            outf=os.path.join(outfolder, os.path.splitext(os.path.basename(zipf))[0].split('_')[-1])
            zip_ref.extractall(outf)
            zip_ref.close()
            fnout=legacy.merge_ca_data(outf, **pars)
            h = experiment_data.CaImagingData(fnout)
            h.sync2time()
            h.close()
            timing2csv(fnout)
