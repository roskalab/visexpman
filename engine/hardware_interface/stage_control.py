import numpy, struct
import re
import time
try:
    import serial
except:
    print('pyserial not installed')

import unittest
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    print('No pydaqmx installed')
from visexpman.engine.hardware_interface import instrument
import visexpman.engine.generic.configuration
from visexpman.engine.generic import utils
try:
    from visexpman.users.test import unittest_aggregator
    test_mode=True
except IOError:
    test_mode=False

extract_goniometer_axis1 = re.compile('\rX(.+)\n')
extract_goniometer_axis2 = re.compile('\rY(.+)\n')
parameter_extract = re.compile('EOC(.+)EOP')

simulated_stage_position = numpy.zeros(3)

class StageControl(instrument.Instrument):
    '''
    (States: init, ready, moving, error)
    '''
    def __init__(self, config,  log = None, experiment_start_time = None, settings = None, id = 0, queue = None):
        instrument.Instrument.__init__(self, config,  log = None, experiment_start_time = None, settings = None, id = id)
        self.queue = queue
                              
    def init_communication_interface(self):
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.serial_port = serial.Serial(port =self.config.STAGE[self.id]['SERIAL_PORT']['port'],
                                                                baudrate = self.config.STAGE[self.id]['SERIAL_PORT']['baudrate'],
                                                                parity = self.config.STAGE[self.id]['SERIAL_PORT']['parity'],
                                                                stopbits = self.config.STAGE[self.id]['SERIAL_PORT']['stopbits'],
                                                                bytesize = self.config.STAGE[self.id]['SERIAL_PORT']['bytesize'],
                                                                timeout = 0.1)
    def read_position(self):
        pass
        
    def move(self, new_position, relative = True, speed = None, acceleration = None):
        pass
                                                            
    def close_communication_interface(self):
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                try:
                    self.serial_port.close()
                except AttributeError:
                    pass
                
