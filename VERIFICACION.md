# Verificación del avance

Se ejecutaron `manage.py check` y `manage.py test`: **15 pruebas aprobadas**, sin incidencias en las comprobaciones de Django.

Las pruebas verifican autenticación, rechazo de acceso administrativo para trabajadores (GET y POST), persistencia del umbral, validación de porcentajes, conversión a litros, ciclo de alertas sin duplicados, resolución al recuperar nivel, ausencia de alertas de agua para petróleo, API de niveles con fecha y aviso de datos desactualizados, protección CSRF y cierre de sesión mediante POST.

Las cuatro vistas (ingreso, panel, alertas y simulador) también respondieron correctamente al cliente interno de Django con los datos de demostración.

El servidor de desarrollo completó su arranque y sus comprobaciones. La conexión HTTP desde el navegador de la sesión automatizada agotó el tiempo de espera; por eso no se afirma una verificación visual ni una prueba completa en navegador. Ejecuta iniciar.bat desde Windows y abre http://127.0.0.1:8000 para comprobar la presentación.

Se detuvieron los servidores de prueba para dejar el puerto disponible. La demostración conserva los niveles iniciales de agua al 78 % y petróleo al 45 %. Las pruebas usaron una base separada y no modificaron los registros de la demostración.
