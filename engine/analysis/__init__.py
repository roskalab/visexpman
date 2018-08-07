import unittest
from visexpman.engine.generic import fileop

class FileProcessor(object):
    '''
    Class for iterating across files and executing operations on each defined by target and kwargs
    '''
    def __init__(self, target, folder, extension=None, verbose=False, kwargs={}):
        if extension[0]=='.':
            extension=extension[1:]
        self.verbose=verbose
        self.files=fileop.find_files(folder,extension=extension)
        self.target=target
        self.kwargs=kwargs
        if self.verbose:
            print('found {0} files'.format(len(self.files)))
        
    def process(self):
        nfiles=len(self.files)
        i=1
        for f in self.files:
            if self.verbose:
                print ('{0}/{1} {2}'.format(i,nfiles,f))
            try:
                self.target(f, **self.kwargs)
            except:
                import traceback
                print(traceback.format_exc())
            i+=1
            
def process_file(filename, opt=None):
    import hdf5io
    hh=hdf5io.Hdf5io(filename)
    hh.close()
    print(opt)
            
class TestFileProcessor(unittest.TestCase):
    def test(self):
        t=FileProcessor(process_file, '/tmp/1', 'hdf5', verbose=True, kwargs={'opt':True})
        t.process()

            
if __name__ == "__main__":
    unittest.main()
