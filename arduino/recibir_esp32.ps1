param([string]$Puerto)

$ErrorActionPreference = 'Stop'
$intervaloLecturaMs = 2000

function Leer-Nivel([string]$Linea) {
    $patron = '^Distancia:\s+\d+(?:\.\d+)?\s+cm\s*\|\s*Nivel:\s+(?<nivel>\d{1,3}(?:\.\d{1,2})?)\s*%\s*$'
    if ($Linea -cmatch $patron) {
        $valor = [decimal]::Parse($Matches.nivel, [Globalization.CultureInfo]::InvariantCulture)
        if ($valor -le 100) { return $valor }
    }
}

function Nueva-Lectura([decimal]$Nivel) {
    return @{
        id = [guid]::NewGuid().ToString()
        porcentaje = $Nivel.ToString([Globalization.CultureInfo]::InvariantCulture)
        tomada_en = [datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.fffZ', [Globalization.CultureInfo]::InvariantCulture)
    }
}

function Enviar-Lectura([hashtable]$Lectura, [hashtable]$Cabeceras) {
    Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/agua/mediciones/' -Method Post `
        -Headers $Cabeceras -ContentType 'application/json' -Body (ConvertTo-Json -Compress -InputObject $Lectura) `
        -TimeoutSec 4 -MaximumRedirection 0
}

function Iniciar-Lecturas([string]$Puerto) {
    $puertos = @([IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
    if ($puertos.Count -eq 0) { throw 'No hay puertos COM. Conecta el ESP32 con un cable USB de datos.' }
    if (!$Puerto -and $puertos.Count -eq 1) {
        $Puerto = $puertos[0]
        Write-Host "Puerto detectado: $Puerto"
    }
    if (!$Puerto) {
        Write-Host "Puertos disponibles: $($puertos -join ', ')"
        $Puerto = (Read-Host 'Escribe el COM del ESP32').Trim()
    }
    if ($Puerto -notin $puertos) { throw "El puerto $Puerto no esta disponible." }

    $secreto = Read-Host 'Pega el token de agua-esp32' -AsSecureString
    $puntero = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secreto)
    try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($puntero).Trim() }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($puntero); $secreto.Dispose() }
    if ($token -cnotmatch '^[A-Za-z0-9_-]{43}$') { throw 'El token debe tener 43 caracteres. Copia solo el valor.' }
    $cabeceras = @{ Authorization = "Bearer $token"; 'X-Dispositivo' = 'agua-esp32' }

    $serial = [IO.Ports.SerialPort]::new($Puerto, 115200)
    $serial.NewLine = "`n"
    $serial.ReadTimeout = 500
    $serial.WriteTimeout = 500
    $serial.DtrEnable = $false
    $serial.RtsEnable = $false
    $pendiente = $null
    $calibrando = $false
    $cronometro = [Diagnostics.Stopwatch]::StartNew()
    $siguienteEnvio = 0
    try {
        try { $serial.Open() }
        catch { throw "No pude abrir $Puerto. Cierra el Monitor Serie de Arduino IDE y comprueba el cable. $($_.Exception.Message)" }
        Write-Host "Leyendo $Puerto a 115200. V = vacio, L = lleno, Q = salir."
        while ($true) {
            if ([Console]::KeyAvailable) {
                $tecla = [Console]::ReadKey($true).Key
                if ($tecla -eq 'Q') { break }
                if ($tecla -eq 'V') {
                    $calibrando = $true
                    $pendiente = $null
                }
                if ($tecla -in 'V', 'L') { $serial.Write($tecla.ToString()) }
            }
            try { $linea = $serial.ReadLine().Trim() }
            catch [TimeoutException] { continue }
            if ($linea -cmatch '^Lleno guardado:') { $calibrando = $false }
            $nivel = Leer-Nivel $linea
            if ($null -eq $nivel) {
                if ($linea -match '^(Vacio guardado|Lleno guardado|No se guardo|Sin lectura valida|Distancia:)') {
                    Write-Host $linea
                }
                continue
            }
            if ($calibrando) { continue }
            if ($cronometro.ElapsedMilliseconds -lt $siguienteEnvio) { continue }
            if ($null -eq $pendiente) { $pendiente = Nueva-Lectura $nivel }
            try {
                $respuesta = Enviar-Lectura $pendiente $cabeceras
                if ($respuesta.id -ne $pendiente.id) { throw 'Django no confirmo el identificador de la lectura.' }
                $detalle = if ($respuesta.alerta_nueva) { ' | Alerta de nivel bajo abierta' } else { '' }
                Write-Host "Guardada en Django: $($pendiente.porcentaje) %$detalle"
                $pendiente = $null
            } catch {
                $http = $_.Exception.Response
                if ($http -and [int]$http.StatusCode -in 400, 401, 403, 404, 405, 409) {
                    throw "Django devolvio HTTP $([int]$http.StatusCode). Revisa el registro del dispositivo, el token y el servidor."
                }
                Write-Host 'Django no confirmo la lectura. Verifica que el servidor siga abierto. Se reintentara la misma lectura.'
            }
            $siguienteEnvio = $cronometro.ElapsedMilliseconds + $intervaloLecturaMs
        }
    } finally {
        $serial.Dispose()
    }
}

if ($MyInvocation.InvocationName -ne '.') { Iniciar-Lecturas $Puerto }
