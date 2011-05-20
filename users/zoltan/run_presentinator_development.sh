#!/bin/bash
rmmod lp
modprobe ppdev
cd ../../engine
python run_visual_stimulation.py "zoltan/UbuntuDeveloperConfig"
