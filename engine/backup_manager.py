import os,shutil,time,logging,datetime,filecmp,subprocess,Queue,threading,traceback,sys
import unittest

class Config(object):
    last_file_access_timeout=60
    last_run_timeout=60*60*3
    watchdog_timeout=120

class TestConfig(Config):
    def __init__(self):
        self.LOGPATH='/tmp/backup_test.txt'
        self.last_run_timeout=5
        self.last_file_access_timeout=5
        self.COPY= [
                {'src':'/tmp/1', 'dst':['/tmp/a'],'extensions':['.txt'], 'move':True},
                {'src':'/tmp/2', 'dst':['/tmp/b', '/tmp/c'],'extensions':['.mat', '.hdf5'],'move':False}
            ]
            
def ReiSetup(Config):
    def __init__(self):
        self.LOGPATH='q:\\log\\backup_manager.txt'
        self.COPY= [
                {'src':'q:\\raw', 'dst':['/tmp/a'],'extensions':['.tif','.csv', '.txt','.mat'], 'move':True},
                {'src':'q:\\processed', 'dst':['m:\\invitro\\processed'],'extensions':['.hdf5', '.mat'], 'move':True},
            ]
            
def RCSetup(Config):
    def __init__(self):
        self.LOGPATH='/mnt/datafast/log/backup_manager.txt'
        self.COPY= [
                {'src':'/mnt/databig/backup', 'dst':['/mnt/tape/hillier/invivocortex/TwoPhoton/new', '/mnt/mdrive/invivo/rc/raw'],'extensions':['.mat','.hdf5'], 'move':True},
                {'src':'/mnt/databig/processed', 'dst':['/mnt/mdrive/invivo/rc/processed'],'extensions':['.mat','.hdf5', '.png'], 'move':True},
            ]


def watchdog(maxtime,queue):
    logging.info('watchdog starts')
    t0=time.time()
    while True:
        if time.time()-t0>maxtime:
            logging.error('Self terminating')
            subprocess.call('kill -KILL {0}'.format(os.getpid()),shell=True)
        if not queue.empty():
            break
        time.sleep(1)

