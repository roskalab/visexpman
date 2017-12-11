'''
Common file and filename operations
'''
import sys, os, re, ctypes, platform, shutil, numpy, tempfile, time, subprocess, multiprocessing,threading,Queue
from distutils import file_util,  dir_util
try:
    import psutil
except ImportError:
    pass
import utils
timestamp_re = re.compile('.*(\d{10,10}).*')

################# File name related ####################
   
    
def is_first_tag(fn, tag):
    '''
    is tag the first characters of fn?
    '''
    return tag == os.path.split(fn)[1][:len(tag)]

def generate_filename(path, insert_timestamp = False, last_tag = ''):
    '''
    Inserts index into filename resulting unique name.
    '''
    index = 0
    number_of_digits = 5
    while True:
        if last_tag != '':
            testable_path = path.replace('.',  '_{0:0=5}_{1}.'.format(index, last_tag))
        else:
            testable_path = path.replace('.',  '_{0:0=5}.'.format(index))
        if not os.path.isfile(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Filename cannot be generated')
    if insert_timestamp:
        testable_path = path.replace('.',  '_{0}_{1:0=5}.'.format(int(time.time()), index))
    return testable_path
    
def generate_foldername(path):
    '''
    Inserts index into foldername resulting unique name.
    '''
    number_of_digits = 5
    index = 0
    while True:
        testable_path = (path + '_{0:0=5}'.format(index))
        if not os.path.isdir(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Foldername cannot be generated')
    return testable_path

#OBSOLETE
def get_tmp_file(suffix, delay = 0.0):
    path = os.path.join(tempfile.gettempdir(), 'tmp.' + suffix)
    remove_if_exists(path)
    time.sleep(delay)
    return path
    
def replace_extension(fn,ext):
    '''
    Replaces fn's extension to ext
    '''
    return fn.replace(os.path.splitext(fn)[1], ext)
    
def get_convert_filename(filename, extension, tag='', outfolder = None):
    '''
    Generate a filename at dataconversion:
    original base name is kept but replaced to provided extension. If tag is not '', it is inserted between filename and extension
    If outfolder is provided, it is inserted to the basename of the provided filename
    '''
    fn=replace_extension(filename, extension)
    if len(tag)>0:
        fn=fn.replace(extension, tag+extension)
    if outfolder is not None:
        fn=os.path.join(outfolder, os.path.basename(filename))
    return fn
    
def parsefilename(filename, regexdict):
    '''From a string filename extracts fields as defined in a dictionary regexdict. 
    Data will be put into a directory with the same keys as found in regextdict.
    The value of each regextdict key must be a list. The first element of the list
    is a regular expression that tells what to extract from the string. The second element
    is a python class that is used to convert the extracted string into a number (if applicable)
    '''
    import re
    for k,v in regexdict.items():
        for expr in v[:-1]: #iterate through possible patterns (compatibility patters for filename structured used earlier)
            p = re.findall(expr,filename)
        if p:
            if isinstance(p[0], tuple): #stagepos extracts a tuple
                p = p[0]
            try:
                regexdict[k] = [v[-1](elem) for elem in p] # replace the regex pattern with the value
            except TypeError:
                raise
        else:
            regexdict[k] = None # this pattern was not found
    return regexdict
    
def select_folder_exists(folders):
    '''
    Return the first folder from the provided folder names which exists
    '''
    for folder in folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            return folder
    
################# File system ####################

def free_space(path):
    '''
    Calculates the free space on the provided location. Windows, OSX and Linux platforms are all supported
    '''
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    elif platform.system() == 'Linux' or platform.system()=='Darwin':
        s=os.statvfs(path)
        return (s.f_bavail * s.f_frsize)
    else:
        raise NotImplementedError('')
        
def folder_size(path):
    '''
    Size of a folder is calculated, not supported on windows 
    '''
    if platform.system() == 'Linux' or platform.system()=='Darwin':
        tmp='/tmp/o.txt'
        if os.path.exists(tmp):
            os.remove(tmp)
        subprocess.call('du -sh {0}>>{1}'.format(path,tmp), shell=True)
        return read_text_file(tmp).split('\t')[0]
    else:
        raise NotImplementedError('OS not supported')
            
    
def set_file_dates(path, file_info):
    '''
    Sets the timestamp of a file
    '''
    try:
        if hasattr(file_info,'st_atime') and hasattr(file_info,'st_mtime'):
            os.utime(path, (file_info.st_atime, file_info.st_mtime))
        else:
            os.utime(path, (file_info, file_info))
    except:
        pass
        
def file_open_by_other_process(filename):
    '''Checks whether the given file is open by any process'''
    if platform.system() == 'Windows':
        raise NotImplementedError('')
    ccmd = 'lsof -Fp '+filename
    p=subprocess.Popen(ccmd, shell=True)
    res= p.communicate()
    pids = re.findall('p(\d+)', res)
    if len(pids)<1: return False
    elif len(pids)>1 or pids[0]!=os.getpid():return True

def total_size(source):
        total_size_bytes = os.path.getsize(source)
        if not os.path.isfile(source):
            for item in os.listdir(source):
                itempath = os.path.join(source, item)
                if os.path.isfile(itempath):
                    total_size_bytes += os.path.getsize(itempath)
                elif os.path.isdir(itempath):
                    total_size_bytes += total_size(itempath)
        return total_size_bytes
        
def wait4file_ready(f,timeout=60, min_size=0):
    '''
    Waits until f file is ready by checking size periodically. This can be used when a big file is being written by an other process
    or computer on a fileshare
    '''
    if os.path.exists(f):
        filesize_prev=os.path.getsize(f)
    else:
        filesize_prev=0
    t0=time.time()
    while True:
        if os.path.exists(f):
            filesize=os.path.getsize(f)
        else:
            time.sleep(0.5)
            continue
        if filesize==filesize_prev and filesize>min_size:
            break
        else:
            filesize_prev=filesize
            time.sleep(0.2)
        if time.time()-t0>timeout:
            raise RuntimeError('Wait for {} file timeout'.format(f))

def folder_signature(folder):
    '''
    Signature consist of: number of files, overall file size, latest modification date
    '''
    files=find_files_and_folders(folder)[1]
    return (len(files), sum([os.path.getsize(f) for f in files]), max([os.path.getmtime(f) for f in files]))
    
################# File/directory operations ####################

def mkstemp(suffix=None, filename = None):
    '''Creates a temporary file with suffix as extension, e.g. .pdf. Closes the file so that other methods can open it and do what they need.'''        
    if filename is not None:             
        return os.path.join(tempfile.gettempdir(), filename)
    else:
        f,filename = tempfile.mkstemp(suffix=suffix)
        os.close(f)
        os.remove(filename)
        return filename
        
def remove_if_exists(filename):
    '''
    Removes a file if exists
    '''
    if os.path.exists(filename):
        os.remove(filename)

def mkdir_notexists(folder, remove_if_exists=False):
    '''
    Create folder(s) if they do not exist. 
    remove_if_exists: remove folders if folders exists
    '''
    if not isinstance(folder, list):
        folder = [folder]
    for f in folder:
        if remove_if_exists and os.path.exists(f):
            shutil.rmtree(f)
        if not os.path.exists(f):
            os.makedirs(f)
        
def recreate_dir(folder):
    '''
    If folder exists, all of its contents are removed and then the folder is recreated
    '''
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def copy(src, dst, update=1):
    if not os.path.exists(src):
        raise OSError('File or directory to be copied does not exist')
    if os.path.isfile(src): 
        dir_util.mkpath(os.path.split(dst)[0])
        return file_util.copy_file(src, dst, update=1)
    else: 
        dir_util.mkpath(dst)
        return dir_util.copy_tree(src, dst, update=1)
        
def move2zip(src,dst,delete=False):
    '''
    Zip contents of src and save it to dst. if delete==True, remove src folder
    src can be a list of files
    when dst is a folder, zipfilename will be the name of the first file in src
    '''
    import zipfile
    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))
    if isinstance(src,list):
        files=src
        root=os.path.dirname(files[0])
    else:
        files=find_files_and_folders(src)[1]
        root=src
    files.sort()
    if os.path.isdir(dst):
        dst=os.path.join(dst,os.path.splitext(os.path.basename(files[0]))[0]+'.zip')
    zf = zipfile.ZipFile(dst, 'w',zipfile.ZIP_DEFLATED)
    for f in files:
        zf.write(f, f.replace(root,''))
    zf.close()
    if delete:
        shutil.rmtree(src)
    return dst

