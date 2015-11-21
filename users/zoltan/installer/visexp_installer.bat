@echo off
echo Mounting r drive
net use r: \\rzws.fmi.ch\rzws
if not exist r:\installers goto end
if not exist c:\temp mkdir c:\temp
echo copy installers
xcopy /S /Y r:\installers\windows7\install\*.* c:\temp\*.*
cd c:\temp\
Anaconda-2.3.0-Windows-x86_64.exe
PyOpenGL-3.0.2.win-amd64-py2.7.exe
pygame-1.9.2a0.win-amd64-py2.7.exe
pyserial-2.7.win-amd64-py2.7.exe
tcmd851ax64.exe
copy r:\installers\windows7\copy\visexp.pth c:\Anaconda\Lib\site-packages\visexp.pth
mkdir c:\visexp
mkdir c:\visexp\visexpman
copy r:\codes\hdf5io.py c:\visexp
xcopy /S /Y r:\codes\visexpman\*.* c:\visexp\visexpman\*.*
echo Manual settings:
echo 1) install eric: python  c:\temp\eric4-4.5.11\install.py
echo 2) Mute volume
echo 3) Disable screensaver, hibernation and sleep
echo 4) Customize shortcuts
echo 5) Adjust autologin
echo 6) Change windows theme to classic, background color to black
if exist c:\users\mouse\desktop copy c:\visexp\visexpman\visexp_shortcut_template.bat c:\users\mouse\desktop
if not exist c:\users\mouse\desktop echo 6) Copy shortcuts to Desktop
:end
echo Installer exits
pause
