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
    joined = os.path.join(*items)
    return joined.replace('/', '.')
    
def split(dotted_path):
    slashed = dotted_path.replace('.', '/')
    path, name = os.path.split(slashed)
    return path.replace('/', '.'),  name
    
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
