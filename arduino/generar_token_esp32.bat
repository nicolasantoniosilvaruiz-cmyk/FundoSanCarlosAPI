@echo off
setlocal
set "DJANGO="
for /d %%I in ("%USERPROFILE%\OneDrive - INACAP\Universidad\Segundo A?o") do (
  if exist "%%~fI\Segundo Semestre\Proyecto Integrado\FundoSanCarlos\manage.py" set "DJANGO=%%~fI\Segundo Semestre\Proyecto Integrado\FundoSanCarlos"
)
if not defined DJANGO (
  echo No se encontro la carpeta FundoSanCarlos en OneDrive.
  pause
  exit /b 1
)
cd /d "%DJANGO%" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno virtual de FundoSanCarlos.
  pause
  exit /b 1
)
set "DJANGO_SETTINGS_MODULE=config.settings"
echo Generando un token nuevo para agua-esp32. El token anterior quedara invalido.
".venv\Scripts\python.exe" manage.py configurar_agua --codigo agua-esp32 --real
set "RESULTADO=%ERRORLEVEL%"
if "%RESULTADO%"=="0" echo Copia solo el valor del token y pegalo en iniciar_lecturas_esp32.bat.
pause
exit /b %RESULTADO%