class AllegraStage(StageControl):
    
    def init_instrument(self):
        self.command_counter = 0
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.acceleration = self.config.STAGE[self.id]['ACCELERATION']
                self.speed = self.config.STAGE[self.id]['SPEED']
                self.reset_controller()
        self.read_position()

    def move(self, new_position, relative = True, speed = None, acceleration = None):
        '''
        new_position: x, y, z, in um
        '''
        if hasattr(self.config, 'SYSTEM_TEST') and self.config.SYSTEM_TEST:
            self.position = self.position + new_position
            global simulated_stage_position
            simulated_stage_position = self.position
            return True
        reached = False
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                #Disable joystick
                self.execute_command('joff')
                new_position_ustep = numpy.array(new_position) / self.config.STAGE[self.id]['UM_PER_USTEP']
                self.read_position()
                if relative:
                    self.required_position = self.position_ustep + numpy.array(new_position_ustep)
                    movement = numpy.array(new_position_ustep)
                else:
                    self.required_position = numpy.array(new_position_ustep)
                    movement = self.required_position - self.position_ustep
                moved_axes = []
                for axis in range(3):
                    if acceleration == None:
                        accel = self.acceleration
                    else:
                        accel = acceleration
                    if speed == None:
                        spd = self.speed
                    else:
                        spd = speed
                    if relative:
                        mode = 'r'
                    else:
                        mode = 'a'
                    if not (mode == 'r' and new_position_ustep[axis] == 0): #if no rel movement is required on this axis, than command is not issued
                        command = 'vel{0} {2}\nacc{0} {3}\npos{0} {1}\nmov{4}{0}' .format(chr(120+axis), str(int(new_position_ustep[axis])), int(spd), int(accel), mode)
                        self.execute_command(command, wait_after_command = False)
                        moved_axes.append(chr(120 + axis))
                move_timeout = self.config.STAGE[self.id]['MOVE_TIMEOUT']
                self.movement = movement
                start_of_wait = time.time()
                response = ''
                while True:
                    response += self.serial_port.read(10)
                    #check for X stopping, Done Y like responses
                    reached = True
                    for moved_axis in moved_axes:
                        keywords = [moved_axis + ' stopping', 'done ' + moved_axis]
                        keyword_in_response = False
                        for keyword in keywords:
                            if keyword in response.lower():
                                keyword_in_response = True
                        if not keyword_in_response:
                            reached = False
                    if reached:
                        break
                    if time.time() - start_of_wait > move_timeout:
                        #Log: no reponse from stage                    
                        break
                    if hasattr(self,'queue') and hasattr(self.queue,  'empty'):
                        if not self.queue.empty():
                            if 'stop' in parameter_extract.findall(self.queue.get())[0]:
                                print('stop stage')
                                self.stop()
                                break
                self.read_position()
                self.movement_time = time.time() - start_of_wait
                #reenable joystick
                self.execute_command('jon')
                self.log_during_experiment('stage move: {0}' .format(new_position))
        return reached

    def read_position(self):
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.serial_port.flushInput()
                self.execute_command('rx\nry\nrz')
                time.sleep(0.5) #used to be 0.5 s
                response = self.serial_port.read(100)
                position = []
                for line in response.replace('\r','').split('\n'):
                    if len(line) > 0:
                        try:
                            if 'Stopping' not in line and 'Done' not in line:
                                position.append(int(line[1:]))
                        except ValueError:
                            print(response)
                            raise RuntimeError('No valid response from motion controller ' + line)
                            
                self.position_ustep = numpy.array(position)
                try:
                    self.position = self.position_ustep * self.config.STAGE[self.id]['UM_PER_USTEP']
                except ValueError:
                    self.position = numpy.zeros(3, dtype = float)
                    print('position in ustep: {0}' .format(self.position_ustep))
                    
            else:
                self.position = numpy.zeros(3, dtype = float)
            return self.position #in um
        elif hasattr(self.config, 'SYSTEM_TEST') and self.config.SYSTEM_TEST:
            global simulated_stage_position
            self.position = simulated_stage_position
            return self.position

    def reset_controller(self):
        self.serial_port.setRTS(True)
        time.sleep(20e-3) #Min 20 ms
        self.serial_port.setRTS(False)
        time.sleep(0.5) #used to be 0.5 s
        
    def stop(self):
        self.execute_command('STOPALL')
        return self.serial_port.read(100)
        
    def execute_command(self, command, print_response = False, wait_after_command = True):
        commands = command.split('\n')
        response = ''
        for cmd in commands:
            if len(cmd) > 0:
                self.serial_port.write(cmd + '\n')
                if wait_after_command:
                    time.sleep(100e-3) #Takes 100 ms to complete the command
                self.command_counter += 1

    def calculate_move_time(self, movement, speed, acceleration):
        speed_up_time = speed / float(acceleration)
        movement_speed_up = 0.5 * speed_up_time * speed
        if movement_speed_up > movement:
            move_time = 2.0 * float(movement) / speed
        else:
            move_time = speed_up_time + float(movement - movement_speed_up) / speed
        return move_time
        
def stage_calibration(side_usteps, folder):
    import visexpA.engine.dataprocessors.itk_versor_rigid_registration as itk_versor_rigid_registration
    try:
        import Image
    except ImportError:
        from PIL import Image
    import visexpA.engine.dataprocessors.signal as signal
    frames = utils.listdir_fullpath(folder)
    frames.sort()
    print(frames)
    for i in range(len(frames)):
        f2 = numpy.array(Image.open(frames[i]))[:, :, 1]
        
#        f2 = f2.reshape(1, f2.shape[0], f2.shape[1])
#        dim_order = [0, 1]
#        points = signal.regmax(f2,dim_order)
#        print points
        
