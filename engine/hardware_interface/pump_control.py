import serial

class HarvardPeristalticPump(serial.Serial):
    def __init__(self,port):
        serial.Serial.__init__(self, port,115200, timeout=1)
        
    def command(self,cmd):
        self.write(cmd+'\r')
        return self.read(300)
        
    def run(self, rate):
        '''
        rate is expected in ul/minute unit
        '''
        print self.command('rate {0} ul/m'.format(rate))
        print self.command('run')
        
    def is_running(self):
        '''
        If not running user shall press green Run button (bottom right side) to enable run/command mode
        '''
        return self.command('fvolume')!=0
        
    def stop(self):
        self.command('stop')
        
def set_ismatec_ecoline_pump(channel, speed):
    '''
    Direction button shall be set to neutral position.
    Pin5: shall be connected to AO0, 0-5V range-> 3.5-350 rpm
    '''
    from visexpman.engine.hardware_interface import daq_instrument
    daq_instrument.set_voltage(channel,speed*5.0/350)
