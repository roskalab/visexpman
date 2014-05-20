import serial
import os
import time

class SerialPulse(object):
    def __init__(self, port):
        self.s = serial.Serial(port)
        if os.name != 'nt':
            self.s.open()

    def close(self):
        self.s.close()

    def pulse(self, width):
        self.s.setRTS(False)
        self.s.setRTS(True)
        time.sleep(width)
        self.s.setRTS(False)
    

if __name__ == '__main__':
    s = SerialPulse('/dev/ttyS0')
    for i in range(2000):
        s.pulse(10e-3)
        time.sleep(0.05)
#    s.s.setRTS(True)#pulse_with_power_supply(1e-3)
#    time.sleep(200.0)
    s.close()
