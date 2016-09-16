#!/usr/bin/env python
"""
PyZeroMQt - zmqsocket.py: Provides a wrapper for a ZeroMQ socket 
"""
from PyQt4.QtCore import QObject, QSocketNotifier, pyqtSignal
from zmqcontext import ZmqContext
from zmq import FD, LINGER, IDENTITY, SUBSCRIBE, UNSUBSCRIBE, EVENTS, \
                POLLIN, POLLOUT, POLLERR, NOBLOCK, ZMQError, EAGAIN

class ZmqSocket(QObject):
    readyRead=pyqtSignal()
    readyWrite=pyqtSignal()
    def __init__(self, _type, parent=None):
        QObject.__init__(self, parent)

        ctx=ZmqContext.instance()
        self._socket=ctx._context.socket(_type)
        self.setLinger(ctx.linger())

        fd=self._socket.getsockopt(FD)
        self._notifier=QSocketNotifier(fd, QSocketNotifier.Read, self)
        self._notifier.activated.connect(self.activity)

    def __del__(self): self._socket.close()

    def setIdentity(self, name): self._socket.setsockopt(IDENTITY, name)

    def identity(self): return self._socket.getsockopt(IDENTITY)

    def setLinger(self, msec): self._socket.setsockopt(LINGER, msec)

    def linger(self): return self._socket.getsockopt(LINGER)

    def subscribe(self, _filter): self._socket.setsockopt(SUBSCRIBE, _filter)

    def unsubscribe(self, _filter): self._socket.setsockopt(UNSUBSCRIBE, _filter)

    def bind(self, addr): self._socket.bind(addr)

    def connect(self, addr): self._socket.connect(addr)

    def activity(self):
        flags=self._socket.getsockopt(EVENTS)
        if flags&POLLIN: self.readyRead.emit()
        elif flags&POLLOUT: self.readyWrite.emit()
        elif flags&POLLERR: print "ZmqSocket.activity(): POLLERR"
        else: print str(flags) + " ZmqSocket.activity(): fail"

    def _recv(self, flags=NOBLOCK):
        try: _msg=self._socket.recv(flags=flags)
        except ZMQError as e:
            if e.errno==EAGAIN: return None
            else: raise ZMQError(e)
        else: return _msg
        
    def _recv_json(self, flags=NOBLOCK):
        try: _msg=self._socket.recv_json(flags=flags)
        except ZMQError as e:
            if e.errno==EAGAIN: return None
            else: raise ZMQError(e)
        else: return _msg

    def recv(self):
        _return=[]
        while 1:
            _msg=self._recv()
            if not _msg: break
            _return.append(_msg)
        return _return 
 
    def recv_json(self):
        _return=[]
        while 1:
            _msg=self._recv_json()
            if not _msg: break
            _return.append(_msg)
        return _return 

    def send(self, _msg): return self._socket.send(_msg)
