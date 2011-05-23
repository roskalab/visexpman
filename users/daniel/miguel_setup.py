import visual_stimulation.configuration
import generic.utils as utils
class Config(visual_stimulation.configuration.VisualStimulationConfig):   
    def _set_user_specific_parameters(self):
        RUN_MODE = 'user interface' 
        FILTERWHEEL_ENABLE = True       
        ENABLE_PARALLEL_PORT = True        
        FULLSCR = True
        SCREEN_RESOLUTION = utils.rc([768, 1024])
        SCREEN__SCREEN_EXPECTED_FRAME_RATE= 75.0
                        
        SCREEN_UM_TO_PIXEL_SCALE = 3 # um/pixel
        SCREEN_DIRECTLY_ONTO_RETINA = True
#if ~isfield(monitor,'distancefrom_mouseeye')
        # error('monitor struct must have a field ''distancefrom_mouseeye'' in cm')

        #  if ~isfield(monitor,'pixelwidth')
        #   error('monitor struct must have a field ''pixelwidth'' in cm')