# Lecturas reales de agua con el ESP32

Para el prototipo, el ESP32 envía el porcentaje por su cable USB al PC. El programa del PC lo guarda en el mismo Django que consultan la web y la app. Conserva el cableado actual del HC-SR04. La app puede usar un segundo cable USB con su lanzador de Django.

## Preparación única

1. Si tu sketch ya imprime `Distancia: … cm | Nivel: … %` en el Monitor Serie a 115200, puedes conservarlo. Si necesitas volver a cargarlo, abre **NivelAgua.ino** en Arduino IDE, selecciona **DOIT ESP32 DEVKIT V1** y el puerto que aparece al conectar la placa.
2. Abre PowerShell en la carpeta **FundoSanCarlos**. Registra el ESP32 como dispositivo físico. Guarda el token en privado. Volver a ejecutar el comando genera otro token y el anterior deja de funcionar.

   ```powershell
   .\.venv\Scripts\python.exe manage.py configurar_agua --codigo agua-esp32 --real
   ```

## Ensayo y presentación

1. Conecta el ESP32 al PC. Si vas a usar Android por USB, conecta también el teléfono y arranca Django con **iniciar_demo_usb.bat** de FundoSanCarlosAndroid. Si solo vas a probar la web, usa **iniciar.bat** de FundoSanCarlos. Mantén Django abierto en el puerto 8000.
2. Cierra el Monitor Serie de Arduino IDE y detén el script de lecturas simuladas si lo habías iniciado.
3. Abre **iniciar_lecturas_esp32.bat** de esta carpeta. Elige el COM del ESP32 y pega el token de `agua-esp32`. El token se oculta al escribirlo.
4. Si la placa perdió la calibración al reiniciarse, deja el recipiente vacío y pulsa **V** en la ventana del receptor. Cuando confirme el vacío, agrega **1 litro** y pulsa **L**. El frente del sensor debe quedar a **5 cm o más** del agua al llenar, y debes mantener el sensor inmóvil durante la prueba.
5. Espera **Guardada en Django**. Saca agua con la manguera y verifica que baja el porcentaje en **http://127.0.0.1:8000/agua/** y en Android. El receptor envía una lectura aproximadamente cada 2 segundos y Android consulta el nivel cada 2 segundos mientras el panel está visible. Pulsa **Q** para cerrar el receptor.

Django convierte el porcentaje según la capacidad del estanque. Para esta demostración la capacidad es **1.000 mL**, por lo que **50 % equivale a 500 mL** y un umbral de **30 % equivale a 300 mL**.

## Si algo falla

| Síntoma | Qué revisar |
| --- | --- |
| El puerto COM no aparece | Prueba el cable USB de datos y confirma en Arduino IDE qué puerto desaparece al desconectar el ESP32. |
| Acceso denegado al COM | Cierra el Monitor Serie, el Serial Plotter y cualquier otra ventana que esté leyendo ese puerto. |
| Aparece «Pendiente: calibra» | Pulsa V con el recipiente vacío y luego L con el litro de referencia. Revisa el mensaje de confirmación de cada paso. |
| «Sin lectura válida» | Revisa que el sensor apunte hacia abajo y tenga espacio libre. Confirma primero que mide desde Arduino IDE. |
| Django no confirma la lectura | Abre el panel web en el PC y comprueba que Django siga en el puerto 8000. El receptor reintenta la lectura pendiente con el mismo identificador. |
| HTTP 401 | Confirma que el token pertenece a `agua-esp32` y al mismo Django que está ejecutándose. |
| El panel muestra la lectura anterior | Espera la confirmación del receptor y actualiza. Si quedan registros simulados posteriores, detén el simulador y espera una lectura física nueva. |

Los paneles y las alertas registradas en Django pueden probarse localmente. Para recibir una notificación Android con la pantalla bloqueada, todavía necesitas Firebase configurado e internet en el PC y el teléfono.
