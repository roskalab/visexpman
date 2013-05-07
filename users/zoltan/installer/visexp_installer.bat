@echo off
:: folders
set install_source_folder=M:\Zoltan\visexpman\visexpman_installers
set tmp_folder=c:\temp

:: installable executables:
set daqmx_exe=NIDAQ940f1.exe
set pythonxy_exe="Python(x,y)-2.7.3.1.exe"
set pygame_exe="pygame-1.9.2a0.win32-py2.7.msi"
set crimson_exe=cedt-286-setup.exe
set winmerge_exe=WinMerge-2.12.4-Setup.exe
set zip_exe=7z920.exe
set pydaqmx_tar = PyDAQmx-1.2.1.tar.gz
set zclockfile_tar = zc.lockfile-1.0.2.tar.gz

:: Mount m and g drive if necessary
if not exist g:\ net use g: \\argon\roska.b
if not exist m:\ net use m: \\samarch1\groska.mdrive
echo Copy daqmx
if not exist %tmp_folder%\%daqmx_exe% copy %install_source_folder%\%daqmx_exe% %tmp_folder%\%daqmx_exe%
echo Install daqmx
c:
cd %tmp_folder%
%daqmx_exe%
echo Copy pythonxy
if not exist %tmp_folder%\%pythonxy_exe% copy %install_source_folder%\%pythonxy_exe% %tmp_folder%\%pythonxy_exe%
echo Select Full installation
pause
%pythonxy_exe%
echo Install Pygame
if not exist %tmp_folder%\%pygame_exe% copy %install_source_folder%\%pygame_exe% %tmp_folder%\%pygame_exe%
%pygame_exe%
echo Install code editor and Winmerge
m:
cd %install_source_folder%
%crimson_exe%
%winmerge_exe%
%zip_exe%
Path=%Path%;"C:\Program Files\7-Zip"
echo Install giveio
c:
cd \
mkdir giveio
cd giveio
7z e -y %install_source_folder%\giveio.zip
copy c:\giveio\Load_parallel_port_driver.txt "c:\Documents and Settings\All Users\Desktop\Load_parallel_port_driver.txt"
copy c:\giveio\Load_parallel_port_driver.lnk "c:\Documents and Settings\All Users\Desktop\Load_parallel_port_driver.lnk"
echo Install parallel port driver according to Load_parallel_port_driver.txt on the desktop
echo Phase 1 is complete. After reboot start phase 2
pause
::TODO: after reboot:
echo Install PyDAQmx
c:
cd \
cd temp
7z x -y %install_source_folder%\%pydaqmx_tar%
7z x -y %pydaqmx_tar%
cd PyDAQmx-1.2.1
python setup.py install

echo Install zc.lockfie
cd \
cd temp
7z x -y %install_source_folder%\%zclockfile_tar%
7z x -y %pydaqmx_tar%
cd zc.lockfile-1.0.2
python setup.py install

echo Install Vision Experiment Manager
c:
cd \
if not exist visexp mkdir visexp
cd visexp
7z x -y %install_source_folder%\visexp\visexpman.zip
7z x -y %install_source_folder%\visexp\visexpA.zip
python visexpman/users/zoltan/installer/create_pth.py
copy c:\visexp\visexpman\visexp_runner.bat "c:\Documents and Settings\All Users\Desktop\visexp_runner.bat"
cd \
cd c:\temp
if not exist c:\temp\test mkdir test
echo test installation
cd \
python c:\visexp\visexpman\users\zoltan\test\test_installation.py
echo Done
