@echo off
set ncpus=4

SET FileToDelete="%TEMP%\data.txt"
IF EXIST %FileToDelete% del /F %FileToDelete%
SET FileToDelete="%TEMP%\out.txt"
IF EXIST %FileToDelete% del /F %FileToDelete%

::http://www.robvanderwoude.com/dialogboxes.php#OpenFolderBox
OpenFolderBox e:\181214_Lema_offcell "Select folder where smr and avi files are">>%TEMP%\data.txt
OpenFolderBox e:\out "Select folder where aligned data will be saved">>%TEMP%\out.txt

set /p data=<%TEMP%\data.txt
set /p out=<%TEMP%\out.txt

python c:\visexp\visexpman\users\santiago\smr_aligner.py %data% %out% %ncpus%
pause
