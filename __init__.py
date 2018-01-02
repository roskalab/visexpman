'''
==== Get started with Vision Experiment Manager framework  ====
    !!! Outdated !!!
    === Framework installation ===

        = Ubuntu 12.04 =
            Analysis, stimulation development, limited stimulation
            (graphic card may not work well, only parallel port/serial port controlled hardware is available)
            with sudo apt-get install or synaptic:
                python-numpy
                python-scipy
                python-zc.lockfile
                python-sip
                python-imaging
                python-tables
                python-serial
                python-parallel
                python-qt4
                python-qwt5-qt4
                python-opengl
                python-pygame
                python-sklearn
                python wxgtk2.8
                python-opencv
                python-matplotlib
            Optional:
                python-zmq
                python-celery
                python-pp
            From source (check pypi.org)
                mahotas, polygon,pymorph
            Install Framework:
            mkdir visexp
            cd visexp
            git clone git@github.com:roskalab/visexpman.git
            git clone git@github.com:hillierdani/visexpA.git
            sudo gedit /usr/lib/python2.7/dist-packages/visexp.pth
            type in full path of previously created visexp folder
                        
        = Windows XP/Windows7 =
            Usage: Visual stimulation, retinal Ca imaging, RC Cortical GUI
            Download pythonxy 2.7.3.1 package, install all modules
            Install DAQmx driver
            Install zc.lockfile and PyDAQmx from source
            Install pygame
            Install giveio parallel port driver (does not work on windows 7)
            Copy visexpA and visexpman into c:\visexp
            create c:\Python27\Lib\site-packages\visexp.pth containing c:\\visexp
            
    === Setting up visual stimulation ===

        = Perform projector calibration by using Thorlabs PM100USB device = 
            Install PM100USB driver on computer
            Run c:\visexp\visexpman\users\zoltan\projector_calibration.py
            Results are saved to c:\visexp\data\gamma.hdf5 and gamma.mat
            
        = Create machine configuration = 
            The configuration file shall reside in the c:\visexp\visexpman\users\<username> folder, its extension is .py
            use the SafestartConfig as a template class (c:\visexp\visexpman\users\default\default_configs.py)
            Make sure that the following modules are imported:
            
            import os.path
            from visexpman.engine.vision_experiment import configuration
            from visexpman.engine.generic import utils
            
            The machine configuration class shall inherit from a platform specific class.
            class MyMachineConfig(<Platform specific machine config template>):
                <Platform specific machine config template> can be 
                    configuration.ElphysRetinalCaImagingConfig
                    configuration.RcCorticalCaImagingConfig
                    configuration.AoCorticalCaImagingConfig
                    configuration.MCMEAConfig (Multi channel systems multi electrode array setup)
                    configuration.HiMEAConfig (Hierleman Multi electrode array setup)
                    configuration.VisionExperimentConfig: Shall be used for stimulation development only
                
                def _set_user_parameters(self):
                    <Define parameter values>
            
                    self._create_parameters_from_locals(locals())
                    
            Define the following paramters:
            LOG_PATH - where application log files are saved, might be important when something goes wrong
            EXPERIMENT_LOG_PATH - where experiment log files are saved. Timing of a stimulation can be tracked here
            EXPERIMENT_DATA_PATH - By default file generated during stimulation is saved here. 
            This file contains the parameters of the stimulation, timing/syncronization info, data about software environment. 
            It may also contain electrophysiology data
            SCREEN_RESOLUTION = utils.cr([800,600]) Screen resolution in column, row format
            COORDINATE_SYSTEM='center' Origin of coordinate system used to display stimulation, center and ul_corner (upper left corner) are supported
            ENABLE_FRAME_CAPTURE = False Set it to True to save each frame to CAPTURE_PATH folder, might help stimulation dvelopment
            SCREEN_EXPECTED_FRAME_RATE = 60.0 The frame rate of the projector
            SCREEN_UM_TO_PIXEL_SCALE = 1 Size of 1 um in pixels. Has to be measured at each setup
            ACQUISITION_TRIGGER_PIN = 2 The pin number on the parallel port interface that triggers the data acquisition. On Elphys setups this signal is connected to the PFI0 input.
            FRAME_TIMING_PIN = 0 On this parallel port pin a pulse is generated at each low level screen update. Consequently its frequency will be equal with the projector's frame rate
            BLOCK_TIMING_PIN = 1 This signal can be used to align stimulation with electrophysiology data. There is a level change when the visual information is updated on the screen
            ENABLE_FILTERWHEEL = True Enable filterwheel control
            Example for configuring two filterwheels. user has to make sure that the right port name and baudrate is used
            import serial
            FILTERWHEEL_SERIAL_PORT = [{ 
                                        'port' :  'COM3',   
                                        'baudrate' : 115200,
                                        'parity' : serial.PARITY_NONE,
                                        'stopbits' : serial.STOPBITS_ONE,
                                        'bytesize' : serial.EIGHTBITS,                                    
                                        }, 
                                        {
                                        'port' :  'COM4',
                                        'baudrate' : 115200,
                                        'parity' : serial.PARITY_NONE,
                                        'stopbits' : serial.STOPBITS_ONE,
                                        'bytesize' : serial.EIGHTBITS,                                    
                                        }]
            There are two ways of defining a gamma correction curve:
                1. Provide a two dimensional array where the first column is the intensity set on the projector, the second is the intensity value measured
                        import numpy
                        self.GAMMA_CORRECTION = numpy.array([
                                                 [0, 15.6], 
                                                 [20, 54],
                                                 
                                                 ......
                                                 [230, 9500],
                                                 [255, 9500], 
                                                 ])
                2. Load gamma curve file from automated measurement, here is an example for that:
                        gamma_corr_filename = 'c:\\visexp\\gamma.hdf5'
                        if os.path.exists(gamma_corr_filename):
                            import hdf5io
                            import copy
                            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction'))
            
        = Implementing user stimulations =
            The stimulation (aka experiment) file shall reside in the c:\visexp\visexpman\users\<username> folder, its extension is .py
            Make sure that the following modules are imported:
                from visexpman.engine.vision_experiment import experiment
                from visexpman.engine.generic import utils
            These two might be also necessary
                import time
                import numpy
            You can also make a copy of the following template file: c:\visexp\visexpman\users\tempateuser\template_experiment.py.
            A stimulation can be divided to two entities: sequence of instructions (stimulation patterns, calls to external devices) and parameters.
            Experiment config:
                One instruction sequence may have several parameter sets. Consequently two classes make up a stimulation: an Experiment and an ExperimentConfig.
                The _create_parameters method (def _create_parameters(self):) of the experiment config class creates the experiment parameters as follows:
                self.COLOR = 1.0 Color like parameters are always in the 0.0....1.0 range. In greyscale 1.0 is white, 0.0 is black. A color can be defined in RGB format as follows:
                self.MY_FANCY_COLOR = [1.0, 0.5, 0.25]
                self.DURATION = 1.0 Duration like parameters should be interpreted in seconds. For ms or us use the scientific format like 10e-3 = 10 ms. 
                    If the duration of a stimulus pattern is 0, it will be displayed for one frame time.
                Finally these three (or two) lines are mandatory:
                self.runnable = 'TemplateExperiment'  Name of experiment class
                self.pre_runnable = 'TemplatePreExperiment' Optional, name of pre experiment class. A pre experiment is shown when stimulation is not running.
                    If it would be a fullscreen pattern with a color, it is easier to set the BACKGROUND_COLOR parameter in the machine config to the desired value
                self._create_parameters_from_locals(locals()) Mandatory
                
            Experiment:
                The run method of the experiment class executes all the instructions necessary to accomplish an experiment. Stimulation patterns, experiment and machine config parameters
                and call to external devices are available here.
                self.experiment_config.COLOR - reference to an experiment config parameter
                self.machine_config.SCREEN_RESOLUTION['row'] - reference to the row field of the screen resolution machine config
                Other useful variables:
                    self.frame_counter - frame counter, incremented at each flip. Showing a 2 sec stimulus at a 60 Hz frame rate, its increment is 120
                        using time.sleep() function does not increment the frame counter, but the self.show_fullscreen() does.
                    self.abort - if True, stimulation patterns are skipped
                    self.start_time - time when experiment started
                    self.elapsed_time - time elapsed since experiment start
                    
                Summary of stimulation patterns (more detail c:\visexp\visexpman\engine\vision_experiment\stimulation_library.py):
                1. Show fullscreen for 1 second with white color
                    self.show_fullscreen(duration = 1.0,  color = 1.0)
                2. Show a shape, that can be shape = 'spot', 'rectangle', 'annulus'
                    self.show_shape(shape = 'spot',  duration = 1.0,  pos = utils.rc((0,  0)),  color = 1.0,  background_color = 0.5, orientation = 0.0,  size = utils.rc((10, 10)), block_trigger = False)
                    pos - position on screen in row/col format
                    color - Color of shape. A color sequence can be loaded by passing an nx1 dimensional array. Duration parameter is overriden, each color is displayed for one frame time
                    orienatation - in degrees, applies to rectangle shape
                    size - size of shape in row/col format in um
                    block trigger - if True the corresponding parallel port pin is set to high at the beginning, and set back to low at the end
                3. Increasing spot
                    self.increasing_spot(spot_sizes, on_time, off_time, color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)), block_trigger = True)
                    spot_sizes - a sequence of sport sizes in um
                    on_time - each spot is shown for this time
                    off_time - time between spots
                    pos - position of spot in row/col format
                4. Moving shape
                    self.moving_shape(size, speeds, directions, shape = 'rect', color = 1.0, background_color = 0.0, pause=0.0)
                    size - size of shape in um
                    shape - same as show_shape
                    speeds - movement speeds in um/s
                    directions - series of movement directions in degree. Shape is moved in all directions and in all speeds
                    pause - pause between different moves
                5. Show grating
                    self.show_grating(duration = 10.0,  profile = 'sqr',  white_bar_width =100,  orientation = 0,  velocity = 0.0,  color_contrast = 1.0,  color_offset = 0.5,  duty_cycle = 1.0)
                    white_bar_width - width of white (highest contrast) bar in um
                    orientation - in degrees
                    velocity - speed of movement in um/s
                    duty_cycle - the ratio of black and white bars
                6. Show flashes
                    self.flash_stimulus(shape, timing, colors, repeats = 1, block_trigger = True)
                    shape - same as at show_shape, 'ff' for fullfield flash
                    timing - sequence of timing values: black duration, white duration, black duration, white duration ....
                    colors - can be a sequence of colors or a single color
                7. Show image at filename for 2 sec. Image is shown with a 1:1 scaling
                    self.show_image(filename,  duration = 2.0)
                    
                Additional stimulation possibilities:
                LED flashing for ChR stimulation
                    self.led_controller.set([[timing offset from stimulus start, flash durations, flash_amplitude in volts]], overall_time)
                    self.led_controller.start()
                    The daqmx device needs to be set up in machine config:
                        DAQ_CONFIG = [
                            {
                            'ANALOG_CONFIG' : 'ao',
                            'DAQ_TIMEOUT' : 3.0,
                            'SAMPLE_RATE' : 1000,
                            'AO_CHANNEL' : 'Dev1/ao0',
                            'MAX_VOLTAGE' : 10.0,
                            'MIN_VOLTAGE' : 0.0,
                            'ENABLE' : True
                            }
                            ]
                Controlling Polychrome device
                    from visexpman.engine.hardware_interface import polychrome_interface
                    self.polychrome = polychrome_interface.Polychrome(self.machine_config)
                    self.polychrome.set_wavelength(wavelength in nm)
                    self.polychrome.set_intensity(intensity in 0.0...1.0 range in 0.1 steps)
                    self.polychrome.release_instrument()#Mandatory
                
                Helpers:
                    Intert a delay:  time.sleep(delay in seconds)
                    control parallel port pin: self.parallel_port.set_data_bit(pin id 0...7, logical value (0, 1))
                    
        = Run stimulation software =
        python c:\visexp\visexpman\engine\visexp_runner.py <username> <machine config>

'''
#TODO: remove these 3 imports:
import sys
import os
import numpy

version = 'v0.3.0'
try:
    from visexpman.engine.visexp_smallapp import rotate_images
    from visexpman.applications.led_stimulator import led_stimulator
except:
    pass
