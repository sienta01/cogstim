@echo off
REM Launch the admin panel app detached and exit the batch immediately
start "" pythonw "%~dp0admin_desktop.py"
exit /b 0