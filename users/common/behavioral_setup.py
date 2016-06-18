import os
from visexpman.engine.vision_experiment.configuration import BehavioralConfig
from visexpman.engine.generic import fileop

class BehavioralSetup(BehavioralConfig):
        LOG_PATH = fileop.select_folder_exists(['q:\\log', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['q:\\data', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        CONTEXT_PATH = fileop.select_folder_exists(['q:\\context', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        ENABLE_CAMERA=True
        CAMERA_ID=0
        CAMERA_FRAME_RATE=7
        CAMERA_FRAME_WIDTH=640/2
        CAMERA_FRAME_HEIGHT=480/2
        TREADMILL_SPEED_UPDATE_RATE=100e-3
        TREADMILL_READ_TIMEOUT=100e-3
        TREADMILL_DIAMETER=150#mm
        TREADMILL_PULSE_PER_REV=18
        WATER_VALVE_DO_CHANNEL=0
        AIRPUFF_VALVE_DO_CHANNEL=1
        FAN_DO_CHANNEL=2
        SCREEN_SIZE=[1366,700]
        SCREEN_OFFSET=[4,19]
        BOTTOM_WIDGET_HEIGHT=260
        PLOT_WIDGET_WIDTH=700
        MINIMUM_FREE_SPACE=20#GByte
        ARDUINO_SERIAL_PORT='COM5' if os.name=='nt' else '/dev/ttyACM0'
        LASER_AO_CHANNEL='Dev1/ao0'
        LED_AO_CHANNEL='Dev1/ao1'
        STIM_SAMPLE_RATE=1000
        POSITIVE_DIRECTION=-1
        PROTOCOL_ORDER=['ForcedKeepRunningRewardLevel1', 'ForcedKeepRunningRewardLevel2', 'ForcedKeepRunningRewardLevel3', 'StopReward', 'StopRewardLevel2', 'StimStopReward', 'FearResponse']
        
class BehavioralSetup2(BehavioralSetup):
    ARDUINO_SERIAL_PORT='COM3'
    SCREEN_OFFSET=[4,25]
    SCREEN_SIZE=[1280,950]
    PLOT_WIDGET_WIDTH=600
    BOTTOM_WIDGET_HEIGHT=400
    WATER_VALVE_DO_CHANNEL=1
    AIRPUFF_VALVE_DO_CHANNEL=2

class BehavioralSetup3(BehavioralSetup):
    SCREEN_OFFSET=[4,37]
    SCREEN_SIZE=[1920,950]
    PLOT_WIDGET_WIDTH=1200
    BOTTOM_WIDGET_HEIGHT=400
    ARDUINO_SERIAL_PORT='COM3'
    WATER_VALVE_DO_CHANNEL=2


class OfficeTestComputer(BehavioralSetup):
    LASER_AO_CHANNEL='/Dev2/ao0'
    ENABLE_CAMERA=False
