from visexpman.engine.vision_experiment.configuration import BehavioralConfig
from visexpman.engine.generic import fileop

class BehavioralSetup(BehavioralConfig):
        LOG_PATH = fileop.select_folder_exists(['q:\\log', '/tmp', 'c:\\Users\\rz\\tmp'])
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['q:\\data', '/tmp', 'c:\\Users\\rz\\tmp'])
        CONTEXT_PATH = fileop.select_folder_exists(['q:\\context', '/tmp', 'c:\\Users\\rz\\tmp'])
        ENABLE_CAMERA=True
        CAMERA_FRAME_RATE=7
        CAMERA_FRAME_WIDTH=640/2
        CAMERA_FRAME_HEIGHT=480/2
        TREADMILL_SPEED_UPDATE_RATE=50e-3
        
        
