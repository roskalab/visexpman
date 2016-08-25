'''Collection of methods that work on (list of) strings'''
import re
import numpy
import os
import unittest

def str2params(par_str):
    '''
    String containing comma separated numbers is converted to a list if floats
    '''
    try:
        return map(float, str(par_str).split(','))
    except ValueError:
        return []

def long_substr(data):
    '''extracts longest common substring from a list of strings'''
    substr = ''
    if len(data) > 1 and len(data[0]) > 0:
        for i in range(len(data[0])):
            for j in range(len(data[0])-i+1):
                if j > len(substr) and all(data[0][i:i+j] in x for x in data):
                    substr = data[0][i:i+j]
    return substr

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
    joined = os.path.join(*items)
    return joined.replace('/', '.')
    
def split(dotted_path):
    slashed = dotted_path.replace('.', '/')
    path, name = os.path.split(slashed)
    return path.replace('/', '.'),  name


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
    
def to_variable_name(s):
    return s.lower().replace(' ', '_')
    
def to_title(s):
    return s.replace('_', ' ').title()
    
def string_in_list(list_of_string, keyword, return_match=False, any_match = False):
    '''
    Checks if keyword is in any items of list
    '''
    if return_match:
        result = [item for item in list_of_string if keyword in item or (any_match and item in keyword)]
        if len(result) == 1:
            return result[0]
    else:
        return len([item for item in list_of_string if keyword in item or (any_match and item in keyword)]) > 0

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