class MotorizedGoniometer(StageControl):
    def init_instrument(self):
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.execute_command('?R')
                readin = self.serial_port.read(100)
                if 'OK' not in readin:
                    raise RuntimeError('Goniometer does not respond: {0}'.format(readin))

    def execute_command(self, commands, wait_after_command = True):
        if not isinstance(commands,  list):
            commands = [commands]
        for command in commands:
            self.serial_port.write(command + '\r')
            if wait_after_command:
                time.sleep(100e-3)
                
    def set_speed(self,  speed):
        self.execute_command(['V'+str(int(speed))])
        if 'OK' in self.serial_port.read(100):
            return True
        else:
            return False

    def read_position(self, print_position = False):
        #flush input buffer
        self.serial_port.read(100)
        result  = False
        self.execute_command(['?X', '?Y'])
        response = self.serial_port.read(100)
        if len(response)>0:
            try:
                self.position_ustep = numpy.array(map(int,  [extract_goniometer_axis1.findall(response)[0],  extract_goniometer_axis2.findall(response)[0]]))
                self.position = self.position_ustep * self.config.STAGE[self.id]['DEGREE_PER_USTEP']
                result = True
            except:
                if print_position:
                    import traceback
                    print(traceback.format_exc())
                    print(response)
        if not hasattr(self, 'position'):
            self.position = numpy.zeros(2)
        if print_position:
            print(self.position)
        return self.position, result
        
    def move(self, angle):
        '''
        Move 2 axis goniometer relative to current position
        '''
        initial_position = self.read_position()[0]
        angle_in_ustep =  angle / self.config.STAGE[self.id]['DEGREE_PER_USTEP']
        axis = ['X', 'Y']
        result = True
        for i in range(2):
            if angle_in_ustep[i] < 0:
                sign = '-'
            else:
                sign = '+'
            if angle_in_ustep[i] != 0:
                self.execute_command('{2}{0}{1}'.format(sign,  int(abs(angle_in_ustep[i])),  axis[i]))
                timeout = utils.Timeout(self.config.STAGE[self.id]['MOVE_TIMEOUT'])
                if not timeout.wait_timeout(self.position_reached):
                    result = False
        return result
            
    def position_reached(self):
        if 'OK' in self.serial_port.read(100):
            return True
        else:
            return False
            
class RemoteFocus(object):
    '''
    Remote Focus device controls objective position. Default baud rate is 1200
    '''
    def __init__(self,comport, baudrate = 1200):
        self.scale = 1e-2
        self.serial_port = serial.Serial(port =comport, baudrate = baudrate,
                                                    parity = serial.PARITY_NONE,
                                                    stopbits = serial.STOPBITS_ONE,
                                                    bytesize = serial.EIGHTBITS,    
                                                    timeout = 1.0)
        pass
    
    def execute_command(self, command, wait_after_command = True):
        self.serial_port.write(command + '\r\n')
        if wait_after_command:
            time.sleep(500e-3)
            
    def read(self):
        return self.read_position()
    
    def read_position(self, print_position = False):
        self.serial_port.flushInput()
        pos = None
        ct = 0
        while not isinstance(pos, float):
            self.execute_command('WZ')
            pos = self._parse_response(self.serial_port.read(30))
            ct += 1
            if ct > 10:
                break
        return pos
                
    def _parse_response(self,response):
        if 'Unknown Command' in response:
            return False
        if len(response)>0:
            try:
                return float(response.split(':A')[1])*self.scale
            except:
                print(response)
                return False
        return False
                
    def move(self, position):
        resp = ''
        ct = 0
        while resp != ':A\n\r':
            self.execute_command('MZ{0}'.format(int(int(position)/self.scale)))
            resp = self.serial_port.read(30)
            ct += 1
            if ct>10:
                break
        
        
    def close(self):
        try:
            self.serial_port.close()
        except AttributeError:
            pass
            
