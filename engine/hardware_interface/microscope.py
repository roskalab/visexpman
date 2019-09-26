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
        
    def close(self):
        pass
        
    def finish_batch(self):
        '''
        Any action needed for finishing a batch experiment like setting back z position
        '''
        
    def start_batch(self):
        '''
        Any action needed for starting a batch experiment like resetting z position
        '''
