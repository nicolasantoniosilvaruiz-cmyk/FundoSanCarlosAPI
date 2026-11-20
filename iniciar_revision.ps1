param([switch]$Usb, [switch]$Verificar, [switch]$Preparar)

$ErrorActionPreference = 'Stop'
$proyecto = Join-Path $PSScriptRoot 'django'
$python = Join-Path $proyecto '.venv\Scripts\python.exe'
$requisitos = Join-Path $proyecto 'requirements.txt'
if (!(Test-Path -LiteralPath (Join-Path $proyecto 'manage.py'))) {
    throw 'Mantenga este lanzador al lado de las carpetas django, android y arduino.'
}
if (!(Test-Path -LiteralPath (Join-Path $proyecto 'db.sqlite3'))) {
    throw 'Falta django\db.sqlite3. Descargue el repositorio completo con su base de revision.'
}

$direcciones = @([Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
    Where-Object { $_.OperationalStatus -eq 'Up' -and $_.NetworkInterfaceType -eq 'Wireless80211' } |
    ForEach-Object { $_.GetIPProperties().UnicastAddresses } |
    Where-Object { $_.Address.AddressFamily -eq 'InterNetwork' } |
    ForEach-Object { $_.Address.ToString() } | Sort-Object -Unique)

$adb = $null
if ($Usb) {
    $candidatos = @(Join-Path $env:USERPROFILE 'AppData\Local\Android\Sdk\platform-tools\adb.exe')
    foreach ($variable in 'ANDROID_HOME', 'ANDROID_SDK_ROOT') {
        $sdk = [Environment]::GetEnvironmentVariable($variable)
        if ($sdk) { $candidatos += Join-Path $sdk 'platform-tools\adb.exe' }
    }
    $adb = $candidatos | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (!$adb) { throw 'Abra Android Studio e instale SDK Platform-Tools. Si usa un SDK personalizado, configure ANDROID_HOME.' }
}

Write-Host ''
Write-Host 'Fundo San Carlos - Revision'
Write-Host 'Web en este PC: http://127.0.0.1:8000/'
foreach ($ip in $direcciones) { Write-Host "Telefono u otro PC en el mismo Wi-Fi: http://${ip}:8000" }
if ($Usb) { Write-Host 'Android por USB: http://127.0.0.1:8000' }
if (!$direcciones -and !$Usb) { Write-Host 'No se detecto IPv4 Wi-Fi. La web funciona en este PC; para Android puede usar USB.' }

if ($Verificar) {
    Write-Host 'Carpetas y base encontradas. Esta comprobacion no instala dependencias ni inicia Django.'
    exit 0
}

if (!(Test-Path -LiteralPath $python)) {
    Write-Host 'Creando el entorno virtual. Esta primera preparacion requiere Python instalado.'
    $comando = Get-Command py -ErrorAction SilentlyContinue
    if ($comando) { & $comando.Source -3 -m venv (Join-Path $proyecto '.venv') }
    else {
        $comando = Get-Command python -ErrorAction SilentlyContinue
        if (!$comando) { throw 'Instale Python desde python.org y habilite Add Python to PATH. Luego abra este archivo otra vez.' }
        & $comando.Source -m venv (Join-Path $proyecto '.venv')
    }
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $python)) { throw 'No se pudo crear el entorno virtual. Revise la instalacion de Python.' }
}

& $python -c "import importlib.util, sys; sys.exit(importlib.util.find_spec('pip') is None)"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Completando pip en el entorno virtual.'
    & $python -m ensurepip --upgrade --default-pip
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar pip. Revise los permisos de la carpeta y la instalacion de Python.' }
}

$huella = (Get-FileHash -LiteralPath $requisitos -Algorithm SHA256).Hash
$marca = Join-Path $proyecto '.venv\requisitos.sha256'
if (!(Test-Path -LiteralPath $marca) -or (Get-Content -LiteralPath $marca -Raw).Trim() -ne $huella) {
    Write-Host 'Instalando dependencias del proyecto. La primera vez necesita internet.'
    & $python -m pip install -r $requisitos
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion. Revise internet y los mensajes de pip. No cierre la ventana antes de leer el error.' }
    Set-Content -LiteralPath $marca -Value $huella -Encoding ascii
}

$env:DJANGO_SETTINGS_MODULE = 'config.settings'
$env:DJANGO_DEBUG = '1'
$env:DB_ENGINE = 'sqlite'
Remove-Item Env:DJANGO_PUBLIC_ORIGIN -ErrorAction SilentlyContinue
$env:DJANGO_ALLOWED_HOSTS = (@('127.0.0.1', 'localhost') + $direcciones) -join ','
Set-Location -LiteralPath $proyecto
& $python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones de Django.' }
& $python manage.py check
if ($LASTEXITCODE -ne 0) { throw 'Django detecto un problema en la configuracion.' }
if ($Preparar) { Write-Host 'Entorno preparado correctamente.'; exit 0 }

try {
    if ($Usb) {
        Write-Host 'Conecte el telefono, desbloqueelo y acepte la depuracion USB.'
        & $adb -d reverse tcp:8000 tcp:8000
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo conectar al telefono. Revise la autorizacion USB y que haya un solo telefono conectado.' }
    }
    Write-Host ''
    Write-Host 'Abra la direccion indicada en el navegador. Deje esta ventana abierta.'
    Write-Host 'Si el puerto 8000 esta ocupado, cierre la otra instancia de Django con Ctrl+C.'
    & $python manage.py runserver 0.0.0.0:8000 --noreload
    if ($LASTEXITCODE -ne 0) { throw 'Django se detuvo con un error. Revise el mensaje anterior.' }
} finally {
    if ($Usb) { & $adb -d reverse --remove tcp:8000 }
}
