
'''
The hdf5io module is a class that should be inherited. It provides methods to automatically save, load data from a hdf5 file 
and recreate derived data types.
'''
import sys, traceback, pdb
try:
    import Image
except ImportError:
    from PIL import Image
import zc.lockfile
import numpy
import re
#import Helpers
#from Helpers import normalize, rc,  introspect.acquire,  imshow
import visexpman.engine.generic.introspect as introspect
from visexpman.engine.generic.introspect import full_exc_info
from visexpman.engine.generic.stringop import split, join
from visexpman.engine.generic import fileop
import os
from subprocess import *
import tables
import StringIO
import cStringIO
import zipfile
import time
import datetime
import math
import traceback
#import PyQt4.QtCore as QtCore
try:
    import PyQt4.QtCore as QtCore
except ImportError:
    print "Try importing PySide.QtCore"
    try:
        import PySide.QtCore as QtCore
    except ImportError:
        raise Exception("hdf5io.py requires either PyQt4 or PySide; neither package could be imported.")


import logging
import shutil
import threading,  Queue
from contextlib import contextmanager
log = logging.getLogger('hdf5io')
import warnings
warnings.filterwarnings('ignore',category=tables.NaturalNameWarning)
try: 
    import psutil    
    RAMLIMIT = psutil.virtual_memory().free*0.7
except:
    RAMLIMIT = 2*10**9 #2Gb
    pass
    
class GlobalThreadLocks(threading.Thread):
    '''Class that keeps a global dict of lock objects. Locks have to be created with the create method since dict is not thread safe
    so we mush ensure there are no concurrent write operations to the lock dict. Once there is an entry with a lock it can safely be read
    by other threads to share the lock object. So there is a small speed penalty when creating the lock entry but virually no speed sacrifice
    when accessing the lock.'''
    
    def __init__(self):
        self.lockpool = {}
        self.queue = Queue.Queue()
        self.terminatesignal = object()
        threading.Thread.__init__(self)
        self.daemon=True
    
 #  def __del__(self): just let thread be terminated when main process stops?
  #      self.queue.put(self.terminatesignal)
        
    def run(self):
        while 1:
            command = self.queue.get(True)
            if command is self.terminatesignal: break
            if command[0] =='create': # (create, filename, lock object, threading.event)
                self.lockpool[command[1]] = command[2]
           # elif command[0] =='remove': #ever use this?
              #  del self.lockpool[command[1]]
                command[3].set()
    
    def create(self, key,  lockobject):
        if key in self.lockpool: 
           # print key+' lock alread exists'
            return
        signal = threading.Event()
        self.queue.put(('create', key, lockobject, signal))
        signal.wait()

class GlobalLock(object):
    def __init__(self):
        self.lock=threading.RLock()
        
    @contextmanager
    def acquire(self, block):
        if self.lock.acquire(block) is False:
            print 'already locked'
            pdb.set_trace()
            raise RuntimeError('Cannot lock object,  it is already locked in another thread')
        yield
        self.lock.release()
        
    def release(self):
        self.lock.release()

if not hasattr(sys.modules[__name__], 'lockman'): #module might be imported multiple times but we only need a single class
    lockman = GlobalThreadLocks()
    lockman.start()

class Hdf5io(object):
    ''' 
    Handles data between RAM and hdf5 file. 
The create_ functions should not expect any parameters but have to access data from self so that these methods can be called in a loop.
    '''
    maxelem =5 #number of digits defining how many items a list of dicts or list of lists can have. 5 means 999999
    elemformatstr = '{0:0'+str(maxelem)+'g}'
    def __init__(self,filename, config=None, name = None, file_always_open=True,  filelocking=True):
        '''
        Opens/creates the hdf5 file for reading/writing.
        '''
        if config is None and filelocking is True:
            raise RuntimeError('You cannot open a hdf5 file with locking enabled without providing a config object')
        if not hasattr(self, 'attrnames'):
            self.attrnames = []
        if not config is None and hasattr(config,'ramlimit'):
            self.ramlimit = min(RAMLIMIT,config.ramlimit)
        else:
            self.ramlimit = RAMLIMIT
        self.config = config
        self.filelocking=filelocking
        self.file_always_open = file_always_open
        self.pixellist = [] # there is one big data attribute handled by the class. In case of a series of 2D images, data is stored in chunks along pixels
        if hasattr(filename,'shape') and filename.shape==(1,):
            filename = filename[0]
        if not filename[-4:] == 'hdf5':
            raise NameError("HDF5 file name must have .hdf5 extension")
            return
        self.filename = filename
        cp, cf = os.path.split(self.filename)
        if not os.path.exists(cp):
            os.makedirs(cp)
        if os.path.exists(self.filename):
           if tables.is_pytables_file(self.filename) is None:
            # checks is file is usable, if not then renames current hdf5 file and starts a new one
            log.error(self.filename + "corrupted?")
            os.rename(self.filename, self.filename+'corrupted')
            raise RuntimeError('corrupted file?')
           else:
               filemode = 'a'
        else:
            filemode = 'a' # new file
        self.filelockkey = self.filename.replace('/', '\\') #introspect.ReadWriteLock() # this is different from file-based locking, that does not exclude multiple threads access the same open file and cause problems
        lockman.create(self.filelockkey, GlobalLock())
        self.blocking_lock = True
        self.open_with_lock(filemode)
     #   self.bind_finalizer('h5f')
        self.h5fpath = 'h5f.root'
        self.rawdatasource = join(self.h5fpath,'rawdata') #in memory, alternative is 'h5f.root' for disk mapped access
 #       self.rawdatasource = 'self.h5f.root.rawdata'
        if introspect.traverse(self, self.rawdatasource) is not None and self.attrsize('rawdata') <= self.ramlimit: #not too big to fit in memory:
            self.rawdatasource = 'rawdata' #will load to memory
        self._want_abort = 0
        log.debug('Opening '+self.filename)
