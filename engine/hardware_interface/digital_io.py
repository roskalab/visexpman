import serial
import os
import time

class SerialPulse(object):
    def __init__(self, port):
        self.s = serial.Serial(port)
        if os.name != 'nt':
            self.s.open()
        self.s.setRTS(False)#Activates power supply


    def close(self):
        self.s.close()

    def pulse(self, width):
        self.s.setRTS(False)
        self.s.setRTS(True)
        time.sleep(width)
        self.s.setRTS(False)
        
    def pulse_with_power_supply(self, width):
        time.sleep(20e-3)
        self.pulse(width)
        time.sleep(20e-3)

if __name__ == '__main__':
    s = SerialPulse('/dev/ttyS0')
    s.pulse_with_power_supply(1e-3)
    s.close()
