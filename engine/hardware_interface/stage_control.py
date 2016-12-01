import numpy
import re
import time
import os
try:
    import serial
except:
    print 'pyserial not installed'

import unittest

import instrument
import visexpman.engine.generic.configuration
from visexpman.engine.generic import utils
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

extract_goniometer_axis1 = re.compile('\rX(.+)\n')
extract_goniometer_axis2 = re.compile('\rY(.+)\n')
parameter_extract = re.compile('EOC(.+)EOP')

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
                    
class AllegraStage(serial.Serial):
    def __init__(self,port, timeout=1,um_per_step=0.75/51.0):
        serial.Serial.__init__(self,port, 19200, timeout=timeout)
        self.um_per_step=um_per_step
        time.sleep(0.1)
        self.read(100)
        
    def reset(self):
        self.setRTS(1)
        time.sleep(20e-3)
        self.setRTS(0)
        time.sleep(0.5)
        self.read(100)
        
    def joystick_on(self):
        self.write('jon\n')
        time.sleep(0.3)
        response=self.read(100)
        if 'Joystick is on\r\n' not in response:
            raise RuntimeError('Joystick cannot be enabled: "{0}"'.format(response))
        
    def joystick_off(self):
        self.write('joff\n')
        time.sleep(0.3)
        response=self.read(100)
        if response!='Joystick is off\r\n':
            raise RuntimeError('Joystick cannot be disabled: "{0}"'.format(response))
        
    def read_position(self):
        ntrials=5
        for trial in range(ntrials):
            self.write('rx\nry\n')
            time.sleep(0.5)
            response=self.read(100)
            try:
                self.position = self.parse_position(response)
                break
            except:
                if trial==ntrials-1:
                    print('Stage position read fail.')
                    return numpy.zeros((2,))
                    raise RuntimeError('Stage position cannot be read: "{0}"'.format(response))
                else:
                    time.sleep(0.5)
        return self.position
        
    def parse_position(self, response):
        values=[int(l[1:]) for l in response.split('\r\n')[:-1] if (l[0]=='X' or l[0]=='Y') and not ' ' in l]
        if len(values)!=2:
            raise RuntimeError('Stage position cannot be read: "{0}"'.format(response))
        return numpy.array(values)*self.um_per_step
        
    def setparams(self, speed=5000,acceleration=2000):
        self.speed=speed
        self.acceleration=acceleration
        self.write('velx {0}\naccx {1}\nvely {0}\naccy {1}\n'.format(int(speed), int(acceleration)))
        self.read(100)#Flush
        
    def move(self,x,y):
        if abs(x)>2000 or abs(y)>2000:
            raise RuntimeError('Big movements are not supported')
        self.joystick_off()
        #self.read(100)#Flush
        stepsx=int(x/self.um_per_step)
        stepsy=int(y/self.um_per_step)
        self.write('rx\n')
        self.write('ry\n')
        time.sleep(0.3)
        self.write('posx {0}\n'.format(stepsx))
        time.sleep(0.3)
        self.write('posy {0}\n'.format(stepsy))
        time.sleep(0.3)
        self.write('movrx\n')
        time.sleep(0.3)
        self.write('movry\n')
        time.sleep(0.3)
        movement_time=1.5*float(max(abs(stepsx), abs(stepsy)))/self.speed
        time.sleep(movement_time)
        response=self.read(100)
        lines=response.split('\r\n')
        try:
            initial_position = self.parse_position(response)
        except:
            self.joystick_on()
            raise RuntimeError('Initial position unknown: {0}'.format('\r\n'.join(lines)))
        if 'Done Y' not in lines or 'X Stopping' not in lines or 'X Rel. move' not in lines or 'Y Rel. move' not in lines:
            self.joystick_on()
            raise RuntimeError('Stage was not moved: "{0}"'.format('\r\n'.join(lines)))
        self.joystick_on()
        final_position=self.read_position()
        movement=final_position-initial_position
        error=numpy.array([x,y])-movement
        if (abs(error)).sum()>1:
            raise RuntimeError('Stage was not moved to desired position. Inital: {0}, final: {1}, movement: {2}, {3}'
                .format(initial_position,final_position,x,y))
        return final_position
                
    def stop(self):
        self.write('STOPALL\n')
        return self.read(100)
                
