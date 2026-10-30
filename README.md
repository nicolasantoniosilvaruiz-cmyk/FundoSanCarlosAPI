# Fundo San Carlos

Primer avance funcional del sistema de monitoreo de agua y petróleo. Aplicación web Django con plantillas, CSS y JavaScript local; no requiere Node ni recursos de internet para la demostración.

## Ejecutar mañana

1. Abre esta carpeta y haz doble clic en **iniciar.bat**.
2. Mantén abierta su ventana y entra a **http://127.0.0.1:8000**.
3. Para detenerlo, presiona Ctrl+C en esa ventana.

También puedes abrir una terminal en esta carpeta y ejecutar:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

No necesitas activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

## Cuentas locales de demostración

| Rol | Usuario | Contraseña |
| --- | --- | --- |
| Administrador | admin | FundoDemo2026! |
| Trabajador | trabajador | CampoDemo2026! |

Estas cuentas son para la presentación local. El administrador de la aplicación no es un superusuario del sitio técnico /admin/. Para crear uno: `.\.venv\Scripts\python.exe manage.py createsuperuser`.

## Guion de demostración (3 minutos)

1. Ingresa como **admin**. Muestra las capacidades: agua 30.000 L; petróleo 1.000 L.
2. Abre **Alertas de agua**, fija el umbral en **30 %** y guarda.
3. En **Registro de lecturas**, selecciona **Estanque de agua**, ingresa **25 %** y guarda. Se registran **7.500 L**, aparece el aviso de nivel bajo y se crea una alerta.
4. Simula **20 %** de agua: el aviso continúa, sin duplicar la alerta activa. Entra a Alertas para verificarlo.
5. Simula **85 %**: el nivel sube a **25.500 L** y la alerta se resuelve. Una nueva bajada al 25 % genera otra alerta.
6. Sal de la cuenta e ingresa como **trabajador**. Puede consultar ambos niveles; no tiene botones administrativos. Si escribe /alertas/ o /simulador/ en la dirección, el servidor responde con acceso restringido.
7. Explica que los valores quedan en la base de datos incluso si se reinicia el servidor. Si tienes otro navegador con una sesión abierta, el panel actualiza los niveles cada 15 segundos.

La pantalla Registro de lecturas escribe registros nuevos y conserva el historial. No tiene un botón que borre datos. Los botones de ejemplo solo rellenan el porcentaje: selecciona el estanque antes de confirmar.

## Qué está implementado

- Inicio de sesión real, contraseñas con hash y cierre de sesión mediante POST con CSRF.
- Roles Administrador y Trabajador; permisos comprobados en el servidor.
- Panel adaptable a móvil y escritorio, con litros, porcentaje, última lectura y aviso si pasan cinco minutos sin datos nuevos.
- Umbral de agua persistente, alerta visual y registro de alertas activas/resueltas.
- Simulador con validación de valores entre 0 y 100 %, conversión a litros y UUID por medición.
- API de consulta autenticada /api/niveles/ y actualización periódica de la interfaz.
- Modelos y migraciones para usuarios, estanques, mediciones y alertas.

## Alcance de este avance

Las mediciones son **simuladas**, no provienen del ESP32. Las alertas son **visuales en la web**: todavía no son notificaciones push. El historial individual de retiros, RFID, válvula, sincronización offline, recuperación de cortes, recargas y reportes no se han implementado.

Se usa **SQLite para la demostración local**, evitando depender de instalar un servidor adicional. El diseño definitivo propone **MySQL**. El modelo se maneja con el ORM de Django y las configuraciones para MySQL están previstas mediante variables de entorno. Este avance implementa cuatro entidades del modelo final; no representa todavía la base de doce entidades completa.

La disponibilidad indicada en el panel es la conexión del navegador con el servidor, no la conectividad de un sensor real. Las lecturas se marcan desactualizadas después de cinco minutos sin una nueva medición. Un fallo de red conserva en pantalla los últimos datos recibidos; no se garantiza que la web abra sin conexión. La operación offline de ESP32 sigue pendiente.

El umbral se considera cruzado cuando la lectura es **menor** al valor configurado. Igualarlo o superarlo resuelve la alerta. Cambiar el umbral reevalúa la última lectura. El petróleo se visualiza pero no genera alertas en esta versión, conforme al alcance principal acordado.

## Desarrollo

Python 3.14 y Django 5.2 LTS. Dependencias exactas en requirements.txt.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py preparar_demo
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver
```

`preparar_demo` crea cuentas/estanques faltantes sin borrar mediciones ni cambiar contraseñas de usuarios existentes. Para restablecer una contraseña usa `manage.py changepassword admin`.

Estructura: `config/` configura Django; `monitoreo/` contiene modelos, formularios, servicios, vistas y pruebas; `templates/` contiene las pantallas; `static/` contiene CSS y JavaScript.

## Paso futuro a MySQL y despliegue

Instalar mysqlclient, crear una base MySQL vacía y configurar DB_ENGINE=mysql, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST y DB_PORT en el entorno. Luego ejecutar migrate y preparar_demo. Los registros que ya están en SQLite no se transfieren automáticamente; una migración de datos debe planificarse aparte.

El servidor de desarrollo escucha solo en 127.0.0.1. Para publicar se requiere alojamiento con HTTPS, DJANGO_DEBUG=0, DJANGO_SECRET_KEY segura, DJANGO_ALLOWED_HOSTS, configuración de cookies seguras y servidor WSGI/ASGI de producción. La clave local está en .django-secret y no se incluye en Git. Las credenciales visibles de demostración deben retirarse antes de publicar.

## Presentación de la interfaz

La interfaz utiliza textos operativos sin carteles académicos. La herramienta que antes se llamaba Simulador aparece como **Registro de lecturas**, conserva sus valores rápidos y permite ingresar niveles manualmente. Internamente las mediciones siguen marcadas como simuladas; este cambio visual no conecta los sensores ni activa notificaciones push. Las cuentas siguen documentadas arriba y ya no aparecen en la pantalla de ingreso.
