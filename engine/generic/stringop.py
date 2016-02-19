'''Collection of methods that work on (list of) strings'''
import re
import numpy
import os
import unittest

def extract_common_string(flist, to_remove=['\)-r\d-']):
    ''' Locates '-rx-' part in filenames (where -rx- mean repetition x) and tries to find filenames that differ
    only in x but otherwise are identical,i.e. these files represent repeated trials of the stimulus. Returns the 
    strings without the varying parts
    '''
    flist2 = flist[:]
    for k in to_remove: # remove varying parts from the strings
        ss = re.compile(k)
        flist2= [ss.sub('', i) for i in flist2]
    flistu,  indices = numpy.unique(flist2, return_inverse=True)
    commons   =[]
    for i in numpy.unique(indices):
        commons.append([flist2[i1] for i1 in numpy.where(indices==i)[0]][0])
    return  commons

def join(*args):
    '''Same functionality as os.path.join but for paths using dot as separator'''
    items = [text.replace('.', '/') for text in args]
    joined = '/'.join(items)
    return joined.replace('/', '.')
    
def split(dotted_path):
    slashed = dotted_path.replace('.', '/')
    path, name = os.path.split(slashed)
    return path.replace('/', '.'),  name
    
def dirListing(directory='~', ext = '', prepend='', dflag = False, sort = False,  noext=False):
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
    except OSError:
        return ''
    if len(prepend)>0 and prepend[-1] != os.sep:
        prepend = prepend + os.sep
                #get just the directories
    for x in listing:
        cext = next((ex for ex in ext if re.search(ex+'$',x) is not None), None)
        id = (os.path.isdir(directory+os.sep+x))
        if id and (dflag == True or len(ext)==0):# just include the subdirectory in the result list
            dirs.append(prepend+x)
            lastmod.append(os.stat(os.path.join(directory,x))[8])
        elif not id and cext is not None and len(cext) > 0 and not x[0] == '.':# and not id: # add matching files, exclude hidden files whose name starts with .
            dirs.append(prepend+x)
            lastmod.append(os.stat(os.path.join(directory,x))[8])
        elif id or cext is None: # recursive call to look in subdirectories if dirname does not contain the extension
            rdirs = dirListing(directory+os.sep+x, ext, prepend+x, dflag)
            if not os.path.exists(prepend+x): # create directory
                os.makedirs((prepend+x))
            dirs.extend(rdirs[:])
    if sort:
        from operator import itemgetter
        dirs, modtimes = zip(*sorted(zip(dirs,lastmod), key=itemgetter(1)))
    if noext: # remove extensions
        dirs = [item[:item.rfind('.')] for item in dirs]
    return dirs

def array2string(inarray):
    if inarray.ndim == 2:
        a = ["%.3g "*inarray.shape[1] % tuple(x) for x in inarray]
    elif inarray.ndim == 1:
        a = [str(x) for x in inarray]
    return numpy.array(a)

def get_recent_file(flist, ref_date = None, mode = 'earlier', interval=numpy.Inf):
    '''
    Checks the date of each file in the list and returns the most recent one.
    If ref_date is provided then returns the file closest in time. If interval is set then only returns files
    that were created within time limit from ref_date.
    '''
    import time
    if len(flist) == 0:
        raise StandardError("Empty list provided")
    lastmod_date = []
    for f in range(len(flist)):
        stats = os.stat(flist[f])
        lastmod_date.append(time.localtime(stats[8]))
    if ref_date is None:
        lm = lastmod_date.index(max(lastmod_date))
    else:
        datediff = numpy.asarray([time.mktime(ref_date) - time.mktime(fdate) for fdate in lastmod_date])
        try:
            if mode=='earlier': #get the file created before the ref_date
                valids = numpy.where(numpy.logical_and(datediff>=0,  datediff<interval))[0]
                lm = valids[numpy.where(datediff[valids]==min(datediff[valids]))[0]]
            elif mode == 'later':
                valids = numpy.where(numpy.logical_and(datediff<=0,  datediff>-1*interval))[0]
                lm = valids[numpy.where(datediff[valids]==max(datediff[valids]))[0]]
            elif mode == 'closest': #earlier or later does not matter, closest in time
                lm = numpy.where(numpy.logical_and(abs(datediff) == min(abs(datediff)), abs(datediff) < abs(interval)))[0]
        except:
            lm = []#raise IOError("No file found that matches the creation date limit")
    if len(lm)>1:
        raise ValueError('More than one file matches time criterium. Files created at exactly same times?')
    elif len(lm)==1: 
        lm=lm[0]
    return numpy.array(flist)[lm], numpy.array(lastmod_date)[lm]

class TestUtils(unittest.TestCase):
    def setUp(self):
        pass
            
    def tearDown(self):
        pass

    def test_01_join_split(self):
        path = 'level1.level2'
        add = 'level3'
        self.assertEqual(split(join(path, add)),(path,add, ))
    

if __name__=='__main__':
    unittest.main()
