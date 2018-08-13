import os, re
import os.path
import shutil
import numpy
import tempfile
import time
import subprocess as sub
import multiprocessing,threading,queue
import time
from distutils import file_util,  dir_util
try:
    import psutil
except ImportError:
    pass
timestamp_re = re.compile('.*(\d{10,10}).*')

def wait4file_ready(f,timeout=60):
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
        if filesize==filesize_prev:
            break
        else:
            filesize_prev=filesize
            time.sleep(0.2)
        if time.time()-t0>timeout:
            raise RuntimeError('Wait for {} file timeout'.format(f))

def select_folder_exists(folders):
    for folder in folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            return folder
            
def delete_old_files(folder,minimum_age=100):
    files=find_files_and_folders(folder)[1]
    now=time.time()
    nfiles=len([os.remove(f) for f in files if now-os.path.getmtime(f)>86400*minimum_age])
    return nfiles

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
                self.message_out_queue=queue.Queue()
            else:
                multiprocessing.Process.__init__(self)
                self.message_out_queue = multiprocessing.Queue()
            self.debug = debug
            self.postpone_seconds= postpone_seconds
            self.parentpid = os.getpid() #init is executed in the parent process
            self.timeout=0.5 #sec
            
            
        def run(self):
            import logging
            logging.basicConfig(filename= '/mnt/datafast/log/background_copier.txt',
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
            fn = generate_filename('/tmp/log.txt')
            self.logfile=open(fn,'w+')
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
                        if p.parent().pid!=self.parentpid:
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
                        print(file_list)
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
                                    logging.info('{0} -> {1}'.format(source, target))
                                    if os.path.exists(target) and os.stat(source).st_size==os.stat(target).st_size:
                                        if self.debug:
                                            current_exception='File '+source+' copied OK'
                                else:
                                    current_exception = '{0} has same size as {1}'.format(source, target)
                            except Exception as e:
                                current_exception=str(e)
                                print(e)
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
                children = psutil.Process(os.getpid()).children(recursive=True)
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

def free_space(path):
    """ Return folder/drive free space (in bytes)
    """
    import platform
    if platform.system() == 'Windows':
        import ctypes
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        s=os.statvfs(path)
        return (s.f_bavail * s.f_frsize)

def file_open_by_other_process(filename):
    '''Checks whether the given file is open by any process'''
    ccmd = 'lsof -Fp '+filename
    p=sub.Popen(ccmd, shell=True)
    res= p.communicate()
    pids = re.findall('p(\d+)', res)
    if len(pids)<1: return False
    elif len(pids)>1 or pids[0]!=os.getpid():return True

def compare_timestamps(string1, string2):
        '''Finds timestamps in the strings and returns true if the timestamps are the same'''
        ts1 = timestamp_re.findall(str(string1))[0]
        ts2 = timestamp_re.findall(str(string2))[0]
        if int(ts1)==int(ts2): return True
        else: return False

def copy_reference_fragment_files(reference_folder, target_folder):
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)
    shutil.copytree(reference_folder, target_folder)
    return find_files_and_folders(target_folder, extension = 'hdf5',filter='fragment')[1]
    
def get_id_node_name_from_path(path):#Using similar function from component guesser may result segmentation error.
    return '_'.join(os.path.split(path)[1].split('.')[-2].split('_')[-3:])

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
            
def get_tmp_file(suffix, delay = 0.0):
    path = os.path.join(tempfile.gettempdir(), 'tmp.' + suffix)
    if os.path.exists(path):
        os.remove(path)
    time.sleep(delay)
    return path
def folder_signature(folder):
    '''
    Signature consist of: number of files, overall file size, latest modification date
    '''
    files=find_files_and_folders(folder)[1]
    return (len(files), sum([os.path.getsize(f) for f in files]), max([os.path.getmtime(f) for f in files]))
    

def mkstemp(suffix=None, filename = None):
    '''Creates a temporary file with suffix as extension, e.g. .pdf. Closes the file so that other methods can open it and do what they need.'''        
    if filename is not None:             
        return os.path.join(tempfile.gettempdir(), filename)
    else:
        f,filename = tempfile.mkstemp(suffix=suffix)
        os.close(f)
        return filename
    
def set_file_dates(path, file_info):
    try:
        os.utime(path, (file_info.st_atime, file_info.st_mtime))
    except:
        pass

def mkdir_notexists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
        