################# File finders ####################

def listdir_fullpath(folder):#Legacy
    return listdir(folder)
    
def listdir(folder):
    '''
    Return lfull path of files in folder in alphabetical order
    '''
    files = os.listdir(folder)
    files.sort()
    return map(os.path.join, len(files)*[folder],files)
    
def find_latest(path, extension=None):
    '''
    Find the latest file in the folder
    '''
    if not os.path.isdir(path):
        raise RuntimeError('Foldername expected not filename: {0}'.format(path))
    fns = [fn for fn in listdir_fullpath(path) if os.path.splitext(fn)[1]==extension or extension is None and not os.path.isdir(fn)]
    if len(fns) == 0:
        return
    fns_dates = map(os.path.getmtime, fns)
    latest_file_index = fns_dates.index(max(fns_dates))
    return fns[latest_file_index]
     
def find_content_in_folder(content, folder_name, file_filter):
    found_in_files = []
    for file in filtered_file_list(folder_name,  file_filter, fullpath = True):
        if content in read_text_file(file):
            found_in_files.append(file)
    return found_in_files

def find_files_and_folders(start_path,  extension = None, filter = None):
        '''
        Finds all folders and files. With extension the files can be filtered
        '''
        directories = []
        all_files  = []
        directories = []
        for root, dirs, files in os.walk(start_path):            
            for dir in dirs:
                directories.append(root + os.sep + dir)
            for file in files:
                if extension != None:
                    if file.split('.')[-1] == extension:
                        all_files.append(root + os.sep + file)
                elif filter != None:
                    if filter in file:
                        all_files.append(root + os.sep + file)
                else:
                    all_files.append(root + os.sep + file)    
        return directories, all_files

