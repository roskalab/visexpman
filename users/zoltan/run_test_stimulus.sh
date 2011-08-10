#!/bin/bash
rmmod lp
modprobe ppdev
nice -11 python test_stimulus.py
