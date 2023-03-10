Vision Experiment Manager
============================================

Vision Experiment Manager is a framework for building automated experiments for visual neuroscience. Its main modules are visual stimulation, two photon imaging, device interfaces and a user interface library.

Vision Experiment Manager was developed in Botond Roska's lab in Friedrich Miescher Instiute and Institute of Molecular and Clinical Ophthalmology Basel from 2011.

Installation
============

Windows 10
--------------

1. Download http://atlas.sens.hu/web/python_installer.zip and unzip to c:\software
2. Install python 3.8.0, installation location is c:\Python38. Select "install for all users", disable long path limit
3. Install pyopengl from local wheel:

.. code:: shell

        cd c:\software\visexpman_installers
        pip install PyOpenGL-3.1.3rc1-cp38-cp38-win_amd64.whl
        
4. Install Daqmx driver (ni-daqmx_19.6_online.exe)
5. Copy ffmpeg.exe and ffprobe.exe to c:\software
6. Add c:\software to Path environmental variable
7. Clone Visexpman to c:\software: git clone https://github.com/rzoli/visexpman.git
8. Install python dependencies: run install_modules.bat from c:\software\visexpman_installers (preferred)
                OR
                pip install -r c:\software\visexpman\requirements.txt


Developer's Guide
=================

GUI Development (visexpman.generic.gui)
---------------------------------------

How to build a simple GUI that triggers data acquisition and sends digital triggers?

VisExpMan has a SimpleGuiWindow class for implementing simple PyQt based applications. Based on Qt.QMainWindow and by default it consist of a log and a debug widget.

The full version of the code is 'here. <https://raw.githubusercontent.com/roskalab/visexpman/zdev/applications/data_acquisition_gui.py>'

.. code:: python

    from visexpman import gui

    class DaqGUi(gui.SimpleGuiWindow):
        pass
            
    if __name__=='__main__':
        gui=DaqGui()

Running it would look like this:
        
.. image:: https://raw.githubusercontent.com/roskalab/visexpman/zdev/images/basic_gui.png

Let's add a plot widget for visualizing recorded signals to the left side.. For this gui.SimpleGuiWindow class's init_gui method needs to be overloaded:

.. code:: python

    def init_gui(self):#This will be called upon initialization
        self.plot=gui.Plot(self)
        self.plot.setMinimumHeight(500)
        self.plot.setMinimumWidth(500)
        self.add_dockwidget(self.plot, 'Recorded Signals', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea)

Also add a Settings tab to the right side for controlling recording parameters:

.. code:: python

        params_config = [
                {'name': 'Recording Name', 'type': 'str', 'value': ''},
                {'name': 'Sampling Rate', 'type': 'float', 'value': 1000.0,  'suffix': ' Hz', 'decimals':6},
                {'name': 'Recording Duration', 'type': 'float', 'value': 10.0,  'suffix': ' s', 'decimals':6},
                ]
        self.params = gui.ParameterTable(self, params_config)
        self.params.setMinimumWidth(300)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)#Function called when any setting modified by the user
        self.add_dockwidget(self.params, 'Settings', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea)
        
    def parameter_changed(self):
        self.setting_values=self.params.get_parameter_tree(return_dict=True)#Grab all values from Settings tab and organize to a dictionary
        self.log(self.setting_values)#Display setting values on log widget and also save to logfile

parameter_changed method is for processing changes at Setting values. This function needs to be called to copy all initial values to self.setting_values variable:

.. code:: python

    def init_gui(self):
        ...
        self.parameter_changed()

Calling self.log(msg) prints messages to logfile and GUI's log window. Logfile's location can be set as follows:

.. code:: python

    if __name__=='__main__':
        gui=DaqGui(logfolder=r'c:\tmp')
    
Adding start, stop and exit buttons to toolbar:

.. code:: python

    def init_gui(self):
        ...
        toolbar_buttons=['start', 'stop', 'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        

Callback functions assigned to toolbar buttons
        
.. code:: python
    
    def start_action(self):
        pass
        
    def stop_action(self):
        pass
        
    def exit_action(self):
        self.close()
    
Also add statusbar for displaying the acquisition status to init_gui method:

.. code:: python

        import PyQt5.QtGui as QtGui
        self.statusbar=self.statusBar()
        self.statusbar.msg=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.msg)
        self.statusbar.status_msg=QtGui.QLabel('', self)
        self.statusbar.addPermanentWidget(self.statusbar.status_msg)
        self.set_status('Idle','gray')
    
The set_status function is available for changing acquisition status:

.. code:: python

    def set_status(self,state, color):
        self.statusbar.status_msg.setStyleSheet(f'background:{color};')
        self.statusbar.status_msg.setText(state)
        QtCore.QCoreApplication.instance().processEvents()
        
Plotter function for displaying recorded traces

.. code:: python

    def plot_traces(self, sig,channel_names,fsample):
        import numpy
        x=[numpy.arange(sig.shape[1])/fsample]*sig.shape[0]
        y=[sig[i] for i in range(sig.shape[0])]
        from visexpman import colors
        pp=[{'name': (str(channel_names[i])), 'pen':(numpy.array(colors.get_color(i))*255).tolist()} for i in range(len(x))]
        self.plot.update_curves(x, y, plotparams=pp)

Test the plotter function from the GUI's Python Debug console, the trace shows up on the plot widget.

.. image:: https://raw.githubusercontent.com/roskalab/visexpman/zdev/images/python_debug_console.png

.. code:: python
    
    self.plot_traces(numpy.random.random((2,1000)),['ch1','ch2'],1000)

For recording real signals an NI USB daq device is needed (e.g USB 6003). For simulating signals please connect AO1 to AI1. In NI MAX find out device id which is Dev2 for now. Import visexpman's daq module:

.. code:: python

    from visexpman import daq
    
Add triggering signal acquisition to start(self) method.

.. code:: python

    def start_action(self):
        duration=self.setting_values['params/Recording Duration']#Take recording duration from Settings
        fsample=self.setting_values['params/Sampling Rate']
        self.ai=daq.AnalogRead('Dev2/ai1:2', duration, fsample)

The recording will be triggered for the predefined duration, so stop_action function needs to be called after completion. Therefore in self start_action() a timer is started:

.. code:: python

    def start_action(self):
        ...
        self.timer=QtCore.QTimer()
        self.timer.singleShot(int(duration*1000), self.finish_recording)
        self.log('Recording started')#Notify user about the beginning of recording data
        
stop_action method takes care of reading data, terminating the recording process and visualization:

.. code:: python

    def finish_recording(self):
        data=self.ai.read()#Read acquired data
        self.plot_traces(data,['AI1', 'AI2'],fsample=self.setting_values['params/Sampling Rate'])
        self.plot.plot.setTitle(self.setting_values['params/Recording Name'])#Copy recording name to plot's title
        self.log('Recording ended')
    
Press run and wait until completes. This is just some noise so let's generate a sinus waveform using AO1 channel:

.. code:: python

    def start_action(self):
        ...
        import numpy
        waveform=numpy.zeros((1,int(duration*fsample)))
        waveform[0]=numpy.sin(2*numpy.pi*numpy.arange(waveform.shape[1])/waveform.shape[1])
        self.ao,d=daq.set_waveform_start('Dev2/ao1',waveform,fsample)
        
    def finish_recording(self):
        ...
        daq.set_waveform_finish(self.ao, 1)

Save data to hdf5 format:

.. code:: python

    def save_data(self,data):
        import os
        import tables
        from visexpman.engine.vision_experiment.experiment_data import get_id
        name=self.setting_values['params/Recording Name']
        fn=os.path.join(r'c:\tmp', f'data_{name}_{get_id()}.h5')#Generate a filename with unique id
        fh=tables.open_file(fn,'w')
        #Use zlib for data compression, compression level 5 is optimal
        datacompressor = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
        #Initialize array
        datatype=tables.Float32Atom(data.shape)
        data_handle=fh.create_earray(fh.root, 'data', datatype, (0,),filters=datacompressor)
        #Add data
        data_handle.append(data[None,:])
        #Save recording parameters as attributes
        setattr(fh.root.data.attrs,'sample_rate',self.setting_values['params/Sampling Rate'])
        fh.close()
        