#        self.command_queue=Queue.Queue()
   #     self.queueshutdown = object() #each thread has this object that has to be put in the command queue to stop the thread
    
    def open_with_lock(self, filemode='a'):
        with lockman.lockpool[self.filelockkey].acquire(False):
            try:
                if self.filelocking:
                    if not os.path.exists(os.path.join(self.config.temppath, 'filelocks')):
                        os.makedirs(os.path.join(self.config.temppath, 'filelocks'))
                    hdf5filelock_filename = os.path.join(os.path.join(self.config.temppath, 'filelocks', os.path.split(self.filename)[1][:-3]+'.lock'))
                    self.hdf5file_lock = zc.lockfile.LockFile(hdf5filelock_filename) # cross platform file lock, but puts an extra lock file in the file system
                self.h5f = tables.open_file(self.filename, mode = filemode)
                #list compression used to create CArrays in the file and check if pytables has the required library installed
                #the line below causes segfaul if hdf file is already open?
                carray_complib = [item.filters.complib for item in self.h5f.iter_nodes(self.h5f.root,'CArray')] # walknodes is slow for file containing lots of nodes
                if len(carray_complib)>0:
                    versions = [tables.which_lib_version(item) for item in carray_complib if item is not None]
                    if 0 and None in versions: # not in use but kept as a way to check complib versions
                        self.h5f.close()
                        if self.filelocking:self.hdf5file_lock.close()
                        raise RuntimeError('Compression library used for creating a CArray in this file is not available in the pytables installation on this computer')
            except zc.lockfile.LockError:
                with open(hdf5filelock_filename, 'r') as lockf:
                    lockf.seek(1)
                    pidinlock = lockf.read().strip()
                raise RuntimeError(str(os.getpid())+" cannot lock file "+self.filename+" that is currently locked by pid "+ pidinlock)
            except:
                traceback.print_exc()
                #pdb.post_mortem(full_exc_info()[2])
                raise RuntimeError("File cannot be opened, giving up.")
            finally:
                if hasattr(self, 'h5f') and self.h5f.isopen and not self.file_always_open:
                    self.h5f.close()
                if hasattr(self, 'hdf5file_lock') and self.filelocking:self.hdf5file_lock.close()
            
    
    def copy_file(self, newname, overwrite=False):
        '''copy, when file exists it will not overwrite'''
        if not overwrite and os.path.exists(newname):
            raise IOError('Destination hdf file exists and overwrite is set to False')
        newh = Hdf5io(newname,  self.config) #opens with locking
        newh.h5f.close() #closes hdf5 file but does not release the lock
        self.h5f.copy_file(newname, overwrite=True) # this operation does not check the lock but 
        #we have it so, no problem. Set overwrite to true since we just created the destination hdf file to make sure we have the lock for it
        newh.hdf5file_lock.close() #release the lock for the new file
        
    @property
    @contextmanager
    def write(self):
        #print os.path.split(self.filename)[1]+'write blocks:'+str(self.blocking_lock)
        with lockman.lockpool[self.filelockkey].acquire(self.blocking_lock):#self.filelock:#.writelock:
            try:
                if not self.h5f.isopen: 
                    closeit=True
                    self.open_with_lock('a')
                    print 'write opened '+self.filename
                else:
                    closeit = False
                if self.h5f.isopen and self.h5f.mode!='a':
                    self.h5f.close()
                    if self.filelocking: self.hdf5file_lock.close()
                    self.open_with_lock('a')
                    print 'write opened '+self.filename
                    reopen = True
                else:
                    reopen = False
                yield
            except:
                traceback.print_exc()
                #pdb.post_mortem(full_exc_info()[2])
            finally: 
                if closeit or reopen: 
                    print 'hdf5io write context closes file'+self.filename
                    self.h5f.close()
                    if self.filelocking: self.hdf5file_lock.close()
                if reopen: 
                    self.open_with_lock('a')
                    print 'write reopened '+self.filename
        

    @property        
    @contextmanager
    def read(self):
        #with self.filelock.readlock:
       # print os.path.split(self.filename)[1]+'read blocks:'+str(self.blocking_lock)
        with lockman.lockpool[self.filelockkey].acquire(self.blocking_lock):
            try:
                if not self.h5f.isopen: 
                    closeit=True
                    self.open_with_lock('a')
                    print 'read opened '+self.filename
                else: 
                    closeit = False
                yield
            except:
                traceback.print_exc()
                #pdb.post_mortem(full_exc_info()[2])
                raise
            finally: 
                if closeit: 
                    print 'hdf5io read closes file'
                    self.h5f.close()
                    if self.filelocking: self.hdf5file_lock.close()
        
