#!/bin/bash
rmmod lp
modprobe ppdev
cd engine
python visexp_runner.py
