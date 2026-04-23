@echo off
REM Wrapper to run the PowerShell build script with default arguments
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\build_exe.ps1" %*
endlocal