class BackupManager(object):
    '''
    1) locking mechanism
    2) copy config
    
    '''
    def __init__(self, config):
        self.config=config
        if self.islocked(): return
        logging.basicConfig(filename= self.config.LOGPATH,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
        logging.info('Started')
        if self.check_dest_folders(): return
        logging.info('Dest folders OK')
    
    def islocked(self):
        return os.path.exists(self.config.LOGPATH) and time.time()-os.path.getmtime(self.config.LOGPATH)<self.config.last_run_timeout
        
    def check_dest_folders(self):
        result=True
        q=Queue.Queue()
        wd=threading.Thread(target=watchdog,args=(self.config.watchdog_timeout,q))
        wd.start()
        for folders in  [f['dst'] for f in self.config.COPY]:
            for folder in folders:
                if not os.path.exists(folder):
                    self.error('{0} is not available'.format(folder))
                    result=False
        q.put('terminate')
        wd.join()
        return result
            
    def list_all_files(self, path):
        all_files = []
        for root, dirs, files in os.walk(path):            
                all_files.extend([root + os.sep + file for file in files])
        return all_files
    
    def is_file_closed(self,f):
        now=time.time()
        return now-os.path.getmtime(f)>self.config.last_file_access_timeout
                 
    def sendmail(self, to, subject, txt):
        if os.name=='posix':
            message = 'Subject:{0}\n\n{1}\n'.format(subject, txt)
            logging.info('Sending mail')
            fn='/tmp/email.txt'
            fp=open(fn,'w')
            fp.write(message)
            fp.close()
            # Send the mail
            cmd='/usr/sbin/sendmail {0} < {1}'.format(to,fn)
            res=subprocess.call(cmd,shell=True)
            logging.info(str(res))
            os.remove(fn)
            return res==0
            
    def error(self,msg):
        logging.error(msg)
        self.sendmail('zoltan.raics@fmi.ch','backup manager error', msg)
        
    def check_mounts(self):
        q=Queue.Queue()
        wd=threading.Thread(target=watchdog,args=(2*60,q))
        wd.start()
        logging.info('Check network drives')
        if not is_mounted():
            self.error('Tape or m mdrive not mounted: m: {0}, tape: {1}'.format(os.path.ismount('/mnt/tape'), os.path.ismount('/mnt/mdrive')))
            return
        q.put('terminate')
        wd.join()
        
    def copy(self,copy):
        files=self.list_all_files(copy['src'])
        files=[f for f in files if os.path.splitext(f)[1] in copy['extensions']]#Filter expected extensions
        files.sort()
        for f in files:
            try:
                if not self.is_file_closed(f):
                    return
                #generate dst filenames
                dst_files = [os.path.join(dst, os.path.basename(f)) for dst in copy['dst']]
                [os.makedirs(os.path.dirname(f)) for dst in copy['dst'] if not os.path.exists(os.path.dirname(f))]
                #compare files
                if not all([os.path.exists(dst_file) and filecmp.cmp(f,dst_file) for dst_file in dst_files]):
                    for dst_file in dst_files:
                        shutil.copyfile(f,dst_file) 
                        logging.info('Copied {0} to {1} ({2})'.format(f, dst_file, os.path.getsize(dst_file)))
                else:
                    if copy['move']:
                        os.remove(f)
                        logging.info('Deleted {0}'.format(f))
            except:
                self.error(traceback.format_exc())
        
    def run(self):
        for copy in self.config.COPY:
            self.copy(copy)
        logging.info('Done')
        
class TestStimulationPatterns(unittest.TestCase):
    def setUp(self):
        self.config=TestConfig()
        for f in self.config.COPY:
            for folder in f['dst']:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                os.mkdir(folder)
    
    def test_01_bulocking(self):
        if os.path.exists(self.config.LOGPATH):
            os.remove(self.config.LOGPATH)
        BackupManager(self.config)
        BackupManager(self.config)
        time.sleep(5)
        BackupManager(self.config)
        f=open(self.config.LOGPATH,'rt')
        txt=f.read()
        f.close()
        self.assertEqual(txt.count('Started'),2)
        
    def test_02_copy(self):
        #Generate test files
        extensions=[]
        for e in self.config.COPY:
            extensions.extend(e['extensions'])
        nfiles=10
        for c in self.config.COPY:
            if os.path.exists(c['src']):
                shutil.rmtree(c['src'])
            os.makedirs(c['src'])
            for e in extensions:
                for i in range(nfiles):
                    f=open(os.path.join(c['src'],'{0}{1}'.format(i,e)),'wb')
                    f.write('x'*100)
                    f.close()
        BackupManager(self.config).run()
        files=[]
        for f in self.config.COPY:
            for folder in f['dst']:
                files.extend(os.listdir(folder))
        self.assertEqual(len(files),0)#Brand new files none of them should be copied
        time.sleep(5)
        bum=BackupManager(self.config)
        bum.run()
        bum.run()
        for c in self.config.COPY:
            #check src:
            src_exts=[os.path.splitext(f)[1] for f in os.listdir(c['src'])]
            extensions_in_src=[0 for e in src_exts if e in c['extensions']]
            if c['move']:
                self.assertEqual(len(extensions_in_src),0)
            else:
                self.assertGreater(len(extensions_in_src), 0)
            for folder in c['dst']:
                dst_exts=[os.path.splitext(f)[1] for f in os.listdir(folder)]
                extensions_in_dst=[0 for e in dst_exts if e in c['extensions']]
                self.assertEqual(len(dst_exts),len(extensions_in_dst))
        
            
    
if __name__ == "__main__":
    unittest.main()
