#OBSOLETE
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.configuration as configuration
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.test.unittest_aggregator as unittest_aggregator
import Queue
import os.path
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.dataprocessors.signal as signal
import time
import numpy

class MesTestConfig(configuration.Config):
    def _set_user_parameters(self):
        import random
        self.BASE_PORT = 10000 + 0* int(10000*random.random())
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : '172.27.25.220', 
        'ENABLE' : True, 
        'TIMEOUT' : 10.0, 
        'CONNECTION_MATRIX':
            {
            'TEST_MES'  : {'TEST' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}},             
            }
        }
        EXPERMENT_DATA_PATH = '/home/zoltan/share/data'
        MES_DATA_FOLDER = 'V:\\data'
        
        self._create_parameters_from_locals(locals())
        
class MesTest(object):
    def __init__(self, config):
        self.config = config
        self.server = network_interface.CommandRelayServer(self.config)
        self.mes_command_queue = Queue.Queue()
        self.mes_response_queue = Queue.Queue()        
        self.mes_connection = network_interface.start_client(self.config, 'TEST', 'TEST_MES', self.mes_response_queue, self.mes_command_queue)        
            
    def experiment_z_stack(self, test_mat_file = None, timeout = 0.0):
        '''

        '''
        raw_input('Connect MES and press a key')
        z_stack, results = mes_interface.acquire_z_stack( self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout, test_mat_file = test_mat_file)
        print z_stack, results
        
    def experiment_z_stack_set_points(self, test_mat_file = None, timeout = 0.0):
        '''
            Acquire z stack
            find points with um coordinates.
            Acquire zstack with different xyz scales/ranges.
            Display the points found in the 1st zstack 
        '''
        raw_input('Connect MES and press a key')
        z_stack, results = mes_interface.acquire_z_stack( self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout, test_mat_file = test_mat_file)
        raw_input('Z stack done?')        
        if z_stack != {}:
            centroids = find_cells_centroids(z_stack)            
            print centroids ['row'].max(), centroids ['row'].min(), centroids ['col'].max(), centroids ['col'].min(), centroids ['depth'].max(), centroids ['depth'].min()
            raw_input('Create new z stack and press a key')
            return mes_interface.set_points(centroids, self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout)
        else:
            return 'no z stack'
            
    def experiment_set_points(self, z_stack_path, timeout = 0.0):
        '''
        Find points in a given z stack mes file and send them to mes
        '''
        z_stack = {}        
        z_stack['data'], z_stack['origin'], z_stack['scale'], z_stack['size'] = mes_interface.z_stack_from_mes_file(z_stack_path)
        centroids = find_cells_centroids(z_stack)
        raw_input('MES shall be connected, ready to send points?')
#        centroids = generate_cube(z_stack)
        print centroids
        return mes_interface.set_points(centroids, self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout)        
 
    def experiment_rc_scan(self, timeout = 0.0, z_stack_path = None):
        '''
        Acquire z stack 
        find points in um 
        send point to MES and request RC scan on those points 
        MES gives back the estimated trajectory 
        MES scans the trajectory and gives back vector of xyz - intensity value pairs 
        find points on the result data give back to MES and overlay on original zstack
        '''
        raw_input('Connect MES and press a key')
        z_stack = {}
        z_stack, results = mes_interface.acquire_z_stack( self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout)        
        if z_stack == {} and z_stack_path != None:            
            z_stack['data'], z_stack['origin'], z_stack['scale'], z_stack['size'] = mes_interface.z_stack_from_mes_file(z_stack_path)   
        
        trajectory = find_cells_centroids(z_stack)
        scanned_trajectory, results = mes_interface.rc_scan(trajectory, self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout)            
        centroids = trajectory #cells need to be find in scanned_trajectory
        raw_input('Send back cell centroids found in trajectory scan')
        mes_interface.set_points(centroids, self.mes_command_queue, self.mes_response_queue, self.config, timeout = timeout)
            
    def close(self):
        self.mes_command_queue.put('SOCclose_connectionEOCstop_clientEOP')        
        time.sleep(0.5)
        for i in self.server.get_debug_info():
            print i
        self.server.shutdown_servers()
        time.sleep(1.0)
        
def generate_cube(z_stack):
    centroid_dtype = [('row', numpy.float64), ('col', numpy.float64), ('depth', numpy.float64)]
    vertices = numpy.array([[0, 0, 0], 
                 [0, 0, 1], 
                 [0, 1, 0], 
                 [0, 1, 1], 
                 [1, 0, 0], 
                 [1, 0, 1], 
                 [1, 1, 0], 
                 [1, 1, 1] ], dtype = numpy.float64)
    lengths = [1]
    centroids = []
    for length in lengths:
        for vertice in vertices:
            centroids.append(tuple(z_stack['origin']+z_stack['size'] * vertice))
    centroids = numpy.array(centroids, dtype = centroid_dtype)
    return centroids
    
def find_cells_centroids(z_stack):
    #Find cell centers
    dim_order = [0, 1, 2]
    centroids = signal.regmax(z_stack['data'],dim_order)
    #convert from record array to normal array, so that it could be shifted and scaled, when RC array operators are ready,. this wont be necessary anymore
    centroids = numpy.array([centroids['row'], centroids['col'], centroids['depth']], dtype = numpy.float64).transpose()
    #Scale to um
    centroids *=  z_stack['scale']
    #Move with MES system origo
    centroids += z_stack['origin']
    #Convert back to recordarray
    centroid_dtype = [('row', numpy.float64), ('col', numpy.float64), ('depth', numpy.float64)]
    centroids_tuple = []
    for centroid in centroids:
        centroids_tuple.append((centroid[0], centroid[1], centroid[2]))
    centroids = numpy.array(centroids_tuple, dtype = centroid_dtype)
    return centroids
        
if __name__ == '__main__':
    c = MesTestConfig()
    m = MesTest(c)
#    print m.experiment_z_stack_set_points(test_mat_file = None,  timeout = 30.0)
#    print m.experiment_set_points('/home/zoltan/share/data/z_stack_00000.mat',  timeout = 2.0)    
#    print m.experiment_z_stack_set_points(timeout = 5.0)
#    m.experiment_rc_scan(timeout = 1.0,z_stack_path = '/home/zoltan/share/data/z_stack_00000.mat')
    m.experiment_z_stack(timeout = 10.0)
    m.close()
