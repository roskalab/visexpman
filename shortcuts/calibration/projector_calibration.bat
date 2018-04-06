@echo off
set /p visexppath=<C:\Python27\Lib\site-packages\visexp.pth
cd /D %visexppath%\visexpman\users\zoltan
python projector_calibration.py --calibrate
pause
