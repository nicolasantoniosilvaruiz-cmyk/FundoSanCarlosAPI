# Activar avisos de agua en Android

## En Firebase, una vez

1. En la [consola de Firebase](https://console.firebase.google.com/), crea o selecciona un proyecto. Registra una app Android con el nombre de paquete **cl.fundosancarlos.app**. Descarga **google-services.json** y guárdalo en **C:\Users\Merce\Documents\Codex\FundoSanCarlosAndroid\app\google-services.json**. El proyecto Android ya incorpora Firebase Messaging y lee ese archivo al compilar. [Configuración oficial de Android](https://firebase.google.com/docs/android/setup)
2. En el mismo proyecto, abre **Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada**. Guarda ese segundo archivo como **C:\Users\Merce\Documents\Codex\FundoSanCarlosFirebase\firebase-admin.json**. La clave privada se queda en el PC. [Autorización del servidor](https://firebase.google.com/docs/cloud-messaging/auth-server)

## En Android Studio y durante el ensayo

1. Conecta el teléfono por USB y pulsa **Run** una vez para instalar la compilación que incluye Firebase.
2. Reinicia Django con **iniciar_inacap.bat**. Si los dos archivos están en su sitio y coinciden, el lanzador mostrará **Firebase: archivos verificados**.
3. Conecta ambos equipos al mismo Wi-Fi, abre la app y entra por la dirección de **Telefono por Wi-Fi** que imprime el lanzador. Desconecta el USB del teléfono. Mantén el USB del ESP32 al PC.
4. Entra como **administrador**, permite las notificaciones y comprueba en **Alertas** que los avisos estén activados en el teléfono. El PC y el teléfono necesitan internet para comunicarse con Firebase.
5. Fija el umbral en **30 %**, verifica una lectura sobre ese valor y bloquea la pantalla. Baja el agua hasta cerca de **25 %**. Espera **Alerta de nivel bajo abierta** en el receptor y verifica **Nivel bajo de agua** en el teléfono. Para repetir, deja que Django registre primero una lectura de 30 % o más.

Si la red bloquea el acceso al PC por Wi-Fi, el USB permite acceder al panel. Para probar además Firebase por USB, inicia `iniciar_demo_usb.bat` desde una ventana que ya tenga **FIREBASE_PROJECT_ID** y **GOOGLE_APPLICATION_CREDENTIALS** configuradas.
