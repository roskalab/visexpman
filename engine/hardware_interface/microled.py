import numpy
import serial
import os
import time
import unittest
import instrument

class MicroLEDArray(instrument.Instrument):
    '''
    Usage:
        self.machine_config.STIMULUS2MEMORY = True
        <<stimulus code comes here>>
        self.machine_config.STIMULUS2MEMORY = False
        s = MicroLEDArray(config)
        s.prepare_stimulus(numpy.array(self.stimulus_bitmaps))
        while True:
            islast = s.update_uled(1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            self._frame_trigger_pulse()
            if islast:
                break
        s.release_instrument()
        
    '''
    def init_instrument(self):
        self.command_list = ['0', '9']
        if not hasattr(self.config,  'ULED_SERIAL_PORT'):
            raise RuntimeError('ULED_SERIAL_PORT must be defined in machine config')
        self.s = serial.Serial(port =self.config.ULED_SERIAL_PORT,
                                                    baudrate =921600,
                                                    timeout = 0.1)
        if os.name != 'nt':
            self.s.open()
        
    def send_command(self, command, trigger, pixels):
        '''
        trigger:list of channels need to be turned on
        '''
        if command not in self.command_list:
            raise RuntimeError('{0} is not a supported command'.format(command))
        if trigger == 'all':
            trigger_value = 0xffff
        else:
            trigger_value = 0
            for t in trigger:
                if t >= 16:
                    raise RuntimeError('Invalid trigger channel: {0}. 0-15 is tha valid range'.format(t))
                trigger_value += 1<<t
        if command =='0':
            self.write('{0}{1:x}{2}\n'.format(command, trigger_value, pixels))
        elif command == '9':
            self.write('{0}\n'.format(command))
            
    def display_pixels(self, trigger, pixels, duration):
        if not isinstance(pixels, str):
            pixels_ = self._to_pixel_string(pixels)
        else:
            pixels_ = pixels_
        self.send_command('0', trigger, pixels_)
        time.sleep(duration)
        self.send_command('9')
        
        
    def _to_pixel_string(self, pixels):
        '''
        pixels: 16x16 boolean array
        '''
        if pixels.shape[0] != 16 or pixels.shape[1] != 16 or pixels.dtype != numpy.bool:
            raise RuntimeError('pixels must be provided in a 16x16 boolean array')
        #Swapping first and second line is necessary due to led configuration
        pixels_string = 64*['0']
        #Row order: 2,1,4,3,6,5...
        indexes = numpy.reshape(numpy.arange(64), (8,8))
        indexes_swapped_rows = numpy.zeros_like(indexes)
        indexes_swapped_rows[:,:4]=indexes[:,4:]
        indexes_swapped_rows[:,4:]=indexes[:,:4]
        indexes = indexes_swapped_rows.reshape(16,4)
        for row in range(pixels.shape[0]):
            line = pixels[row]
            for byte_index in range(indexes[row].shape[0]):
                #Taking 4 bits from pixels and converting to hexadecimal digit
                nibble_value = pixels[row][byte_index*4:(byte_index+1)*4]
                nibble_string = '{0:x}'.format(numpy.array([1<<bit_position for bit_position in numpy.nonzero(nibble_value[::-1])[0]],  dtype=numpy.int).sum())
                pixels_string[indexes[row, byte_index]] = nibble_string
        return ''.join(pixels_string)
        
    def prepare_stimulus(self, pixels):
        '''
        3d pixel array is expected
        '''
        self.pixel_bytes = [self._to_pixel_string(frame) for frame in numpy.cast['bool'](pixels)]
        self.frame_counter = 0

    def update_uled(self, duration, trigger = []):
        '''
        Displays next frame on microled array. Assumes that prepare_stimulus has already been called
        '''
        self.display_pixels(self, trigger, self.pixel_bytes[self.frame_counter], duration)
        self.frame_counter += 1
        if self.frame_counter == len(self.pixel_bytes):
            islast = True
        else:
            islast = False
        
    def release_instrument(self):
        self.s.close()

class TestConfig(object):
    def __init__(self):
        self.ULED_SERIAL_PORT = 'COM5'
        
class TestDigitalIO(unittest.TestCase):
#    @unittest.skip('')
    def test_01_uled(self):
        config = TestConfig()
        s = MicroLEDArray(config)
        pixels = numpy.zeros((16, 16), dtype=numpy.bool)
        pixels[0, 0]=True
        pixels[0, 2]=True
        s.display_pixels([1], pixels, 1.0)
        s.release_instrument()
        
if __name__ == '__main__':
    unittest.main()
