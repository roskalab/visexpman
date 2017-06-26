import os,hdf5io, tables,unittest,sys,shutil,time,traceback,logging
from visexpman.engine.generic import fileop,utils
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.analysis import aod

class AoJobhandler(object):
    def __init__(self, experiment_data_path, backup_path, logpath, database_filename):
        self.db=DatafileDatabase(database_filename)
        self.experiment_data_path=experiment_data_path
        self.backup_path=backup_path
        self.mesfile_minimum_age=10
        self.ignore_errors=False
        self.logfile = os.path.join(logpath, 'jobhandler_{0}.txt'.format(utils.timestamp2ymdhm(time.time()).replace(':','').replace(' ','').replace('-','')))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
level=logging.INFO)
        print 'todo: check free space'
        
    
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
        hdf5files=fileop.find_files_and_folders(self.experiment_data_path,extension='hdf5')[1]
        mesfiles=[f for f in fileop.find_files_and_folders(self.experiment_data_path,extension='mat')[1] if self.mesfile_ready(f)]
        files2process=[f for f in hdf5files if not self.db.exists(f) and f.replace('.hdf5', '.mat') in mesfiles]
        now=time.time()
        for f in files2process:
            p=experiment_data.parse_recording_filename(f)
            if self.db.add(filename=p['file'], measurement_ready_time=now):
                self.db.update(filename=p['file'], measurement_ready=True)
        pass
        
    def fetch_job(self):
        query='(measurement_ready==1)'
        if not self.ignore_errors:
            query+='& (error==0)'
        active_jobs=[[r['filename'], r['backed_up'], r['mesextractor_ready'], r['converted']] for r in self.db.hdf5.root.datafiles.where( query)]
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
            fn, bu, mesextr, converted=[j for j in active_jobs if j[0]==filenames[-1]][0]
            next_job=[fn]
            if not mesextr:
                next_job.append('mesextractor')
            elif not converted:
                next_job.append('convert')
        #Get full filename
        hdf5files=fileop.find_files_and_folders(self.experiment_data_path,extension='hdf5')[1]
        fullpath=[f for f in hdf5files if os.path.basename(f)==next_job[0]][0]
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
            self.db.update(**kwargs)
        except:
            self.db.update(filename=next_job[0], error=True, error_message=next_job[1])
            self.printl(traceback.format_exc(),'error')

    def backup(self, filename):
        mesfilename=filename.replace('.hdf5', '.mat')
        dst=os.path.join(self.backup_path, *mesfilename.split(os.sep)[-3:-1])
        if not os.path.exists(dst):
            os.makedirs(dst)
        shutil.copy(mesfilename, dst)
        self.printl('{0} copied to {1}'.format(mesfilename, dst))
        #Check hdf5 file
        if not os.path.exists(os.path.join(dst, os.path.basename(filename))):
            raise RuntimeError('{0} not backed up'.format(filename))
        
    def mesextractor(self,filename):
        aod.AOData(filename)
        

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
        nfiles=10
        stimname='TestStim'
        now=time.time()
        for i in range(nfiles):
            idn=experiment_data.get_id(now-i)
            fn=os.path.join(experiment_data_path, '_'.join(['data', stimname, idn])+'.hdf5')
            fileop.write_text_file(fn,10*'a')
            if i%2==0:
                fileop.write_text_file(fn.replace('.hdf5', '.mat'),100*'a')
        backup_path=os.path.join(root, 'bu')
        os.mkdir(backup_path)
        logpath='/tmp'
        jh=AoJobhandler(experiment_data_path,backup_path, logpath,dbfilename)
        jh.add_jobs()
        self.assertEqual(len(jh.db.hdf5.root.datafiles), 0)
        time.sleep(jh.mesfile_minimum_age+0.1)
        jh.add_jobs()
        self.assertEqual(len(jh.db.hdf5.root.datafiles), nfiles/2)
        jh.add_jobs()
        for i in range(10):
            jh.fetch_job()
        pass
        pass
            
            
        
    


if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        pass
