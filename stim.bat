@echo off
set /p visexppath=<C:\Python27\Lib\site-packages\visexp.pth
cd /D %visexppath%\visexpman\engine\
python visexp_app.py -u zoltan -c CaImagingTestConfig -a stim
pause
