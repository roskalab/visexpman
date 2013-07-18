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
if not exist m:\ net use m: \\argon\groska.mdrive
::Installation, phase 1
if not exist "c:\Program Files\National Instruments\NI-DAQ" (
    if not exist %tmp_folder%\%daqmx_exe% (
        echo Copying daqmx ...
        copy %install_source_folder%\%daqmx_exe% %tmp_folder%\%daqmx_exe%
    )
    echo Install daqmx
    c:
    cd %tmp_folder%
    %daqmx_exe%
) else (
    echo Daqmx already installed
)
if not exist c:\Python27 (
    if not exist %tmp_folder%\%pythonxy_exe% (
        echo Copying pythonxy ...
        copy %install_source_folder%\%pythonxy_exe% %tmp_folder%\%pythonxy_exe%
    )
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
echo Fix OpenGL installation

if not exist c:\Python27\Lib\site-packages\OpenGL\DLLS (
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
xcopy %install_source_folder%\modules\*.* %tmp_folder% /s /y>> %tmp_folder%\copylog.txt
if not exist c:\visexp (
    echo Copying Vision Experiment Manager files ...
    mkdir c:\visexp
    xcopy %visexp_files%\*.* c:\visexp /s /y >> %tmp_folder%\copylog.txt
)
if exist %tmp_folder%\copylog.txt (
    del %tmp_folder%\copylog.txt
)
copy c:\visexp\visexpman\visexp_runner.bat "c:\Documents and Settings\All Users\Desktop\visexp_runner.bat"
copy c:\visexp\visexpman\visexp_gui.bat "c:\Documents and Settings\All Users\Desktop\visexp_gui.bat"
python c:\visexp\visexpman\users\zoltan\installer\post_install.py
python c:\visexp\visexpman\users\zoltan\test\test_installation.py
echo Done
pause
