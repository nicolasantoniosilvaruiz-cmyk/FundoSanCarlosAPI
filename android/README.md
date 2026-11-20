# Fundo San Carlos para Android

Para revisar esta copia del repositorio, siga **LEEME_PROFESOR.txt** en la raíz. Los lanzadores **INICIAR_WEB.bat** e **INICIAR_ANDROID_USB.bat** usan las carpetas incluidas en esta entrega.

App nativa en Java, compatible con Android 8.0 o posterior. Comparte las cuentas y los datos de Django mediante la API. La base principal es `django/db.sqlite3`. El teléfono guarda la última respuesta en una SQLite propia para consulta sin conexión; las escrituras requieren que Django esté disponible.

## Instalar y conectar la versión 1.1

Abre esta carpeta en Android Studio con el JDK integrado y el SDK Android 36.1. Selecciona tu teléfono y usa **Run ▶**.

- **Prueba por USB.** Con depuración USB autorizada, cierra el servidor anterior si ocupa el puerto 8000 y ejecuta **iniciar_demo_usb.bat**. Abre San Carlos e inicia sesión. La app de depuración usa el túnel USB por defecto cuando no tiene una URL integrada.
- **Presentación sin cable.** Una vez alojado Django, agrega `SAN_CARLOS_SERVER_URL=https://tu-servidor.example` a **local.properties** y recompila. El teléfono solo pide las credenciales de Django.
- **Respaldo LAN.** En la versión de depuración sin URL integrada, **Opciones de conexión** permite usar una dirección privada para pruebas. En **Cuenta → Volver a configurar conexión** puedes limpiar una sesión que todavía apunta a una dirección antigua.

Para verificar los roles y el panel sin conexión, sigue el checklist de **GUIA_PRESENTACION.md** en la carpeta de Django.
## Activar avisos nativos con el teléfono bloqueado

**El panel funciona sin Firebase.** Para recibir notificaciones necesitas configurar Firebase una vez. El APK sin esa configuración muestra el panel y las alertas del servidor, pero no recibe avisos en segundo plano.

1. En la [consola de Firebase](https://console.firebase.google.com/), crea o abre un proyecto. Registra una app Android con el identificador exacto **`cl.fundosancarlos.app`**.
2. Descarga **`google-services.json`** y déjalo en **`android/app/google-services.json`**. Android Studio debe recompilar e instalar nuevamente. El proyecto lee esa configuración al compilar. [Guía oficial para Android](https://firebase.google.com/docs/android/setup).
3. Para Django, configura una credencial de una cuenta de servicio del mismo proyecto con acceso a Firebase Cloud Messaging HTTP v1. El **JSON privado de la cuenta de servicio es otro archivo**. Guárdalo fuera del repositorio y de la carpeta de Android. No lo envíes por chat ni lo incluyas en el APK. [Autorización de FCM HTTP v1](https://firebase.google.com/docs/cloud-messaging/auth-server).
4. En el PowerShell de **FundoSanCarlos**, detén Django con Ctrl+C y configura estas variables en **esa misma ventana**, con tu ID y la ruta real:

```powershell
$env:FIREBASE_PROJECT_ID = "ID-REAL-DE-TU-PROYECTO"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\ruta\privada\cuenta-de-servicio.json"
& "..\INICIAR_ANDROID_USB.bat"
```

5. Abre **San Carlos** en un Android con servicios de Google Play e internet. En Android 13 o posterior, permite los avisos cuando el sistema lo pida al abrir la app por primera vez. Entra como administrador y verifica el estado en **Alertas**. Si Android ya bloqueó el aviso, el botón puede abrir directamente **los ajustes de notificaciones de San Carlos**. Al volver con el permiso activo, la app vincula el teléfono.
6. Fija el umbral de agua en **30 %**. Desde el PC, guarda agua al **78 %** para cerrar cualquier alerta anterior. Bloquea la pantalla del teléfono. En el PC guarda agua al **25 %**. Espera un aviso **«Nivel bajo de agua»** de **San Carlos**. Una lectura al **20 %** no debe repetirlo y una al **85 %** debe resolver la alerta. El teléfono debe permitir avisos en la pantalla bloqueada.
7. Si no llega, confirma que Django sigue funcionando y tiene internet, que el teléfono tiene conexión, que ambos JSON corresponden al mismo proyecto y que la app dice **Avisos activados en este teléfono**. Los mensajes que acepta FCM se cuentan en el historial de la API como `avisos_android`; esa aceptación no demuestra que Android lo mostró.

Para esta prueba de Android **no necesitas Cloudflare** si el teléfono usa el túnel por USB o el servidor ya tiene HTTPS. El envío Django → Firebase y la recepción en Android sí necesitan internet. El permiso de Chrome es independiente del permiso de esta aplicación.

## Alcance

La app replica lo que ya existe en Django: cuentas, roles, niveles de agua y petróleo, registro manual, umbral e historial de alertas. El ESP32 seguirá enviando datos al mismo Django. RFID, válvula e historial de retiros no forman parte de la versión existente. Para campo, usen una URL HTTPS estable, cuentas de usuario reales y un servidor que permanezca encendido.
