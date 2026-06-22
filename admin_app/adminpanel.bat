@echo off
REM Launch the admin panel app detached and exit the batch immediately
start "" pythonw "%~dp0src\admin_desktop.py"
exit /b 0