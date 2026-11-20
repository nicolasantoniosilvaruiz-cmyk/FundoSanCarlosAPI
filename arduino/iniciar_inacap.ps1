param([switch]$Verificar, [string]$IpWifi)

$ErrorActionPreference = 'Stop'

function Es-IPv4Privada([string]$Direccion) {
    $ip = $null
    if ($Direccion -notmatch '^\d{1,3}(\.\d{1,3}){3}$' -or
        ![Net.IPAddress]::TryParse($Direccion, [ref]$ip) -or
        $ip.ToString() -ne $Direccion) {
        return $false
    }
    $bytes = $ip.GetAddressBytes()
    return ($bytes[0] -eq 10 -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168))
}

$universidad = Join-Path $env:USERPROFILE 'OneDrive - INACAP\Universidad'
$proyectos = @(Get-ChildItem -Path (Join-Path $universidad 'Segundo A?o') -Directory |
    ForEach-Object { Join-Path $_.FullName 'Segundo Semestre\Proyecto Integrado\FundoSanCarlos' } |
    Where-Object { Test-Path -LiteralPath (Join-Path $_ 'manage.py') -PathType Leaf })
if ($proyectos.Count -ne 1) { throw 'No pude identificar la carpeta FundoSanCarlos en OneDrive.' }
$proyecto = $proyectos[0]
$python = Join-Path $proyecto '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw 'No encontre el entorno virtual de FundoSanCarlos.' }

$wifi = @([Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
    Where-Object { $_.NetworkInterfaceType -eq 'Wireless80211' -and $_.OperationalStatus -eq 'Up' } |
    ForEach-Object { $_.GetIPProperties().UnicastAddresses } |
    ForEach-Object { $_.Address.ToString() } |
    Where-Object { Es-IPv4Privada $_ } | Sort-Object -Unique)

if ($IpWifi) {
    $ipWifi = $IpWifi.Trim()
    if (!(Es-IPv4Privada $ipWifi) -or $ipWifi -notin $wifi) {
        throw 'La IPv4 indicada no pertenece al Wi-Fi activo de este PC.'
    }
} elseif ($wifi.Count -eq 1) {
    $ipWifi = $wifi[0]
} elseif (!$Verificar) {
    Write-Host 'No encontre una sola IPv4 de Wi-Fi. Busca la del PC con ipconfig.'
    if ($wifi.Count) { Write-Host "Direcciones Wi-Fi disponibles: $($wifi -join ', ')" }
    $ipWifi = (Read-Host 'IPv4 privada del Wi-Fi del PC').Trim()
    if (!(Es-IPv4Privada $ipWifi)) { throw 'Ingresa una IPv4 privada valida, por ejemplo 10.30.16.79.' }
}

$env:DJANGO_SETTINGS_MODULE = 'config.settings'
$env:DJANGO_DEBUG = '1'
Remove-Item Env:DJANGO_PUBLIC_ORIGIN -ErrorAction SilentlyContinue
$env:DJANGO_ALLOWED_HOSTS = '127.0.0.1,localhost'
if ($ipWifi) { $env:DJANGO_ALLOWED_HOSTS += ",$ipWifi" }
Set-Location -LiteralPath $proyecto

$codex = Join-Path $env:USERPROFILE 'Documents\Codex'
$firebaseAdmin = Join-Path $codex 'FundoSanCarlosFirebase\firebase-admin.json'
$firebaseAndroid = Join-Path $codex 'FundoSanCarlosAndroid\app\google-services.json'
if ((Test-Path -LiteralPath $firebaseAdmin -PathType Leaf) -and
    (Test-Path -LiteralPath $firebaseAndroid -PathType Leaf)) {
    try {
        $admin = Get-Content -LiteralPath $firebaseAdmin -Raw | ConvertFrom-Json
        $android = Get-Content -LiteralPath $firebaseAndroid -Raw | ConvertFrom-Json
    } catch {
        throw 'No pude leer los JSON de Firebase. Descargalos de nuevo desde la consola.'
    }
    if ($admin.type -ne 'service_account' -or !$admin.project_id -or !$admin.client_email -or !$admin.private_key) {
        throw 'firebase-admin.json debe ser la credencial de la cuenta de servicio de Firebase.'
    }
    if ($admin.project_id -cne $android.project_info.project_id -or
        'cl.fundosancarlos.app' -cnotin $android.client.client_info.android_client_info.package_name) {
        throw 'Los JSON deben pertenecer al mismo proyecto Firebase y a la app cl.fundosancarlos.app.'
    }
    $env:FIREBASE_PROJECT_ID = $admin.project_id
    $env:GOOGLE_APPLICATION_CREDENTIALS = $firebaseAdmin
    Write-Host 'Firebase: archivos verificados. Django usara esta configuracion para los avisos.'
} elseif ($env:FIREBASE_PROJECT_ID -and $env:GOOGLE_APPLICATION_CREDENTIALS -and
    (Test-Path -LiteralPath $env:GOOGLE_APPLICATION_CREDENTIALS -PathType Leaf)) {
    Write-Host 'Firebase: Django usara la configuracion de esta ventana.'
} else {
    Write-Host 'Firebase pendiente. El panel funciona, pero faltan los archivos para el aviso Android.'
}

if ($Verificar) {
    Write-Host "Proyecto encontrado: $proyecto"
    Write-Host "IPv4 Wi-Fi detectadas: $($wifi -join ', ')"
    & $python manage.py check
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host "Telefono por Wi-Fi:   http://${ipWifi}:8000"
Write-Host "Prueba en Chrome:     http://${ipWifi}:8000/agua/"
Write-Host 'Panel web en el PC:  http://127.0.0.1:8000/agua/'
Write-Host 'Deja esta ventana abierta. El receptor del ESP32 sigue usando USB.'
Write-Host 'Si el puerto 8000 esta ocupado, cierra el Django anterior con Ctrl+C.'
Write-Host ''
& $python manage.py runserver 0.0.0.0:8000 --noreload
exit $LASTEXITCODE
