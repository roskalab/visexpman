#TODO: old test animal from prev day and new on this day: why is the old one selected
import tables,os,unittest,time,zmq,logging,sys,threading,cPickle as pickle,numpy,traceback,pdb,shutil,Queue
import scipy.io,multiprocessing,stat,subprocess,io
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import utils
try:
    from visexpman.engine.generic import file as fileop
except ImportError:
    from visexpman.engine.generic import fileop
import visexpman.engine.vision_experiment.configuration
import visexpA.engine.configuration
from visexpA.engine.datahandlers import importers,hdf5io,matlabfile
from visexpman.engine import backup_manager

dbfilelock=threading.Lock()
THREAD=True
GUI_CONN=not False
#TODO: P2:backup animal files, check backup status, check files (mouse file too) on u:\data,

def chmod(f):
    try:
        os.chmod(f,stat.S_IRWXG|stat.S_IRWXO|stat.S_IRWXU)
    except:
        logging.error(traceback.format_exc())

class Jobhandler(object):
    def __init__(self,user,config_class):
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct=False)[0][1]()
        aconfigname = 'Config'
        self.analysis_config = utils.fetch_classes('visexpA.users.'+user, classname=aconfigname, required_ancestors=visexpA.engine.configuration.Config,direct=False)[0][1]()
        self.logfile = os.path.join(self.config.LOG_PATH, 'jobhandler_{0}.txt'.format(utils.timestamp2ymdhm(time.time()).replace(':','').replace(' ','').replace('-','')))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
        self.jrq=Queue.Queue()
        self.jr=JobReceiver(self.config,self.jrq)
        if THREAD:
            self.jr.start()
        self.queues = {}
        self.queues['gui'] = {}
        self.queues['gui']['out'] = Queue.Queue()
        self.queues['gui']['in'] = Queue.Queue()
        if GUI_CONN:
            self.connections = {}
            self.connections['gui'] = network_interface.start_client(self.config, 'ANALYSIS', 'GUI_ANALYSIS', self.queues['gui']['in'], self.queues['gui']['out'])
        self.printl('Jobhandler started')
        import getpass
        self.printl('Current user is {0}'.format(getpass.getuser()))
        logging.info(sys.argv)
        logging.info(utils.module_versions(utils.imported_modules()[0])[0])
        self._check_freespace()
        self.issued_jobs=[]
                    
    def printl(self,msg,loglevel='info'):
        getattr(logging, loglevel)(msg)
        print msg
        if loglevel =='error' or loglevel=='warning':
            self.queues['gui']['out'].put('SOCnotifyEOC{0} {1}EOP'.format(loglevel,msg))
        else:
            self.queues['gui']['out'].put(msg)

    def _check_freespace(self):
        #Check free space on databig and tape
        free_space_on_datafast = fileop.free_space(self.config.EXPERIMENT_DATA_PATH)/(1024**3)
        free_space_on_databig = fileop.free_space(self.config.DATABIG_PATH)/(1024**3)
        free_space_on_m = fileop.free_space('/mnt/mdrive')/(1024**3)
        try:
            free_space_on_tape = fileop.free_space(self.config.TAPE_PATH)/(1024**3)
        except:
            free_space_on_tape = 'Not available'
        if free_space_on_databig < 50:
            raise RuntimeError('Critically low free space on databig: {0} GB'.format(free_space_on_databig))
            sys.exit(0)
        if free_space_on_datafast < 50:
            raise RuntimeError('Critically low free space on datafast: {0} GB'.format(free_space_on_datafast))
            sys.exit(0)
        self.printl('Free space on datafast (v:\\, limit is 50 GB) {2} GB, on databig (u:\\) {0} GB, on m drive: {3} GB and tape {1} GB'.format(free_space_on_databig, free_space_on_tape, free_space_on_datafast,free_space_on_m))

    def run(self):
        while True:
            try:
                if not THREAD:
                    self.jr.check4newjob()
                nextfunction, nextpars=self.nextjob()
                if nextfunction != None:
                    self.process_job(nextfunction, nextpars)
            except:
                self.printl(traceback.format_exc(),'error')
                #pdb.set_trace()
            if utils.enter_hit(): break
            time.sleep(0.2)
            if int(time.time())%20==0:
                logging.debug('alive')
                time.sleep(1)
        self.printl('Jobhandler is shutting down')
        self.queues['gui']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        if THREAD:
            self.jrq.put('terminate')
            self.jr.join()
            print 'thread terminated'
        self.connections['gui'].wait()
        print 'done'
        
    def process_job(self,nextfunction, nextpars):
        getattr(self,nextfunction)(*nextpars)
        
    def get_active_animal(self):
        afiles= fileop.find_files_and_folders(self.config.ANIMAL_FOLDER)[1]
        now=time.time()
        #Exclude files which have not been modified in the last 30 days
        recent_files=[a for a in afiles if now-os.stat(a).st_mtime<30*86400 and a[-5:]=='.hdf5']
        if len(recent_files)==0:
            return
        #Read status info from files
        active_animals = {}
        for f in recent_files:
            last_job_added,unprocessed_jobs=database_status(f)
            if unprocessed_jobs>0:
                active_animals[f]=last_job_added
        if active_animals=={}:
            #No active files found
            return
        current_animal=[k for k, v in active_animals.items() if v ==max(active_animals.values())][0]
        logging.debug('Active animals: {0}'.format(active_animals))
        return current_animal
                
    def nextjob(self):
        '''
        Selects next job from database:
        1) Ignore files which mtime was 30 days ago
        2) Find animals which have unprocessed recordings
        3) From these find out which has the most recent recording
        4) Open this animal file and find out the oldest unprocessed file
        5) This animal file is considered as current, cell detection and conversion is done
        
        '''
        ca=self.get_active_animal()
        if ca is None:
            return None,None
        else:
            self.current_animal=ca
        logging.debug('Current animal: {0}'.format(self.current_animal))
        dbfilelock.acquire()
        try:
            h=tables.open_file(self.current_animal, mode = "r")
            recent_scan_regions=dict([(row['recording_started'],row['region']) for row in h.root.datafiles.where('(~is_analyzed | ~is_mesextractor | ~is_converted) & is_measurement_ready')])
            current_scan_region=recent_scan_regions[max(recent_scan_regions.keys())]
            allfiles=fileop.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH)[1]
            jobs={}
            for row in h.root.datafiles.where('(~is_converted | ~is_analyzed | ~is_mesextractor) & is_measurement_ready & ~is_error'):
                if not row['is_mesextractor']:
                    weight=1
                    offset=0
                elif row['is_mesextractor'] and not row['is_analyzed']:
                    weight=1
                    offset=-0.1
                elif row['is_mesextractor'] and row['is_analyzed']:
                    weight=0
                    offset=0