#    def __del__(self): #do not use: it is allowed to open the same file in multiple threads, locking ensures this is safe
   #     self.close()
    
    def __finalize__(self):
        try:
            self.h5f.close()
            print 'hdf5io finalizer closes file'
        except Exception  as detail:
            print(detail)
            print('finalizer could not close hdf5 file')
            
    def close(self):
        '''You must call this method if you want to close the hdf5 file'''
        self._want_abort = 1
        self.stacktrace = traceback.extract_stack()
  #      if self.is_alive():
     #       self.command_queue.put(self.queueshutdown)
       # else:
        log.debug("will abort "+self.filename)
        self.cleanup() # let running processes know that they must stop
    #print self.filename+' closed in hdf5io'
        
    
    def isUsable(self):
        '''returns true if hdf5 file is usable, i.e. not corrupted'''
        if not os.path.exists(self.filename):# or tables.is_pytables_file(self.filename) is None:
            a = self.h5f
            log.warning("HDF file not usable,  not exists or nor pytables file")
            return False
        elif os.path.exists(self.filename) and self.h5f.isopen and not hasattr(self.h5f.root, "rawdata"):
            a = self.h5f
            return False
        a = self.h5f
        return True
    
    def findvar(self, vnames,  stage=True, errormsg='',  overwrite=False, path =None):
        '''First checks if requested data is already in memory, if not it tries to load it from the hdf5 file,
        if data is neither in the hdf5 file, it tries to recreate from rawdata.
        This is the generic way of accessing data (excluding rawdata).
        Set stage to False if you do not want data be loaded from disk, just get the reference to it.'''
        if not isinstance(vnames,(tuple,list)):
            vnames = [vnames]
        mynodes = []
        for vname in vnames:
            if not hasattr(self, vname):
                if path is None:
                    path = self.h5fpath
                mynode,mypath  = self.find_variable_in_h5f(vname,path=path,return_path=True)
                if len(mynode)==0 and hasattr(self, 'create_'+vname):
                    mynode = self.perform_create_and_save(vname,overwrite,path)
                elif len(mynode)>0:
                    
                    if stage: # load data into memory
                        if vname =='rawdata':
                            with self.read:
                                if hasattr(self.h5f.root, 'rawdata'): 
                                    self.rawdata = self.h5f.root.rawdata.read()
                                else: raise RuntimeError('Rawdata not found in hdf5 file.')
                        else:
                            self.load(vname,path=mypath[0])
                        try:
                            mynode = getattr(self, vname)
                            dir(self)
                        except: 
                            traceback.print_exc()
                            #pdb.post_mortem(full_exc_info()[2])
                            raise
                else:
                    log.debug(errormsg+';'+vname+' not found in memory or in the hdf5 file')
                    mynode = None
            else:
                mynode = getattr(self, vname)
            mynodes.append(mynode)
        if len(mynodes)==1: return mynodes[0]
        else: return mynodes
        
    def perform_create_and_save(self,vname,overwrite=True,path='h5f.root',**kwargs):
        nodelist = getattr(self, 'create_'+vname)(**kwargs)
        mynode = getattr(self, vname)
        try:
            self.save(nodelist, overwrite ,path=path) 
        except Exception as detail:
            log.debug(detail)
        return mynode
        
    def managed_names(self):
        '''collects variable names from methods that start with 'create_'
        These data are managed by this class and transfer between hdf5 file and memory is done automatically'''
        import inspect
        return ['rawdata']+[method[7:] for method in self.__dict__ if inspect.ismethod(getattr(self, method)) and method.find('create_')>-1]
    
    def check_before_file_operation(self, names):
        '''various checks to be performed before saving/loading '''
        self.attrnames = list(set(self.attrnames)) # make sure entries are unique
        if names is not None and isinstance(names, basestring):
            names = [names]
        elif names is None:
            names = self.managed_names()+self.attrnames
        return names
        
    def save(self, names=None, overwrite=True, path=None,  verify=False):
        ''' Saves data to the hdf5 file. If name is omitted then all data managed by this class will be saved.
           Numpy array, recarray,(list of) list of arrays,  and dict are supported.'''
        try:
            with self.write:
                if path is None: path = self.h5fpath
                names = self.check_before_file_operation(names)
                filters = tables.Filters(complevel=1, complib='lzo', shuffle = 1)
                croot=introspect.traverse(self,path)
                for vname in names:
                    if QtCore.QCoreApplication.instance() is not None:
                        QtCore.QCoreApplication.processEvents()
                    hasit = self.find_variable_in_h5f(vname,path=path)
                    if hasit is None:
                        pass
                    if not hasattr(self, vname) and len(hasit)>0 and overwrite==False:
                        continue #item already in file but not in memory, nothing to do now
                    elif not hasattr(self, vname) and len(hasit)>0 and overwrite==True:
                        log.error('Tried to overwrite '+vname+' in hdf5 file but it is not in memory.')
                    if isinstance(getattr(self, vname), (basestring,  int,  float,  bool,  complex)):
                        #strings, int and float are saved as attribute
                        setattr(croot._v_attrs,vname,getattr(self,vname))
                        continue
                    if vname in hasit:
                        if overwrite:# we cannot be sure that new content is the same size as old content
                            for vn1 in hasit:
                                # bug: hasit contains nodes different from root, but user is not obliged to provide the path for those nodes, thus removenode will not find the node in the root
                                try:
                                    self.h5f.remove_node(croot,vn1, recursive=True)
                                except Exception as e: #only if vn1 is stored as attribute?
                                    print e
                        else:
                            # if data exist in hdf5 file then return. If user explicitly told to overwrite it, then continue
                            continue
                    vp = getattr(self,vname)
                    hp = croot #pointer to keep track where we are in the hdf hierarchy
                    if vp is None:
                        log.warning('Requested to save '+vname +' but it is not available in this object.')
                        continue
                    if isinstance(vp,list): self.list2hdf(vp, vname,hp, filters,  overwrite)            
                    elif isinstance(vp,numpy.ndarray): self.ndarray2hdf(vp, vname,hp, filters,  overwrite)
                    elif isinstance(vp,dict): self.dict2hdf(vp, vname,hp,  filters, overwrite)            
                    else:
                        raise TypeError(vname+' cannot be saved, its type is unsupported')
                self.h5f.flush()
                if verify:
                    written = self.findvar(names)
                    self.close()
                    self.open_with_lock('a')
                    reread = self.findvar(names)
                    print 'verified'
                    if written !=reread:
                        raise IOError('Reread data is not the same as written')
        except Exception as e:
            print e
            pdb.set_trace()

        
    def save_vlarray(self, root, vn,  alist, filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1)):
        myatom = tables.Atom.from_dtype(numpy.dtype(alist[0].dtype, (0, )*alist[0].ndim))
        vlarray = self.h5f.create_vlarray(root, vn,
                                                 myatom,#(shape=()),
                                                 vn,
                                                 filters=filters)#VLarrays
        try:
            for item in alist:
                if item.ndim==0:
                    vlarray.append([item.tolist()])
                else:
                    vlarray.append(item)
        except:
            traceback.print_exc()
            pdb.set_trace()
    
    def list2hdf(self, vp , vn,hp,   filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1), overwrite=False):
        if len(vp)==0: #empty list
            self.h5f.create_array(hp, vn, 'empty list', "empty list")
            return
        list_type = introspect.list_type(vp)
        if list_type is 'list': #check if list contains only numeric values
            if numpy.array(vp).dtype is object:#numpy.isnan(vp).any():
                raise NotImplementedError('List of mixed types cannot be saved into hdf5 file yet.')
            else:
                self.ndarray2hdf(numpy.array(vp), vn,hp,  filters, overwrite)     
                return                
        if list_type is 'list_of_arrays':
            self.save_vlarray(hp, vn, vp, filters=filters)
        elif list_type is 'arrayized':
            vpa= numpy.array(vp)
            self.saveCArray(vpa, vpa.shape,tables.Atom.from_dtype(vpa.dtype), hp, vn, overwrite, filters, typepost='arrayized')
        elif 'recarrays' in list_type:# is 'list_of_recarrays': 
            # list of recarrays that have the same fields
            root = self.h5f.create_group(hp, vn, vn+'_'+list_type)
            for d in range(len(vp[0].dtype)):
                fname = vp[0].dtype.names[d]
                if 'uniform_shaped' in list_type:
                    numpyarray=numpy.squeeze([v[fname] for v in vp])
                    self.saveCArray(numpyarray, numpyarray.shape, tables.Atom.from_dtype(vp[0][fname].dtype), root, fname, overwrite, filters, typepost='_'+list_type)
                else: # each recarray in the list has different numbe of elements
                    self.save_vlarray(root, fname, [v[fname] for v in vp],filters=filters )
        elif list_type is 'list_of_lists':
            if len(vp)>10**Hdf5io.maxelem:
                raise NotImplementedError('Saving list of lists is supported till '+str(10**Hdf5io.maxelem)+' elements, increase x in the expression {0:0x} below and make sure old files will be read')
            root = self.h5f.create_group(hp, vn, vn+'_list_of_lists')
            for i in range(len(vp)):
                if QtCore.QCoreApplication.instance() is not None:
                    QtCore.QCoreApplication.processEvents()
                self.list2hdf(vp[i],Hdf5io.elemformatstr.format(i),root,filters,overwrite)
            if 0: # list type already detects if list of lsit is arrayizable so this below is deprected
               list_type = introspect.list_type(vp[0])
               if list_type is 'list_of_arrays': # list of lists of arrays
                    vlarray = self.h5f.create_vlarray(hp, vn,
                                                     tables.Atom.from_dtype(vp[0][0].dtype),#(shape=()),
                                                     vn,
                                                     filters=tables.Filters(1))#VLarrays
                    for item in vp:
                        shapes = [i.shape for i in item]
                        allequal = [s == shapes[0] for s in shapes]
                        if sum(allequal) == len(item): # all elements in the list have the same number of values
                            conc_item = numpy.r_[item]
                        else:
                            raise NotImplementedError('Saving list of lists of arrays when arrays have different shape is not implemented')
                        vlarray.append(conc_item)
                    setattr(self._v_attrs,vn+'_listlength',len(vp[0]))
        elif list_type is 'list_of_dicts': # list of dicts, all elements of the list must be a dict
            if len(vp)>10**Hdf5io.maxelem:
                raise NotImplementedError('Saving list of dicts is supported till '+str(10**Hdf5io.maxelem)+' elements, increase x in the expression {0:0x} below and make sure old files will be read')
            root = self.h5f.create_group(hp, vn, vn+'_list_of_dicts')
            for i0 in range(len(vp)):
                self.dict2hdf(vp[i0], Hdf5io.elemformatstr.format(i0),root, filters,  overwrite)
                
                
    def ndarray2hdf(self,vp, vn,hp,  filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1), overwrite=False, typepost=''):
        if isinstance(vn, basestring) and vn == 'rawdata':
            atom = tables.Atom.from_dtype(getattr(self, vn).dtype)
            shapestring = ''.join(str(v)+',' for v in getattr(self, vn).shape)
            chunkshapestring = '(1,1,'+str(getattr(self, vn).shape[2])+','+str(getattr(self, vn).shape[3])+')'
            pcmd = vn+" = self.h5f.create_carray(self.h5f.root, '"+vn+"', atom,("+shapestring+"), filters=filters, chunkshape = "+chunkshapestring+", title=typepost"+")"
            exec(pcmd) in locals()
            self.write_rawdatapixels('all', 'all')
            if self.rawdata.size* self.rawdata.dtype.itemsize > self.ramlimit: #if rawdata is bigger than maximum allocatable RAM specified by user then delete it from RAM and use direct disk access later if you need rawdata
                delattr(self, vn)
            return
        else: #vp contains the pointer to the actual numpy ndarray            
            vdtype =vp.dtype#eval('self.'+vn+'.dtype')
            if vdtype.names is None:
                self.saveCArray(vp, vp.shape,tables.Atom.from_dtype(vp.dtype), hp, vn, overwrite, filters, typepost=typepost)
            else: # save recarray
                gn = vn
                cdtype = vdtype.fields
                fnames = cdtype.keys() #names in hdf5 file's subgroup, e.g. self.h5f.root.quantified.full
                vnames = [gn+"['"+c+"']" for c in cdtype.keys()] # names in the current object e.g. self.quantified['full']
                vdtypes = [cdtype[d][0] for d in fnames]
                root = self.h5f.create_group(hp, gn, gn+'_recarray')
                for vn, fn, vdtype in zip(vnames,fnames,vdtypes):
                    atom = tables.Atom.from_dtype(vdtype)
                    cvp = getattr(vp.view(numpy.recarray), fn)
                    vs = cvp.shape
                    self.saveCArray(cvp, vs, atom, root, fn, overwrite, filters)
    
    def dict2hdf(self, vp, vn,hp,  filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1),  overwrite=False):
        '''Saves a python dict into the hdf5 file. There are restrictions on what elements a dict can have but 
        this method can be updated to meet new needs.
        This methods tries to determine if an item in the dict is anything other than (array or list) of numeric values. 
        Array (or list) of numeric values is simply saved as CArray (or attribute), other types are saved calling
        the appropriate xxx2hdf method recursively.
        '''
        gn = vn
        fnames = vp.keys() #names in hdf5 file's subgroup, e.g. self.h5f.root.quantified.full
        #vnames = [gn+"['"+str(c)+"']" for c in fnames] # names in the current object e.g. self.quantified['full']
        root = self.h5f.create_group(hp, gn, gn+'_dict')
        for fn in fnames:
            if QtCore.QCoreApplication.instance() is not None:
                QtCore.QCoreApplication.processEvents()
            if vp[fn] is None:
                vp[fn] = []
            if hasattr(vp[fn], 'keys'): 
                self.dict2hdf(vp[fn], fn,root, filters,  overwrite)
                continue
            if not isinstance(fn, basestring):
                from numbers import Number
                if isinstance(fn, numpy.ndarray) and sum(fn.shape)==0 or isinstance(fn, Number):
                    typepost = '__Number'
                else:
                    raise TypeError('Dict key with this type cannot be saved into hdf5 hierarchy')
            else:
                typepost=''
            if introspect.list_type(vp[fn]) is not None:
                self.list2hdf(vp[fn], fn ,root, filters,  overwrite)  # save as list of lists
                continue
            else:
                vp[fn] = numpy.array(vp[fn])
            #atom = tables.Atom.from_dtype(vp[fn].dtype)
            vs = vp[fn].shape
            if len(vs)==0:
                setattr(root._v_attrs,str(fn)+typepost,vp[fn])
            else:
                self.ndarray2hdf(vp[fn], str(fn),root,  filters, overwrite, typepost=typepost)
