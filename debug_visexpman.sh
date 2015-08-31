#!/bin/bash

export PYTHONPATH=~/Software:PYTHONPATH

if [ -z $1 ]
then
    ./engine/visexp_app.py -u roland -c MEAConfigDebug -a stim  
else
    ./engine/visexp_app.py -u roland -c MEAConfigDebug -a stim -s $1
fi