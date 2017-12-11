import os,tables,unittest,sys,shutil,time,traceback,logging,getpass
from visexpman.engine.generic import fileop,utils,introspect
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.analysis import aod

class AoJobhandler(object):
    def __init__(self, experiment_data_path, backup_path, logpath, database_filename):
        self.db=DatafileDatabase(database_filename)
        self.experiment_data_path=experiment_data_path
        self.backup_path=backup_path
        self.mesfile_minimum_age=60
        self.fileepoch=utils.datestring2timestamp('26/07/2017',format="%d/%m/%Y")
        self.logfile = os.path.join(logpath, 'jobhandler_{0}.txt'.format(utils.timestamp2ymdhm(time.time()).replace(':','').replace(' ','').replace('-','')))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
level=logging.INFO)
        self.minimum_free_space=15e9/10
        fs=fileop.free_space(experiment_data_path)
        print '='*80#Indicate the beginning of jobhandler prints on console
        self.printl('{0} GB free space is on {1}'.format(int(fs/2**30), experiment_data_path))
        if fs<self.minimum_free_space:
            raise RuntimeError('Less than {1} GB space on {0}'.format(experiment_data_path,int(self.minimum_free_space/2**30)))
        if fileop.free_space(backup_path)<self.minimum_free_space:
            raise RuntimeError('Less than {1} GB space on {0}'.format(experiment_data_path, int(self.minimum_free_space/2**30)))
        import visexpman
        self.printl(os.path.abspath(visexpman.__file__))
        self.printl('Current user is {0}'.format(getpass.getuser()))
        self.printl(sys.argv)
        self.printl(utils.module_versions(utils.imported_modules()[0])[0])
    
    def printl(self,msg,loglevel='info'):
        print msg
        getattr(logging,loglevel)(msg)
        
    def mesfile_ready(self,filename):
        res=False
        fileop.wait4file_ready(filename)
        if time.time()-os.path.getctime(filename)>self.mesfile_minimum_age:
            res=True
        return res
        
    def add_jobs(self):
        try:
            allfiles=[f for f in fileop.find_files_and_folders(self.experiment_data_path)[1] if os.path.getctime(f)>self.fileepoch]
        except OSError:
            return
        hdf5files=[f for f in allfiles if os.path.splitext(f)[1]=='.hdf5']
        mesfiles=[f for f in allfiles if os.path.splitext(f)[1]=='.mat' and self.mesfile_ready(f)]
        files2process=[f for f in hdf5files if not self.db.exists(f) and f.replace('.hdf5', '.mat') in mesfiles]
        now=time.time()
        for f in files2process:
            p=experiment_data.parse_recording_filename(f)
            if self.db.add(filename=p['file'], measurement_ready_time=now):
                self.db.update(filename=p['file'], measurement_ready=True)
                self.printl('{0} added'.format(p['file']))
        pass
        
    def fetch_job(self):
        query='(measurement_ready==1)&((backed_up==0) | (mesextractor_ready==0) | (converted==0) | (copied==0))'
        self.rerun_failed=not os.path.exists(os.path.join(self.experiment_data_path, 'rerun_failed.txt'))
        if self.rerun_failed:
            query+='& (error==0)'
        active_jobs=[[r['filename'], r['backed_up'], r['mesextractor_ready'], r['converted'], r['copied']] for r in self.db.hdf5.root.datafiles.where( query)]
        if len(active_jobs)==0:
            return
        #Not backed up files has the highest priority
        not_backed_up=[j[0] for j in active_jobs if not j[1]]
        not_backed_up.sort()
        if len(not_backed_up)>0:
            next_job=[not_backed_up[0], 'backup']#Select oldest, not backed up
        else:
            #Find the latest unprocessed
            filenames=[j[0] for j in active_jobs]
            filenames.sort()
            fn, bu, mesextr, converted, copied=[j for j in active_jobs if j[0]==filenames[-1]][0]
            next_job=[fn]
            if not mesextr:
                next_job.append('mesextractor')
            elif not converted:
                next_job.append('convert')
            elif not copied:
                next_job.append('copy')
        #Get full filename
        hdf5files=fileop.find_files_and_folders(self.experiment_data_path,extension='hdf5')[1]
        fullpath=[f for f in hdf5files if os.path.basename(f)==next_job[0]]
        if len(fullpath)==0:
            return
        else:
            fullpath=fullpath[0]
        try:            
            getattr(self, next_job[1])(fullpath)
            now=time.time()
            kwargs={'filename':next_job[0]}
            if  next_job[1]=='backup':
                kwargs['backed_up']=True
                kwargs['backup_time']=now
            elif next_job[1]=='mesextractor':
                kwargs['mesextractor_ready']=True
                kwargs['mesextractor_time']=now
            elif next_job[1]=='convert':
                kwargs['converted']=True
                kwargs['converted_time']=now
            elif next_job[1]=='copy':
                kwargs['copied']=True
                kwargs['copied_time']=now
            self.db.update(**kwargs)
            self.printl('{0}/{1} job done'.format(*next_job))
        except:
            self.db.update(filename=next_job[0], error=True, error_message=next_job[1])
            self.printl(traceback.format_exc(),'error')

    def backup(self, filename):
        mesfilename=filename.replace('.hdf5', '.mat')
        dst=os.path.join(self.backup_path, 'raw', *mesfilename.split(os.sep)[-3:-1])
        if not os.path.exists(dst):
            os.makedirs(dst)
        shutil.copy(mesfilename, dst)
        self.printl('{0} copied to {1}'.format(mesfilename, dst))
        #Check hdf5 file
        if not os.path.exists(os.path.join(dst, os.path.basename(filename))):
            raise RuntimeError('{0} not backed up'.format(filename))
        
    def mesextractor(self,filename):
        #Check if input files are valid
        files=[filename, filename.replace('.hdf5', '.mat')]
        for f in files:
            if os.path.getsize(f)<1e6:
                raise IOError('{0} is corrupt'.format(f))
        if introspect.is_test_running(): return
        a=aod.AOData(filename)
        a.crop_timg()
        a.close()
        
    def convert(self,filename):
        experiment_data.hdf52mat(filename)
    
    def copy(self,filename):
        dst=os.path.join(self.backup_path, 'processed', *filename.split(os.sep)[-3:-1])
        if not os.path.exists(dst):
            os.makedirs(dst)
        files2copy=[filename, experiment_data.add_mat_tag(filename)]
        for f in files2copy:
            shutil.copy(f, dst) 
            
    def close(self):
        self.printl('Jobhandler closed')
        self.db.close()
        