class SutterStage(serial.Serial):
    """
    Commands are based on http://neurophysics.ucsd.edu/Manuals/Sutter%20Instruments/MP-285%20Reference%20Manual.pdf
    #Set speed  self.write(b'V'+struct.pack('<H', 1)+b'\r');self.read(100)
    """
    def __init__(self, port, baudrate):
        #TODO: set speed at init
        serial.Serial.__init__(self,  port, baudrate=9600, timeout=1)
        time.sleep(2)
        try:
            self.reset_controller()
            time.sleep(100e-3)
            #self.write(b'b\r')#Set to relative mode
            self.write(b'\x03')#Abort any motion
            self.write(b'a\r')#Set to absolue mode
            print(self.read(100))
            self.high_speed=not True
            self.set_speed(high= not True)
            self.setnowait=False
            initial=self.z
        except:
            import pdb, traceback
            print(traceback.format_exc())
            #pdb.set_trace()
        pass
        
    def set_speed(self, high=False):
        if not high:# and self.high_speed:
            #self.write('V\x01\x00\r'.encode())#Set speed to 250 ustep/second 22 s 500 ustep
            self.write('V\x02\x00\r'.encode())#Set speed to 500 ustep/second, 1 sec
            self.high_speed=False
            time.sleep(100e-3)
            self.check_response()
            print('Set low speed')
        elif high:# and not self.high_speed:
            self.write('V\x7f\x00\r'.encode())
            self.high_speed=True
            time.sleep(100e-3)
            self.check_response()
            print('Set high speed')
        
    def check_response(self):
        resp=self.read(10)
        if resp!=b'\r':
            print(f"Try to recover: {resp}")
            time.sleep(1)
            self.reset_controller()
            #raise IOError('No access to stage: {0}'.format(resp))
            
    def reset_controller(self):
        self.write(b'r\r')
        time.sleep(2)
        resp=self.read(10)
        if len(resp)==0:
            #import pdb;pdb.set_trace()
            raise IOError('No access to stage: {0}'.format(resp))
            
    def is_moving(self):
        try:
            pos=self.z
            return False
        except:
            return True
        
    @property
    def z(self):#self.write(b'c\r');resp=self.read(13);struct.unpack('<iii',resp[:-1])
        self.write(b'c\r')
        resp=self.read(13)
        if resp[-1]==255:
            print("Try to recover")
            self.reset_controller()
            self.write(b'c\r')
            resp=self.read(13)
        if len(resp)!=13 or resp[-1]!=13:
            print(self.read(1000))
            raise IOError("Invalid response: {0}, {1}".format(resp, len(resp)))
        self.xyz=struct.unpack('<iii',resp[:-1])
        return self.xyz[2]
        
    @z.setter
    def z(self, value):#self.write(b'm'+struct.pack('<iii', 0, 0, 0)+b'\r');self.read(1)
        cmd=struct.pack('<iii', 0, 0, int(value))
        deltaz=abs(value-self.xyz[2])
        #print(deltaz)
        if deltaz>30000:
            raise ValueError(f'too big movement: {deltaz}')
#        elif deltaz>1000:
#            self.set_speed(high=True)
#        elif deltaz<1000:
#            self.set_speed(high=False)
        self.write(b'm'+cmd+b'\r')
        self.xyz=(self.xyz[0], self.xyz[1], value)
        if not self.setnowait:
            self.check_response()
        else:
            if self.in_waiting>0:
                self.read(self.in_waiting)
                
    def setz(self, value, timeout=5):
        cmd=struct.pack('<iii', 0, 0, int(value))
        self.write(b'm'+cmd+b'\r')
        self.wait(timeout)
        
    def wait(self, timeout):
        t0=time.time()
        while True:
            time.sleep(0.5)
            if self.in_waiting>0:
                print(self.read(self.in_waiting))
                break
            if time.time()-t0>timeout*60:
                if not self.is_moving():
                    print('Timeout')
                    break
        
        print(time.time()-t0)
        
    def setz2(self, value):
        if self.in_waiting>0:
            print(self.read(self.in_waiting))
        cmd=struct.pack('<iii', 0, 0, int(value))
        self.write(b'm'+cmd+b'\r')
        
class EncoderReader(object):
    def __init__(self, devref):
        self.ctr=PyDAQmx.Task()
        self.ctr.CreateCIAngEncoderChan(devref,"enc",DAQmxConstants.DAQmx_Val_X4, 0, 0.0, DAQmxConstants.DAQmx_Val_AHighBHigh, DAQmxConstants.DAQmx_Val_Degrees, 8192, 0.0,"")
        self.ctr.StartTask()
        self.readbuf = DAQmxTypes.ctypes.c_long()
        self.data = numpy.zeros((1,), dtype=numpy.float64)
        
    def read(self, timeout=-1):
        self.ctr.ReadCounterF64(DAQmxConstants.DAQmx_Val_Auto, timeout, self.data, 1000, DAQmxTypes.byref(self.readbuf), None)
        print('encoder reader', self.data)
        return self.data[0]

    def close(self):
        self.ctr.ClearTask()

class MotorTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        unittest_aggregator.TEST_stage_com_port = 'COM1'
        stage_serial_port = {
                                    'port' :  unittest_aggregator.TEST_stage_com_port,
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        goniometer_serial_port = {
                                    'port' :  unittest_aggregator.TEST_goniometer_com_port,
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }
        remote_focus_serial_port = {
                                    'port' :  unittest_aggregator.TEST_remote_focus_com_port,
                                    'baudrate' : 1200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }
        #One step is 0.9 degree, 8 microsteps make one step and the transmission ratio is 1:252: 
        degree_factor = 0.9/(8*252)
        degree_factor = 0.00045*4 #According to manufacturer
        #xmin = 20.2644, ymin =  171.3096
        #xmax = 63.0108, ymax= 212.9562
        #Counter ranges x axis: 11266-35005, y axis: 95179 - 118301
        STAGE = [{'SERIAL_PORT' : stage_serial_port,
                 'ENABLE':True,
                 'SPEED': 1000000,
                 'ACCELERATION' : 1000000,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : numpy.ones(3, dtype = numpy.float)
                 },
                 {'SERIAL_PORT' : goniometer_serial_port,
                 'ENABLE':True,
                 'SPEED': 1000000,
                 'ACCELERATION' : 1000000,
                 'MOVE_TIMEOUT' : 15.0,
                 'DEGREE_PER_USTEP' : degree_factor * numpy.ones(2, dtype = numpy.float)
                 },
                 {'SERIAL_PORT' : remote_focus_serial_port,
                 'ENABLE':True,
                 }]
        
        self._create_parameters_from_locals(locals())
        
        #Test with different positions, speeds and accelerations, log, disabled
if test_mode:
    class TestAllegraStage(unittest.TestCase):
        def setUp(self):
            self.config = MotorTestConfig()
            self.stage = AllegraStage(self.config, None)
    
        def tearDown(self):
            self.stage.release_instrument()
            
        @unittest.skipIf(not unittest_aggregator.TEST_stage,  'Stage tests disabled')
        def test_01_initialize_stage(self):
            self.assertEqual((hasattr(self.stage, 'SPEED'), hasattr(self.stage, 'ACCELERATION'), 
                            hasattr(self.stage, 'position'), hasattr(self.stage, 'position_ustep')),
                            (True, True, True, True))
    
        #For some reason the absolute movement does not work reliably
    #     def test_02_absolute_movement(self):
    #         initial_position = self.motor.position
    #         target_position = initial_position + numpy.array([100.0,0.0,0.0])
    #         result1 = self.motor.move(target_position, relative = False)
    #         result2 = self.motor.move(initial_position, relative = False)
    #         self.assertEqual((result1, result2, (abs(self.motor.position - initial_position)).sum()), (True, True, 0.0))
    
        @unittest.skipIf(not unittest_aggregator.TEST_stage,  'Stage tests disabled')
        def test_03_relative_movement(self):
            initial_position = self.stage.position
            movement_vector = numpy.array([10000.0,1000.0,10.0])
            result1 = self.stage.move(movement_vector)
            result2 = self.stage.move(-movement_vector)
            self.assertEqual((result1, result2, (abs(self.stage.position - initial_position)).sum()), (True, True, 0.0))
            
        @unittest.skipIf(not unittest_aggregator.TEST_stage,  'Stage tests disabled')
        def test_04_movements_stage_disabled(self):
            self.config.STAGE[0]['ENABLE'] = False
            self.stage.release_instrument()
            self.stage = AllegraStage(self.config, None)
            initial_position = self.stage.position
            movement_vector = numpy.array([10000.0,1000.0,10.0])
            result1 = self.stage.move(movement_vector)        
            self.assertEqual((result1, (abs(self.stage.position - initial_position)).sum()), (False, 0.0))
            
        @unittest.skipIf(not unittest_aggregator.TEST_stage,  'Stage tests disabled')
        def test_05_big_movement_at_different_speeds(self):
            initial_position = self.stage.position
            movement_vector = numpy.array([300000.0,-50000.0,100.0])
            result = True
            spd = [10000000, 1000000, 100000]
            accel = [1000000, 100000]
            
            for i in range(len(spd)):
                for j in range(len(accel)):
                    if not self.stage.move(movement_vector, speed = spd[i], acceleration = accel[j]):
                        result = False
                    movement_vector = - movement_vector
    #                 print '{0}\t{1}\t{2}\t{3}\t{4}' .format(spd[i], accel[j], self.motor.movement, self.motor.movement_time, self.motor.expected_move_time)
            
            self.assertEqual((result, (abs(self.stage.position - initial_position)).sum()), (True, 0.0))
            
        def test_06_debug_stage(self):
            pass
    
    class TestMotorizedGoniometer(unittest.TestCase):
        def setUp(self):
            self.config = MotorTestConfig()
            self.mg = MotorizedGoniometer(self.config, id = 1)
    
        def tearDown(self):
            self.mg.release_instrument()
    
        @unittest.skipIf(not unittest_aggregator.TEST_goniometer,  'Stage tests disabled')
        def test_01_goniometer_small_movement(self):
            angle_factor = -16.0
            movements = [angle_factor * numpy.array([1.0, 1.0])]#, -angle_factor * numpy.array([1.0, 2.0])]
            results = []
            if self.mg.set_speed(300):
                for m in movements:
                    results.append(self.mg.move(m))
                    time.sleep(0.0)
            self.assertEqual(False in results,  False)
            
    class TestRemoteFocus(unittest.TestCase):
        def setUp(self):
            self.rf = RemoteFocus('COM3')
    
        def tearDown(self):
            self.rf.close()
    
        @unittest.skipIf(not unittest_aggregator.TEST_remote_focus,  'Stage tests disabled')
        def test_01(self):
            pos = [10.0,100.,-201.,0., -15]
            for p in pos:
                self.rf.move(p)
                print(p,self.rf.read_position())
                self.assertEqual(self.rf.read_position(),p)
                
class TestSutter(unittest.TestCase):
    def test(self):
        stage = SutterStage("COM7", 9600)
        time.sleep(2)
        stage.write('V\x7f\x00\r'.encode())
        print(stage.read(13))
        stage.setz(100)
        stage.setz(0)
        print(stage.z)
        stage.z=3000
        self.assertEqual(stage.z, 3000)
        self.assertEqual(stage.z, 3000)
        print(stage.z)
        stage.z=-1000
        self.assertEqual(stage.z, -1000)
        print(stage.z)
        stage.z=123456789
        self.assertEqual(stage.z, 123456789)
        print(stage.z)
        print(stage.z)
        stage.z=-98765432
        print(stage.z)
        self.assertEqual(stage.z, -98765432)
        
    def test_sutter_restart(self):
        stage = SutterStage("COM7", 9600)
        time.sleep(3)
        stage.z=10000
        time.sleep(5)
        stage.close()
        print('Restart stage, terminate ongoing motion')
        stage = SutterStage("COM7", 9600)
        time.sleep(3)
        print(stage.z, '?')
        stage.setz(0)
        print(stage.z, 0)
        stage.setz(250)
        print(stage.z, 250)
        stage.setz(0)
        print(stage.z, 0)
        stage.close()
        print('Test jump back to initial position')
        stage = SutterStage("COM7", 9600)
        time.sleep(3)
        print(stage.z)
        stage.set_speed(high=True)
        stage.setz(20000)
        print(stage.z, 20000)
        stage.set_speed(high=False)
        stage.setz(19900)
        stage.set_speed(high=True)
        stage.setz(0)
        print(stage.z, 0)
        stage.close()
        
    def test_setz_nowait(self):
        stage = SutterStage("COM7", 9600)
        time.sleep(3)
        print(stage.z, 0)
        stage.setz2(100)
        stage.wait(5)
        stage.setz2(5000)
        stage.wait(5)
        print(stage.z, 5000)
        stage.setz(0)
        stage.close()
        
if __name__ == "__main__":
    mytest = unittest.TestSuite()
    mytest.addTest(TestSutter('test_setz_nowait'))
    unittest.TextTestRunner(verbosity=2).run(mytest)

