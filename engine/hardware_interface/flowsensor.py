#-------------------------------------------------------------------------------
# Name:        example_2_single_measurement_SF04
# Purpose:     Example code (2) for the RS485 Sensor Cable with the SHDLC
#              Protocol
#
#              Switch on the heater of the sensor
#              Set the measurement resolution of the sensor to 16 bit
#              Start a single measurement
#              Get result of the single measurement
#              Switch off the heater of the sensor
#
# Author:      nsaratz
#
# Created:     04. 10. 2012
# Update:      13.12.2019
# Copyright:   (c) Sensirion AG 2019
# Licence:     All Rights Reserved
#-------------------------------------------------------------------------------
#!/usr/bin/env python


# Serial port package for Python
import serial
import serial.serialwin32 # for Windows
# import serial.serialposix # for Unix/Linux/MacOS


class Flowsensor:
    def __init__(self, COMport, explainmode=False):
        # enable/disable explain-mode (details of command generation printed to stdout)
        self.explainmode = explainmode

        self.ser = serial.Serial(
            port=COMport,  # COM port
            baudrate=115200,  # baudrate
            bytesize=serial.EIGHTBITS,  # number of databits
            parity=serial.PARITY_NONE,  # enable parity checking
            stopbits=serial.STOPBITS_ONE,  # number of stopbits
            timeout=1,  # set a timeout value (example only because reset
            # takes longer)
            xonxoff=0,  # disable software flow control
            rtscts=0,  # disable RTS/CTS flow control
        )

        # specify the address of the RS485 adapter cable
        self.ADDRESS = 0

        # Set the scale factor used to convert the sensor output to physical units. The
        # scale factor is indicated on the Flow Meter's datasheet. E.g. its value is
        # 13.0 for the SLQ-QT105 Flow Meter
        self.SCALEFACTOR = 13.0

        self.switch_heater(1)
        self.set_resolution()
        self.clear_buffer()
    
    
    def compute_SHDLC_checksum(self, listofbytes):
        """
        compute the SHDLC checksum of a list of bytes
        """
        # sum up all bytes
        tmpchecksum = sum(listofbytes)
    
        # take least significant byte
        tmpchecksum = tmpchecksum & 0xff
    
        # invert (bit-wise XOR with 0xff)
        tmpchecksum = 0xff ^ tmpchecksum
    
        return tmpchecksum

    def byte_stuff(self, listofbytes):
            """
            Perform byte stuffing on 'listofbytes',
            i.e. replace special characters as follows:
            0x7e --> 0x7d, 0x5e
            0x7d --> 0x7d, 0x5d
            0x11 --> 0x7d, 0x31
            0x13 --> 0x7d, 0x33
            """
            i=0
            while i<len(listofbytes):
                if listofbytes[i]==0x7e:
                    listofbytes[i]=0x7d
                    listofbytes.insert(i+1,0x5e)
                    i+=1
                elif listofbytes[i]==0x7d:
                    listofbytes[i]=0x7d
                    listofbytes.insert(i+1,0x5d)
                    i+=1
                elif listofbytes[i]==0x11:
                    listofbytes[i]=0x7d
                    listofbytes.insert(i+1,0x31)
                    i+=1
                elif listofbytes[i]==0x13:
                    listofbytes[i]=0x7d
                    listofbytes.insert(i+1,0x33)
                    i+=1
                i+=1
            return listofbytes


    def make_and_send_SHDLC_command(self, commandID, data):
        """
        sends command 'commandID' with data 'data' to device on address 'address'.
        address: number between 0 and 254 (address 255 is reserved for broad-cast)
        commandID: byte
        data: list of bytes
        """
        datalength = len(data)
        # compose command
        command = [self.ADDRESS, commandID, datalength] + data
        if self.explainmode: print('command before checksum:',command)
    
        # compute checksum
        command.append(self.compute_SHDLC_checksum(command))
        if self.explainmode: print('command with checksum:',command)
    
        # do byte stuffing
        command = self.byte_stuff(command)
    
        if self.explainmode: print('command with byte stuffing:', command)
        # add start byte and stop byte
    
        command = [0x7e] + command + [0x7e]
        if self.explainmode: print('command with start stop byte:',command)
    
        # convert list of numbers to bytearray
        command = bytearray(command)
    
        # send command to the device
        self.ser.write(command)

    def read_SHDLC_response(self):
        """
        reads the response from the SHDLC device and
        returns the data as list of bytes
        """
        response = []
        res = ''
    
        # Iterate read until res is empty or stop byte received
        firstbyte=True
        while True:
            res = self.ser.read(1)
            if not res:
                break
            elif firstbyte or (ord(res) != 0x7e):
                firstbyte = False
                response.append(ord(res))
            else:
                response.append(ord(res))
                break
    
        # print response as it comes from the device
        if self.explainmode: print('response from sensor:',response)
    
        # remove first element (the start byte) from the response
        response.pop(0)
        # remove the last element (the stop byte) form the response
        response.pop(-1)
    
        # print response without start- and stop-bytes
        if self.explainmode: print('response w/o start/stop:',response)
    
    
        # Check for bytes that are stuffed
        i=0
        #loop through response list
        while i<len(response):
            if response[i] == 0x7D:
                # 0x7d marks stuffed bytes. see SHDLC documentation
                if response[i+1] == 0x5E:
                    response[i] = 0x7E
                elif response[i+1] == 0x5D:
                    response[i] = 0x7D
                elif response[i+1] == 0x31:
                    response[i] = 0x11
                elif response[i+1] == 0x33:
                    response[i] = 0x13
                response.pop(i+1)
            i+=1
    
        if self.explainmode: print('response w/o byte stuffing:',response)
    
        # confirm check sum is correct
    
        #remove last element from response-list and store it in variable checksum
        checksum = response.pop(-1)
    
        # compare to received checksum
        if self.explainmode:
            print('checksum correct?',checksum == self.compute_SHDLC_checksum(response))
            print('response without checksum', response)
            print('address:',response[0])
            print('command:',hex(response[1]))
            print('status:', response[2])
            print('data length:', response[3])
            print('data:', response[4:])
    
        # return only the 'data' portion of the response
        return response[4:]

        
    def switch_heater(self, val):
        # ------------------------------------------------------------------------------
        # switch heater, val is 1 (ON) or 0 (OFF)
        # ------------------------------------------------------------------------------
        self.make_and_send_SHDLC_command(0x42, [val])
        self.read_SHDLC_response()

    def set_resolution(self):

        # ------------------------------------------------------------------------------
        # set resolution
        # ------------------------------------------------------------------------------
        # set resolution to 16 bit
        self.make_and_send_SHDLC_command(0x41, [16])
        self.read_SHDLC_response()

    def clear_buffer(self):
        # ------------------------------------------------------------------------------
        # clear measurement buffer
        # ------------------------------------------------------------------------------
        # discard any old measurements which may still be in the buffer
        self.make_and_send_SHDLC_command(0x36, [2])
        self.read_SHDLC_response()

    def start_single_measurement(self):
        # ------------------------------------------------------------------------------
        # start single measurement
        # ------------------------------------------------------------------------------
        self.make_and_send_SHDLC_command(0x31, [])
        self.read_SHDLC_response()

    def start_continuous_measurement(self):
        # ------------------------------------------------------------------------------
        # start continuous measurement
        # ------------------------------------------------------------------------------
        # start continuous measurement with measure interval 100 ms
        # NOTE: the measure interval must be supplied as 16 bit integer, i.e. two bytes
        # (most significant, least significant) must be sent.
        self.make_and_send_SHDLC_command(0x33, [1, 0])
        self.read_SHDLC_response()

    def read_measured_data_single(self):
        # ------------------------------------------------------------------------------
        # read the measured data
        # ------------------------------------------------------------------------------
        
        #initialize variable 'data' as empty list
        data=[]
        # loop until data is available and has been read. (execution of a single
        # measurement may take between 1 and 80 ms for resolutions between 9 and 16 bit,
        # respectively.)
        while len(data)<2:
            # get single measurement
            self.make_and_send_SHDLC_command(0x32, [])
            data = self.read_SHDLC_response()
        
        # combine the two data bytes into one 16bit data value
        value_from_sensor = data[0]*256 + data[1]
        if self.explainmode: print('value from sensor:',value_from_sensor)
        
        #compute two's complement (handle negative numbers!)
        if value_from_sensor >= 2**15:  # 2**15 = 32768
            value_from_sensor = value_from_sensor-2**16     # 2**16 = 65536
        
        flow = value_from_sensor / self.SCALEFACTOR
        if self.explainmode:
            print('value with twos complement:',value_from_sensor)        
            print('value with scale factor:', flow)
        return flow

    def read_measured_data_continuous(self):
        # ------------------------------------------------------------------------------
        # read the measured data
        # ------------------------------------------------------------------------------

        # create an empty list to store all data points
        all_data = []

        # loop until 10 data points have been acquired
        while len(all_data) < 10:

            # create empty data list
            data = []
            # loop until data is available and read.

            while len(data) < 2:
                # get measurement buffer
                self.make_and_send_SHDLC_command(ADDRESS, 0x36, [])
                data = self.read_SHDLC_response()

            # loop through the received data
            while len(data) > 0:
                # combine the first two data bytes into one 16bit data value
                value_from_sensor = data[0] * 256 + data[1]
                if self.explainmode: print('value from sensor:', value_from_sensor)

                # compute two's complement (handle negative numbers!)
                if value_from_sensor >= 2 ** 15:  # 2**15 = 32768
                    value_from_sensor = value_from_sensor - 2 ** 16  # 2**16 = 65536

                if self.explainmode: print('value with 2s comlement:', value_from_sensor)

                # apply the scale factor to get real flow units. The scale factor is 13.0 for
                # the SLQ-QT105 flow meter
                if self.explainmode: print('value with scale factor:', value_from_sensor / self.SCALEFACTOR)

                # append the datapoint to 'all_data'
                all_data.append(value_from_sensor / 13.0)
                # remove the first two data bytes from the 'data' list
                data.pop(0)
                data.pop(0)
        return all_data

    def stop_continuous_measurement(self):
        # ------------------------------------------------------------------------------
        # stop continuous measurement
        # ------------------------------------------------------------------------------
        self.make_and_send_SHDLC_command(0x34, [])
        self.read_SHDLC_response()
        
    def ser_close(self):
        self.ser.close()

