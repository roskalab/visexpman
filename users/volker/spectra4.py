import serial,time


class Spectra4Controller(object):
    '''
    
    '''
    SPECTRA4_SERIAL_PORT='COMX'
    DIGITAL_IO_PORT='COMX'

    def __init__(self, intensity_increment=1):
        self.intensity_increment=intensity_increment
        self.spectra4serial=serial.Serial(self.SPECTRA4_SERIAL_PORT,9600,timeout=1)
        self.digital_io=serial.Serial(self.DIGITAL_IO_PORT)
        self.channels=['Red','Green','Cyan','UV','Blue','Teal']
        self.spectra4serial.write('\x57\x02\xFF\x50')#Init commands
        self.spectra4serial.write('\x57\x03\xFF\x50')#Init commands
        self.spectra4serial.write('\x4F\x7F\x50')#Disable all channels
        
    def enable_channel(self,channel):
        channel_index=self.channels.index(channel)+1
        self.spectra4serial.write('\x4F{0}\x50'.format(hex(255^(1<<channel_index))))
    
    def set_intensity(self, channel, intensity):
        iic_address= '\x1a' if channel in ['Blue','Teal'] else '\x18'
        channel_index=self.channels.index(channel)+1
        if channel in ['Blue','Teal']:
            channel_index-=2
        intensity_word=intensity*16+0xF000
        w1=(intensity_word&0xFF00)>>8
        w2=intensity_word&255
        self.spectra4serial.write('\x53{0}\x03{1}{2}{3}\x50'.format(iic_address, hex(channel_index),hex(w1),hex(w2)))
        
    def read_digital_in(self):
        return self.digital_io.getCTS()
        
    def experiment(self):
        self.channel='Blue'        
        self.intensity=1
        self.enable_channel(self.channel)
        while True:
            print 'wait for digital input'
            while self.read_digital_in():
                time.sleep(10e-3)
            print 'set intensity to {0}'.format(self.intensity)
            self.set_intensity(self.channel, self.intensity)
            self.intensity+=self.intensity_increment
            if self.intensity==256:
                self.intensity=0

        
        
        
        
        
        

if __name__ == "__main__":
    sc=Spectra4Controller()
    sc.enable_channel('Teal')
    sc.set_intensity('Teal',128)
    time.sleep(1)
    sc.set_intensity('Teal',0)
    
