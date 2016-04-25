from visexpman.engine.vision_experiment.configuration import BehavioralConfig
from visexpman.engine.generic import fileop

class BehavioralSetup(BehavioralConfig):
        LOG_PATH = fileop.select_folder_exists(['q:\\log', '/tmp', 'c:\\Data'])
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['q:\\data', '/tmp', 'c:\\Data'])
        CONTEXT_PATH = fileop.select_folder_exists(['q:\\context', '/tmp', 'c:\\Data'])
        ENABLE_CAMERA=True
        CAMERA_FRAME_RATE=7
        CAMERA_FRAME_WIDTH=640/2
        CAMERA_FRAME_HEIGHT=480/2
        TREADMILL_SPEED_UPDATE_RATE=100e-3
        TREADMILL_DIAMETER=150#mm
        TREADMILL_PULSE_PER_REV=18
        WATER_VALVE_DO_CHANNEL=0
        AIRPUFF_VALVE_DO_CHANNEL=1
        FAN_DO_CHANNEL=2
        SCREEN_SIZE=[1366,700]
        SCREEN_OFFSET=[4,19]
        BOTTOM_WIDGET_HEIGHT=260
        MINIMUM_FREE_SPACE=20#GByte
        ARDUINO_SERIAL_PORT='/dev/ttyACM0'
        LASER_AO_CHANNEL='/Dev1/ao0'
        POSITIVE_DIRECTION=-1
        
class OfficeTestComputer(BehavioralSetup):
    LASER_AO_CHANNEL='/Dev2/ao0'
    ENABLE_CAMERA=False
        
