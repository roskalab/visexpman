@echo off
title Vision Experiment Manager
::set /p visexppath=<C:\Python27\Lib\site-packages\v.pth
x:
cd X:\software\santiago-setup\visexpman\engine\
python visexp_app.py -u santiago -c SantiagoSetupMainConfig -a main_ui --kill 1
pause
sleep 3600