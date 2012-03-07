import logging
import logging.handlers
log = logging.getLogger('introspect')
import PyQt4.QtCore as QtCore
from contextlib import contextmanager
import inspect
import time
import re
## {{{ http://code.activestate.com/recipes/519621/ (r4)
import weakref

class Finalizable(object):
    """
    Base class enabling the use a __finalize__ method without all the problems
    associated with __del__ and reference cycles.

    If you call bind_finalizer(), it will call __finalize__ with a single
    "ghost instance" argument after the object has been deleted. Creation
    of this "ghost instance" does not involve calling the __init__ method,
    but merely copying the attributes whose names were given as arguments
    to bind_finalizer().

    A Finalizable can be part of any reference cycle, but you must be careful
    that the attributes given to enable_finalizer() don't reference back to
    self, otherwise self will be immortal.
    """

    __wr_map = {}
    __wr_id = None

    def bind_finalizer(self, *attrs):
        """
        Enable __finalize__ on the current instance.
        The __finalize__ method will be called with a "ghost instance" as
        single argument.
        This ghost instance is constructed from the attributes whose names
        are given to bind_finalizer(), *at the time bind_finalizer() is called*.
        """
        cls = type(self)
        try:
            ghost = object.__new__(cls)
        except:
            import sip
            ghost = sip.wrapper.__new__(cls)
        ghost.__dict__.update((k, getattr(self, k)) for k in attrs)
        cls_wr_map = cls.__wr_map
        def _finalize(ref):
            try:
                ghost.__finalize__()
            finally:
                del cls_wr_map[id_ref]
        ref = weakref.ref(self, _finalize)
        id_ref = id(ref)
        cls_wr_map[id_ref] = ref
        self.__wr_id = id_ref

    def remove_finalizer(self):
        """
        Disable __finalize__, provided it has been enabled.
        """
        if self.__wr_id:
            cls = type(self)
            cls_wr_map = cls.__wr_map
            del cls_wr_map[self.__wr_id]
            del self.__wr_id


class TransactionBase(Finalizable):
    """
    A convenience base class to write transaction-like objects,
    with automatic rollback() on object destruction if required.
    """

    finished = False

    def enable_auto_rollback(self):
        self.bind_finalizer(*self.ghost_attributes)

    def commit(self):
        assert not self.finished
        self.remove_finalizer()
        self.do_commit()
        self.finished = True

    def rollback(self):
        assert not self.finished
        self.remove_finalizer()
        self.do_rollback(auto=False)
        self.finished = True

    def __finalize__(ghost):
        ghost.do_rollback(auto=True)


class TransactionExample(TransactionBase):
    """
    A transaction example which close()s a resource on rollback
    """
    ghost_attributes = ('resource', )

    def __init__(self, resource):
        self.resource = resource
        self.enable_auto_rollback()

    def __str__(self):
        return "ghost-or-object %s" % object.__str__(self)

    def do_commit(self):
        pass

    def do_rollback(self, auto):
        if auto:
            print "auto rollback", self
        else:
            print "manual rollback", self
        self.resource.close()
## end of http://code.activestate.com/recipes/519621/ }}}


@contextmanager
def acquire(locks,  lockregistry=dict()): # assigning lockregistry a mutable type keeps it persistent!
    '''Fancy lock context manager. It works very well but represents a noticeable computing overhead
    if called frequently'''
    locklock = QtCore.QReadWriteLock()
    debug = 0
    threadid = str(id(QtCore.QThread.currentThread()))
    if len(locks) == 2 and not isinstance(locks[1],tuple):
       locks = (locks, )
    if debug: mn = inspect.stack()[2][3]
    else: mn = ''
    # Check to make sure we're not violating the order of locks already acquired
    try:
        for L in locks:
            i = id(L[0])
            with QtCore.QReadLocker(locklock): # make sure that the common lockregistry is not accessed by concurrent threads at the same time
                seen = i in lockregistry #this lock is already existing
                if seen: write = 'write' in lockregistry[i] # this lock has been acquired for writing
                else: write = False
            if seen and write:
                print mn+threadid + ' tries to relock '+str(i)+ ' for '+L[1]+' that is locked for writing'
                with QtCore.QReadLocker(locklock):
                    print lockregistry
                L[0].lockForWrite()
                with QtCore.QWriteLocker(locklock):
                    lockregistry[i].append(L[1])
                    #raise RuntimeError(threadid + ' tries to relock '+str(i)+ ' that is locked for writing')
                print inspect.stack()[2][3]

            elif seen and L[1]=='read' and not write:
                if debug: print mn+threadid + " reacquires "+str(i)+" for reading"
                L[0].lockForRead()
                with QtCore.QWriteLocker(locklock):
                    lockregistry[i].append(L[1])
            elif seen and L[1]=='write' and not write:
                print mn+threadid + ' tries to relock '+str(i)+ ' for writing that is locked for reading. This would block forever.'
                raise RuntimeError(mn+threadid + ' tries to relock '+str(i)+' for writing that is locked for reading. This would block forever.')
            elif not seen:
                with QtCore.QWriteLocker(locklock):
                    lockregistry[i] = [L[1]]
                if L[1] == 'read':
                    L[0].lockForRead()
                else:
                    L[0].lockForWrite()
                if debug: print mn+ threadid + " locked "+str(i)+ " for "+L[1]
        yield
    finally:
        for lock in reversed(locks):
            lock[0].unlock()
            i = id(lock[0])
            with QtCore.QWriteLocker(locklock):
                if i in lockregistry: # else lock was not acquired because of deadlock prevention
                    if len(lockregistry[i]) == 1:
                        del lockregistry[i]
                    else:
                        lockregistry[i].pop()
                    if debug:
                        print mn+threadid + " unlocked "+str(i)+ " for "+lock[1]

