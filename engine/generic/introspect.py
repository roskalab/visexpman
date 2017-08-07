import logging
import logging.handlers
log = logging.getLogger('introspect')
try:
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.QtCore as QtCore
from contextlib import contextmanager
import inspect
import time
import re
import sys
import numpy
import copy
import hashlib
## {{{ http://code.activestate.com/recipes/519621/ (r4)
import weakref
import subprocess

@contextmanager
def nostderr():
    savestderr = sys.stderr
    class Devnull(object):
        def write(self, _): pass
    sys.stderr = Devnull()
    yield
    sys.stderr = savestderr

def hash_variables(variables):
        import hashlib
        import cPickle
        myhash = hashlib.md5()
        if not isinstance(variables, (list, tuple)): variables = [ variables]
        for v in variables:
            myhash.update(cPickle.dumps(v))
        return myhash.digest()
        
def kill_child_processes(parent_pid, sig='SIGTERM'):
        ps_command = subprocess.Popen("ps -o pid --ppid %d --noheaders" % parent_pid, shell=True, stdout=subprocess.PIPE)
        ps_output = ps_command.stdout.read()
        retcode = ps_command.wait()
        assert retcode == 0, "ps command returned %d" % retcode
        for pid_str in ps_output.split("\n")[:-1]:
            try:
                os.kill(int(pid_str), getattr(signal, sig))
            except:
                pass

class FauxTb(object):
    def __init__(self, tb_frame, tb_lineno, tb_next):
        self.tb_frame = tb_frame
        self.tb_lineno = tb_lineno
        self.tb_next = tb_next

def current_stack(skip=0):
    try: 1/0
    except ZeroDivisionError:
        f = sys.exc_info()[2].tb_frame
    for i in xrange(skip + 2):
        f = f.f_back
    lst = []
    while f is not None:
        lst.append((f, f.f_lineno))
        f = f.f_back
    return lst

def extend_traceback(tb, stack):
    """Extend traceback with stack info."""
    head = tb
    for tb_frame, tb_lineno in stack:
        head = FauxTb(tb_frame, tb_lineno, head)
    return head

def full_exc_info():
    """Like sys.exc_info, but includes the full traceback."""
    t, v, tb = sys.exc_info()
    full_tb = extend_traceback(tb, current_stack(1))
    return t, v, full_tb
        
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
## {{{ http://code.activestate.com/recipes/502283/ (r1)
# -*- coding: iso-8859-15 -*-
"""locks.py - Read-Write lock thread lock implementation

See the class documentation for more info.

Copyright (C) 2007, Heiko Wundram.
Released under the BSD-license.
"""

# Imports
# -------

from threading import Condition, Lock, currentThread
#from time import time


# Read write lock
# ---------------