#                if row['region']==current_scan_region:#Increase priority for current scan regions
#                    weight+=2
                    
                priority=10**(numpy.ceil(numpy.log10(row['recording_started']))+1)*weight+row['recording_started']+offset
                filename=[f for f in allfiles if os.path.basename(f)==row['filename']]
                if filename==[]:
                    self.printl('{0} does not exists'.format(row['filename']))
                    continue
                else:
                    filename=filename[0]
                next_params=[filename]
                if not row['is_mesextractor'] and not row['is_analyzed'] and not row['is_converted']:
                    nextfunction='mesextractor'
                elif row['is_mesextractor'] and not row['is_analyzed'] and not row['is_converted']:
                    nextfunction='analyze'
                    next_params.extend([row['stimulus'],row['user']])
                elif row['is_mesextractor'] and row['is_analyzed'] and not row['is_converted']:
                    nextfunction='convert_and_copy'
                    next_params.extend([row['user'],row['region_add_date'],row['animal_id']])
                jobs[priority]=[nextfunction,next_params]
        except:
            self.printl(traceback.format_exc(),'error')
        finally:
            h.close()
            dbfilelock.release() 
        if jobs=={}:
            return None,None
        job_order=jobs.keys()
        job_order.sort()
        job_order.reverse()
        job_selected=False
        for jp in job_order:
            if jobs[jp] not in self.issued_jobs:
                nextfunction=jobs[jp][0]
                nextpars=jobs[jp][1]
                self.printl('Next {0}({1})'.format(nextfunction,nextpars))
                self.issued_jobs.append([nextfunction, nextpars])
                job_selected=True
                break
        if job_selected:
            return  nextfunction, nextpars
        else:
            logging.error('Job cannot be selected. Latest datafile may have some errors. Current animal is {0}.'.format(self.current_animal))
            if 0:
                self.printl('Job cannot be selected. Latest datafile may have some errors. Current animal is {0}. Is that correct?'.format(self.current_animal))
                pdb.set_trace()
            return None,None
        
    def mesextractor(self,filename):
        if not os.path.exists(filename):
            error_msg='hdf5 file not found'
        elif not os.path.exists(filename.replace('.hdf5','.mat')):
            error_msg='mat file not found'
        elif os.path.getsize(filename)<1e6:
           error_msg='hdf5 file corrupt'
        elif os.path.getsize(filename.replace('.hdf5','.mat'))<5e6:
            error_msg= 'mat file corrupt'
        elif not os.access(filename,os.R_OK|os.W_OK):
            error_msg= 'file acces error'
        elif os.path.exists(filename.replace('.hdf5', '_1.mat')):
            error_msg= 'Unknown MES format'
        else:
            error_msg=''
            file_info = os.stat(filename)
            logging.info(str(file_info))
            mes_extractor = importers.MESExtractor(filename, config = self.analysis_config)
            data_class, stimulus_class,anal_class_name, mes_name = mes_extractor.parse(fragment_check = True, force_recreate = False)
            extract_prepost_scan(mes_extractor.hdfhandler)
            mes_extractor.hdfhandler.close()
            #fileop.set_file_dates(filename, file_info)
            time.sleep(0.1)
            logging.info(os.stat(filename))
            self.printl('MESextractor done')
        dbfilelock.acquire()
        try:
            db=DatafileDatabase(self.current_animal)
            if error_msg=='':
                db.update(filename=os.path.basename(filename), is_mesextractor=True, mesextractor_time=time.time())
            else:
                db.update(filename=os.path.basename(filename), error_message=error_msg, is_error=True)
                raise RuntimeError(filename+' '+error_msg)
        except:
            self.printl(traceback.format_exc(),'error')
        finally:
            db.close()
            dbfilelock.release()

    def analyze(self,filename,stimulus,user):
        if len([sn for sn in self.config.ONLINE_ANALYSIS_STIMS if sn.lower() in stimulus.lower()])>0:
            create = ['roi_curves','soma_rois_manual_info']
            export = ['roi_curves'] 
            file_info = os.stat(filename)
            logging.info(str(file_info))
            self.analysis_config.ROI['parallel']='mp-wiener' if user == 'fiona' else 'mp'
            h = hdf5io.iopen(filename,self.analysis_config)
            if h is not None:
                for c in create:
                    self.printl('create_'+c)
                    h.perform_create_and_save(c,overwrite=True,force=True,path=h.h5fpath)
                for e in export:
                    self.printl('export_'+e)
                    getattr(h,'export_'+e)()
                h.close()
                #fileop.set_file_dates(filename, file_info)
                time.sleep(0.1)
                logging.info(os.stat(filename))
                pngfolder=os.path.join(os.path.dirname(filename),'output', os.path.basename(filename))
                if os.path.exists(pngfolder):#Make png folder accessible for everybody
                    res=subprocess.call('chmod 777 {0} -R'.format(pngfolder),shell=True)
                    logging.info(res)
                self.printl('Analysis done')
        else:
            self.printl('Online analysis is not available')
        dbfilelock.acquire()
        try:
            db=DatafileDatabase(self.current_animal)
            db.update(filename=os.path.basename(filename), is_analyzed=True, analyzed_time=time.time())
        except:
            self.printl(traceback.format_exc(),'error')
        finally:
            db.close()
            dbfilelock.release()
        
    def convert_and_copy(self,filename,user,region_add_date,animal_id):
        '''
        Converts hdf5 file to mat, copies hdf5, mat and png files to u:\data\user\...
        For certain users conversion is not performed.
        
        Copy:
            processed hdf5 file
            converted mat file
            png files
            
        Finally: backup status is checked
        '''
        if user!='fiona':
            files2copy=[filename]
        else:
            files2copy=[]
        if user!='daniel':
            h=hdf5io.Hdf5io(filename,config=self.analysis_config)
            ignore_nodes=['hashes']
            rootnodes=[v for v in dir(h.h5f.root) if v[0]!='_' and v not in ignore_nodes]
            mat_data={}
            for rn in rootnodes:
                if os.path.basename(filename).split('_')[-2] in rn:
                    rnt='idnode'
                else:
                    rnt=rn
                mat_data[rnt]=h.findvar(rn)
            if mat_data.has_key('soma_rois_manual_info') and mat_data['soma_rois_manual_info']['roi_centers']=={}:
                del mat_data['soma_rois_manual_info']
            h.close()
            matfile=filename.replace('.hdf5', '_mat.mat')
            scipy.io.savemat(matfile, mat_data, oned_as = 'row', long_field_names=True,do_compression=True)
            chmod(matfile)
            self.printl('Converted to {0}'.format(matfile))
            files2copy.append(matfile)
        #dst folder
        if user=='daniel' or user=='default_user':
            dst_folder=os.path.join(self.config.DATABIG_PATH,region_add_date.split(' ')[0].replace('-',''),animal_id)
        else:
            dst_folder=os.path.join(self.config.PROCESSED_FILES_PATH,user,region_add_date.split(' ')[0].replace('-',''),animal_id)
        if not os.path.exists(dst_folder):
            logging.info('Creating {0}'.format(dst_folder))
            os.makedirs(dst_folder)
            chmod(dst_folder)
        for f in files2copy:
            shutil.copy2(f,dst_folder)
            logging.info('copy {0} to {1}'.format(f, dst_folder))
        #Copy pngs if exists
        pngfolder=os.path.join(os.path.dirname(filename),'output', os.path.basename(filename))
        if os.path.exists(pngfolder) and len(os.listdir(pngfolder))>0:
            dst_pngfolder=os.path.join(dst_folder,'output',os.path.basename(filename))