Call save_data function from finish_recording

.. code:: python

    def finish_recording(self):
        ...
        self.save_data(data)
        
For triggering recording with a keyboard shortcut a QShortcut object's activated slot is connected to start_action method:

.. code:: python

    def init_gui(self):
        ...
        self.shortcut_start = QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self)
        self.shortcut_start.activated.connect(self.start_action)

Statusbar is used for displaying recording status. This is turned to red when recording is started, changes to yellow during saving data and set back to gray after everything is done.
        
.. code:: python

    def start_action(self):
        ...
        self.set_status('recording','red')
        
    def finish_recording(self):
        ...
        self.set_status('saving','yellow')
        self.save_data(data)
        self.set_status('Idle','gray')
        
Popup windows are useful for showing important information to the user or ask for confirmation:

.. code:: python

    def save_data(self,data):
        import os
        import tables
        from visexpman.engine.vision_experiment.experiment_data import get_id
        if not self.ask4confirmation('Do you want to save data?'):
            return
       
        ...
       
        fh.close()
        self.notify('Information', f'Data is saved to {fn}')

self.ask4confirmation and self.notify are helper functions of gui.SimpleGuiWindow which is the superclass of this GUI.

To make the GUI look more professional an icon and a window title is added in def init_gui():

.. code:: python

    def init_gui(self):
        import os
        import PyQt5.QtGui as QtGui
        iconfn=os.path.join(os.sep.join(__file__.split(os.sep)[:-2]),'data','icons','main_ui.png')
        #Set an application icon
        self.setWindowIcon(QtGui.QIcon(iconfn))
        #Icon shows up on taskbar
        gui.set_win_icon()
        #Set name of main window
        self.setWindowTitle('Data Acquisition GUI')
        
After running a recording the GUI should look like this:

.. image:: https://raw.githubusercontent.com/roskalab/visexpman/zdev/images/acquisition_complete.png

Error handling
11. live display
12. Add image display, where? tabbed?

Advanced version: integrate with other Vision Experiment Manager applications (gui.VisexpmanMainWindow)

Reimplement 1-9 to this 

Device Interfaces (visexpman.hardware_interface)
------------------------------------------------

visexpman.hardware_interface.daq - controlling National Instruments DAQmx based devices  - docstring !

def set_voltage(channel, voltage):

def set_waveform(channels,waveform,sample_rate = 1000):

def set_waveform_start(channels,waveform,sample_rate):

def set_waveform_finish(analog_output, timeout,wait=True):

class AnalogRead():
    """
    Utility for recording finite analog signals in a non-blocking way
    """
    def __init__(self, channels, duration, fsample,limits=[-5,5], differential=False, timeout=3):

def read(self):

def abort(self):

def set_digital_line(channel, value):

def digital_pulse(channel,duration):

class SyncAnalogIO():

class AnalogRecorder(multiprocessing.Process):

visexpman.hardware_interface.openephys - docstring !

def start_recording(ip=None,  tag=""):

def stop_recording(ip=None):

def read_sync(in_folder):

visexpman.hardware_interface.stage_control

visexpman.hardware_interface.camera



Stimulus Protocol Development
---------------------------------------

class experiment.Stimulus() methods
stimulation_library functions


[WIP] Configuration
====================

Run a simple stimulus +GUI
----------------------------

TBD

Create Experimental Setup's configuration
---------------------------------------------

Also describe here setup's hardware configuration, wiring, photodiode installation

- Network configuration for direct network link

- stimulus speed config

[WIP] Use Cases
===============

- Visual Stimulation
- Two Photon Imaging
- Electrophysiology
- Behavioral Experiment Control
- Ca Imaging Setup with Visual Stimulation

Output data format
---------------------------------------

stimulus_frame_info

sync, machine_configuration