def filtered_file_list(folder_name,  filter, fullpath = False, inverted_filter = False, filter_condition = None):
    import numpy
    files = os.listdir(folder_name)    
    filtered_files = []
    for file in files:
        if isinstance(filter,  list) or isinstance(filter,  tuple):
            found  = False
            conditions_met = []
            for filter_item in filter:
                if inverted_filter:
                    if filter_item not in file:
                        found = True
                        conditions_met.append(found)
                else:
                    if filter_item in file:
                        found = True
                        conditions_met.append(found)
            if (filter_condition == 'and' and numpy.array(conditions_met).sum() == len(filter)) or (filter_condition == None and found):
                if fullpath:
                    filtered_files.append(os.path.join(folder_name, file))
                else:
                    filtered_files.append(file)
        elif isinstance(filter,  str):
            found = False
            if inverted_filter:
                if filter not in file:
                    found = True
            else:
                if filter in file:
                    found = True
            if found:
                if fullpath:
                    filtered_files.append(os.path.join(folder_name, file))
                else:
                    filtered_files.append(file)
    return filtered_files

def dirListing2(rootdir, pattern='*', excludenames=[]):
    import fnmatch
    matches = []
    for root, dirnames, filenames in os.walk(rootdir):
        if len([e for e in excludenames if e in root])>0: continue
        for filename in fnmatch.filter(filenames, pattern):
            if len([e for e in excludenames if e in filename])==0:
                matches.append(os.path.join(root, filename))
    return matches
      
def dirListing(directory='~', ext = '', prepend='', dflag = False, sortit = False,  noext=False,  excludenames = [], fullpath = False):
    """Returns a list of directories. Set 'prepend' to the same as 'directory'
    to get results relative to 'directory'. Set 'prepend' to another base path
    to get results relative to that base path. If the subdirectories under
    'prepend' do not exist, they will be created.
    Set dflag=True if you only want directories be searched or returned. Otherwise only files will be returned.
    Set noext=True if you want the file extensions cut (anything after the last dot)"""
                #variables
    dirs = [] #list of directories
                #list of directories and files
    lastmod = []
    if ext=='' and sort == True:
        raise ValueError("Recursive listing with sorting is not implemented")

    if isinstance(ext,basestring):
        ext = [ext]
    ext = [ex[ex.find('.')+1:] for ex in ext] #remove . from extension if it is there
    try:
        listing = os.listdir(directory)
        listing = [l1 for l1 in listing if sum([e in l1 for e in excludenames])==0]
    except OSError:
        return ''
    if len(prepend)>0 and prepend[-1] != os.sep:
        prepend = prepend + os.sep
                #get just the directories
    for x in listing:
        if ext[0]!='%':
            cext = next((ex for ex in ext if re.search(ex+'$',x) is not None), None)
        else:
            cext = 'dummy'
        id = (os.path.isdir(directory+os.sep+x))
        if id and (dflag == True or len(ext)==0):# just include the subdirectory in the result list
            dirs.append(prepend+x)
            lastmod.append(os.stat(os.path.join(directory,x))[8])
        elif not id and cext is not None and len(cext) > 0 and not x[0] == '.':# and not id: # add matching files, exclude hidden files whose name starts with .
            dirs.append(prepend+x)
            lastmod.append(os.stat(os.path.join(directory,x))[8])
        elif id or cext is None: # recursive call to look in subdirectories if dirname does not contain the extension
            rdirs = dirListing(directory+os.sep+x, ext, prepend+x, dflag, sortit = sortit,  noext=noext,  excludenames = excludenames)
            if not os.path.exists(prepend+x): # create directory
                os.makedirs((prepend+x))
            dirs.extend(rdirs[:])
    if sortit:
        from operator import itemgetter
        dirs, modtimes = zip(*sorted(zip(dirs,lastmod), key=itemgetter(1)))
    if noext: # remove extensions
        dirs = [item[:item.rfind('.')] for item in dirs]
    if fullpath:
        dirs = [os.path.join(directory, fn) for fn in dirs]
    return dirs

