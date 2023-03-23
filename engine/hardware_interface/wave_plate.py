from pylablib.devices import Thorlabs
import logging
from visexpman import daq
import numpy

class WavePlate(object):
    def __init__(self, waveplate_id, logfile, config, interpol):#Handles single waveplate, identification: RR0, GR1 etc
        self.waveplate_id = waveplate_id
        self.logfile = logfile
        self.config = config
        self.interpol = interpol
        self.current_pos = 0.0
        self.param_name = self.waveplate_id+'_servo_ID'
        
        logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(self.logfile), logging.StreamHandler()])
        devicelist = Thorlabs.list_kinesis_devices()
        logging.info(devicelist)
        
        if len([device for device in devicelist if device[0] == self.config['SERVOCONF'][self.param_name]]):
            #servo motor ID is in the list of connected devices
            motor = Thorlabs.KinesisMotor(self.config['SERVOCONF'][self.param_name], scale='stage')
            logging.info(motor.get_status())
            
            if motor.is_homed() == False:
                logging.info('Homing ' + self.waveplate_id + '...')
                motor.home()
                motor.wait_for_home()
                logging.info('Homing ' + self.waveplate_id + ' done')
                                

            
            logging.info('Positioning ' + self.waveplate_id + ' to 0 deg')
            motor_des_pos = self.interpol(0)
            motor.move_to(motor_des_pos)
            motor.wait_move()   
            motor.close()
            logging.info('Positioning done')
        else:
            logging.error('Motor ' + self.waveplate_id + ' is not connected or its ID need to be changed in the config file!')
            #getattr(self.logger, 'filename') 
            
    def set_position(self, des_pos):
        logging.info('Changing ' + self.waveplate_id + ' waveplate position...')
        motor = Thorlabs.KinesisMotor(self.config['SERVOCONF'][self.param_name], scale='stage')
            
        if motor.is_homed() == False:
            logging.error('Motor ' + self.waveplate_id + ' is not homed!')
            motor.close()
            return ['SET_SERVO_ERROR']
        else:       
            motor_des_pos = self.interpol(des_pos/100.0)
            logging.info('Positioning ' + self.waveplate_id + ' to: ' + str(des_pos) + '%, ' +  str(motor_des_pos) + ' deg')
            motor.move_to(motor_des_pos)
            motor.wait_move()
            logging.info(self.waveplate_id + ' position: ' + str(motor.get_position()) + ' deg')
            motor.close()
            self.current_pos = des_pos
            return ['SET_SERVO_DONE',  self.current_pos]
    
    def get_position(self):
        return self.current_pos      



def read_config(logfile, config_file):
    import configparser
    import os
    from scipy import interpolate
    logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(logfile), logging.StreamHandler()])
    if os.path.isfile(config_file) == False:
        logging.error('Config file is missing!')
        exit(1)
    config = configparser.ConfigParser()
    config.read(config_file)
    
    if 'SERVOCONF' in config and 'SHUTTERCONF' in config and 'NETWORKCONF' in config:
        logging.info(config['SERVOCONF']['GR0_servo_ID'])
        logging.info(config['SERVOCONF']['RR0_servo_ID'])
        logging.info(config['SERVOCONF']['GR0_angle_deg'])
        logging.info(config['SERVOCONF']['GR0_power_mW'])
        logging.info(config['SERVOCONF']['RR0_angle_deg'])
        logging.info(config['SERVOCONF']['RR0_power_mW'])
        logging.info(config['SHUTTERCONF']['GS0_channel'])
        logging.info(config['SHUTTERCONF']['RS0_channel'])
        logging.info(config['NETWORKCONF']['ip_address0'])
        logging.info(config['NETWORKCONF']['ip_address1'])
        logging.info(config['NETWORKCONF']['port0'])
        logging.info(config['NETWORKCONF']['port1'])
        
        GR0_angle_deg = [float(i) for i in config['SERVOCONF']['GR0_angle_deg'].split(',')]
        GR0_power_mW = [float(i) for i in config['SERVOCONF']['GR0_power_mW'].split(',')]
        GR0_power = (GR0_power_mW - numpy.min(GR0_power_mW)) / (numpy.max(GR0_power_mW) - numpy.min(GR0_power_mW)) #normalization
        RR0_angle_deg = [float(i) for i in config['SERVOCONF']['RR0_angle_deg'].split(',')]
        RR0_power_mW = [float(i) for i in config['SERVOCONF']['RR0_power_mW'].split(',')]
        RR0_power = (RR0_power_mW - numpy.min(RR0_power_mW)) / (numpy.max(RR0_power_mW) - numpy.min(RR0_power_mW)) #normalization
    else:
        logging.error('Config file format error')
        exit(1)
        
    GR0_interpolation = interpolate.interp1d(GR0_power, GR0_angle_deg)
    RR0_interpolation = interpolate.interp1d(RR0_power, RR0_angle_deg)
    return config, GR0_interpolation, RR0_interpolation


  