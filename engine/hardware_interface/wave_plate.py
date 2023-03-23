from pylablib.devices import Thorlabs #pip install pylablib
import logging
from visexpman import daq
import numpy



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



def init_devices(logfile, config, interpol0, interpol1):
    logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(logfile), logging.StreamHandler()])
    devicelist = Thorlabs.list_kinesis_devices()
    logging.info(devicelist)
    daq.set_digital_line(config['SHUTTERCONF']['GS0_channel'],  0)
    daq.set_digital_line(config['SHUTTERCONF']['RS0_channel'],  0)
    
    if len([device for device in devicelist if device[0] == config['SERVOCONF']['GR0_servo_ID']]) and len([device for device in devicelist if device[0] == config['SERVOCONF']['RR0_servo_ID']]):
        #both motors are connected (their IDs exist in the device list)
        motor0 = Thorlabs.KinesisMotor(config['SERVOCONF']['GR0_servo_ID'], scale='stage')
        motor1 = Thorlabs.KinesisMotor(config['SERVOCONF']['RR0_servo_ID'], scale='stage')
        
        logging.info(motor0.get_status())
        logging.info(motor1.get_status())
        
        if motor0.is_homed() == False or motor1.is_homed() == False:
            logging.info('Homing GR0 and/or RR0...')
                
            if motor0.is_homed() == False:
                motor0.home()
                motor0.wait_for_home()

            if motor1.is_homed() == False:
                motor1.home()
                motor1.wait_for_home()
            logging.info('Homing GR0 and/or RR0 done')
                            
        motor0_des_pos = interpol0(0)
        motor1_des_pos = interpol1(0)
        
        logging.info('Positioning GR0 and RR0 to 0 deg...')
        motor0.move_to(motor0_des_pos)
        motor1.move_to(motor1_des_pos)
        motor0.wait_move()
        motor1.wait_move()    
        motor0.close()
        motor1.close()
        logging.info('Positioning done')
        return [0.0, 0.0]
    else:
        logging.error('Motors are not connected or their IDs need to be changed in the config file!')
        exit(0)
        
    
def set_servo(logfile, config, interpol0, interpol1, des_pos, current_pos):
    logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(logfile), logging.StreamHandler()])
    logging.info('Changing waveplate position...')
    motor0 = Thorlabs.KinesisMotor(config['SERVOCONF']['GR0_servo_ID'], scale='stage')
    motor1 = Thorlabs.KinesisMotor(config['SERVOCONF']['RR0_servo_ID'], scale='stage')
        
    if motor0.is_homed() == False or motor1.is_homed() == False:
        logging.error('Motors are not homed!')
        motor0.close()
        motor1.close()
        return ['SET_SERVO_ERROR']
    else:       
        motor0_des_pos = interpol0(des_pos[0]/100.0)
        motor1_des_pos = interpol1(des_pos[1]/100.0)
        logging.info('Positioning GR0 to: ' + str(des_pos[0]) + '%, ' +  str(motor0_des_pos) + ' deg')
        logging.info('Positioning RR0 to: ' + str(des_pos[1]) + '%, ' +  str(motor1_des_pos) + ' deg')
        motor0.move_to(motor0_des_pos)
        motor0.wait_move()
        motor1.move_to(motor1_des_pos)
        motor1.wait_move()
        logging.info('GR0 position: ' + str(motor0.get_position()) + ' deg')
        logging.info('RR0 position: ' + str(motor1.get_position()) + ' deg')
        motor0.close()
        motor1.close()
        current_pos[0] = des_pos[0]
        current_pos[1] = des_pos[1]
        return ['SET_SERVO_DONE',  des_pos[0], des_pos[1]]         