class Datafile(tables.IsDescription):
    user = tables.StringCol(16)
    recording_start_time = tables.Float64Col()
    measurement_ready = tables.BoolCol()
    measurement_ready_time = tables.Float64Col()
    backed_up = tables.BoolCol()
    backup_time = tables.Float64Col()
    mesextractor_ready= tables.BoolCol()
    mesextractor_time = tables.Float64Col()
    converted = tables.BoolCol()
    converted_time = tables.Float64Col()
    copied = tables.BoolCol()
    copied_time = tables.Float64Col()
    error = tables.BoolCol()
    error_message=tables.StringCol(256)
    filename=tables.StringCol(256)
    
class DatafileDatabase(object):
    def __init__(self, filename):
        self.filename=filename
        self.hdf5 = tables.open_file(self.filename, mode = "a", title = os.path.splitext(os.path.basename(filename))[0])
        if not hasattr(self.hdf5.root, 'datafiles'):
            self.table=self.hdf5.create_table(self.hdf5.root, 'datafiles', Datafile)            
            
    def add(self, **kwargs):
        if self.exists(kwargs['filename']):
            return False
        item = self.hdf5.root.datafiles.row
        for f,v in Datafile.columns.items():
            if kwargs.has_key(f):
                item[f]=kwargs[f]
            else:
                item[f]=Datafile.columns[f].dflt
        item.append()
        self.hdf5.flush()
        return True
        
    def update(self, **kwargs):
        if kwargs.has_key('filename'):
            keyname='filename'
            key='"{0}"'.format(kwargs['filename'])
        rowsfound=len([1 for row in self.hdf5.root.datafiles.where('{0}=={1}'.format(keyname, key))])
        if rowsfound==0:
            pass
        elif rowsfound > 1:
            raise RuntimeError('{0} id is not unique'.format(kwargs['id']))
        else:
            for row in self.hdf5.root.datafiles.where('{0}=={1}'.format(keyname, key)):
                for f,v in kwargs.items():
                    row[f]=v
                row.update()
            self.hdf5.flush()
        
    def exists(self, filename):
        return len([1 for item in self.hdf5.root.datafiles.where('filename==\"{0}\"'.format(filename))])==1
    
    def export(self):
        pass
        
    def close(self):
        self.hdf5.close()
            


