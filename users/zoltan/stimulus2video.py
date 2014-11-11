import os
import os.path
import tempfile
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment

class FlickerExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Flicker'
        self.FRQS = [1.0, 2.0, 3.0, 5.0, 10.0, 15.0,  30.0]
        self.DURATION = 10.0
        self._create_parameters_from_locals(locals())          

class Flicker(experiment.Experiment):
    def run(self):
        for frq in self.experiment_config.FRQS:
            for f in os.listdir(self.machine_config.CAPTURE_PATH):
                os.remove(os.path.join(self.machine_config.CAPTURE_PATH, f))
            on_duration = 0.5*1/frq
            off_duration = on_duration
            for i in range(int(self.experiment_config.DURATION*frq)):
                self.show_fullscreen(duration=on_duration,  color=1.0)
                self.show_fullscreen(duration=off_duration,  color=0.0)
            if len(os.listdir(self.machine_config.CAPTURE_PATH)) != self.experiment_config.DURATION * self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
                print 'Incorrect number of frames generated: {0}, {1}' .format(len(os.listdir(self.machine_config.CAPTURE_PATH)), self.experiment_config.DURATION * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            videofilename = '/mnt/datafast/debug/flicker_{0}_Hz.mp4'.format(int(frq))
            if os.path.exists(videofilename):
                os.remove(videofilename)
            self.export2video(videofilename)

class Config(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        root_folder = tempfile.gettempdir()
        drive_data_folder = os.path.join(root_folder, 'experiment_data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #Create folders that does not exists
        for folder in [drive_data_folder, LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, CONTEXT_PATH, CAPTURE_PATH]:
            fileop.mkdir_notexists(folder)
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE =  not False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        ENABLE_PARALLEL_PORT = False
        STIM_RECORDS_ANALOG_SIGNALS = False
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":
    v = visexp_runner.VisionExperimentRunner('zoltan', 'Config')
    v.run_experiment(user_experiment_config = 'FlickerExperimentConfig')