class ReadWriteLock(object):
    """Read-Write lock class. A read-write lock differs from a standard
    threading.RLock() by allowing multiple threads to simultaneously hold a
    read lock, while allowing only a single thread to hold a write lock at the
    same point of time.

    When a read lock is requested while a write lock is held, the reader
    is blocked; when a write lock is requested while another write lock is
    held or there are read locks, the writer is blocked.

    Writers are always preferred by this implementation: if there are blocked
    threads waiting for a write lock, current readers may request more read
    locks (which they eventually should free, as they starve the waiting
    writers otherwise), but a new thread requesting a read lock will not
    be granted one, and block. This might mean starvation for readers if
    two writer threads interweave their calls to acquireWrite() without
    leaving a window only for readers.

    In case a current reader requests a write lock, this can and will be
    satisfied without giving up the read locks first, but, only one thread
    may perform this kind of lock upgrade, as a deadlock would otherwise
    occur. After the write lock has been granted, the thread will hold a
    full write lock, and not be downgraded after the upgrading call to
    acquireWrite() has been match by a corresponding release().
    """

    def __init__(self):
        """Initialize this read-write lock."""

        # Condition variable, used to signal waiters of a change in object
        # state.
        self.__condition = Condition(Lock())

        # Initialize with no writers.
        self.__writer = None
        self.__upgradewritercount = 0
        self.__pendingwriters = []

        # Initialize with no readers.
        self.__readers = {}

    def acquireRead(self, blocking=True, timeout=None):
        """Acquire a read lock for the current thread, waiting at most
        timeout seconds or doing a non-blocking check in case timeout is <= 0.

        In case timeout is None, the call to acquireRead blocks until the
        lock request can be serviced.

        In case the timeout expires before the lock could be serviced, a
        RuntimeError is thrown."""

        if not blocking:
            endtime = -1
        elif timeout is not None:
            endtime = time.time() + timeout
        else:
            endtime = None
        me = currentThread()
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # If we are the writer, grant a new read lock, always.
                self.__writercount += 1
                return
            while True:
                if self.__writer is None:
                    # Only test anything if there is no current writer.
                    if self.__upgradewritercount or self.__pendingwriters:
                        if me in self.__readers:
                            # Only grant a read lock if we already have one
                            # in case writers are waiting for their turn.
                            # This means that writers can't easily get starved
                            # (but see below, readers can).
                            self.__readers[me] += 1
                            return
                        # No, we aren't a reader (yet), wait for our turn.
                    else:
                        # Grant a new read lock, always, in case there are
                        # no pending writers (and no writer).
                        self.__readers[me] = self.__readers.get(me,0) + 1
                        return
                if timeout is not None:
                    remaining = endtime - time.time()
                    if remaining <= 0:
                        # Timeout has expired, signal caller of this.
                        raise RuntimeError("Acquiring read lock timed out")
                    self.__condition.wait(remaining)
                else:
                    self.__condition.wait()
        finally:
            self.__condition.release()

    def acquireWrite(self,blocking=True, timeout=None):
        """Acquire a write lock for the current thread, waiting at most
        timeout seconds or doing a non-blocking check in case timeout is <= 0.

        In case the write lock cannot be serviced due to the deadlock
        condition mentioned above, a ValueError is raised.

        In case timeout is None, the call to acquireWrite blocks until the
        lock request can be serviced.

        In case the timeout expires before the lock could be serviced, a
        RuntimeError is thrown."""

        if not blocking:
            endtime = -1
        elif timeout is not None:
            endtime = time() + timeout
        else:
            endtime = None
        me, upgradewriter = currentThread(), False
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # If we are the writer, grant a new write lock, always.
                self.__writercount += 1
                return
            elif me in self.__readers:
                # If we are a reader, no need to add us to pendingwriters,
                # we get the upgradewriter slot.
                if self.__upgradewritercount:
                    # If we are a reader and want to upgrade, and someone
                    # else also wants to upgrade, there is no way we can do
                    # this except if one of us releases all his read locks.
                    # Signal this to user.
                    raise ValueError(
                        "Inevitable dead lock, denying write lock"
                        )
                upgradewriter = True
                self.__upgradewritercount = self.__readers.pop(me)
            else:
                # We aren't a reader, so add us to the pending writers queue
                # for synchronization with the readers.
                self.__pendingwriters.append(me)
            while True:
                if not self.__readers and self.__writer is None:
                    # Only test anything if there are no readers and writers.
                    if self.__upgradewritercount:
                        if upgradewriter:
                            # There is a writer to upgrade, and it's us. Take
                            # the write lock.
                            self.__writer = me
                            self.__writercount = self.__upgradewritercount + 1
                            self.__upgradewritercount = 0
                            return
                        # There is a writer to upgrade, but it's not us.
                        # Always leave the upgrade writer the advance slot,
                        # because he presumes he'll get a write lock directly
                        # from a previously held read lock.
                    elif self.__pendingwriters[0] is me:
                        # If there are no readers and writers, it's always
                        # fine for us to take the writer slot, removing us
                        # from the pending writers queue.
                        # This might mean starvation for readers, though.
                        self.__writer = me
                        self.__writercount = 1
                        self.__pendingwriters = self.__pendingwriters[1:]
                        return
                if timeout is not None:
                    remaining = endtime - time()
                    if remaining <= 0:
                        # Timeout has expired, signal caller of this.
                        if upgradewriter:
                            # Put us back on the reader queue. No need to
                            # signal anyone of this change, because no other
                            # writer could've taken our spot before we got
                            # here (because of remaining readers), as the test
                            # for proper conditions is at the start of the
                            # loop, not at the end.
                            self.__readers[me] = self.__upgradewritercount
                            self.__upgradewritercount = 0
                        else:
                            # We were a simple pending writer, just remove us
                            # from the FIFO list.
                            self.__pendingwriters.remove(me)
                        raise RuntimeError("Acquiring write lock timed out")
                    self.__condition.wait(remaining)
                else:
                    self.__condition.wait()
        finally:
            self.__condition.release()

    def release(self):
        """Release the currently held lock.

        In case the current thread holds no lock, a ValueError is thrown."""

        me = currentThread()
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # We are the writer, take one nesting depth away.
                self.__writercount -= 1
                if not self.__writercount:
                    # No more write locks; take our writer position away and
                    # notify waiters of the new circumstances.
                    self.__writer = None
                    self.__condition.notifyAll()
            elif me in self.__readers:
                # We are a reader currently, take one nesting depth away.
                self.__readers[me] -= 1
                if not self.__readers[me]:
                    # No more read locks, take our reader position away.
                    del self.__readers[me]
                    if not self.__readers:
                        # No more readers, notify waiters of the new
                        # circumstances.
                        self.__condition.notifyAll()
            else:
                raise ValueError("Trying to release unheld lock")
        finally:
            self.__condition.release()
            
    @property
    @contextmanager
    def readlock(self):
        self.acquireRead()
        try:
            yield
        finally:
            self.release()
            
    @property
    @contextmanager
    def writelock(self):
        self.acquireWrite()
        try:
            yield
        finally:
            self.release()
            