################# Text file related ####################

def read_text_file(path):
    f = open(path,  'rt')
    txt =  f.read(os.path.getsize(path))
    f.close()
    return txt
    
def write_text_file(filename, content):
    f = open(filename,  'wt')
    f.write(content)
    f.close()

################# Vision experiment manager related ####################
#TODO: This should go to experiment_data
def visexpman_package_path():
    import visexpman
    return os.path.split(sys.modules['visexpman'].__file__)[0]
    
def visexpA_package_path():
    try:
        import visexpA
        return os.path.split(sys.modules['visexpA'].__file__)[0]
    except ImportError:
        return None

def get_user_module_folder(config):
    '''
    Returns folder path where user's stimulation files or other source files reside
    '''
    return os.path.join(visexpman_package_path(), 'users', config.user)

def get_context_filename(config,extension=' npy'):
    '''
    Generate context filename from CONTEXT_PATH, username and application name
    '''
    if not hasattr(config, 'CONTEXT_PATH'):
        raise RuntimeError('CONTEXT_PATH is not defined in machine config')
    import platform
    uiname=config.user_interface_name if hasattr(config, 'user_interface_name') else config.PLATFORM
    user = config.user if hasattr(config, 'user') else ''
    filename = 'context_{0}_{1}_{2}.{3}'.format(uiname, user, platform.uname()[1],extension)
    return os.path.join(config.CONTEXT_PATH, filename)
    
def get_log_filename(config):
    if not hasattr(config, 'LOG_PATH'):
        raise RuntimeError('LOG_PATH is not defined in machine config')
    import platform
    uiname=config.user_interface_name if hasattr(config, 'user_interface_name') else config.PLATFORM
    dt=utils.timestamp2ymdhms(time.time(), filename=True)
    filename = 'log_{0}_{1}.txt'.format(uiname, dt)
    return os.path.join(config.LOG_PATH, filename)

def cleanup_files(config):
    [shutil.rmtree(getattr(config,pn)) for pn in ['DATA_STORAGE_PATH', 'EXPERIMENT_DATA_PATH', 'LOG_PATH', 'REMOTE_LOG_PATH', 'CAPTURE_PATH'] if hasattr(config, pn) and os.path.exists(getattr(config,pn))]
    if os.path.exists(get_context_filename(config)):
        os.remove(get_context_filename(config))
        
################# Experiment file related ####################


class DataAcquisitionFile(object):
    '''
    Opens an hdf5 file and data can be saved sequentally
    '''
    def __init__(self,nchannels,dataname, datarange,filename=None,compression_level=5):
        self.nchannels=nchannels
        self.datarange=datarange
        self.scale=(2**16-1)/(datarange[1]-datarange[0])
        self.offset=-datarange[0]
        self.dataname=dataname
        if filename is None:
            self.filename=os.path.join(tempfile.gettempdir(), 'recorded_{0}.hdf5'.format(time.time()))
            if os.path.exists(self.filename):
                os.remove(self.filename)
        else:
            self.filename=filename
        import hdf5io,tables
        self.hdf5 = hdf5io.Hdf5io(self.filename,filelocking=False)
        setattr(self.hdf5,dataname+'_scaling', {'range': self.datarange, 'scale':self.scale,'offset':self.offset})
        self.hdf5.save(dataname+'_scaling')
        datacompressor = tables.Filters(complevel=compression_level, complib='zlib', shuffle = 1)
        datatype = tables.UInt16Atom(self.nchannels)
        setattr(self,self.dataname, self.hdf5.h5f.create_earray(self.hdf5.h5f.root, dataname, datatype, (0,),filters=datacompressor))
                    
    def _scale(self,data):
        clipped=numpy.where(data<self.datarange[0],self.datarange[0],data)
        clipped=numpy.where(clipped>self.datarange[1],self.datarange[1],clipped)
        return numpy.cast['uint16']((clipped+self.offset)*self.scale)
            
    def add(self,data):
        if data.shape[1]!=self.nchannels:
            raise RuntimeError('Invalid number of channels: {0}, expected: {1}, data.shape: {2}'.format(data.shape[1],self.nchannels,data.shape))
        getattr(self, self.dataname).append(self._scale(data))
        self.hdf5.h5f.flush()
