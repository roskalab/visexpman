import visexpman
import unittest

start_directory = '/home/zoltan/development/visexpman/engine/generic'
#start_directory = '/home/zoltan/development/visexpman'
test_configs = [
               {'module_path' : 'visexpman.engine.generic.configuration', 
               'test_class' : 'testConfiguration', 
               'enable' : True
               }               
               ]

testable_modules = unittest.TestLoader().discover(start_directory, pattern = '*.py')
#testable_modules = unittest.TestLoader().loadTestsFromModule(visexpman.engine.generic.configuration)
#testable_modules = unittest.TestLoader().loadTestsFromModule(visexpman.engine.generic.configuration)
print testable_modules
for testable_module in testable_modules:
    if testable_module.countTestCases() > 0:
        print testable_module
#        unittest.TextTestRunner(verbosity=2).run(testable_module)



#for test_config in test_configs:
#    __import__(test_config['module_path'])
##    suite = unittest.TestLoader().loadTestsFromTestCase(visexpman.engine.generic.configuration.testConfiguration)    
#    module_path = test_config['module_path'].split('.')
#    suite = unittest.TestLoader().loadTestsFromTestCase(getattr(visexpman, test_config['module_path'].replace('.visexpman', '')))
#    unittest.TextTestRunner(verbosity=2).run(suite)
