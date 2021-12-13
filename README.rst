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

Toolbar

basic_gui_image



1. add central plot
2. set up logger
3. toolbar
4. statusbar
5. display results
6. save to h5 file
7. daq control

Bells and whistles:
8. icon
9. live display

Advanced version: integrate with other Vision Experiment Manager applications (gui.VisexpmanMainWindow)

Reimplement 1-9 to this 

Output data format
---------------------------------------

stimulus_frame_info

sync, machine_configuration