#            if not os.path.exists(dst_pngfolder):
#                logging.info('Creating {0}'.format(dst_pngfolder))
#                os.makedirs(dst_pngfolder)
#                os.chmod(dst_pngfolder,0777)
            try:
                shutil.copytree(pngfolder,dst_pngfolder)
            except:
                self.printl(traceback.format_exc())
                pdb.set_trace()
            logging.info('copy files from {0} to {1}'.format(pngfolder, dst_pngfolder))
        self.printl('File copy done')
        dbfilelock.acquire()
        try:
            db=DatafileDatabase(self.current_animal)
            db.update(filename=os.path.basename(filename), is_converted=True, converted_time=time.time())
            if 0:
                backupstatus=backup_manager.check_backup(os.path.basename(filename).replace('.hdf5','').split('_')[-2])
                self.printl('Current backup status is {0}'.format(backupstatus))
                if 'tape' in backupstatus and 'm drive' in backupstatus:
                    db.update(filename=os.path.basename(filename), backup_status=backupstatus)
                else:
                    db.update(filename=os.path.basename(filename), backup_status=backupstatus, backup_ok_time=time.time())
        except:
            self.printl(traceback.format_exc(),'error')
        finally:
            db.close()
            backup_animal_file(db.filename,self.config)
            dbfilelock.release()
        