def nameless_dummy_object_with_methods(*methods):
    d = {}
    for sym in methods:
        d[sym] = lambda self,*args,**kwargs: None
    return type("",(object,),d)()
    
def flatten(l, ltypes=(list, tuple)):
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


    
def traverse(obj,  attrchain):
    '''Walks trough the attribute chain starting from obj and returns the last element of the chain. E.g.
    attrchain = '.h5f.root.rawdata' will return obj.h5f.root.rawdata if all members of the chain exist'''
    attrs = re.findall('\.*(\w+)\.*', attrchain)
    for a in attrs:
        if not hasattr(obj,a):#not a in obj.__dict__:
            return None
        obj = getattr(obj, a)
    return obj

def index(seq, f):
    """Return the index of the first item in seq where f(item) == True.
    Example: check if Intrinsic can be found in a list of strings:
    if Helpers.index(zlist, lambda text: text.find('Intrinsic')):
        return 'Intrinsic'
    else:
        return 'Calcium'
    """
    return next((i for i in xrange(len(seq)) if f(seq[i])), None)

class Timer(object):
    '''Simple measurement utility, use as:
    with Timer('give_a_name'):
        statement1
        statementN
    '''
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        if self.name:
            print '[%s]' % self.name,
        print 'Elapsed: %s' % (time.time() - self.tstart)

def celery_available():
    try:
        import celery
        ct=celery.task.control.ping()
        if len(ct)>0:
            return True # at least 1 worker is alive
        else:
            return False # no workers alive
    except: # no celery, run 1 threaded version
        return False
        
def is_list(item):
    if isinstance(item,(list,tuple)):
        response='list'
        if isinstance(item[0],(list,tuple)):
            response='list_of_lists'
        if sum(isinstance(i0,dict) for i0 in item)==len(item):
            response='list_of_dicts'
        if sum(hasattr(i0,'shape') and len(i0.dtype) == 0 for i0 in item)==len(item):
            response = 'list_of_arrays'
        if sum(hasattr(i0,'shape') and len(i0.dtype) > 0 for i0 in item)==len(item):
            response = 'list_of_recarrays'
    else:
        response=None
    return response

from collections import deque
class ModifiableIterator(object):
    '''Implements an normal iterator but the order of the elements in the list being iterated 
    can be rearranged during run-time.'''
    def __init__(self,alist):
        from collections import deque
        self.original = list(alist)
        self.consuming = []
        self.refill()
    
    def refill(self):
        self.list = deque(self.original)
        self.consumed = list(self.consuming) # keep contents in case user wants to look at it
        self.consuming = []
    
    def __len__(self):
        '''Gives back the number of items to be processed'''
        return len(self.list)
        
    def next(self):
        if len(self.list) == 0:
            self.refill()
            raise StopIteration
        else:
            if not hasattr(self.list,'popleft'): # user modified list, make it correct type
                self.list = deque(self.list)
            self.consuming.append(self.list.popleft())
            return self.consuming[-1]
    
    #def __next__(self):
       # self.next()
        
    def __getitem__(self,index):
        if index > len(self.consumed)-1:
            raise IndexError('Index value too hight, cannot return non-consumed items')
        return self.consumed[index]
        
    def __iter__(self):
        if len(self.consuming)>0:
            raise UserWarning('Using the same instance of this class in different for loops can lead to unexpected behavior.')
        return self
    
    def reorder(self,order_list):
        if len(order_list) != len(self.list):
            raise ValueError('Length of the list containing the ordering indices differs from the length of the iterator') 
        self.list = deque(self.list[i] for i in order_list)
    
    def consume(self,items):
        '''Moves the items from the list of items to be iterated to the list of items already visited'''
        self.consuming.extend(items)
        self.list = deque([f for f in self.list if f not in items])
    
      ## {{{ http://code.activestate.com/recipes/82234/ (r1)
# Importing a dynamically generated module

def import_code(code,name,add_to_sys_modules=0):
    """
    Import dynamically generated code as a module. code is the
    object containing the code (a string, a file handle or an
    actual compiled code object, same types as accepted by an
    exec statement). The name is the name to give to the module,
    and the final argument says wheter to add it to sys.modules
    or not. If it is added, a subsequent import statement using
    name will return this module. If it is not added to sys.modules
    import will try to load it in the normal fashion.

    import foo

    is equivalent to

    foofile = open("/path/to/foo.py")
    foo = importCode(foofile,"foo",1)

    Returns a newly generated module.
    """
    import sys,imp

    module = imp.new_module(name)

    exec code in module.__dict__
    if add_to_sys_modules:
        sys.modules[name] = module
    return module


  
import unittest
class TestUtils(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_01_ModifiableIterator(self):
        list = [1,2,3,4]
        alist = ModifiableIterator(list)
        result=[]
        for item in alist:
            if item==2:
                alist.list = [1,3,4,5]
            result.append(item)
        self.assertEqual(result,[1,2,1,3,4,5])
        
    def test_flatten(self):
        a = []
        for i in xrange(3):
            a = [a, i]
            a = flatten(a)
        #self.assertEqual()
        
    def test_dynamic_import(self):
        # Example
        code = \
        """
        def testFunc():
            print "spam!"

        class testClass:
            def testMethod(self):
                print "eggs!"
        """

        m = import_code(code,"test")
        m.testFunc()
        o = m.testClass()
        o.testMethod()
        ## end of http://code.activestate.com/recipes/82234/ }}}
    
if __name__=='__main__':
    unittest.main()
   






    
