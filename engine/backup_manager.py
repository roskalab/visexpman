import os,shutil,time,logging,datetime,filecmp,subprocess,threading,Queue
transient_backup_path='/mnt/databig/backup'
tape_path='/mnt/tape/hillier/invivocortex/TwoPhoton/new'
mdrive='/mnt/mdrive/invivo/rc/raw'
logfile_path='/mnt/datafast/log/backup_manager.txt'
rei_data='/mnt/databig/debug/cacone'
rei_data_tape=os.path.join(tape_path,'retina')
last_file_access_timout=300

transient_processed_files='/mnt/databig/processed'
mdrive_processed='/mnt/mdrive/invivo/rc/processed'


tape_file='/mnt/tape/hillier'
mdrive_file='/mnt/mdrive/invivo'
ISMOUNT_ENABLED=True

def watchdog(maxtime,queue):
    logging.info('Watchdog started')
#    maxtime,queue=args
    t0=time.time()
    while True:
        if time.time()-t0>maxtime:
            logging.error('Self terminating')
            logging.error('done')
            subprocess.call('kill -KILL {0}'.format(os.getpid()),shell=True)
        if not queue.empty():
            break
        time.sleep(30)

def is_id_on_drive(id, drive):
    return len([f for f in list_all_files(drive) if str(id) in os.path.basename(f) and os.path.getsize(f)>0])==2

def check_backup(id):
    #Check tape first
    status=''
    if is_id_on_drive(id, tape_path):
        status='tape'
    if is_id_on_drive(id, mdrive):
        status+=' m drive'
    if is_id_on_drive(id, transient_backup_path):
        status +=' databig'
    if status=='':
        status='not found'
    return status

def sendmail(to, subject, txt):
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

def is_mounted():
    if ISMOUNT_ENABLED:
        if not os.path.ismount('/mnt/tape'):
            try:
                subprocess.call(u'mount /mnt/tape',shell=True)
                subprocess.call(u'fusermount -u /mnt/tape',shell=True)
            except:
                pass
        return os.path.ismount('/mnt/tape') and os.path.ismount('/mnt/mdrive')
    else:
        return os.path.exists(tape_file) and os.path.exists(mdrive_file)
            
    
def list_all_files(path):
    all_files = []
    for root, dirs, files in os.walk(path):            
            all_files.extend([root + os.sep + file for file in files])
    return all_files
    
def is_file_closed(f):
    now=time.time()
    return now-os.path.getmtime(f)>last_file_access_timout# and now-os.path.getctime(f)>last_file_access_timout#ctime is the change of metadata
    
def copy_file(f):
    try:
        copy2m= os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))!='daniel'#Daniel's fiels are not copied to m drive only to tape
        path=f.replace(transient_backup_path+'/','')
        target_path_tape=os.path.join(tape_path,path)
        target_path_m=os.path.join(mdrive,path)
        if os.path.exists(target_path_tape) and filecmp.cmp(f,target_path_tape) and (not copy2m or (os.path.exists(target_path_m) and filecmp.cmp(f,target_path_m))):#Already backed up
            os.remove(f)
            logging.info('Deleted {0}'.format(f))
            return
        folders=[target_path_tape]
        if copy2m:
            folders.append(target_path_m)
        for p in folders:
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p))
        if not is_file_closed(f):
            return
        if not os.path.exists(target_path_tape) or 'mouse' in os.path.basename(target_path_tape) or 'animal' in os.path.dirname(f):
            shutil.copy2(f,target_path_tape)
            logging.info('Copied to tape: {0}, {1}'.format(f, os.path.getsize(target_path_tape)))
        if copy2m and (not os.path.exists(target_path_m) or 'mouse' in os.path.basename(target_path_m)):#Mouse file may be updated with scan regions
            shutil.copyfile(f,target_path_m)
            logging.info('Copied to m: {0}, {1}'.format(f, os.path.getsize(target_path_m)))
    except:
        import traceback
        msg=traceback.format_exc()
        logging.error(msg)
        sendmail('zoltan.raics@fmi.ch', 'backup manager raw cortical file copy error', msg)
        
