#TODO: rename to stage_control
import numpy
import instrument
import visexpman.engine.generic.configuration
import visexpman.engine.generic.utils as utils
import os
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

try:
    import serial
except:
    pass

import unittest
import time
import re
extract_goniometer_axis1 = re.compile('\rX(.+)\n')
extract_goniometer_axis2 = re.compile('\rY(.+)\n')

class StageControl(instrument.Instrument):
    '''
    (States: init, ready, moving, error)
    '''
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
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.command_counter = 0
                self.acceleration = self.config.STAGE[self.id]['ACCELERATION']
                self.speed = self.config.STAGE[self.id]['SPEED']
                self.reset_controller()
        self.read_position()

    def move(self, new_position, relative = True, speed = None, acceleration = None):
        '''
        new_position: x, y, z, in um
        '''
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
                            print response
                            raise RuntimeError('No valid response from motion controller ' + line)
                            
                self.position_ustep = numpy.array(position)
                try:
                    self.position = self.position_ustep * self.config.STAGE[self.id]['UM_PER_USTEP']
                except ValueError:
                    self.position = numpy.zeros(3, dtype = float)
                    print 'position in ustep: {0}' .format(self.position_ustep)
                    
            else:
                self.position = numpy.zeros(3, dtype = float)
            return self.position #in um
        
                                         
    def reset_controller(self):
        self.serial_port.setRTS(True)
        time.sleep(20e-3) #Min 20 ms
        self.serial_port.setRTS(False)
        time.sleep(0.5) #used to be 0.5 s
        
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
    import Image
    import visexpA.engine.dataprocessors.signal as signal
    frames = utils.listdir_fullpath(folder)
    frames.sort()
    print frames
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
                if 'OK' not in self.serial_port.read(100):
                    raise RuntimeError('Goniometer does not respond')

        self.read_position()
        self.execute_command(['V50'])
        print self.serial_port.read(100)
        current_pos = self.position
        self.move(-numpy.array([1, 1]))
        time.sleep(1.0)
        self.read_position()
        print self.position-current_pos,  self.position
        
        
    def execute_command(self, commands, wait_after_command = True):
        if not isinstance(commands,  list):
            commands = [commands]
        for command in commands:
            self.serial_port.write(command + '\r')
            if wait_after_command:
                time.sleep(10e-3)
                
    def read_position(self,  print_position = False):
        self.execute_command(['?X', '?Y'])
        response = self.serial_port.read(100)
        try:
            self.position_ustep = numpy.array(map(int,  [extract_goniometer_axis1.findall(response)[0],  extract_goniometer_axis2.findall(response)[0]]))
            self.position = self.position_ustep * self.config.STAGE[self.id]['DEGREE_PER_USTEP']
        except:
            self.position = None
        if print_position:
            print self.position
        return self.position
        
    def move(self, angle):
        '''
        Move 2 axis goniometer relative to current position
        '''
        angle_in_ustep =  angle / self.config.STAGE[self.id]['DEGREE_PER_USTEP']
        axis = ['X', 'Y']
        for i in range(1):
            if angle_in_ustep[i] < 0:
                sign = '-'
            else:
                sign = '+'
            self.execute_command('{2}{0}{1}'.format(sign,  abs(angle_in_ustep[i]),  axis[i]))
            time.sleep(100e-3)
            response = self.serial_port.read(100)
            print response
            time.sleep(1.0)

class MotorTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        
        motor_serial_port = {
                                    'port' :  unit_test_runner.TEST_stage_com_port,
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        goniometer_serial_port = {
                                    'port' :  unit_test_runner.TEST_goniometer_com_port,
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }
                                    
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
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
                 'MOVE_TIMEOUT' : 45.0,
                 'DEGREE_PER_USTEP' : numpy.ones(2, dtype = numpy.float)
                 }]
        
        self._create_parameters_from_locals(locals())
        
        #Test with different positions, speeds and accelerations, log, disabled
#class TestAllegraStage(unittest.TestCase):
class TestAllegraStage():
    def setUp(self):
        self.config = MotorTestConfig()
        self.stage = AllegraStage(self.config, None)

    def tearDown(self):
        self.stage.release_instrument()
        
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

    def test_03_relative_movement(self):
        initial_position = self.stage.position
        movement_vector = numpy.array([10000.0,1000.0,10.0])
        result1 = self.stage.move(movement_vector)
        result2 = self.stage.move(-movement_vector)
        self.assertEqual((result1, result2, (abs(self.stage.position - initial_position)).sum()), (True, True, 0.0))
        
    def test_04_movements_stage_disabled(self):
        self.config.STAGE[0]['ENABLE'] = False
        self.stage.release_instrument()
        self.stage = AllegraStage(self.config, None)
        initial_position = self.stage.position
        movement_vector = numpy.array([10000.0,1000.0,10.0])
        result1 = self.stage.move(movement_vector)        
        self.assertEqual((result1, (abs(self.stage.position - initial_position)).sum()), (False, 0.0))
        
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

class TestMotorizedGoniometer(unittest.TestCase):
    def setUp(self):
        self.config = MotorTestConfig()
        self.mg = MotorizedGoniometer(self.config, id = 1)

    def tearDown(self):
        self.mg.release_instrument()
        
    def test_01_goniometer_init(self):
        pass
        
if __name__ == "__main__":
    unittest.main()
#    stage_calibration(1, '/home/zoltan/visexp/debug/stage/cut/0')
