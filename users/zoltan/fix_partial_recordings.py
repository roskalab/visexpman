from visexpman.engine import jobhandler1
import visexpA.engine.configuration,os,shutil
from visexpA.engine.datahandlers import importers,hdf5io,matlabfile
from visexpman.engine.generic import file,utils
config=[
    
    ['fragment_xy_master_0_0_0.0_MovingGratingFiona3x_1497540710_0.mat',
    'fragment_xy_master_0_0_0.0_MovingGratingFiona3x_1497541243_0.mat',
    'fragment_xy_master_0_0_0.0_MovingGratingFiona3x_1497539210_0.mat',
    'fragment_xy_master_0_0_-4.0_MovingGratingFiona3x_1497542722_0.mat',
    'fragment_xy_master_0_0_-115.7_MovingGratingFiona3x_1496068777_0.hdf5'],
    ['fragment_xy_master_0_0_-8.3_NaturalMovieSv1_1497543974_0.mat',
    'fragment_xy_master_0_0_-1000.0_NaturalMovieSv1_1497270296_0.hdf5']]

class FixPartial(object):
    def __init__(self):
        self.src='/mnt/datafast/experiment_data/fiona'
        self.dst='/mnt/datafast/debug/fiona'
        self.mdrive_folder='/mnt/mdrive/invivo/rc/raw/fiona'
        
    def copy(self):
        mdrivefiles=file.find_files_and_folders(self.mdrive_folder)[1]
        for fns in config:
            for fn in fns:
                if 'hdf5' in fn:
                    src=[f for f in mdrivefiles if os.path.basename(f) ==fn]
                    shutil.copy(src[0], self.dst)
                else:
                    shutil.copy(os.path.join(self.src,fn), self.dst)
                
    def clone_hdf5files(self):
        for fns in config:
            for f in fns[:-1]:
                donor=os.path.join(self.dst, fns[-1])
                cloned=os.path.join(self.dst, f.replace('.mat', '.hdf5'))
                donor_id='_'.join(os.path.splitext(fns[-1])[0].split('_')[-3:])
                target_id='_'.join(os.path.splitext(f)[0].split('_')[-3:])
                if donor!=cloned:
                    shutil.copy(donor, cloned)
                    hh=hdf5io.Hdf5io(cloned,filelocking=False)
                    getattr(hh.h5f.root,donor_id)._f_move(newname=target_id)
                    hh.close()
                    
    def process(self):
        aconfigname = 'Config'
        user ='daniel'
        analysis_config = utils.fetch_classes('visexpA.users.'+user, classname=aconfigname, required_ancestors=visexpA.engine.configuration.Config,direct=False)[0][1]()
        for fns in config:
            for f in fns[:-1]:
                try:
                    filename=os.path.join(self.dst,f).replace('.mat', '.hdf5')
                    mes_extractor = importers.MESExtractor(filename, config = analysis_config, close_file=False)
                    data_class, stimulus_class,anal_class_name, mes_name = mes_extractor.parse(fragment_check = True, force_recreate = True)
                    mes_extractor.hdfhandler.close()
                except:
                    if hasattr(mes_extractor,'sync_signal'):
                        mes_extractor.hdfhandler.save('sync_signal',overwrite=True)
                    mes_extractor.hdfhandler.close()
                jobhandler1.hdf52mat(filename, analysis_config)
                    
                
                
if __name__=='__main__':
    fp=FixPartial()
    print 'copy'
    fp.copy()
    print 'clone hdf5'
    fp.clone_hdf5files()
    print 'mesextractor'
    fp.process()
    print 'Done'
    