#                self.saveCArray(vp[fn], vs, atom, root, fn,overwrite,filters)
                
    def saveCArray(self,vp, vs, atom, root, fn, overwrite,filters, typepost=''):
        '''Saves a numpy array as CArray in the opened pytables file.
       vp is the reference to the actual data, vs is the shape of the array, root is the node under which the array has to be created
        fn is the name of the new node in the pytables file.'''
        if sum(vs)==0 or vp.size ==0: #0 dim array
            vla = self.h5f.create_vlarray(root,fn,atom,fn+typepost,filters=filters)
            if len(vp.data)==0: #empty array, create placeholder in h5f file
                return
            else:
                vla.append([vp])
                return
        if not overwrite and hasattr(root, fn):#vn in self.h5f.root.__members__:
            # if data exist in hdf5 file then return. If user explicitly told to overwrite it, then continue
            return
        if overwrite and hasattr(root, fn):#vn in self.h5f.root.__members__: # we cannot be sure that new content is the same size as old content
            self.h5f.remove_node(root,fn)
            self.h5f.flush()
        self.h5f.create_carray(root, fn, atom,vs, filters=filters,title=typepost)
        log.debug("writing " + fn)
        dimstr = ':,'*len(vs)
        pcmd = "getattr(root,fn)"+"["+dimstr[:-1]+"] =vp["+dimstr[:-1]+"]"
        exec(pcmd) in locals()


    def load(self, names=None, path=None):
        names = self.check_before_file_operation(names)
        if path is None: path = self.h5fpath
        with self.read:
            for vname in names:
                if hasattr(self.h5f.get_node(self.dot2slash(path))._v_attrs,vname): #data stored as attribute?
                    setattr(self,vname,getattr(self.h5f.get_node(self.dot2slash(path))._v_attrs,vname))
                    continue
                if len(self.find_variable_in_h5f(vname,path=path))>0  and not self._want_abort: # data is in the file but not available in the class instance, load
                    log.debug("loading "+vname)
                    if not self._want_abort: 
                        self.load_variable(vname, path=path)

    def find_variable_in_h5f(self, vn, path = None,return_path=False,  regexp=False):
        '''Tries to give back any leaf name in self.h5f that contain vn. Group nodes '''
        with self.read:
            if path is None:
                path = self.h5fpath
            if path.find('.')>-1:
                path = self.dot2slash(path)
            try:
                myroot = self.h5f.get_node(path)
            except:
                log.warning(path+' not found in '+self.filename)
                if return_path:   return [], []
                else: return []
            #else: # maybe we look for a variable that is split up into multiple leafs?
            if hasattr(myroot._v_attrs, vn): 
                if return_path:
                    hpath = [self.slash2dot(path)]
                hasit = [vn] # variable is found as an attribute
            else:
                nodelist = self.h5f.list_nodes(path)
                if regexp:
                    ree = re.compile(vn)
                    if return_path:
                        hpath = [self.slash2dot(n._v_parent._v_pathname) for n in nodelist if len(re.findall(ree,n._v_name))>0]
                    hasit = [n._v_name for n in nodelist if len(re.findall(ree,n._v_name))>0]
                else:
                    if return_path:
                        hpath = [self.slash2dot(n._v_parent._v_pathname) for n in nodelist if n._v_name==vn]
                    hasit = [n._v_name for n in nodelist if n._v_name==vn]
            if return_path:
                return hasit,hpath
            else:
                return hasit
            
    def slash2dot(self, slashedpath):
        if slashedpath =='/': return 'h5f.root'
        else:
            path= slashedpath.replace('/','.')
            return ('h5f.root'+path)
        
    def dot2slash(self,dottedpath):
        '''converts a hdf5 path string from the format:
        'h5f.root' to '/'
        '''
        startnode = dottedpath.replace('.','/')
        startnode = startnode[startnode.index('root')+4:] or '/'
        return startnode
    
    def load_variable(self, vn, path=None):
        '''
        Loads the variable "vname" from the hdf5 file.
        '''
        try:
            if path is None:path=self.h5fpath
            croot = introspect.traverse(self,path)
            hasit = self.find_variable_in_h5f(vn,path=path)
            if len(hasit)>0:
                for vname in hasit:
                    if vname == 'rawdata' and self.rawdatasource =='rawdata':
                       self.request_rawdata((('all','all'),'dummy')) # dummy SIGNAL    : we do not need data returned
                    elif not vname == 'rawdata':
                        if self.h5f.get_node(croot, vname)._v_title == 'empty list':
                            setattr(self, vname, [])
                            return
                        log.debug("reading "+vn+" in 1 chunk")
                        if isinstance(self.h5f.get_node(croot, vname),tables.Group):
                            # read a (eventually) nested data structure
                            group = self.h5f.get_node(croot, vname) 
                            myvar = self.step_into_hdfgroup(group)
                            setattr(self,vname,myvar)
                        else:
                            if self.h5f.get_node(croot, vname).shape[0]==0: #saved empty list or empty array
                                setattr(self, vname, numpy.empty((0, ))) # simple read would return a list which is not the same as the empty numpy array saved in the file
                                return
                            setattr(self, vname, self.h5f.get_node(croot, vname).read()) # load array  from hdf5 file
                            if 'arrayized' in self.h5f.get_node(croot, vname)._v_title:
                                setattr(self, vname, getattr(self, vname).tolist())
                            # list of equal sized non-recarrays:
                            if isinstance(self.h5f.get_node(croot, vname),tables.VLArray) and hasattr(croot._v_attrs,vname+'_listlength'):
                                a = [numpy.split(item,getattr(croot._v_attrs,vname+'_listlength')) for item in getattr(self,vname)]
                                setattr(self,vname,a)
            else:
                log.debug("Variable "+vn+" not found in the cache file!")
                pass
        except Exception:
            import traceback
            print traceback.format_exc()
            log.debug("error reading "+vn+" from "+self.filename)
   
    def hdf2dict(self, group):
        myvar = {}
        for n in self.h5f.iter_nodes(group):#read data stored in arrays, walk trough names in hdf5 file's subgroup, e.g. self.h5f.root.quantified.full
            if isinstance(n,tables.Group):
                myvar[n._v_name]=self.step_into_hdfgroup(n)
            else:
                try:
                    myvar[n._v_name] = n.read()
                except:
                    raise RuntimeError('')
                if 'arrayized' in n._v_title:
                    myvar[n._v_name]=myvar[n._v_name].tolist()
                try:
                    if isinstance(myvar[n._v_name], basestring) and myvar[n._v_name] =='empty list': myvar[n._v_name]=[]
                except:
                    raise RuntimeError('')
        for n in group._v_attrs._f_list(): # read values stored as attribute
            typepos=  n.find('__')
            if typepos>0:
                mytype = n[typepos+2:]
                if mytype =='Number':
                    if '.' in n[:typepos]:
                        vname = float(n[:typepos]) # use float for ints too
                    else:
                        vname = int(n[:typepos])
                else:
                    raise TypeError('Type '+mytype+' not implemented to be stored in hdf5')
            else: vname=n
            myvar[vname] = getattr(group._v_attrs, n)
            if myvar[vname] =='empty list': myvar[vname]=[]
        return myvar
                        
    def hdf2ndarray(self, group):
        mydtype = [n._v_name for n in self.h5f.iter_nodes(group)]
        myshape = getattr(group,mydtype[0]).shape
        value_type = getattr(group,mydtype[0]).atom.dtype
        if 'recarrays' in group._v_title:
            listoflists= zip(*[getattr(group, d).read() for d in mydtype])
            myvar = [numpy.rec.fromrecords(zip(*i), names=mydtype) for i in listoflists] # na itt akad
        else: # pack out into one numpy ndarray
            myvar = numpy.empty(myshape, dtype=zip(mydtype,[value_type]*len(mydtype)))
            for nodename in mydtype:
                myvar[nodename] = self.h5f.get_node(group,nodename).read()
        return myvar
      
    def hdf2recarray(self,group):
        '''reads a record array from hdf5 file'''
        hasit = self.h5f.list_nodes(group)
        names = [n._v_name for n in hasit]
        firstnode = hasit[0]
        vdtype = numpy.dtype({'names':names, 'formats':[firstnode.atom.dtype.type]*len(hasit)})
        var0 = [] # empty list that will contain n lists that each contain numpy arrays of different length
        for v_i in range(len(hasit)):
            var0.append( hasit[v_i].read()) # load from hdf5 file
        #now we have all our fields, let's merge them
        var3 = zip(*var0) # now we can slice as : var3[0][0] contains e.g. soma_roi_cols and var3[0][1] contains rows
        try:
            if 'uniform_shaped' in group._v_title:
                var2 = [numpy.array(item, dtype=vdtype) for item in var3]
            else: raise
        except:
            var2 = [numpy.array(zip(*item[:]), dtype=vdtype) for item in var3]
        return var2   
        
    def hdf2list(self,group):
        listlength = len([n._v_name for n in self.h5f.iter_nodes(group) if n._v_name.isdigit()])
        mylist = [[]]*listlength
        for n in self.h5f.iter_nodes(group):
            if isinstance(n,tables.Group):
                mylist[int(n._v_name)] = self.step_into_hdfgroup(n)
            else:
                mylist[int(n._v_name)] = n.read()
                if 'arrayized' in n._v_title:
                    mylist[int(n._v_name)]=mylist[int(n._v_name)].tolist()
        return mylist
                            
    def step_into_hdfgroup(self, group):
        '''reads complex datatypes (dict, list, numpy recarray) from the hdf hierarchy
        '''
        gtitle = str(group._v_title)#.tostring()
        if gtitle.find('dict')==len(group._v_title)-4:
            myvar=self.hdf2dict(group)
        elif 'recarrays' in group._v_title:
            myvar = self.hdf2recarray(group)
        elif gtitle.find('recarray')==len(group._v_title)-8:
            myvar=self.hdf2ndarray(group)
        elif 'list_of_' in gtitle:
            myvar= self.hdf2list(group)
        else: raise NotImplementedError(group._v_name+ ' has unknown data type in hdf5 file.')
        return myvar
        
    def cleanup(self):
        if hasattr(self, 'h5f') and self.h5f is not None and self.h5f.isopen:
            log.debug("object closing closes h5f")
            with lockman.lockpool[self.filelockkey].acquire(False):
                self.h5f.flush()
                self.h5f.close()
        log.debug("aborted, file closed "+self.filename)


    def attrsize(self, name):
        '''Gives back the size of the attribute "name" in bytes.'''
        n = getattr(self, name+'source')
        obj = introspect.traverse(self, n)
        if 'h5f' in n: #we check in the hdf5 file
            return numpy.cumprod(obj.shape)[-1] * obj.atom.dtype.itemsize
        else:
            return obj.size*obj.dtype.itemsize
            
            
    def check_hashes(self,vname,function,*args,**kwargs):
        '''Checks whether the function code and argument hashes exist in the hdf5 file and updates them if necessary'''
        fh=self.findvar(vname+'_function_hash', path='/hashes')
        ah=self.findvar(vname+'_function_arguments_hash', path='/hashes')
        try:
            from visexpA.engine.dataprocessors.generic import check_before_long_calculation
            new_fh, new_ah = check_before_long_calculation(fh, function, ah,*args,**kwargs)
        except ImportError:
            new_fh = None
        if new_fh is None: # argument and function hashes are the same, no need to recalculate
            self.load(vname)
            return True
        else:
            with self.write:
                if not hasattr(self.h5f.root, 'hashes'):
                    self.h5f.root.hashes = self.h5f.create_group('/', 'hashes', 'Hash sums stored to check if data needs to be recreated')
                setattr(self, vname+'_function_hash',new_fh)
                setattr(self,vname+'_function_arguments_hash', numpy.array(new_ah))
                self.save([vname+'_function_hash',vname+'_function_arguments_hash'], overwrite=True, path='h5f.root.hashes')
            return False

