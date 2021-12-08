[WORK IN PROGRESS] Vision Experiment Manager
============================================

Vision Experiment Manager is a framework for building automated experiments for visual neuroscience. Its main modules are visual stimulation, two photon imaging, device interfaces and a user interface library.

Vision Experiment Manager was developed in Botond Roska's lab in Friedrich Miescher Instiute and Institute of Molecular and Clinical Ophthalmology Basel from 2011.

Installation
============

Notes:
- http://atlas.sens.hu/web/python_installer.zip (not complete)
- https://github.com/roskalab/visexpman/blob/zdev/shortcuts/install_modules.bat
- Which exact python version?
- stimulus speed config
- ffmpeg to path
- c:\software
- Installation on win10
- PyDAQmx and DAQmx installation


Create Experimental Setup's configuration
---------------------------------------------

Also describe here setup's hardware configuration, wiring, photodiode installation

- Network configuration for direct network link

Run a simple stimulus +GUI
----------------------------

TBD


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

Toolbar

Output data format
---------------------------------------

hdf5 file structure, mat file


Example: Two Photon GUI Development Guide
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Example: Carandini Behavioral Protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


