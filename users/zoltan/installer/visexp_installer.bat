@echo off
:: folders
set install_source_folder=M:\Zoltan\visexpman\visexpman_installers
set tmp_folder=c:\temp\visexp_installers
if not exist %tmp_folder% mkdir %tmp_folder%

:: installable executables:
set daqmx_exe=NIDAQ940f1.exe
set pythonxy_exe="Python(x,y)-2.7.3.1.exe"
set pygame_exe="pygame-1.9.2a0.win32-py2.7.msi"
set visexp_files=%install_source_folder%\visexp
REM set visexp_files=v:\codes\zdev

:: Mount m and g drive if necessary
if not exist g:\ net use g: \\argon\roska.b
if errorlevel 1 (
    echo G drive cannot be mounted
)
if not exist m:\ net use m: \\argon\groska.mdrive
::Installation, phase 1
if not exist "c:\Program Files\National Instruments\NI-DAQ" (
    echo Copying daqmx ...
    if not exist %tmp_folder%\%daqmx_exe% copy %install_source_folder%\%daqmx_exe% %tmp_folder%\%daqmx_exe%
    echo Install daqmx
    echo Select "Reboot later" after installation
    c:
    cd %tmp_folder%
    %daqmx_exe% 
    pause
    ::'_exe' is not recogniezed as a command
 else (
    ::This appears when daqmx is not yet installed but copied
    echo Daqmx already installed
)
if exist c:\Python26 (
    echo Uninstall Python 2.6 and restart installer
    exit /B
)
if not exist c:\Python27 (
    echo Copying pythonxy ...
    if not exist %tmp_folder%\%pythonxy_exe% copy %install_source_folder%\%pythonxy_exe% %tmp_folder%\%pythonxy_exe%
    echo Do not install python xy before Daqmx is installed
    echo Type of installation is Full
    c:
    cd %tmp_folder%
    %pythonxy_exe%
    pause
) else (
    echo Python already installed
)
if not exist c:\Python27\Lib\site-packages\pygame (
    echo Install Pygame
    if not exist %tmp_folder%\%pygame_exe% copy %install_source_folder%\%pygame_exe% %tmp_folder%\%pygame_exe%
    %pygame_exe%
) else (
    echo Pygame already installed
)

if not exist c:\Python27\Lib\site-packages\OpenGL\DLLS (
    echo Fixing OpenGL installation...
    mkdir c:\Python27\Lib\site-packages\OpenGL\DLLS
    xcopy %install_source_folder%\DLLS\*.* c:\Python27\Lib\site-packages\OpenGL\DLLS /s /y >> %tmp_folder%\copylog.txt
)
::Install giveio only on windows xp machines
if not exist c:\users (
    if not exist c:\giveio (
        echo Install giveio
        c:
        cd \
        mkdir giveio
        copy %install_source_folder%\giveio\*.* c:\giveio
        copy c:\giveio\Load_parallel_port_driver.txt "c:\Documents and Settings\All Users\Desktop\Load_parallel_port_driver.txt"
        copy c:\giveio\Load_parallel_port_driver.lnk "c:\Documents and Settings\All Users\Desktop\Load_parallel_port_driver.lnk"
        echo Type: c:\giveio\giveio.sys and press Install, then press OK
        c:\giveio\LOADDRV.exe
    ) else (
        echo giveio already installed
    )
)
echo Copying python module installers ...
::TODO: check if already copied
xcopy %install_source_folder%\modules\*.* %tmp_folder% /s /y>> %tmp_folder%\copylog.txt
if not exist c:\visexp (
    echo Copying Vision Experiment Manager files ...
    mkdir c:\visexp
    xcopy %visexp_files%\*.* c:\visexp /s /y >> %tmp_folder%\copylog.txt
    mkdir c:\visexp\data
)
if exist %tmp_folder%\copylog.txt (
    del %tmp_folder%\copylog.txt
)
if exist c:\users\mouse (
    set desktop=c:\users\mouse\Desktop
) else (
    set desktop="c:\Documents and Settings\All Users\Desktop"
)
echo Copy application starters to Desktop
copy c:\visexp\visexpman\visexp_runner.bat %desktop%\visexp_runner.bat
copy c:\visexp\visexpman\visexp_gui.bat %desktop%\visexp_gui.bat
copy c:\visexp\visexpman\projector_calibration.bat %desktop%\projector_calibration.bat
copy c:\visexp\visexpman\check_projector_calibration.bat %desktop%\check_projector_calibration.bat
echo Running post install script...
python c:\visexp\visexpman\users\zoltan\installer\post_install.py
:: post install module installer does not work for pydaqmx
python c:\visexp\visexpman\users\zoltan\test\test_installation.py
echo Done
pause
