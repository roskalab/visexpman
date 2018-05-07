@echo off
set /p visexppath=<C:\Python27\Lib\site-packages\visexp.pth
cd /D %visexppath%\visexpman\applications\
python visexpman_main.py -u zoltan -c CaImagingTestConfig -a ca_imaging
pause