class JobReceiver(threading.Thread):
    def __init__(self,config,command):
        threading.Thread.__init__(self)
        self.config=config
        self.command=command
        self.init_zmq()
        
    def init_zmq(self):
        self.context = zmq.Context()
        ip=self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX']['GUI_ANALYSIS']['ANALYSIS']['LOCAL_IP']
        port=self.config.JOBHANDLER_PUSHER_PORT
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://{0}:{1}".format(ip,port))

    def printl(self,msg,loglevel='info'):
        print msg
        getattr(logging,loglevel)(msg)
        
    def run(self):
        while True:
            self.check4newjob()
            if not self.command.empty():
                break
            time.sleep(0.1)
        self.socket.close()
            
    def check4newjob(self):
        try:
            msg=self.socket.recv(flags=zmq.NOBLOCK)
            if msg=='ping':
                self.socket.send('pong',flags=zmq.NOBLOCK)
                return
            else:
                new_job=pickle.loads(msg)
        except zmq.ZMQError:
            return
        self.printl('{0} recevived {1} {2} {3}'.format(new_job['id'], new_job['region'],new_job['stimulus'],new_job['depth']))
        dbfilelock.acquire()
        try:
            dbf=DatafileDatabase(self.config.ANIMAL_FOLDER,new_job['animal_id'],new_job['user'])
            dbf.add(**new_job)
            self.socket.send(new_job['id'],flags=zmq.NOBLOCK)
        except:
            self.printl(traceback.format_exc(),'error')
        finally:
            dbf.close()
            backup_animal_file(dbf.filename,self.config)
            dbfilelock.release()
            
