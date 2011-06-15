#!/bin/bash
rmmod lp
modprobe ppdev
cd ../../..
python visexpman/engine/run_visual_stimulation.py "zoltan/UbuntuDeveloperConfig"
