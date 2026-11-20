# QA de San Carlos Android 1.1

| Prueba | Resultado |
| --- | --- |
| Suite completa de Django | 33 pruebas aprobadas, incluidas cuatro del perfil de alojamiento y la preparación de datos de presentación. |
| Cambios de esquema en Django | Sin migraciones nuevas. |
| Código Android | Java compilado con el SDK de Android. Nueve casos de validación de URL aprobados, incluidos USB, HTTPS y rechazo de HTTP público. |
| APK de depuración 1.1 | 125 entradas verificadas, firma APK v2/v3, alineación válida y permiso POST_NOTIFICATIONS en el manifiesto. |
| Compilación estándar | AAPT2 terminó durante el enlace de recursos con dos versiones. Para el APK USB se verificaron los recursos completos por CRC y se ensambló y firmó el paquete con el código 1.1. |
| Teléfono real | Pendiente. ADB no detectó un dispositivo conectado. |
| Notificaciones en pantalla bloqueada | Pendiente de Firebase y de la prueba en teléfono. El APK USB incluido no tiene configuración de Firebase. |
| Alojamiento HTTPS y red de INACAP | Configuración preparada. Despliegue y prueba desde la red pendientes. |

APK de prueba **SanCarlos-1.1-debug.apk**. SHA-256 `FAE5B37B21F2EBAD6BA5475409585E80EA1FA31C5E1EC6A701580BAB566CFD97`.

Para la prueba en Android, sigue **GUIA_PRESENTACION.md** en la carpeta de Django. El permiso inicial se verifica en Android 13 o posterior con una instalación nueva, o en un perfil de prueba sin una decisión de permiso previa. Comprueba que el inicio de sesión enmascara la contraseña, que los niveles coinciden con la web y que un trabajador no puede editar el umbral. Con Firebase configurado, cruza el umbral con el teléfono bloqueado y verifica que aparece el aviso de San Carlos.
