# Cómo recibir una alerta de agua en el teléfono

El panel de agua, la recepción de lecturas y las notificaciones están integrados en el mismo Django. No necesitas el ESP32 para esta prueba: el script de Python se conecta por la misma API. La aplicación puede seguir usando SQLite.

## 1. Prepara el proyecto

Abre PowerShell en la carpeta **FundoSanCarlos**. Si tienes abierto el servidor de `iniciar.bat`, ciérralo con Ctrl+C para liberar el puerto 8000.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py preparar_demo
.\.venv\Scripts\python.exe manage.py preparar_push
.\.venv\Scripts\python.exe manage.py configurar_agua
```

Guarda en privado el **token** que muestra el último comando. Su código por defecto es `agua-simulador`. Si vuelves a ejecutar ese comando, el token anterior deja de funcionar. `preparar_demo` conserva los registros y las cuentas existentes. `preparar_push` conserva la clave existente; si la cambias, vuelve a suscribir el teléfono.

Si solo quieres probar el panel y el simulador por ahora, arranca **iniciar.bat**, ejecuta `.\.venv\Scripts\python.exe simular_agua.py` en otra ventana, y pega el token. Esto usa HTTP local y no valida la recepción de avisos en el teléfono.

## 2. Habilita una URL HTTPS temporal

La IP local por HTTP sirve para el panel, pero no habilita Web Push en el teléfono. Para esta prueba puedes usar un túnel temporal. **La URL queda accesible desde internet y Django exige iniciar sesión.** Hazlo solo con datos de prueba, cambia ambas contraseñas de ejemplo y detén el túnel al terminar. Si estás en una red institucional, utiliza una red en la que puedas hacer la prueba.

Cambia las contraseñas conocidas antes de abrir el túnel:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin
.\.venv\Scripts\python.exe manage.py changepassword trabajador
```

Instala **cloudflared** según la [guía oficial de Cloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/). En una ventana aparte ejecuta:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Copia la URL `https://...trycloudflare.com` que imprime Cloudflare y deja abierta esa ventana. En la ventana de PowerShell de **FundoSanCarlos** arranca Django con esa URL y tu correo de contacto:

```powershell
.\.venv\Scripts\python.exe servir_agua_https.py "https://TU-URL.trycloudflare.com" --contacto "TU-CORREO@ejemplo.cl"
```

Mantén las dos ventanas abiertas. Usa la URL **HTTPS** tanto en el teléfono como en el simulador durante esta prueba. Si reinicias el túnel y cambia la URL, reinicia también Django con la nueva URL y vuelve a activar los avisos en el teléfono. Para uso permanente, utiliza una URL estable con HTTPS. [Documentación de túneles de prueba](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

## 3. Suscribe tu teléfono

1. **Android:** abre la URL HTTPS en Chrome. **iPhone (iOS 16.4 o posterior):** abre la URL, agrégala a **Inicio** y abre la app desde ese ícono. [Requisitos en iPhone](https://webkit.org/blog/13878/).
2. Entra con la cuenta **admin** y su nueva contraseña.
3. Ve a **Alertas de agua → Notificaciones al teléfono → Activar notificaciones**. Acepta el permiso del sistema.
4. Cuando aparezca **Notificaciones activadas en este dispositivo**, pasa al siguiente paso para provocar una alerta mediante una lectura.

## 4. Provoca una alerta real con una lectura de prueba

En **Alertas de agua**, configura el umbral en **30 %**. Sal de la app o vuelve a la pantalla de inicio del teléfono. En otra ventana de PowerShell en **FundoSanCarlos**:

```powershell
.\.venv\Scripts\python.exe simular_agua.py --url "https://TU-URL.trycloudflare.com" --pausa 20 78 25 20 85
```

Pega el token cuando se pida (no se mostrará). Espera este recorrido:

| Lectura | Qué debe ocurrir |
| --- | --- |
| 78 % | Nivel normal; resuelve cualquier alerta anterior. |
| 25 % | Se abre una alerta y llega un aviso al teléfono. |
| 20 % | La alerta sigue activa sin otro aviso. |
| 85 % | La alerta se resuelve. |

En el panel verás las lecturas. En **Alertas de agua** puedes revisar el registro y cuántos avisos aceptó el proveedor. La notificación abre la página de alertas. Cierra el túnel y el servidor con Ctrl+C al terminar.

## Si algo no funciona

- **El botón está deshabilitado:** comprueba que la URL diga HTTPS, que hayas ejecutado `preparar_push` y que hayas arrancado con `servir_agua_https.py`. En iPhone usa la app desde el ícono de Inicio.
- **Permiso bloqueado o no aparece el aviso:** revisa los permisos de notificaciones de la app en el teléfono y el modo No molestar/Concentración. Si cambiaste las claves o la URL, desactiva y vuelve a activar o agrega el nuevo ícono.
- **Error 502 al entrar al túnel:** confirma que el servidor arrancó y escucha en el puerto 8000. Si la app devuelve 400, revisa que la URL de arranque sea exactamente la que dio el túnel.
- **HTTP 401 en el simulador:** revisa el token y el código de dispositivo. Si registraste otro código, pásalo con `--codigo`. Si regeneraste el token, usa el nuevo.
- **La suscripción está activa pero no llega el aviso:** comprueba que el umbral sea 30 % y primero envía una lectura superior para resolver una alerta anterior. El aviso automático se genera una vez por alerta nueva.

## Contrato para el ESP32

Envía `POST /api/agua/mediciones/` con `Content-Type: application/json`, `X-Dispositivo: <código>` y `Authorization: Bearer <token>`. Para registrar una placa real usa `manage.py configurar_agua --codigo agua-esp32 --real`; conserva el código y el token en privado.

```json
{
  "id": "16268c86-6886-4a04-9d46-0e43e9f3ade7",
  "porcentaje": 25.0,
  "tomada_en": "2026-11-06T19:00:00Z"
}
```

Usa la fecha real de la lectura. El porcentaje va de 0 a 100, con hasta dos decimales. HTTP **201** confirma una lectura nueva y **200** confirma un reintento idéntico. En un reintento usa el mismo UUID, fecha y porcentaje. Un UUID reutilizado para otros datos devuelve **409**. Una lectura antigua se conserva sin reemplazar la lectura más reciente ni generar una alerta retroactiva.

La suscripción queda asociada al administrador y a la URL HTTPS en la que la activó. El envío se intenta tras guardar la alerta; no existe una cola de reintentos de notificaciones en este avance. Cuando llegue el hardware, queda calibrar el sensor, convertir su lectura a porcentaje y comprobar el flujo con el ESP32.