def backup_animal_file(filename,config):
    dst_folder=os.path.join(config.BACKUP_PATH, 'animals', os.path.basename(os.path.dirname(filename)))
    if not os.path.exists(dst_folder):
        logging.info('Creating {0}'.format(dst_folder))
        os.makedirs(dst_folder)
        chmod(dst_folder)
    try:
        shutil.copy2(filename,dst_folder)
    except:
        logging.error(traceback.format_exc())
    logging.info('Copied  {0} to {1}'.format(filename,dst_folder))
    
def database_status(filename):
    dbfilelock.acquire()
    try:
        h=tables.open_file(filename, mode = "r")
        r2=h.root.last_job_added[0]
        unprocessed_jobs=len([1 for row in h.root.datafiles.where('(~is_analyzed | ~is_mesextractor | ~is_converted) & is_measurement_ready')])
    except:
        logging.error(traceback.format_exc())
        r2=None
        unprocessed_jobs=None
    finally:
        h.close()
        dbfilelock.release()
    return r2,unprocessed_jobs

class Datafile(tables.IsDescription):
    id = tables.UInt32Col()
    region = tables.StringCol(64)
    user = tables.StringCol(32)
    animal_id = tables.StringCol(32)
    stimulus = tables.StringCol(64)
    region_add_date = tables.StringCol(64)
    recording_started = tables.Float64Col()
    is_measurement_ready = tables.BoolCol()
    measurement_ready_time = tables.Float64Col()
    is_analyzed = tables.BoolCol()
    analyzed_time = tables.Float64Col()
    is_mesextractor = tables.BoolCol()
    mesextractor_time = tables.Float64Col()
    is_converted = tables.BoolCol()
    converted_time = tables.Float64Col()
    backup_status = tables.StringCol(16)#on databig/on tape/on m drive/on tape and m drive/not found
    backup_ok_time = tables.Float64Col()
    is_error = tables.BoolCol()
    error_message=tables.StringCol(256)
    laser = tables.Float64Col()
    depth = tables.Float64Col()
    filename=tables.StringCol(256)