#        getattr(self, self.dataname).append(data)
            
    def close(self):
        self.hdf5.close()
        

def generate_animal_filename(animal_parameters):
    '''
    Generate animal file name from animal parameters.
    '''
    if '_' in animal_parameters['strain']:
        raise RuntimeError('Strain name cannot contain \"_\": {0}'.format(animal_parameters['strain']))
    filename = 'animal_{0}_{1}_{2}_{3}_L{4}R{5}.hdf5'.format(animal_parameters['id'], 
                                                                                            animal_parameters['strain'], 
                                                                                            animal_parameters['birth_date'] , 
                                                                                            animal_parameters['injection_date'],
                                                                                            animal_parameters['ear_punch_left'], 
                                                                                            animal_parameters['ear_punch_right'])
    return filename
    
def parse_animal_filename(filename):
    '''
    Parses animal parameters from animal filename
    '''
    parts = filename[:-4].split('_')
    animal_parameters={}
    animal_parameters['injection_date'] = parts[-2]
    animal_parameters['birth_date'] = parts[-3]
    animal_parameters['strain'] = parts[-4]
    animal_parameters['id'] = '_'.join(parts[1:-4])
    animal_parameters['ear_punch_left'] = parts[-1][1]
    animal_parameters['ear_punch_right'] = parts[-1][3]
    return animal_parameters
    
def is_animal_file(filename):
    fn = os.path.split(filename)[1]
    if is_first_tag(fn, 'animal_') and os.path.splitext(fn)[1] == '.hdf5':
        return True
    else:
        return False
    
def copy_reference_fragment_files(reference_folder, target_folder):
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)
    shutil.copytree(reference_folder, target_folder)
    return find_files_and_folders(target_folder, extension = 'hdf5',filter='fragment')[1]
    
def get_id_node_name_from_path(path):#Using similar function from component guesser may result segmentation error.
    return '_'.join(os.path.split(path)[1].split('.')[-2].split('_')[-3:])
#OBSOLETE
def get_measurement_file_path_from_id(id, config, filename_only = False, extension = 'hdf5', subfolders =  False):
    if hasattr(config, 'EXPERIMENT_DATA_PATH'):
        folder = config.EXPERIMENT_DATA_PATH
    else:
        folder = config
    if isinstance(folder, str) and os.path.exists(folder):
        path = filtered_file_list(folder,  [id, '.'+extension], fullpath = True, filter_condition = 'and')
        if len(path)==0:
            return
        path = path[0]
        if filename_only: 
            return os.path.split(path)[1]
        else:
            return path
#OBSOLETE
def find_file_from_timestamp(dir, timestamp):
    #from visexpman.engine.generic.fileop import dirListing
    from visexpA.engine.component_guesser import get_mes_name_timestamp
    files = dirListing(dir, ['.hdf5'], dir)
    matching = [f for f in files if str(int(timestamp)) in f]
    if len(matching)==0: # no filename contained the timestamp, go and open those hdf5 files that have no timestamp in their names
        stamps = [get_mes_name_timestamp(f)[1] for f in files]
        matching = [f for s, f in zip(stamps, files) if s is not None and str(int(s))==str(int(timestamp))]
    if len(matching)==0: return None
    else: return matching[0]

#OBSOLETE
def convert_path_to_remote_machine_path(local_file_path, remote_machine_folder, remote_win_path = True):
    filename = os.path.split(local_file_path)[-1]
    remote_file_path = os.path.join(remote_machine_folder, filename)
    if remote_win_path:
        remote_file_path = remote_file_path.replace('/',  '\\')
    return remote_file_path
