@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo San Carlos - acceso desde Android
echo.
echo Direcciones IPv4 de este equipo:
ipconfig | findstr /I "IPv4 Wi-Fi"
echo.
".venv\Scripts\python.exe" servir_android_lan.py
pause
