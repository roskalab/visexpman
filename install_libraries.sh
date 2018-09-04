#!/bin/bash

sudo apt-get install python-parallel python-serial python-pip python-psutil python-numpy python-scipy python-qwt5-qt4 python-zc.lockfile python-tables python-pygame python-pyqtgraph

pip install pyzmq


# In order to use the parallel port, change the driver:
sudo rmmod lp
sudo rmmod parport_pc

sudo modprobe ppdev


## For anaconda

conda install pyzmq
conda install pyqt=4
conda install pyserial

pip install pygame
pip install zc.lockfile
pip install PyOpenGL
pip install PythonQwt