#OBSOLETE    
def parse_fragment_filename(path):
    fields = {}
    filename = os.path.split(path)[1]
    if '.hdf5' in path:
       filename = filename.replace('.hdf5', '')
    elif '.mat' in path:
        filename = filename.replace('.mat', '')
    else:
        return fields
    filename = filename.split('_')
    if len(filename) == 1:
        return None
    fields['scan_mode'] = filename[1]
    fields['depth'] = filename[-4]
    fields['stimulus_name'] = filename[-3]
    fields['id'] = filename[-2]
    fields['fragment_id'] = filename[-1]
    fields['region_name'] = '_'.join(filename[2:-4])
    return fields

################# Not fileop related ####################

def compare_timestamps(string1, string2):
        '''Finds timestamps in the strings and returns true if the timestamps are the same'''
        ts1 = timestamp_re.findall(str(string1))[0]
        ts2 = timestamp_re.findall(str(string2))[0]
        if int(ts1)==int(ts2): return True
        else: return False


################# Others ####################

def BackgroundCopier(command_queue,postpone_seconds = 60, thread=1,debug=0):
    if thread:
        base = threading.Thread
    else:
        base = multiprocessing.Process
    class BackgroundCopierClass(base):
        '''Background copier function: provide source,target path tuples in src_dst_list.
        The first item in src_dst_list is used to control the process: src_dst_list[0]=='active' means the process
        stays alive and copies any item put in the list.
        Exceptions are dumped into the message_list. Both lists should be Manager.list() instances.
        '''
        def __init__(self, command_queue,postpone_seconds = 60, thread=1,debug=0):
            self.isthread = thread
            self.command_queue=command_queue
            if thread:
                threading.Thread.__init__(self)
                self.message_out_queue=Queue.Queue()
            else:
                multiprocessing.Process.__init__(self)
                self.message_out_queue = multiprocessing.Queue()
            self.debug = debug
            self.postpone_seconds= postpone_seconds
            self.parentpid = os.getpid() #init is executed in the parent process
            self.timeout=0.5 #sec
            
        def run(self):
            self.logfile=open('/tmp/log.txt','w+')
            try:
                if self.isthread:
                    self.postponed_list = [] #collects items that could not be copied for any reason
                else:
                    self.manager = multiprocessing.Manager()
                    self.postponed_list = self.manager.list() #collects items that could not be copied for any reason
                    self.pid1 = self.manager.Value('i',0)
                    self.pid1.set(os.getpid())
                while 1:
                    # make sure this process terminates when parent is no longer alive
                    if not self.isthread:
                        p = psutil.Process(os.getpid())
                        #self.message_out_queue.put('Bg pid:{0}, parentpid:{1}, current parentpid{2}'.format(p.pid,self.parentpid,p.parent.pid))
                        if p.parent.pid!=self.parentpid:
                            if debug:
                                self.logfile.write( 'Parent died?')
                            self.close()
                            return
                        else:
                            if self.debug:
                                self.logfile.write('pid:{1},current time:{0}'.format(time.time(),os.getpid()))
                            self.logfile.flush()
                    if self.command_queue.empty() and len(self.postponed_list)==0:
                        time.sleep(0.5)
                        file_list = []
                        if self.debug:
                            pass#self.message_out_queue.put('No message',True,self.timeout)
                    elif not self.command_queue.empty(): #first process new commands
                        file_list = [self.command_queue.get(True,self.timeout)]
                    elif len(self.postponed_list)>0: #no commands but some leftovers
                        if debug:
                            self.logfile.write('sleeping to process postponded list\n')
                            self.logfile.flush()
                        time.sleep(self.postpone_seconds)
                        if self.debug:
                            self.message_out_queue.put('Retrying after '+str(self.postpone_seconds)+' seconds',True,self.timeout)
                        file_list = self.postponed_list[:]
                    else:
                        if self.debug:
                            self.logfile.write('nothing to do\n');self.logfile.flush()
                        continue
                    if debug and self.isthread:
                        print file_list
                    for item in file_list:
                        try:
                            current_exception=''
                            if item=='TERMINATE':
                                self.close()
                                return
                            source=item[0]; target  = item[1]
                            try:
                                if not os.path.exists(source):
                                    current_exception='source file does not exist {0}'.format(item)
                                elif not os.path.exists(target) or (os.path.exists(target) and os.stat(source).st_size!=os.stat(target).st_size):
                                    shutil.copy(source, target)
                                    if os.path.exists(target) and os.stat(source).st_size==os.stat(target).st_size:
                                        if self.debug:
                                            current_exception='File '+source+' copied OK'
                                else:
                                    current_exception = '{0} has same size as {1}'.format(source, target)
                            except Exception as e:
                                current_exception=str(e)
                                print e
                                self.postponed_list.append((source,target))
                            if item in self.postponed_list:
                                self.postponed_list.remove(item)
                            self.message_out_queue.put(current_exception,True,self.timeout)
                        except Exception as e:
                            self.logfile.write(str(e))
            except Exception as e:
                self.logfile.write(str(e))
                self.logfile.flush()
               
        def close(self):
            try:
                self.manager.shutdown()
                children = psutil.Process(os.getpid()).get_children(recursive=True)
                self.logfile.write('no of children:{0}'.format(len(children)))
                for c1 in children:
                    c1.kill()
                    self.logfile.write('{0} with pid {1} killed\n'.format(c1.name,c1.pid))
                    self.logfile.flush()
            except Exception as e:
                self.logfile.write(str(e))
                self.logfile.flush()
            if self.debug:
                self.logfile.write('logfile close')
                self.logfile.close()

    return BackgroundCopierClass(command_queue,postpone_seconds, thread,debug)

