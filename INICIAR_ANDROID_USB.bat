@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_revision.ps1" -Usb
pause