def read_item(filename,  attrname,  config=None,  filelocking=True):
    '''Opens the hdf5file, reads the attribute and closes the file'''
    if config is None and filelocking is True:
        raise RuntimeError('You cannot open a hdf5 file with locking enabled without providing a config object')
    if not os.path.exists(filename):
        raise OSError('Hdf5file '+filename+' not found')
    if not filename[-5:]=='.hdf5':
        log.warning(filename + ' is not a hdf5 file')
        return None
    h5f=None
    value=None
    try:
        h5f = Hdf5io(filename, config, filelocking=filelocking)
        value = h5f.findvar(attrname)
    except:
        import traceback
        traceback.print_exc()
        raise
        #pdb.post_mortem(full_exc_info()[2])

        raise OSError('Problem with hdf5file')
    finally:
        if h5f is not None and h5f.h5f.isopen: 
          #  print 'read ite mcloses file'
            h5f.close()
    return value
    
def save_item(filename,  varname,  var, config=None, overwrite = False, filelocking=True):
    if config is None and filelocking is True:
        raise RuntimeError('You cannot open a hdf5 file with locking enabled without providing a config object')
    try:
        h = Hdf5io(filename, config, filelocking=filelocking)
        setattr(h,  varname,  var)
        h.save(varname,  overwrite = overwrite)
    except:
        raise OSError('Problem with hdf5file')
    finally:
        h.close()

