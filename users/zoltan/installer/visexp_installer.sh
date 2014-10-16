#!/bin/bash
#general
apt-get install gnome-commander eric git synaptic libav-tools libavcodec-extra-53
#TODO: update fstab, install smb, mount rlvivo1, mdrive, gdrive
#visexp specific
apt-get install python-numpy python-scipy python-zc.lockfile python-sip python-imaging python-serial python-parallel python-qt4 python-qwt5-qt4 python-opengl python-pygame python-sklearn python wxgtk2.8 python-opencv python-matplotlib python-zmq python-celery python-pp libhdf5-serial-dev
apt-get install python pip
pip install numexpr
pip install Cython
pip install tables
mkdir visexp
cd visexp
git clone git@github.com:roskalab/visexpman.git
git clone git@github.com:hillierdani/visexpA.git
#TODO: unzip & delete zips
python visexpman/users/zoltan/installer/create_pth.py
python visexpman/users/zoltan/test/test_installation.py



