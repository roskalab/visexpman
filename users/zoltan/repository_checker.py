import os,zipfile,unittest,time,logging,shutil,filecmp,traceback,sys

class RepositoryChecker(object):
    def __init__(self, database_folder, repository_folder, vip_files=[], ignore_folder=[]):
        self.logfile=os.path.join(database_folder,'log_repochecker.txt')
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        logging.info(('Repo checker started',database_folder, repository_folder, vip_files, ignore_folder))
        self.extensions=['.py', '.bat', '.sh']
        self.database_folder=database_folder
        self.repository_folder=repository_folder
        self.vip_files=vip_files
        self.ignore_folder=ignore_folder
        
    def read(self):
        '''
        read source files in folder
        '''
        all_files = []
        for root, dirs, files in os.walk(self.repository_folder):            
            all_files.extend([root + os.sep + file for file in files])
        self.all_files=[f for f in all_files if os.path.splitext(f)[1] in self.extensions]
        self.vip=[os.path.join(self.repository_folder, f) for f in self.vip_files]
        self.core=[f for f in self.all_files if not (f in self.vip)]
        self.core=[f for f in self.core if len([1 for ifolder in self.ignore_folder if ifolder in f])==0]
        
        
    def check(self):
        '''
        Checks vip files separately
        '''
        src='/tmp/src'
        if os.path.exists(src):
            shutil.rmtree(src)
        os.mkdir(src)
        zipfiles=[os.path.join(self.database_folder, f) for f in os.listdir(self.database_folder) if os.path.splitext(f)[1]=='.zip' and '_'.join(os.path.basename(self.zipfn).split('_')[:-1]) in f]
        zipfiles.sort()
        if len(zipfiles)==0:
            return
        latest=zipfiles[-2]
        ziph = zipfile.ZipFile(latest, 'r')
        ziph.extractall(src)
        ziph.close()
        keep_last_record=False
        try:
            logging.info('Comparing vip files')
            vip_not_matching=[vf for vf in self.vip if not filecmp.cmp(vf.replace(self.repository_folder,src),vf)]
            if len(vip_not_matching):
                logging.warning('VIP file(s) changed: {0}'.format(vip_not_matching))
                keep_last_record=True
            logging.info('Comparing core files')
            core_not_matching=[cf for cf in self.core if not filecmp.cmp(cf.replace(self.repository_folder,src),cf)]
            if len(core_not_matching):
                logging.error('Core file(s) changed: {0}'.format(core_not_matching))
                keep_last_record=True
        except:
            keep_last_record=True
            logging.error(traceback.format_exc())
        finally:
            shutil.rmtree(src)
        if not keep_last_record:
            os.remove(self.zipfn)
            
        
    def zip(self):
        '''
        zip repository
        '''
        self.zipfn=os.path.join(self.database_folder, self.repository_folder[1:].replace(os.sep,'_')+'_'+str(int(time.time()))+'.zip')
        ziph = zipfile.ZipFile(self.zipfn, 'a')
        for f in self.all_files:
            ziph.write(f, f.replace(self.repository_folder,''))
        ziph.close()
        
    def notify(self):
        fp=open(self.logfile,'r')
        txt=fp.read(-1)
        fp.close()
        lines=txt.split('\n')
        starti=[i for i in range(len(lines)) if 'Repo checker started' in lines[i]][-1]
        notifications=''
        for i in range(starti, len(lines)):
            if 'error' in lines[i].lower() or 'warning' in lines[i].lower():
                notifications+=lines[i]
        print notifications
        if len(notifications)>0:
            import subprocess
            message = 'Subject:{0}\n\n{1}\n'.format('rc setup repository change', notifications)
            fn='/tmp/email.txt'
            fp=open(fn,'w')
            fp.write(message)
            fp.close()
            # Send the mail
            cmd='/usr/sbin/sendmail {0} < {1}'.format('zoltan.raics@fmi.ch',fn)
            res=subprocess.call(cmd,shell=True)
            os.remove(fn)
            
    def run(self):
        self.read()
        self.zip()
        self.check()
        self.notify()
        logging.info('Done')
        
class TestBehavAnalysis(unittest.TestCase):
    def test_01_repository(self):
        r=RepositoryChecker('/tmp/repocheck', '/mnt/datafast/codes/jobhandler', vip_files=['visexpman/users/daniel/configurations.py'],ignore_folder=['visexpman/users/daniel'])
        r.run()
        pass

        
if __name__ == "__main__":
    if len(sys.argv)>1:
        if sys.argv[1]=='rc':
            r=RepositoryChecker('/home/rz/repocheck/rc', '/mnt/datafast/codes/jobhandler',
                                   vip_files=['visexpman/users/daniel/configurations.py','visexpman/users/fiona/flashes.py','visexpman/users/fiona/moving_bar.py',
                                               'visexpman/users/fiona/receptive_field_fiona.py', 'visexpman/users/fiona/grating_fiona.py', 'visexpman/users/common/grating_base.py'],
                                   ignore_folder=['visexpman/users/daniel'])
            r.run()
        elif sys.argv[1]=='ao':
            r=RepositoryChecker('/home/rz/repocheck/ao', '/mnt/datafast/codes/ao-cortical',vip_files=[],ignore_folder=['visexpman/users/adrian'])
            r.run()
        elif sys.argv[1]=='rc_rldata':
            r=RepositoryChecker('/home/rz/repocheck/rc_rldata', '/data/software/rc-setup',
                                   ignore_folder=[])
            r.run()


    else:
        unittest.main()
