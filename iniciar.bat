@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno virtual. Consulta README.md.
  pause
  exit /b 1
)
echo.
echo Fundo San Carlos - Avance funcional
echo Abre http://127.0.0.1:8000 en el navegador.
echo Para detener el servidor presiona Ctrl+C.
echo.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
pause