def getziphandler(zipstream):
    '''convenience wrapper that returns the zipreader object for both a byte array and a string containing 
    the filename of the zip file'''
    import cStringIO,  zipfile
    if hasattr(zipstream, 'data'):
        sstream = cStringIO.StringIO(zipstream.data) # zipfile as byte stream
    else:
        sstream = zipstream #filename
    return zipfile.ZipFile(sstream)

def check_png_hashes(fname,function,*args,**kwargs):
        '''Checks whether the function code and argument hashes exist in the png file and updates them if necessary'''
        try:
            import Image
        except ImportError:
            from PIL import Image 
        from visexpA.engine.dataprocessors.generic import check_before_long_calculation
        fh=None;ah=None
        if os.path.exists(fname):
            oldpng = Image.open(fname)
            if 'function_hash' in oldpng.info:
                fh = oldpng.info['function_hash']
            if 'function_arguments_hash' in oldpng.info:
                ah = oldpng.info['function_arguments_hash']
        else: ah=fh=None
        new_fh, new_ah = check_before_long_calculation(fh, function,ah,*args,**kwargs)
        if new_fh is None: 
            return None
        else:
            return {'function_hash':new_fh, 'function_arguments_hash':new_ah}

def pngsave(im, file):
    '''Wrapper around PIL png writer that properly handles metadata'''
    # these can be automatically added to Image.info dict                                                                              
    # they are not user-added metadata
    reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect')

    # undocumented class
    from PIL import PngImagePlugin
    meta = PngImagePlugin.PngInfo()

    # copy metadata into new object
    for k,v in im.info.iteritems():
        if k in reserved: continue
        meta.add_text(k, v, 0)

    # and save
    im.save(file, "PNG", pnginfo=meta)
    
def download_folder(server, user, src,dst,port=22,password=None):
    import paramiko,zipfile
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=user,port=port,password=password)
    tmpzip='/tmp/download.zip'
    i,o,e1=ssh.exec_command('rm -f {0}'.format(tmpzip))
    #*.pack: git repository specific, takes up a lot of space
    i,o,e3=ssh.exec_command('cd {0};zip -0 -r {1} {2} -x *.pack'.format(os.path.dirname(src),tmpzip,os.path.basename(src)))
    for e in [e1,e3]:
        emsg=e.readline()
        if emsg!='':
            raise RuntimeError(emsg)
    sftp=ssh.open_sftp()
    localzip=os.path.join(tempfile.gettempdir(),'download.zip')
    if os.path.exists(localzip):
        os.remove(localzip)
    sftp.get(tmpzip,localzip)
    zip_ref = zipfile.ZipFile(localzip, 'r')
    zip_ref.extractall(dst)
    zip_ref.close()
    sftp.close()
    ssh.close()
    os.remove(localzip)
    
    
################# End of functions ####################  

