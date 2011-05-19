#!/bin/bash
rmmod lp
modprobe ppdev
python Presentinator.py "UbuntuDeveloperConfig"
