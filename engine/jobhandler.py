import os,hdf5io, tables,unittest,sys,shutil,time
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment_data

class AoJobhandler(object):
    def __init__(self, experiment_data_path,database_filename):
        self.db=DatafileDatabase(database_filename)
        self.experiment_data_path=experiment_data_path
        self.mesfile_minimum_age=10
        print 'todo: check free space'
        
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
            self.db.add(id=p['id'], filename=p['file'], measurement_ready_time=now)
        pass
        

class Datafile(tables.IsDescription):
    id = tables.UInt32Col()
    user = tables.StringCol(16)
    recording_start_time = tables.Float64Col()
    is_measurement_ready = tables.BoolCol()
    measurement_ready_time = tables.Float64Col()
    is_backed_up = tables.BoolCol()
    backup_time = tables.Float64Col()
    is_mesextractor = tables.BoolCol()
    mesextractor_time = tables.Float64Col()
    is_converted = tables.BoolCol()
    converted_time = tables.Float64Col()
    is_error = tables.BoolCol()
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
            raise RuntimeError('{0} already exists'.format(kwargs['filename']))
        item = self.hdf5.root.datafiles.row
        for f,v in Datafile.columns.items():
            if kwargs.has_key(f):
                item[f]=kwargs[f]
            else:
                item[f]=Datafile.columns[f].dflt
        item.append()
        self.hdf5.flush()
        
    def update(self, **kwargs):
        pass
        
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
        experiment_data_path=os.path.join(root, 'data')
        os.makedirs(experiment_data_path)
        nfiles=10
        stimname='TestStim'
        now=time.time()
        for i in range(nfiles):
            fn=os.path.join(experiment_data_path, '_'.join(['data', stimname, experiment_data.get_id(now-i)])+'.hdf5')
            fileop.write_text_file(fn,10*'a')
            if i%2==0:
                fileop.write_text_file(fn.replace('.hdf5', '.mat'),100*'a')
        jh=AoJobhandler(experiment_data_path,dbfilename)
        jh.add_jobs()
        self.assertEqual(len(jh.db.hdf5.root.datafiles), 0)
        time.sleep(jh.mesfile_minimum_age+0.1)
        jh.add_jobs()
        self.assertEqual(len(jh.db.hdf5.root.datafiles), nfiles/2)
        pass
        pass
            
            
        
    


if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        pass