import unittest
class TestFileops(unittest.TestCase):
    def setUp(self):
        import tempfile,os
        f,self.filename = tempfile.mkstemp(suffix='.png')
        os.close(f)

    def tearDown(self):
        os.remove(self.filename)
        pass
        
    @unittest.skip('')
    def test_01_pngsave(self):
        import numpy
        try:
            import Image
        except ImportError:
            from PIL import Image
        from visexpman.engine.generic.introspect import hash_variables
        pic = numpy.zeros((233,234),numpy.uint8)
        pic[0,233]=255
        pilpic = Image.fromarray(pic)
        pilpic.info['mycomment']='my text is short'
        pilpic.info['myhash']= hash_variables(pic)
        pngsave(pilpic,self.filename)
        pilconfirm = Image.open(self.filename)
        self.assertTrue((pilconfirm.info['mycomment']==pilpic.info['mycomment']) and (pilconfirm.info['myhash']==pilpic.info['myhash']))
        pass
        
    @unittest.skip('Starts a process and blocks other tests, needs to be fixed')
    def test_02_copier(self):
        from multiprocessing import Process,Manager
        import threading
        def message_printer(message_list):
            while 1:
                if message_list.empty():
                    time.sleep(0.4)
                    #print 'message list empty'
                else:
                    while not message_list.empty():
                        msg= message_list.get()
                        print msg
                        if msg=='TERMINATE':
                            return
        print os.getpid()
        killit=1
        sourcedir = tempfile.mkdtemp()
        targetdir = tempfile.mkdtemp()
        files = [tempfile.mkstemp(dir=sourcedir,suffix=str(i1)+'.png')[1] for i1 in range(5)]
        [ numpy.savetxt(f1, numpy.random.rand(128,)) for f1 in files]
        srcdstlist = zip(files, [os.path.join(targetdir,os.path.split(f1)[1]) for f1 in files])
        command_queue = multiprocessing.Queue()
        p1 = BackgroundCopier(command_queue,postpone_seconds=5,debug=1,thread=0)
        lister = threading.Thread(target=message_printer, args=(p1.message_out_queue,))
        lister.start()
        p1.start()
        for item in srcdstlist:
            command_queue.put(item)
        if killit and not p1.isthread:
            import signal
            children = psutil.Process(os.getpid()).get_children(recursive=True)
            print('no of children:{0}'.format(len(children)))
            for c1 in children:
                print('child pid {0} name {1}'.format(c1.pid,c1.name))
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGKILL) #kill parent process and see whether child processes quit automatically
            return
        command_queue.put('TERMINATE')
        p1.join()
        p1.message_out_queue.put('TERMINATE') #shuts down listener thread
        lister.join()
        pass
        
    @unittest.skip('')
    def test_03_parse_animal_filename(self):
        ap = {'imaging_channels': 'green', 'red_labeling': 'no', 'green_labeling': 'label', 
        'injection_target': '', 'ear_punch_left': '2', 'comment': 'tbd', 'strain': 'strain1', 
        'ear_punch_right': '1', 'gender': 'male', 
        'birth_date': '1-1-2013', 'injection_date': '1-5-2013', 'id': 'test_ID'}
        ap_parsed = parse_animal_filename(generate_animal_filename(ap))
        for k in ['imaging_channels', 'red_labeling', 'green_labeling', 'injection_target', 'comment', 'gender']:
            del ap[k]
        self.assertEqual(ap, ap_parsed)
        
    @unittest.skip('')
    def test_04_dataacq_file(self):
        daf=DataAcquisitionFile(5,'sync', [-10.0,20.0])
        dd=numpy.empty((0,5))
        for i in range(20):
            s=2
            d=numpy.array(5*range(s)).reshape(5,s).T+0.1*i-8
            d[:,1]*=0.5
            daf.add(d)
            dd=numpy.append(dd,d,axis=0)
        daf.close()
        import hdf5io
        h=hdf5io.Hdf5io(daf.filename, filelocking=False)
        h.load('sync')
        s=h.findvar('sync_scaling')
        numpy.testing.assert_array_almost_equal(h.sync/s['scale']-s['offset'],dd,3)
        h.close()
        
    @unittest.skip('')    
    def test_05_move2zip(self):
        from visexpman.engine.generic import introspect
        with introspect.Timer(''):
            move2zip(['/mnt/rzws/temp/0_aodev/data_GrayBackgndOnly5min_201612132042235.hdf5', 
                    '/mnt/rzws/temp/0_aodev/data_GrayBackgndOnly5min_201612132042235.mat'],
                    '/mnt/rzws/temp/0_aodev/outfolder')
                    
    def test_06_download_folder(self):
        from visexpman.engine.generic import introspect
        with introspect.Timer():
            download_folder('192.168.1.4', 'rz','/data/codes/visexpman', '/tmp',9128)
        
if __name__=='__main__':
#    import sys
#    print sys.argv
#    if len(sys.argv)==3 and sys.argv[1] == 'total_size':
#        print 'Total size:'+str(total_size(sys.argv[2]))
#    elif len(sys.argv)==4 and sys.argv[1] == 'dirListing':
#        print 'dirListing:'
#        print  dirListing(sys.argv[2], sys.argv[3], sys.argv[2])
#    else:
        unittest.main()
