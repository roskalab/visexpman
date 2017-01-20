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
        SCREEN_SIZE=[1366,700]
        SCREEN_OFFSET=[4,19]
        BOTTOM_WIDGET_HEIGHT=260
        PLOT_WIDGET_WIDTH=700
        MINIMUM_FREE_SPACE=20#GByte
        ARDUINO_SERIAL_PORT='COM9'
        PROTOCOL_ORDER=['HitMiss']
        AI_CHANNELS='Dev1/ai0:4'#water valve, lick signal, laser, lick detector output, debug (protocol state)
        AI_SAMPLE_RATE=5000
        BACKUPTIME=3#3am
        BACKUP_LOG_TIMEOUT=60#minutes
        BACKUP_PATH='x:\\behavioral'
        
class BehavioralSetup2(BehavioralSetup):
    ARDUINO_SERIAL_PORT='COM4'
    SCREEN_OFFSET=[4,25]
    SCREEN_SIZE=[1280,950]
    PLOT_WIDGET_WIDTH=600
    BOTTOM_WIDGET_HEIGHT=400
    WATER_VALVE_DO_CHANNEL=1
    AIRPUFF_VALVE_DO_CHANNEL=2
    TREADMILL_READ_TIMEOUT=200e-3

class BehavioralSetup3(BehavioralSetup):
    SCREEN_OFFSET=[4,37]
    SCREEN_SIZE=[1920,950]
    PLOT_WIDGET_WIDTH=1200
    BOTTOM_WIDGET_HEIGHT=400
    ARDUINO_SERIAL_PORT='COM3'
    WATER_VALVE_DO_CHANNEL=2

class OfficeTest(BehavioralSetup):
    LASER_AO_CHANNEL='/Dev2/ao0'
    ENABLE_CAMERA=False
    ARDUINO_SERIAL_PORT='COM9'
    SCREEN_SIZE=[1280,1024]
    PLOT_WIDGET_WIDTH=600
    AI_CHANNELS='Dev2/ai0:4'
    BACKUP_PATH='x:\\behavioral\\test3'
    BACKUPTIME=13
    BACKUP_LOG_TIMEOUT=1#minutes
