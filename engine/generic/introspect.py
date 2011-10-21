import logging
import logging.handlers
log = logging.getLogger('Helpers')
try: import wx
except: log.debug('wx import failed')


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

def traverse(obj,  attrchain):
    '''Walks trough the attribute chain starting from obj and returns the last element of the chain. E.g.
    attrchain = '.h5f.root.rawdata' will return obj.h5f.root.rawdata if all members of the chain exist'''
    attrs = re.findall('\.*(\w+)\.*', attrchain)
    for a in attrs:
        if not hasattr(obj,a):#not a in obj.__dict__:
            return None
        obj = getattr(obj, a)
    return obj
