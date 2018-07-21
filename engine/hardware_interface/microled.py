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
            self._frame_timing_pulse()
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
        self.sent_packets = []
        
    def send_command(self, command, trigger=None, pixels= None):
        '''
        trigger:list of channels need to be turned on
        '''
        if command not in self.command_list:
            raise RuntimeError('{0} is not a supported command'.format(command))
        if trigger == 'all':
            trigger_value = 0xffff
        elif trigger is not None:
            trigger_value = 0
            for t in trigger:
                if t >= 16:
                    raise RuntimeError('Invalid trigger channel: {0}. 0-15 is tha valid range'.format(t))
                trigger_value += 1<<t
        else:
            trigger_value = 0
        if command =='0':
            self.sent_packets.append('{0}{1:0=4x}{2}\n'.format(command, trigger_value, pixels))
        elif command == '9':
            self.sent_packets.append('{0}\n'.format(command))
        self.s.write(self.sent_packets[-1])
            
    def display_pixels(self, pixels, duration, trigger =None, clear=True):
        if not isinstance(pixels, str):
            pixels_ = self._to_pixel_string(pixels)
        else:
            pixels_ = pixels_
        self.send_command('0', trigger, pixels_)
        time.sleep(duration)
        if clear:
            self.reset()
        
    def reset(self):
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
        self.reset()
        self.s.close()

class TestConfig(object):
    def __init__(self):
        self.ULED_SERIAL_PORT = 'COM4'
        self.LIGHT_METER = {'AVERAGING':1, 'TIMEOUT':100e-3}
        
class Testuled(unittest.TestCase):
    def setUp(self):
        self.timing = [2e-3, 10e-3, 20e-3, 50e-3, 100e-3]
        self.timing = [30e-3]
        self.repeats = 3
        self.pause = 1.0
#        self.timing=[10e-3]
        
#    @unittest.skip('')
    def test_01_uled(self):
        config = TestConfig()
        from matplotlib.pyplot import plot, show,figure,legend, xlabel,title,savefig, clf, subplot, ylabel
        import lightmeter
        from multiprocessing import Queue, Process
        from threading import Thread
        from visexpman.engine.generic.introspect import Timer
        enable_measurement=not False
        self.queues = {'command':Queue(), 'data': Queue(), }
        self.process = Thread(target=lightmeter.lightmeter_acquisition_process,  args = (config, self.queues))
        if enable_measurement:
            self.process.start()
        s = MicroLEDArray(config)
        self.blocktimes = []
        time.sleep(1.0)
        for t in self.timing:
            for r in range(self.repeats):
                t0=time.time()
                for i in range(16):
                    pixels = numpy.zeros((16, 16), dtype=numpy.bool)
                    pixels[i, :]=True
                    s.display_pixels(pixels, t, clear= True)
                self.blocktimes.append(time.time()-t0)
                time.sleep(self.pause)
        s.release_instrument()
        time.sleep(1.0)
        if enable_measurement:
            self.queues['command'].put('terminate')            
            self.process.join()
            self.data = []
            while not self.queues['data'].empty():
                self.data.append(self.queues['data'].get())
            self.data=numpy.array(self.data)
            import hdf5io
            from visexpman.engine.generic import fileop
            from visexpman.engine.generic import utils
            h=hdf5io.Hdf5io(fileop.generate_filename('v:\\debug\\uled\\timing.hdf5'), filelocking=False)
            self.sent_packets = utils.object2array(s.sent_packets)
            vns=['pause', 'timing', 'repeats', 'blocktimes', 'data', 'sent_packets']
            for vn in vns:
                setattr(h, vn, getattr(self, vn))
#            import pdb
#            pdb.set_trace()
            h.save(vns)
            h.close()
            plot(self.data[:, 0], self.data[:, 1])
            show()
            
    @unittest.skip('')
    def test_02_eval_timing(self):
        import hdf5io
        p='/mnt/datafast/debug/uled/timing_00001.hdf5'
        p='v:\\debug\\uled\\timing_00001.hdf5'
        h=hdf5io.Hdf5io(p, filelocking=False)
        reps = h.findvar('repeats')
        print h.findvar('timing')
        bt=h.findvar('blocktimes')
        print numpy.array(bt[::reps])/16*1000
        data = h.findvar('data')
        h.close()
        from matplotlib.pyplot import plot, show,figure,legend, xlabel,title,savefig, clf, subplot, ylabel
        t=data[:, 0]
        intensities=data[:, 1]
        edges=t[numpy.nonzero(numpy.diff(numpy.where(intensities>5e-6, 1, 0)))[0]]
        print numpy.diff(edges)[::2][::reps]/16*1000
        plot(data[:, 0], data[:, 1])
        show()

        
if __name__ == '__main__':
    unittest.main()