def iopen(filename, cfg, packagepath=None, file_always_open=True, filelocking = True):
    '''Intelligent open function: given a filename first find out the classname that is used to process the data
    then open the file via that class so that appropriate processing functions will be available.'''
    if filename.find('hdf5') < len(filename)-4 and not cfg is None:
        # not hdf5 extension, try to guess if guessing code is available
        try:
            basedir, dummy = os.path.split(filename)
            import visexpA.engine.component_guesser as component_guesser
            filename = component_guesser.rawname2cachedname(filename, cfg.basepath, cfg.basepath, cfg.rawext, cfg.cacheext)
        except Exception as e:
            log.exception('Could not guess hdf5 filename, unknown rawdata format?')
    if packagepath is None and hasattr(cfg, 'packagepath'):
        packagepath=cfg.packagepath
    classname = read_item(filename, 'exptype', cfg, filelocking = filelocking)
    if classname is None: #MES hdf5 not yet converted?
        import visexpA.engine.datahandlers.importers as importers
        obj = importers.MESExtractor(filename, cfg, filelocking = filelocking)
        data_class, stim_class,classname,timestamp = obj.parse()
        #classname = read_item(filename, 'exptype')
    import visexpman.engine.generic.utils
    if classname is None:
        return
    anal_class=visexpman.engine.generic.utils.fetch_classes(packagepath, classname=classname) # find the required class
    components = {'hdf5_filename':filename}
    return anal_class[0][1](components, cfg, file_always_open=file_always_open, filelocking = filelocking) #open file and return reference
    
