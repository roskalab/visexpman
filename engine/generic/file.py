import os, re
import os.path
import shutil
import numpy
import tempfile
import time
from distutils import file_util,  dir_util
timestamp_re = re.compile('.*(\d{10,10}).*')

def check_file_open(filename):
    '''Checks whether the given file is open by any process'''
    dlist = [d for d in os.walk('/proc') if len([filename in af for af in d[3]])>0]

def compare_timestamps(string1, string2):
        '''Finds timestamps in the strings and returns true if the timestamps are the same'''
        ts1 = timestamp_re.findall(str(string1))
        ts2 = timestamp_re.findall(str(string2))
        if ts1==ts2: return True
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
        os.mkdir(folder)

def copy(src, dst, update=1):
    if not os.path.exists(src):
        raise OSError('File or directory to be copied does not exist')
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
    import cStringIO,  zipfile
    if hasattr(zipstream, 'data'):
        sstream = cStringIO.StringIO(zipstream.data) # zipfile as byte stream
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

def find_file_from_timestamp(dir, timestamp):
    #from visexpman.engine.generic.file import dirListing
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

def listdir_fullpath(folder):
    files = os.listdir(folder)
    full_paths = []
    for file in files:
        full_paths.append(os.path.join(folder,  file))
    return full_paths

def dirListing(directory='~', ext = '', prepend='', dflag = False, sortit = False,  noext=False,  excludenames = []):
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
        import Image 
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
        
if __name__=='__main__':
    import sys
    print sys.argv
    if len(sys.argv)==3 and sys.argv[1] == 'total_size':
        print 'Total size:'+str(total_size(sys.argv[2]))
    elif len(sys.argv)==4 and sys.argv[1] == 'dirListing':
        print 'dirListing:'
        print  dirListing(sys.argv[2], sys.argv[3], sys.argv[2])
    else:
        unittest.main()