def copy_processed_file(f):
    try:
        path=f.replace(transient_processed_files+'/','')
        target_path_m=os.path.join(mdrive_processed,path)
        if os.path.exists(target_path_m) and filecmp.cmp(f,target_path_m):#Already copied up
            os.remove(f)
            logging.info('Deleted {0}'.format(f))
            return
        if not os.path.exists(os.path.dirname(target_path_m)):
            os.makedirs(os.path.dirname(target_path_m))
        if not is_file_closed(f):
            return
        if not os.path.exists(target_path_m) or 'mouse' in os.path.basename(target_path_m):
            shutil.copyfile(f,target_path_m)
            logging.info('Copied to m: {0}, {1}'.format(f, os.path.getsize(target_path_m)))
    except:
        import traceback
        msg=traceback.format_exc()
        logging.error(msg)
        sendmail('zoltan.raics@fmi.ch', 'backup manager processed cortical file copy error', msg)
        
def rei_backup():
    try:
        files=list_all_files(rei_data)
        phys_files=[f for f in files if '.phys'==f[-5:]]
        coord_files=[f for f in files if 'coords.txt'==os.path.basename(f)]
        rawdata_files=[f for f in files if '.csv'==f[-4:] and 'timestamp' not in os.path.basename(f)]
        backupable_files = phys_files
        backupable_files.extend(coord_files)
        backupable_files.extend(rawdata_files)
        for f in backupable_files:
            target_fn=f.replace(rei_data,rei_data_tape)
            if not os.path.exists(os.path.dirname(target_fn)):
                os.makedirs(os.path.dirname(target_fn))
            if is_file_closed(f) and not os.path.exists(target_fn):
                shutil.copy2(f,target_fn)
                logging.info('Copied {0}'.format(f))
    except:
        import traceback
        msg=traceback.format_exc()
        logging.error(msg)
        sendmail('zoltan.raics@fmi.ch', 'backup manager retinal file copy error', msg)
    
def run():
    #Check if previous call of backup manager is complete
    with open(logfile_path) as f:
        txt=f.read()
    lines=txt.split('\n')[:-1]
    done_lines = [lines.index(l) for l in lines if 'done' in l]
    started_lines = [lines.index(l) for l in lines if 'Check network drives' in l]
    if done_lines[-1]<started_lines[-1]:
        ds=[l.split('\t')[0] for l in lines][started_lines[-1]].split(',')[0]
        format="%Y-%m-%d %H:%M:%S"
        if time.time()-time.mktime(datetime.datetime.strptime(ds, format).timetuple())<2*60*60:#If last start happend 3 hours before, assume that there was an error and backup can be started again
            return
    logging.basicConfig(filename= logfile_path,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
    q=Queue.Queue()
    wd=threading.Thread(target=watchdog,args=(2*60,q))
    wd.start()
    #time.sleep(150)
    logging.info('Check network drives')
    if not is_mounted():
        msg='Tape or m mdrive not mounted: tape: {0}, m: {1}'.format(os.path.ismount('/mnt/tape'), os.path.ismount('/mnt/mdrive'))
        logging.error(msg)
        sendmail('zoltan.raics@fmi.ch', 'backup manager mount error', msg)
        return
    q.put('terminate')
    wd.join()
    logging.info('listing rawdata files')
    files = list_all_files(transient_backup_path)
    files.sort()
    
    for f in files:
        copy_file(f)
        
    #Copy processed datafiles from rlvivo to m drive
    logging.info('listing processed files')
    files = list_all_files(transient_processed_files)
    files.sort()
    for f in files:
        copy_processed_file(f)
        
    rei_backup()
    logging.info('done')

if __name__ == "__main__":
    run()
