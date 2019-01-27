class TwoPhotonMicroscopeInterface(object):
    def __init__(self):
        '''
        Initialize microscope interface
        '''
        
    def start(self, duration=None):
        '''
        Start imaging
        '''
        
    def stop(self):
        '''
        Terminate imaging
        '''
        
    def save(self, filename):
        '''
        Save imaging data to provided location
        '''