class AllegraStageOld(StageControl):
    
    def init_instrument(self):
        if hasattr(self.config, 'STAGE'):
            if self.config.STAGE[self.id]['ENABLE']:
                self.command_counter = 0
                self.acceleration = self.config.STAGE[self.id]['ACCELERATION']
                self.speed = self.config.STAGE[self.id]['SPEED']
                #self.reset_controller()
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
                    if hasattr(self.queue,  'empty'):
                        if not self.queue.empty():
                            if 'stop' in parameter_extract.findall(self.queue.get())[0]:
                                print 'stop stage'
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
                print 'r',response
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
        response = self.serial_port.read(100)
        time.sleep(1)
        response = self.serial_port.read(100)
        print 'after reset', response
        
    def stop(self):
        self.execute_command('STOPALL')
        return self.serial_port.read(100)
        
    def execute_command(self, command, print_response = False, wait_after_command = True):
        commands = command.split('\n')
        response = ''
        for cmd in commands:
            if len(cmd) > 0:
                self.serial_port.write(cmd + '\n')
                print 'c',cmd + '\n'
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
    from PIL import Image
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

    def read_position(self,  print_position = False):
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
                    print traceback.format_exc()
                    print response
        if not hasattr(self, 'position'):
            self.position = numpy.zeros(2)
        if print_position:
            print self.position
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

class MotorTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        
        stage_serial_port = {
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
                 }]
        
        self._create_parameters_from_locals(locals())
        
        #Test with different positions, speeds and accelerations, log, disabled
class TestAllegraStage(unittest.TestCase):
    def test_01(self):
        a=AllegraStage('COM7',timeout=0.8)
        a.reset()
        a.setparams()
        a.move(1,-200)
        for i in range(3):
            print a.read_position()
        for j in range(3):
            try:
                a.move(10,20)
                print '+',  j,   a.position
            except:
                print '+',  j,  'error',  a.position
            try:
                a.move(-10,-20)
                print '-',  j,   a.position
            except:
                print '-',  j,  'error',  a.position
        print a.position
        a.close()
#        a=AllegraStage('COM7',timeout=0.8)
#        print a.read_position()
#        a.close()

        
        

class TestAllegraStageOld():
    def setUp(self):
        self.config = MotorTestConfig()
        self.stage = AllegraStage(self.config, None)

    def tearDown(self):
        self.stage.release_instrument()
    
    @unittest.skip('')       
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

    @unittest.skip('')   
    def test_03_relative_movement(self):
        initial_position = self.stage.position
        movement_vector = numpy.array([10000.0,1000.0,10.0])
        result1 = self.stage.move(movement_vector)
        result2 = self.stage.move(-movement_vector)
        self.assertEqual((result1, result2, (abs(self.stage.position - initial_position)).sum()), (True, True, 0.0))
    
    @unittest.skip('')   
    def test_04_movements_stage_disabled(self):
        self.config.STAGE[0]['ENABLE'] = False
        self.stage.release_instrument()
        self.stage = AllegraStage(self.config, None)
        initial_position = self.stage.position
        movement_vector = numpy.array([10000.0,1000.0,10.0])
        result1 = self.stage.move(movement_vector)        
        self.assertEqual((result1, (abs(self.stage.position - initial_position)).sum()), (False, 0.0))
        
    @unittest.skip('')       
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

    @unittest.skip('')   
    def test_01_goniometer_small_movement(self):
        angle_factor = -16.0
        movements = [angle_factor * numpy.array([1.0, 1.0])]#, -angle_factor * numpy.array([1.0, 2.0])]
        results = []
        if self.mg.set_speed(300):
            for m in movements:
                results.append(self.mg.move(m))
                time.sleep(0.0)
        self.assertEqual(False in results,  False)
        
if __name__ == "__main__":
    unittest.main()
#    stage_calibration(1, '/home/zoltan/visexp/debug/stage/cut/0')
