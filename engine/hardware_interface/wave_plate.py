from pylablib.devices import Thorlabs
import logging
from visexpman import daq
import numpy

class WavePlate(object):
    def __init__(self, waveplate_id, logfile, config, interpol):#Handles single waveplate, identification: RR0, GR1 etc
        self.waveplate_id = waveplate_id
        self.logfile = logfile
        self.config = config
        self.current_pos = 0.0
        self.param_name = self.waveplate_id+'_servo_ID'
        self.interpol = interpol
        
        logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(self.logfile), logging.StreamHandler()])
        devicelist = Thorlabs.list_kinesis_devices()
        logging.info(devicelist)
        
        if len([device for device in devicelist if device[0] == self.config['SERVOCONF'][self.param_name]]):
            #servo motor ID is in the list of connected devices
            motor = Thorlabs.KinesisMotor(self.config['SERVOCONF'][self.param_name], scale='stage')
            status = motor.get_status()
            logging.info(status)
            
            if 'enabled' not in status:
                logging.error('Motor ' + self.waveplate_id + ' is disabled! Enable it before using this software!')
                
            else:
                if motor.is_homed() == False:
                    logging.info('Homing ' + self.waveplate_id + '...')
                    motor.home()
                    motor.wait_for_home()
                    logging.info('Homing ' + self.waveplate_id + ' done')
                                    

                if self.interpol is None:
                    motor_des_pos = 0
                    logging.info('Positioning ' + self.waveplate_id + ' to 0 deg')
                else:
                    motor_des_pos = self.interpol(0)
                    logging.info('Positioning ' + self.waveplate_id + ' to 0%')
                motor.move_to(motor_des_pos)
                motor.wait_move()   
                logging.info('Positioning done')
            motor.close()
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
            if self.interpol is None:
                motor_des_pos = des_pos
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
    
    if config.has_option('SERVOCONF', 'GR0_angle_deg') and config.has_option('SERVOCONF', 'GR0_power_mW'):
        GR0_angle_deg = [float(i) for i in config['SERVOCONF']['GR0_angle_deg'].split(',')]
        GR0_power_mW = [float(i) for i in config['SERVOCONF']['GR0_power_mW'].split(',')]
        GR0_power = (GR0_power_mW - numpy.min(GR0_power_mW)) / (numpy.max(GR0_power_mW) - numpy.min(GR0_power_mW)) #normalization
        GR0_interpolation = interpolate.interp1d(GR0_power, GR0_angle_deg)
    else:
        GR0_interpolation = None
        logging.info('GR0 calibration is missing!')
        
    if config.has_option('SERVOCONF', 'RR0_angle_deg') and config.has_option('SERVOCONF', 'RR0_power_mW'):
        RR0_angle_deg = [float(i) for i in config['SERVOCONF']['RR0_angle_deg'].split(',')]
        RR0_power_mW = [float(i) for i in config['SERVOCONF']['RR0_power_mW'].split(',')]
        RR0_power = (RR0_power_mW - numpy.min(RR0_power_mW)) / (numpy.max(RR0_power_mW) - numpy.min(RR0_power_mW)) #normalization
        RR0_interpolation = interpolate.interp1d(RR0_power, RR0_angle_deg)
    else:
        RR0_interpolation = None
        logging.info('RR0 calibration is missing!')
   
    return config, GR0_interpolation, RR0_interpolation


  