import unittest
from visexpman.users.test import unittest_aggregator
class TestUtils(unittest.TestCase):
    def setUp(self):
        import os, visexpman, visexpA.engine.configuration
        import visexpman.engine.generic.utils
        from visexpman.engine.generic.fileop import mkstemp
        self.filename = mkstemp(suffix='.hdf5')
        self.config = visexpman.engine.generic.utils.fetch_classes('visexpA.users.daniel', \
                                classname='Config', required_ancestors=visexpA.engine.configuration.Config)[0][1]()

    def tearDown(self):
        os.remove(self.filename)
        pass

    def test_1000x1000_error(self):
        import numpy
        from visexpA.engine.datahandlers import datatypes
        a=numpy.ones((1000,1000,1,1),dtype=numpy.uint16)
        h=datatypes.ImageData(self.filename,filelocking=False)
        h.rawdata=a
        h.save('rawdata')
        pass
        
    def test_dict2hdf(self):
        import copy
        from visexpman.engine.generic.introspect import dict_isequal
        data = {'a':10, 'b':5*[3]}
        data = 4*[data]
        data2 = {'a':numpy.array(10), 'b':numpy.array(5*[3])}
        h= Hdf5io(self.filename, filelocking=False)
        h.data = copy.deepcopy(data)
        h.data2=copy.deepcopy(data2)
        h.save(['data','data2'])
        del h.data
        h.load(['data','data2'])
        h.close()
        #hdf5io implicitly converts list to ndarray
        self.assertTrue(dict_isequal(data2,h.data2) and data==h.data)
     
    def test_recarray2hdf(self):
        import copy
        data = numpy.array(zip(range(10),range(10)),dtype={'names':['a','b'],'formats':[numpy.int,numpy.int]})
        data = 4*[data]
        h= Hdf5io(self.filename, filelocking=False)
        h.data = copy.deepcopy(data)
        h.save(['data'])
        del h.data
        h.load(['data'])
        h.close()
        self.assertTrue((numpy.array(data)==numpy.array(h.data)).all())
    
    #@unittest.skip('this is not a test')
    def test_findvar(self):
        f = os.path.join(unittest_aggregator.TEST_reference_data_folder,  'fragment_-373.7_-0.8_-160.0_MovingDot_1331897433_3.hdf5')
        h5f=Hdf5io(f, filelocking=False)
        h5f.findvar('MovingDot_1331897433_3')
        res = h5f.findvar(['position','machine_config'])
        pass
        
    def test_complex_data_structure(self):
        item = {}
        item['a1'] = 'a1'
        item['a2'] = 2
        item['a3'] = 5
        items = 5*[item]
        f = self.filename        
        h5f=Hdf5io(f, filelocking=False)
        h5f.items = items
        h5f.save('items', verify=True)
        h5f.close()
        reread = read_item(f, 'items', filelocking=False)
        self.assertEqual(items, reread)
    
    def test_concurrent_access(self):
        items = [['1.1','1.2','1.3'],['2.1','2.2']]
        f = self.filename        
        h5f=Hdf5io(f, self.config)
        h5f.items = items
        h5f.save('items')
        h5f.close()
        t=threading.Thread(target=lambda f=f, self=self: Hdf5io(f, self.config))
        t.start()
        print t.is_alive()
       # t.join()
        handler = iopen(f, self.config)
    
    def test_listoflists(self):
        items = [['1.1','1.2','1.3'],['2.1','2.2']]
        f = self.filename        
        h5f=Hdf5io(f, filelocking=False)
        h5f.items = items
        h5f.save('items')
        h5f.close()
        self.assertEqual(items, read_item(f, 'items'), filelocking=False)
        
    #@unittest.skip('this is a bad test')    
    def test_more_complex_data_structure(self):
        items = {'rising_edges_indexes': 0, 
            'number_of_fragments': 3, 
            'stimulus_frame_info': [{'elapsed_time': 0, 
                                                'stimulus_type': 'show_dots', 
                                                'counter': 0, 
                                                'is_last': False, 
                                                'parameters': 
                                                                {'duration': 0.0, 
                                                                'color': [1.0, 1.0, 1.0], 
                                                                'ndots': 1, 
                                                                'dot_diameters': [299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994], 
                                                                'dot_positions': numpy.array([(-299.99999999999994, 151.26084084909542),
                                                                                               (-266.66666666666663, 151.26084084909542),
                                                                                               (-233.33333333333326, 151.26084084909542),
                                                                                               (-199.99999999999991, 151.26084084909542),
                                                                                               (2200.0000000000014, 2543.93232337115),
                                                                                               (2233.3333333333344, 2543.93232337115),
                                                                                               (2266.666666666668, 2543.93232337115),
                                                                                               (2300.0000000000014, 2543.93232337115),
                                                                                               (2333.333333333335, 2543.93232337115)], 
                                                                                              dtype=[('row', '<f8'), ('col', '<f8')])}}, 
                                                {'elapsed_time': 14.625, 
                                                'stimulus_type': 'show_dots', 
                                                'counter': 719, 
                                                'is_last': True, 
                                                'parameters': 
                                                                {'duration': 0.0, 
                                                                'color': [1.0, 1.0, 1.0], 
                                                                'ndots': 1, 
                                                                'dot_diameters': [299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994, 299.99999999999994], 
                                                                'dot_positions': numpy.array([(-299.99999999999994, 151.26084084909542),
                                                                                                    (-266.66666666666663, 151.26084084909542),
                                                                                                   (2200.0000000000014, 2543.93232337115),
                                                                                                   (2233.3333333333344, 2543.93232337115),
                                                                                                   (2266.666666666668, 2543.93232337115),
                                                                                                   (2300.0000000000014, 2543.93232337115),
                                                                                                   (2333.333333333335, 2543.93232337115)], 
                                                                                                dtype=[('row', '<f8'), ('col', '<f8')])}}, 
                                                {'elapsed_time': 14.625, 
                                                'stimulus_type': 'show_fullscreen', 
                                                'counter': 720, 
                                                'is_last': False, 
                                                'parameters': 
                                                                {'duration': 0.0, 
                                                                'color': 0.0, 
                                                                'flip': True, 
                                                                'count': True}}, 
                                                {'elapsed_time': 14.656000137329102, 
                                                'stimulus_type': 'show_fullscreen', 
                                                'counter': 720, 
                                                'is_last': True, 
                                                'parameters': 
                                                                {'duration': 0.0, 
                                                                'color': 0.0, 
                                                                'flip': True, 
                                                                'count': True}}], 
            'generated_data': {'shown_directions': [(90, 720)]}, 
                                        'experiment_source': numpy.array([39, 39, 39, 10, 13, 10], dtype=numpy.uint8), 
                                        'sync_data': numpy.array([[ 0.,  0.], [ 0.,  0.]]), 
                                        'actual_fragment': 0, 
                                        'current_fragment': 0}
        f = self.filename        
        h5f=Hdf5io(f, filelocking=False)
        h5f.items = items
        h5f.save('items')
        h5f.close()
        equal=True
        result = read_item(f, 'items', filelocking=False)
        for key in result.keys():
            if isinstance(result[key],list):
                for i0,i1 in zip(items[key],result[key]):
                   #add better equality test here
                  # if i0!=i1:
                    #    equal=False
                    pass
            else:
                if items[key]!=result[key]:
                    equal = False
                
        self.assertTrue(equal)
        
if __name__=='__main__':
    unittest.main()


  