class DatafileDatabase(object):
    def __init__(self,folder,animal_id=None,user=None,**kwargs):
        if os.path.exists(folder) and not os.path.isdir(folder):
            self.filename = folder
        else:
            self.filename=os.path.join(folder, user, animal_id+'.hdf5')
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
            chmod(os.path.dirname(self.filename))
        do_chmod=os.path.exists(self.filename)
        self.hdf5 = tables.open_file(self.filename, mode = "a" if not do_chmod else 'r+', title = animal_id)
        self.file_changed=False
        if not do_chmod:
            chmod(self.filename)
        logging.info('Opening {0}'.format(self.filename))
        if not hasattr(self.hdf5.root, 'datafiles'):
            self.create()

    def create(self):
        logging.info('Creating empty table')
        self.table=self.hdf5.create_table(self.hdf5.root, 'datafiles', Datafile)
        self.hdf5.create_array(self.hdf5.root, 'last_job_added', numpy.array([0]),title='Timestamp when last job was added')

    def add(self, **kwargs):
        if len([1 for row in self.hdf5.root.datafiles.where('id=={0}'.format(kwargs['id']))])>0:
            logging.warning('{0} already in database, this entry not added'.format(kwargs['id']))
            return 
        item = self.hdf5.root.datafiles.row
        for f,v in Datafile.columns.items():
            if kwargs.has_key(f):
                item[f]=kwargs[f]
            else:
                item[f]=Datafile.columns[f].dflt
        item.append()
        self.hdf5.root.last_job_added[0]=int(time.time())
        self.hdf5.flush()
        self.file_changed=True
        logging.info('{0} added to database'.format(kwargs['id']))

    def update(self,**kwargs):
        if kwargs.has_key('id'):
            keyname='id'
            key=kwargs['id']
        elif kwargs.has_key('filename'):
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
            logging.info('{0} updated'.format(key))
            self.file_changed=True

    def check(self):
        '''
        Check if data is consistent in table:
        id vs filename
        timestamp order
        flags
        laser range
        depth range
        '''
        pass
        
    def export(self):
        '''
        Export database to txt format which can be displayed by a webpage
        '''
        regions=list(set([r['region'] for r in self.hdf5.root.datafiles]))
        for region in regions:
            lines={}
            for row in self.hdf5.root.datafiles.where('(region=="{0}")'.format(region)):
                state= [row['is_measurement_ready'],row['is_mesextractor'],row['is_analyzed'],row['is_converted']]
                state=''.join(['*' if s else ' ' for s in state ])
                line='{0},{1},{5}%,{2} {3}{4}\r\n'.format(row['stimulus'],int(row['depth']),row['id'], state, 'e' if row['is_error'] else '',int(row['laser']))
                lines[row['id']]=line
                pass
            export_filename=self.filename.replace('.hdf5','_{0}.txt'.format(region))
            fp=open(export_filename,'w')
            ids=lines.keys()
            ids.sort()
            [fp.write(lines[i]) for i in ids]
            fp.close()
            #chmod(export_filename)

    def close(self):
        logging.info('Closing {0}'.format(self.filename))
        if self.file_changed:
            self.export()
        self.hdf5.close()
        #chmod(self.filename)
        

