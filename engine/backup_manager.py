#TODO: reis data

import os,shutil,time,logging,datetime,filecmp
transient_backup_path='/mnt/databig/backup'
tape_path='/mnt/tape/hillier/invivocortex/TwoPhoton'
logfile_path='/mnt/datafast/log/backup_manager.txt'

def is_mounted():
    if not os.path.ismount('/mnt/tape'):
        import subprocess#Mount tape if not mounted
        try:
            subprocess.call(u'mount /mnt/tape',shell=True)
            subprocess.call(u'fusermount -u /mnt/tape',shell=True)
        except:
            pass
    return os.path.ismount('/mnt/tape')
    
def list_all_files(path):
    all_files = []
    for root, dirs, files in os.walk(path):            
            all_files.extend([root + os.sep + file for file in files])
    return all_files
    
def copy_file(f):
    try:
        p=f.replace(transient_backup_path+'/','')
        target_path=os.path.join(tape_path,p)
        if os.path.exists(target_path) and filecmp.cmp(f,target_path):#Already backed up
            os.remove(f)
            logging.info('Deleted {0}'.format(f))
            return
        if not os.path.exists(os.path.dirname(target_path)):
            os.makedirs(os.path.dirname(target_path))
        shutil.copy2(f,target_path)
        logging.info('Copied {0}'.format(f))
    except:
        import traceback
        logging.error(traceback.format_exc())
    
def run():
    #Check if previous call of backup manager is complete
    with open(logfile_path) as f:
        txt=f.read()
    lines=txt.split('\n')[:-1]
    done_lines = [lines.index(l) for l in lines if 'done' in l]
    started_lines = [lines.index(l) for l in lines if 'listing files' in l]
    if done_lines[-1]<started_lines[-1]:
        ds=[l.split('\t')[0] for l in lines][started_lines[-1]].split(',')[0]
        format="%Y-%m-%d %H:%M:%S"
        if time.time()-time.mktime(datetime.datetime.strptime(ds, format).timetuple())<5*60*60:#If last start happend 3 hours before, assume that there was an error and backup can be started again
            return
        
    logging.basicConfig(filename= logfile_path,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
    if not is_mounted():
        logging.error('Tape not mounted')
        return
    logging.info('listing files')
    files = list_all_files(transient_backup_path)
    files.sort()
    
    for f in files:
        copy_file(f)
    logging.info('done')

if __name__ == "__main__":
    run()
