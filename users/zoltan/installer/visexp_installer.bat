@echo off
set uiname=main_ui
:: folders
set install_source_folder=M:\Zoltan\visexpman_installer
set tmp_folder=c:\temp\visexp_installers
if not exist %tmp_folder% mkdir %tmp_folder%

:: installable executables:
set daqmx_exe=NIDAQ940f1.exe
set pythonxy_exe="Python(x,y)-2.7.6.0.exe"
set pygame_exe="pygame-1.9.2a0.win32-py2.7.msi"
set visexp_files=%install_source_folder%\visexp
REM set visexp_files=v:\codes\zdev

if not exist m:\ net use m: \\argon\groska.mdrive

::Installation, phase 1
if not exist "c:\Program Files\National Instruments\NI-DAQ" (
    echo Copying daqmx ...
    if not exist %tmp_folder%\%daqmx_exe% copy %install_source_folder%\common\%daqmx_exe% %tmp_folder%\%daqmx_exe%
    echo Install daqmx
    echo !!! Select "Reboot later" after installation !!!
    c:
    cd %tmp_folder%
    %daqmx_exe% 
    pause  
) else (
    echo Daqmx already installed
)
if exist c:\Python26 (
    echo Uninstall Python 2.6 and restart installer
    exit /B
)
if exist c:\Python27 (
    echo Python already installed
) else (
    if exist "%PROGRAMFILES(X86)%" (
        echo Installing modules for 64 bit
    ) else (
        echo Assuming 32 bit Window XP, copying pythonxy ...
        if not exist %tmp_folder%\%pythonxy_exe% copy %install_source_folder%\windowsxp\%pythonxy_exe% %tmp_folder%\%pythonxy_exe%
        echo !!! Do not install python xy before Daqmx is installed !!!
        echo !!! Type of installation is Full !!!
        c:
        cd %tmp_folder%
        %pythonxy_exe%
        pause
        if not exist c:\Python27\Lib\site-packages\pygame (
            echo Install Pygame
            if not exist %tmp_folder%\%pygame_exe% copy %install_source_folder%\%pygame_exe% %tmp_folder%\%pygame_exe%
            %pygame_exe%
        ) else (
            echo Pygame already installed
        )
        %install_source_folder%\windowxp\Pillow-2.5.1.win32-py2.7.exe
        %install_source_folder%\windowxp\tables-3.1.1.win32-py2.7.exe
        %install_source_folder%\windowxp\tables-3.1.1.win32-py2.7.exe
    )
)
REM if not exist c:\Python27\Lib\site-packages\OpenGL\DLLS (
REM     echo Fixing OpenGL installation...
REM     mkdir c:\Python27\Lib\site-packages\OpenGL\DLLS
REM     xcopy %install_source_folder%\DLLS\*.* c:\Python27\Lib\site-packages\OpenGL\DLLS /s /y >> %tmp_folder%\copylog.txt
REM )
REM echo Copying python module installers ...
::TODO: check if already copied
REM xcopy %install_source_folder%\modules\*.* %tmp_folder% /s /y>> %tmp_folder%\copylog.txt

echo Copy pth file
copy  %install_source_folder%\common\visexp.pth c:\Python27\Lib\site-packages\visexp.pth
echo Shortcut to pth file
set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = "%USERPROFILE%\Desktop\visexp.pth.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "c:\Python27\Lib\site-packages\visexp.pth" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%
if not exist "c:\visexp" (
    mkdir c:\visexp
    mkdir c:\visexp\data
    echo !!! Copy Vision Experiment Manager files manually to c:\visexp then press a key !!!
    pause
)
if exist "c:\visexp" (
    echo Copy application starters to Desktop
    if %uiname%==main_ui copy "c:\visexp\visexpman\main_ui.bat" "%USERPROFILE%\Desktop\main_ui.bat"
    if %uiname%==ca_imaging copy "c:\visexp\visexpman\ca_imaging.bat" "%USERPROFILE%\Desktop\ca_imaging.bat"
    if %uiname%==stim (
        copy "c:\visexp\visexpman\stim.bat" "%USERPROFILE%\Desktop\stim.bat"
        copy "c:\visexp\visexpman\projector_calibration.bat" "%USERPROFILE%\Desktop\projector_calibration.bat"
        copy "c:\visexp\visexpman\check_projector_calibration.bat" "%USERPROFILE%\Desktop\check_projector_calibration.bat"
    )
    echo !!! After installation make sure that the .bat file contains the correct username and machine config !!!
    pause
)
echo Running post install script...
python c:\visexp\visexpman\users\zoltan\installer\post_install.py
python c:\visexp\visexpman\users\zoltan\test\test_installation.py
echo Done
pause
