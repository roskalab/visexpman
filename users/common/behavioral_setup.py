from visexpman.engine.vision_experiment.configuration import BehavioralConfig
from visexpman.engine.generic import fileop

class BehavioralSetup(BehavioralConfig):
        LOG_PATH = fileop.select_folder_exists(['q:\\log', '/tmp'])
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['q:\\data', '/tmp'])
        CONTEXT_PATH = fileop.select_folder_exists(['q:\\context', '/tmp'])
        ENABLE_CAMERA=True
        CAMERA_FRAME_RATE=16
        CAMERA_FRAME_WIDTH=640/2
        CAMERA_FRAME_HEIGHT=480/2
        
        
