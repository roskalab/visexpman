import traceback
import Queue
import re
import unittest
method_extract = re.compile('SOC(.+)EOC') # a command is a string starting with SOC and terminated with EOC (End Of Command)
parameter_extract = re.compile('EOC(.+)EOP') # an optional parameter string follows EOC terminated by EOP. In case of binary data EOC and EOP should be escaped.

class CommandParser(object):
    '''
    generic class that parses the content of incoming queue(s) and calls the corresponding functions
    
    The handlers for user commands are implemented as methods in a subclass of CommandParser. 
    Functions expecting nonkeyword, keyword and mixed arguments are supported
    '''
    def __init__(self, queue_in, queue_out, log = None, failsafe = True):
        if hasattr(queue_in, 'get'):
            self.queue_in = [queue_in]
        elif hasattr(queue_in, 'index'):
            self.queue_in = queue_in
        self.queue_out = queue_out
        self.log = log
        self.function_call_list = []
        self.failsafe = failsafe
    
    def parse(self):
        display_message  = ''
        #gather messages from queues and parse them to function call format
        for queue in self.queue_in:
            while not queue.empty():
                message = queue.get()
                display_message += '\n' + message
                method = method_extract.findall(message)
                arguments = parameter_extract.findall(message.replace('\n',  '<newline>'))
                if len(method) > 0:
                    function_call = {'method' : method[0] }
                    if len(arguments) > 0:
                        arguments = arguments[0].split(',')
                    else:
                        arguments = ()
                    #separate arguments to keyword and non-keyword arguments
                    keyword_arguments = {}
                    non_keyword_arguments = []
                    for argument in arguments:
                        if '=' in argument:
                            keyword_and_value = argument.split('=')
                            keyword_arguments[keyword_and_value[0]] = keyword_and_value[-1]
                        else:
                            non_keyword_arguments.append(argument)
                    non_keyword_arguments = tuple(non_keyword_arguments)
                    function_call['arguments'] = non_keyword_arguments
                    function_call['keyword_arguments'] = keyword_arguments
                    self.function_call_list.append(function_call)
        #call functions
        self.function_call_results = []
        for function in self.function_call_list:
            if hasattr(self, function['method']):
                if self.failsafe:
                    try:
                        self.function_call_results.append(getattr(self, function['method'])(*function['arguments'], **function['keyword_arguments']))
                    except:
                        traceback_info = traceback.format_exc()
                        if hasattr(self.log, 'info'):
                            self.log.info(traceback_info)
                        display_message += '\n' + traceback_info
                else:
                    self.function_call_results.append(getattr(self, function['method'])(*function['arguments'], **function['keyword_arguments']))
                if hasattr(self.log, 'info'):
                    self.log.info(function)
        self.function_call_list = []
        if len(self.function_call_results) > 0:            
            return self.function_call_results
        else:
            return [display_message]
        
class TestCommandParser(CommandParser):
    def test0(self):
        self.test0 = 0
        return 0
        
    def test1(self, par):
        self.test1 = int(par)
        return 1

    def test2(self, par1, par2):
        self.arg1 = int(par1)
        self.arg2 = par2
        return 2
        
    def test_keyword(self, par1, par2 = 3):
        self.par1 = par1
        self.par2 = par2
        return 'kw'
        
    def test_keyword_only(self, par = 0):
        self.par = par
        return 'kw_only'

class TestCommandHandler(unittest.TestCase):
    def setUp(self):
        self.queue_in = Queue.Queue()
        self.queue_out = Queue.Queue()
        
    def test_01_no_arg(self):
        self.queue_in.put('SOCtest0EOCEOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((hasattr(cp, 'test0'), cp.function_call_results[0]), (True, 0))
        
    def test_02_one_arg(self):
        self.queue_in.put('SOCtest1EOC1EOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.test1, cp.function_call_results[0]), (1, 1))
        
    def test_03_two_arg(self):
        self.queue_in.put('SOCtest2EOC1,okEOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.arg1, cp.arg2, cp.function_call_results[0]), (1, 'ok', 2))
        
    def test_04_args_to_function_expects_no_args(self):
        self.queue_in.put('SOCtest0EOC1,okEOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((hasattr(cp, 'arg1'), hasattr(cp, 'arg2'), len(cp.function_call_results)), (False, False, 0))
        
    def test_05_no_args_to_function_that_expects(self):
        self.queue_in.put('SOCtest2EOCEOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((hasattr(cp, 'arg1'), hasattr(cp, 'arg2'), len(cp.function_call_results)), (False, False, 0))
        
    def test_05_function_expects_keywords(self):
        self.queue_in.put('SOCtest_keywordEOC1,par2=2EOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.par1, cp.par2, cp.function_call_results[0]), ('1', '2', 'kw'))
        
    def test_06_function_expects_keywords(self):
        self.queue_in.put('SOCtest_keywordEOC1EOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.par1, cp.par2, cp.function_call_results[0]), ('1', 3, 'kw'))
        
    def test_07_function_expects_only_keywords_no_arg(self):
        self.queue_in.put('SOCtest_keyword_onlyEOCEOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.par, cp.function_call_results[0]), (0, 'kw_only'))

    def test_07_function_expects_only_keywords(self):
        self.queue_in.put('SOCtest_keyword_onlyEOCpar=1EOP')
        cp = TestCommandParser(self.queue_in, self.queue_out)
        cp.parse()
        self.assertEqual((cp.par, cp.function_call_results[0]), ('1', 'kw_only'))

if __name__=='__main__':
    unittest.main()
