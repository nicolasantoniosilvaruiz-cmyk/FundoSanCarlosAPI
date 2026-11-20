@echo off
setlocal
set "ADB=C:\Users\Merce\AppData\Local\Android\Sdk\platform-tools\adb.exe"
set "DJANGO="
for /d %%I in ("%USERPROFILE%\OneDrive - INACAP\Universidad\Segundo A?o") do (
  if exist "%%~fI\Segundo Semestre\Proyecto Integrado\FundoSanCarlos\manage.py" set "DJANGO=%%~fI\Segundo Semestre\Proyecto Integrado\FundoSanCarlos"
)
if not defined DJANGO (
  echo No se encontro la carpeta FundoSanCarlos en OneDrive.
  pause
  exit /b 1
)
if not exist "%ADB%" (
  echo No se encontro ADB en el SDK de Android.
  pause
  exit /b 1
)
if not exist "%DJANGO%\.venv\Scripts\python.exe" (
  echo No se encontro el entorno de Django.
  pause
  exit /b 1
)
echo Conecta el telefono por USB y acepta la depuracion.
"%ADB%" -d reverse tcp:8000 tcp:8000
if errorlevel 1 (
  echo Desbloquea el telefono, acepta la depuracion USB y vuelve a abrir este archivo.
  pause
  exit /b 1
)
cd /d "%DJANGO%" || exit /b 1
set "DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost"
set "DJANGO_PUBLIC_ORIGIN="
set "DJANGO_SETTINGS_MODULE=config.settings"
set "DJANGO_DEBUG=1"
echo Abre San Carlos en el telefono. La version de prueba se conecta por USB.
echo Deja esta ventana abierta. Si el puerto esta ocupado, cierra el Django anterior.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 --noreload
"%ADB%" -d reverse --remove tcp:8000
pause
