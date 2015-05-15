#!/bin/bash

sudo apt-get python-psutil python-numpy python-scipy python-qwt5-qt4 python-zc.lockfile python-tables python-pygame


# In order to use the parallel port, change the driver:
sudo rmmod lp
sudo modprobe ppdev