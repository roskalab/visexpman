#!/bin/bash

export PYTHONPATH=~/Software:PYTHONPATH

if [ -z $1 ]
then
    ./engine/visexp_app.py -u roland -c MEAConfig -a stim  
else
    ./engine/visexp_app.py -u roland -c MEAConfig -a stim -s $1 #pilot02_cell_classification
fi
