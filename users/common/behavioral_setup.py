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
        SCREEN_SIZE=[1366,700]
        SCREEN_OFFSET=[4,19]
        BOTTOM_WIDGET_HEIGHT=290
        
        
