[WORK IN PROGRESS] Vision Experiment Manager
============================================

Vision Experiment Manager is a framework for building automated experiments for visual neuroscience. Its main modules are visual stimulation, two photon imaging, device interfaces and a user interface library.

Vision Experiment Manager was developed in Botond Roska's lab in Friedrich Miescher Instiute and Institute of Molecular and Clinical Ophthalmology Basel from 2011.

Installation
============

Windows 10
--------------

1. Download http://atlas.sens.hu/web/visexpman_installer.zip and unzip to c:\software
2. Install python 3.8.0, installation location is c:\Python38. TBD: options
3. Install pyopengl

.. code:: shell

        cd c:\software\visexpman_installers
        pip install PyOpenGL-3.1.3rc1-cp38-cp38-win_amd64.whl
        
4. Install Daqmx driver (ni-daqmx_19.6_online.exe)
5. Copy ffmpeg.exe and ffprobe.exe to c:\software
6. Add c:\software to Path environmental variable
7. Downlad Visexpman from https://github.com/roskalab/visexpman/archive/refs/heads/zdev.zip and extract to c:\software
8. Install python dependencies: pip install -r c:\software\visexpman\requirements.txt

Run a simple stimulus +GUI
----------------------------

TBD

Create Experimental Setup's configuration
---------------------------------------------

Also describe here setup's hardware configuration, wiring, photodiode installation

- Network configuration for direct network link

- stimulus speed config

Use Cases
=========

- Visual Stimulation
- Two Photon Imaging
- Electrophysiology
- Behavioral Experiment Control
- Ca Imaging Setup with Visual Stimulation

Output data format
---------------------------------------

stimulus_frame_info

sync, machine_configuration




Developer's Guide
=================

Stimulus Protocol Development
---------------------------------------

class experiment.Stimulus() methods
stimulation_library functions

Device Interfaces (visexpman.hardware_interface)
------------------------------------------------

visexpman.hardware_interface.camera

visexpman.hardware_interface.daq - controlling National Instruments DAQmx based devices

visexpman.hardware_interface.openephys

visexpman.hardware_interface.stage_control

GUI Development (visexpman.generic.gui)
---------------------------------------

How to build a simple GUI that triggers data acquisition and sends digital triggers?

VisExpMan has a SimpleGuiWindow class for implementing simple PyQt based applications. Based on Qt.QMainWindow and by default it consist of a log and a debug widget.

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
        setting_values=self.params.get_parameter_tree(return_dict=True)#Grab all values from Settings tab and organize to a dictionary
        self.log(setting_values)#Display setting values on log widget and also save to logfile

parameter_changed method is for processing changes at Setting values. Calling self.log(msg) prints messages to logfile and GUI's log window. Logfile's location can be set as follows:

.. code:: python

    if __name__=='__main__':
        gui=DaqGui(logfolder=r'c:\tmp')
    
3. toolbar
4. statusbar
5. display results
6. self.log(), logfile location
6. save to h5 file
7. daq control

Bells and whistles:
8. icon
9. Notification, ask for ...
10. live display
11. keyboard shortcuts
12. Add image display, where? tabbed?

Advanced version: integrate with other Vision Experiment Manager applications (gui.VisexpmanMainWindow)

Reimplement 1-9 to this 

