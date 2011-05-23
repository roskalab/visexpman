#!/bin/bash
rmmod lp
modprobe ppdev
cd engine
python run_visual_stimulation.py "user/config_class"