## end of http://code.activestate.com/recipes/502283/ }}}

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
    #consider using itertools.chain(*mylist)
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

def list_of_empty_mutables(n, prototype=list()):
    return [copy.deepcopy(prototype) for _ in range(n)]

def dict_of_empty_mutables(keys,prototype=list(),dict_type = dict):
    return dict_type(zip(keys,list_of_empty_mutables(len(keys),prototype)))
    
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
        
def list_type(item):
    try: # is data convertible to numpy array of scalar (including string) values?
        item2=numpy.array(item)
        if isinstance(item, (list, tuple)) and item2.dtype.names is None and item2.dtype !=object:#numpy.issctype(item2.dtype):
            return 'arrayized'
    except Exception as e:
        print e
    if isinstance(item,(list,tuple)):
        if isinstance(item[0],(list,tuple)):
            response='list_of_lists'
        elif sum(isinstance(i0,dict) for i0 in item)==len(item):
            response='list_of_dicts'
        elif sum(hasattr(i0,'shape') and len(i0.dtype) == 0 for i0 in item)==len(item):
            response = 'list_of_arrays'
        elif sum(hasattr(i0,'shape') and len(i0.dtype) > 0 for i0 in item)==len(item):
            if all([i0.shape==item[0].shape for i0 in item]):
                response = 'list_of_uniform_shaped_recarrays'
            else:
                response = 'list_of_recarrays'
        else:
            response = 'inhomogenous_list'
    else:
        response=None
    return response

def dict_isequal(d1,d2):
    if set(d1.keys()) != set(d2.keys()): return False
    for k in d1.keys():
        if hasattr(d1[k],'shape'):
            if numpy.any(d1[k]!=d2[k]): return False
        else: 
            if d1[k]!=d2[k]: return False
    return True

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
   






    
