# Preparar San Carlos para la presentación

## Prueba sin Wi-Fi y sin escribir IP

Usa la versión Android 1.1 de depuración con **SAN_CARLOS_SERVER_URL vacío**. Conecta el teléfono por USB y acepta la depuración. Detén el Django anterior si ocupa el puerto 8000 y abre **iniciar_demo_usb.bat** desde la carpeta del proyecto Android. La app ya trae la dirección USB por defecto; entra con las credenciales de Django. Puedes abrir la web al mismo tiempo en el PC en http://127.0.0.1:8000/.

Si una sesión anterior sigue conectada a una IP vieja, abre **Cuenta → Volver a configurar conexión** en la app. Para una prueba de escritorio con el teléfono por USB, esta opción no depende de la red de INACAP. Los avisos FCM sí requieren internet y credenciales Firebase.

## Versión para presentar sin cable

1. Usa el archivo **render.yaml** como propuesta de alojamiento. El repositorio conectado a Render debe tener la carpeta Django como raíz. Revisa el plan y el precio antes de crear el servicio. Los secretos y la base local están fuera del repositorio.
2. Configura **DEMO_ADMIN_PASSWORD** y **DEMO_TRABAJADOR_PASSWORD** con contraseñas nuevas de al menos 12 caracteres. El servicio inicializa una **base separada de presentación**, con datos simulados. No se copia db.sqlite3 del PC.
3. Cuando el servicio termine, abre su URL HTTPS y verifica **/salud/**. Debe responder con un JSON que diga que está disponible. Entra al panel con la cuenta de presentación.
4. En Android Studio, agrega la línea siguiente al archivo **local.properties** de la copia de Android, sustituyendo la URL por la que entregó el alojamiento:

   `SAN_CARLOS_SERVER_URL=https://TU-SERVIDOR.onrender.com`

   No agregues /agua/ ni /api/. Sincroniza y recompila. El teléfono ahora muestra solo usuario y contraseña: la URL va integrada en la compilación.

5. Para notificaciones, registra **cl.fundosancarlos.app** en Firebase y pon **google-services.json** en **app/** de Android. En Render, guarda el JSON de la cuenta de servicio como archivo secreto; apunta **GOOGLE_APPLICATION_CREDENTIALS** a su ruta, por ejemplo **/etc/secrets/firebase-admin.json**, y configura **FIREBASE_PROJECT_ID**. Usa el mismo proyecto en ambos lados y recompila Android. Nunca pegues la llave privada en el repositorio ni en la app.
6. Abre San Carlos en el teléfono, permite los avisos e ingresa como administrador. Con permiso y Firebase configurado, se vincula al entrar. Verifica el estado en **Alertas**.

Render gratuito puede pausar el servidor si está inactivo y su Postgres gratuito tiene vencimiento. Para la exposición, revisa la fecha de vencimiento y entra antes de presentar. Si necesitan evitar la espera al arrancar, elijan un servicio que no se suspenda dentro de su presupuesto. Conserva el APK de prueba por USB como respaldo independiente de Wi‑Fi.

## QA en el teléfono antes de la exposición

- **Arranque:** instalar en un Android de prueba y confirmar que el sistema pide el permiso de avisos en la primera apertura (Android 13+). Con permiso rechazado, el panel debe seguir funcionando y Alertas debe permitir abrir los ajustes de San Carlos.
- **Ingreso:** comprobar que el texto de la contraseña se ve enmascarado y que las credenciales inválidas se rechazan. La versión con URL integrada no muestra un campo de servidor.
- **Roles:** el administrador cambia el umbral y registra lecturas; el trabajador consulta niveles. La API debe rechazar escrituras del trabajador.
- **Datos compartidos:** cambiar el umbral en Android, recargar la web y verificar que aparece el mismo valor. Hacer también la prueba inversa.
- **Aviso real:** umbral de 30 %, lectura de 78 %, bloquear pantalla, ingresar 25 % desde el PC. Debe aparecer un aviso de San Carlos. Una lectura de 20 % no lo repite y 85 % resuelve la alerta.
- **Pérdida de red:** con el panel ya cargado, cortar la conexión. Verificar que muestra la última lectura como desactualizada. Volver a conectar y actualizar.
- **Entorno de presentación:** probar desde la red de INACAP (o desde datos móviles) usando la URL alojada. Verificar que ambos equipos ven el mismo registro. Si la red da problemas, probar el flujo USB de respaldo.