def recreate_dir(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def copy(src, dst, update=1):
    if not os.path.exists(src):
        raise OSError('File or directory {0} does not exist'.format(src))
    if os.path.isfile(src): 
        dir_util.mkpath(os.path.split(dst)[0])
        return file_util.copy_file(src, dst, update=1)
    else: 
        dir_util.mkpath(dst)
        return dir_util.copy_tree(src, dst, update=1)

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

def getziphandler(zipstream):
    '''convenience wrapper that returns the zipreader object for both a byte array and a string containing 
    the filename of the zip file'''
    import io,  zipfile
    if hasattr(zipstream, 'data'):
        sstream = io.StringIO(zipstream.data) # zipfile as byte stream
    else:
        sstream = zipstream #filename
    return zipfile.ZipFile(sstream)

def parsefilename(filename, regexdict):
    '''From a string filename extracts fields as defined in a dictionary regexdict. 
    Data will be put into a directory with the same keys as found in regextdict.
    The value of each regextdict key must be a list. The first element of the list
    is a regular expression that tells what to extract from the string. The second element
    is a python class that is used to convert the extracted string into a number (if applicable)
    '''
    import re
    for k,v in list(regexdict.items()):
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

def filtered_file_list(folder_name,  filter, fullpath = False, inverted_filter = False, filter_condition = None):    
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

def find_file_from_timestamp(dir, timestamp):
    #from visexpman.engine.generic.string import dirListing
    from visexpA.engine.component_guesser import get_mes_name_timestamp
    files = dirListing(dir, ['.hdf5'], dir)
    matching = [f for f in files if str(int(timestamp)) in f]
    if len(matching)==0: # no filename contained the timestamp, go and open those hdf5 files that have no timestamp in their names
        stamps = [get_mes_name_timestamp(f)[1] for f in files]
        matching = [f for s, f in zip(stamps, files) if s is not None and str(int(s))==str(int(timestamp))]
    if len(matching)==0: return None
    else: return matching[0]

def read_text_file(path):
    f = open(path,  'rt')
    txt =  f.read(os.path.getsize(path))
    f.close()
    return txt
    
def write_text_file(filename, content):
    f = open(filename,  'wt')
    f.write(content)
    f.close()

def listdir_fullpath(folder):
    files = os.listdir(folder)
    full_paths = []
    for file in files:
        full_paths.append(os.path.join(folder,  file))
    return full_paths

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

    if isinstance(ext,str):
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
        dirs, modtimes = list(zip(*sorted(zip(dirs,lastmod), key=itemgetter(1))))
    if noext: # remove extensions
        dirs = [item[:item.rfind('.')] for item in dirs]
    if fullpath:
        dirs = [os.path.join(directory, fn) for fn in dirs]
    return dirs


def find_latest(path):
    number_of_digits = 5
    latest_date = 0
    latest_file = ''
    for file in listdir_fullpath(os.path.split(path)[0]):
        if file.find(os.path.split(path)[-1].split('.')[0][:-number_of_digits]) != -1:
            file_date = os.path.getmtime(file)
            if latest_date < file_date:
                latest_date = file_date
                latest_file = file
    return latest_file
     
def find_content_in_folder(content, folder_name, file_filter):
    found_in_files = []
    for file in filtered_file_list(folder_name,  file_filter, fullpath = True):
        if content in read_text_file(file):
            found_in_files.append(file)
    return found_in_files
    
import os
try:
    import pwd
except ImportError:
    pass
    
def get_username():
    import platform
    if platform.system()=='Windows':
        import getpass
        return getpass.getuser()
    else:
        return pwd.getpwuid( os.getuid() )[ 0 ]
    
    
def generate_filename(path, insert_timestamp = False, last_tag = ''):
    '''
    Inserts index into filename resulting unique name.
    '''
    index = 0
    number_of_digits = 5
    while True:
        if last_tag != '':
            testable_path = path.replace('.',  '_%5i_%s.'%(index, last_tag)).replace(' ', '0')
        else:
            testable_path = path.replace('.',  '_%5i.'%index).replace(' ', '0')
        if not os.path.isfile(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Filename cannot be generated')
    if insert_timestamp:
        testable_path = path.replace('.',  '_%i_%5i.'%(int(time.time()), index)).replace(' ', '0')
    return testable_path
    
def generate_foldername(path):
    '''
    Inserts index into foldername resulting unique name.
    '''
    number_of_digits = 5
    index = 0
    while True:
        testable_path = (path + '_%5i'%index).replace(' ', '0')
        if not os.path.isdir(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Foldername cannot be generated')
    return testable_path

def convert_path_to_remote_machine_path(local_file_path, remote_machine_folder, remote_win_path = True):
    filename = os.path.split(local_file_path)[-1]
    remote_file_path = os.path.join(remote_machine_folder, filename)
    if remote_win_path:
        remote_file_path = remote_file_path.replace('/',  '\\')
    return remote_file_path


def check_png_hashes(fname,function,*args,**kwargs):
        '''Checks whether the function code and argument hashes exist in the png file and updates them if necessary'''
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
    for k,v in im.info.items():
        if k in reserved: continue
        meta.add_text(k, v, 0)

    # and save
    im.save(file, "PNG", pnginfo=meta)
    
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


import unittest
class TestUtils(unittest.TestCase):
    def setUp(self):
        import tempfile,os
        f,self.filename = tempfile.mkstemp(suffix='.png')
        os.close(f)

    def tearDown(self):
        os.remove(self.filename)
        pass
    @unittest.skip('')
    def test_pngsave(self):
        import numpy, Image
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
        
    def test_copier(self):
        from multiprocessing import Process,Manager
        from visexpman.engine.hardware_interface.network_interface import ZeroMQPusher
        import threading
        def message_printer(message_list):
            while 1:
                if message_list.empty():
                    time.sleep(0.4)
                    #print 'message list empty'
                else:
                    while not message_list.empty():
                        msg= message_list.get()
                        print(msg)
                        if msg=='TERMINATE':
                            return
        print(os.getpid())
        killit=1
        sourcedir = tempfile.mkdtemp()
        targetdir = tempfile.mkdtemp()
        files = [tempfile.mkstemp(dir=sourcedir,suffix=str(i1)+'.png')[1] for i1 in range(5)]
        [ numpy.savetxt(f1, numpy.random.rand(128,)) for f1 in files]
        srcdstlist = list(zip(files, [os.path.join(targetdir,os.path.split(f1)[1]) for f1 in files]))
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
            print(('no of children:{0}'.format(len(children))))
            for c1 in children:
                print(('child pid {0} name {1}'.format(c1.pid,c1.name)))
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGKILL) #kill parent process and see whether child processes quit automatically
            return
        command_queue.put('TERMINATE')
        p1.join()
        p1.message_out_queue.put('TERMINATE') #shuts down listener thread
        lister.join()
        pass
        
        
if __name__=='__main__':
    unittest.main()