class TestDatafileDatabase(unittest.TestCase):
    def test_01(self):
        f='/mnt/databig/debug'
        f='/tmp'
        n=1000
        dfdb=DatafileDatabase(f,'151','zoltan')
        initial_nrows=dfdb.hdf5.root.datafiles.nrows
        import time
        id=int(time.time())
        dfdb.add(id=id)
        dfdb.add(id=id+1)

        dfdb.add(id=id+2, region='test')
        dfdb.update(id=id, region='test1', depth=-100.0,animal_id='151')
        
        import random,string
        t=[]
        for i in range(n):
            errmsg=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(100))
            t0=time.time()
            dfdb.add(id=int(random.random()*1e6), region='test', error_message = errmsg,
                                          user='zoltan',filename='okokok', depth=random.random()*100.0)
            t.append(time.time() - t0)
        t0=time.time()
        dfdb.update(id=id, region='test2', depth=-102.0,animal_id='153')
        print t0-time.time()
        
        
        dfdb.export()
        #Tests
        self.assertEqual(dfdb.hdf5.root.datafiles.nrows-initial_nrows, n+3)
        self.assertEqual(len([i for i in dfdb.hdf5.root.datafiles.where('id=={0}'.format(id))]),1)
        self.assertGreaterEqual(len([i for i in dfdb.hdf5.root.datafiles.where('filename==\'okokok\'')]),n)
        
        dfdb.close()
        print sum(t)/1000
        
        
def folder2stimcontext(folder):
    fn=os.path.join('/mnt/datafast/context','stim.hdf5')
    h=hdf5io.Hdf5io(fn,filelocking=False)
    h.load('jobs')
    if not hasattr(h,'jobs'):
        h.jobs=[]
    #fragment_xy_region5_37_201_-72.6_MovingGratingNoMarching_1453402731_0.hdf5
    for f in fileop.listdir_fullpath(folder):
        if f[-5:]!='.hdf5' and 'fragment' in f:continue
        tags=os.path.basename(f).split('_')
        data={'id':tags[-2], 
                    'stimulus': tags[-3], 
                    'region': '_'.join(tags[2:-4]), 
                    'user':'zoltan',
                    'animal_id': 'TT001',
                    'region_add_date':'20170101 000',
                    'recording_started': int(tags[-2]),
                    'is_measurement_ready': True,
                    'measurement_ready_time': float(tags[-2]),
                    'laser': 10.0,
                    'depth':float(tags[-4]),
                    'filename': os.path.basename(f)}
        h.jobs.append(data)
    h.save('jobs')
    h.close()
    
def hdf52mat(filename, analysis_config):
    h=hdf5io.Hdf5io(filename,config=analysis_config)
    ignore_nodes=['hashes']
    rootnodes=[v for v in dir(h.h5f.root) if v[0]!='_' and v not in ignore_nodes]
    mat_data={}
    for rn in rootnodes:
        if os.path.basename(filename).split('_')[-2] in rn:
            rnt='idnode'
        else:
            rnt=rn
        mat_data[rnt]=h.findvar(rn)
    if mat_data.has_key('soma_rois_manual_info') and mat_data['soma_rois_manual_info']['roi_centers']=={}:
        del mat_data['soma_rois_manual_info']
    h.close()
    matfile=filename.replace('.hdf5', '_mat.mat')
    scipy.io.savemat(matfile, mat_data, oned_as = 'row', long_field_names=True,do_compression=True)
    
def hdf52mat_folder(folder):
    aconfigname = 'Config'
    user ='daniel'
    analysis_config = utils.fetch_classes('visexpA.users.'+user, classname=aconfigname, required_ancestors=visexpA.engine.configuration.Config,direct=False)[0][1]()
    for f in fileop.find_files_and_folders(folder)[1]:
        if f[-4:]=='hdf5':
            print f
            hdf52mat(f,analysis_config)

def extract_prepost_scan(h):
    import visexpA.engine.component_guesser as cg
    idnode=h.findvar(cg.get_node_id(h))
    nodes2save=[]
    if idnode.has_key('prepost_scan_image'):
        for k,v in idnode['prepost_scan_image'].items():
            setattr(h, k+'_scan', matlabfile.read_line_scan(io.BytesIO(v), read_red_channel = True))
            nodes2save.append(k+'_scan')
            logging.info(nodes2save[-1]+' extracted')
        h.save(nodes2save)
        
if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        Jobhandler(sys.argv[1], sys.argv[2]).run()

        
