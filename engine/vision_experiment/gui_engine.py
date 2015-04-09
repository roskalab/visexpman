import time
import threading
import multiprocessing
import unittest

class GUIDataItem(object):
    def __init__(self,name,value,path):
        self.name = name
        self.n = name
        self.value = value
        self.v=value
        self.path = path
        self.p=path
        
class GUIData(object):
    def __init__(self,context_filename):
        self.context_filename = context_filename
        #TODO: reads data items from context file
        
    def add(self, name, value, path):
        setattr(self,name,GUIDataItem(name,value,path))#Overwritten if already exists
        
    def read(self, name = None, path = None, **kwargs):
        if name is not None and hasattr(self,name):
            return getattr(self,name).value
        elif path is not None:
            for v in dir(self):
                v = getattr(self,v)
                if isinstance(v, GUIDataItem) and (v.path == path or path in v.path):
                    return v.value
        
    def save(self,context_filename = None):
        if context_filename is None:
            context_filename = self.context_filename
        

class GUIEngineInterface(threading.Thread):
    '''
    GUI engine: receives commands via two queue interfaces (gui, engine) and performs the following actions:
     - stores data internally
     - initiates actions on gui or in engine
     
     Command format:
     {'command_name': [parameters]}
    '''

    def __init__(self, context_filename):
        threading.Thread.__init__(self)
        self.from_gui = multiprocessing.Queue()
        self.to_gui = multiprocessing.Queue()
        self.from_engine = multiprocessing.Queue()
        self.to_engine = multiprocessing.Queue()
        self.data = GUIData(context_filename)
        
    def get_queues(self, interface):
        if interface == 'gui':
            return self.from_gui, self.to_gui
        elif interface == 'engine':
            return self.from_engine, self.to_engine
    
    def run(self):
        while True:
            if not self.from_gui.empty():
                msg = self.from_gui.get()
                if msg == 'terminate':
                    break
                send_to = 'engine'
                source = 'gui'
            elif not self.from_engine.empty():
                msg = self.from_engine.get()
                send_to = 'gui'
                source = 'engine'
            else:
                continue
            #parse message
            if msg.has_key('data'):#expected format: {'data': value, 'path': gui path, 'name': name}
                self.data.add(msg['name'], msg['data'], msg['path'])#Storing gui data
            elif msg.has_key('read'):#engine might need additional data for executing a certain function
                value = self.data.read(**msg)
                getattr(self, 'to_'+source).put(value)
            elif msg.has_key('function'):#Functions are simply forwarded
                #Format: {'function: function name, 'args': [], 'kwargs': {}, 'scope': some information about where the called function resides}
                getattr(self, 'to_'+send_to).put(msg)
            time.sleep(100e-3)
            
class TestGUIEngineIF(unittest.TestCase):
    def setUp(self):
        self.wait = 100e-3
        self.interface = GUIEngineInterface(None)
        self.from_gui, self.to_gui = self.interface.get_queues('gui')
        self.from_engine, self.to_engine = self.interface.get_queues('engine')
        self.interface.start()
        
    def test_01_add_and_read_data(self):
        v = 100
        self.from_gui.put({'data': v, 'name': 'dummy', 'path': 'test.dummy'})
        time.sleep(self.wait)
        self.assertEqual(self.interface.data.dummy.v, v)
        self.assertEqual(self.interface.data.dummy.n, 'dummy')
        self.from_engine.put({'read':None, 'name':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_engine.empty())
        self.assertEqual(self.to_engine.get(), v)
        #access by path
        self.from_engine.put({'read':None, 'path':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_engine.empty())
        self.assertEqual(self.to_engine.get(), v)
        #access by invalid path
        self.from_engine.put({'read':None, 'path':'dummy.'})
        time.sleep(self.wait)
        self.assertFalse(self.to_engine.empty())
        self.assertEqual(self.to_engine.get(), None)
        
    def test_02_function(self):
        function_call={'function': 'test', 'args': [1,2,3], 'scope': 'unknown'}
        self.from_engine.put(function_call)
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertTrue(self.to_engine.empty())
        self.assertEqual(self.to_gui.get(), function_call)
        
        
    def tearDown(self):
        self.from_gui.put('terminate')
        self.interface.join()

            
if __name__=='__main__':
    unittest.main()