class TestJobhandler(unittest.TestCase):
    def test_01_new_jobs(self):
        '''
        Test generates a file tree, with empty files but file names are valid.
        Later additional files are generated.
        Finally content of database file tested
        '''
        import tempfile
        root=os.path.join(tempfile.gettempdir(),'test')
        if os.path.exists(root):
            shutil.rmtree(root)
        dbfilename=os.path.join(root, 'jobs.hdf5')
        experiment_data_path=os.path.join(root, 'data', 'user', '20170101')
        os.makedirs(experiment_data_path)
        backup_path=os.path.join(root, 'bu')
        budst=os.path.join(backup_path,'raw', 'user', '20170101')
        os.makedirs(backup_path)
        os.makedirs(budst)
        nfiles=30
        stimname='TestStim'
        now=time.time()
        import hdf5io, numpy, scipy.io
        validfiles=[]
        for i in range(nfiles):
            idn=experiment_data.get_id(now-i*0.1)
            fn=os.path.join(experiment_data_path, '_'.join(['data', stimname, idn])+'.hdf5')
            
            h=hdf5io.Hdf5io(fn)
            h.data=numpy.random.random((1000,100,10))
            h.save('data')
            h.close()
            if i%2==0:
                data={'data':numpy.random.random((1000,100,10))}
                validfiles.append(fn)
                scipy.io.savemat(fn.replace('.hdf5', '.mat'), data)
                shutil.copy(fn, budst)#Mimic that hdf5 files already backed up
            
        
        logpath='/tmp'
        jh=AoJobhandler(experiment_data_path,backup_path, logpath,dbfilename)
        jh.add_jobs()
        self.assertTrue(len(jh.db.hdf5.root.datafiles)< nfiles/2)
        time.sleep(jh.mesfile_minimum_age+0.1)
        jh.add_jobs()
        self.assertEqual(len(jh.db.hdf5.root.datafiles), nfiles/2)
        jh.add_jobs()
        for i in range(nfiles/2*4+2):
            jh.add_jobs()
            jh.fetch_job()
        jh.close()
        log=fileop.read_text_file(jh.logfile)
        self.assertFalse('error' in log)
        lines=log.split('\n')
        for vf in validfiles:
            lines2vf=[l for l in lines if os.path.basename(vf) in l]
            jobstates=['copy', 'convert', 'mesextractor', 'backup']
            ct=0
            for kw in jobstates:
                ct+=len([1 for l in lines2vf if kw+' job done' in l])
            self.assertEqual(ct, len(jobstates))
    
if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        #/mnt/datafast/debug/ao_jobhandler_test /mnt/databig/ao /mnt/datafast/log_ao /mnt/datafast/context_ao/jobhandler.hdf5
        jh=AoJobhandler(*sys.argv[1:])
        while True:
            if utils.enter_hit(): break
            try:
                jh.add_jobs()
                jh.fetch_job()
            except:
                import traceback
                logging.error(traceback.format_exc())
            time.sleep(0.1)
        jh.close()
