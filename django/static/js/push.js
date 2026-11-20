(() => {
  const panel = document.getElementById('push-controls');
  if (!panel) return;
  const status = panel.querySelector('#push-status');
  const enable = panel.querySelector('[data-push="enable"]');
  const disable = panel.querySelector('[data-push="disable"]');
  const tell = text => {status.textContent = text;};
  const help = panel.querySelector('#push-help');
  const ios = /iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const android = /Android/i.test(navigator.userAgent);
  const needsHomeIcon = ios && !navigator.standalone &&
    !window.matchMedia('(display-mode: standalone)').matches;
  let registration, subscription, busy = false, helpAvailable = false;
  const permissionState = () => window.Notification?.permission || 'default';
  let lastPermission = permissionState();
  const showHelp = () => {
    const device = needsHomeIcon ? 'ios-install' : ios ? 'ios' : android ? 'android' : 'browser';
    help.querySelectorAll('[data-help]').forEach(section => {
      section.hidden = section.dataset.help !== device;
    });
    help.hidden = false;
  };
  const buttons = () => {
    const needsHelp = needsHomeIcon || permissionState() === 'denied';
    enable.textContent = needsHelp ? 'Cómo permitir avisos' : 'Activar notificaciones';
    enable.disabled = busy || (!registration && !helpAvailable);
    disable.disabled = busy || !subscription;
  };

  async function send(data) {
    const r = await fetch(panel.dataset.url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': panel.querySelector('[name=csrfmiddlewaretoken]').value},
      body: JSON.stringify(data),
    });
    const response = await r.json().catch(() => ({}));
    if (!r.ok || !response.ok) throw new Error(response.error || 'No se pudo completar la operación. Revisa tu sesión.');
  }

  function publicKey() {
    const key = panel.dataset.key.replace(/-/g, '+').replace(/_/g, '/');
    return Uint8Array.from(atob(key.padEnd(Math.ceil(key.length / 4) * 4, '=')), c => c.charCodeAt(0));
  }

  async function action(fn) {
    if (busy) return;
    busy = true;
    buttons();
    try { await fn(); }
    catch (error) { tell(error.message || 'No se pudo completar la operación.'); }
    finally { busy = false; buttons(); }
  }

  enable.addEventListener('click', () => action(async () => {
    if (needsHomeIcon || permissionState() === 'denied') {
      showHelp();
      return tell(needsHomeIcon
        ? 'Para recibir avisos, abre San Carlos desde Inicio.'
        : 'El teléfono tiene bloqueados los avisos. Sigue los pasos de abajo.');
    }
    help.hidden = true;
    if (!subscription) {
      // El navegador pide permiso desde subscribe(), en el mismo toque.
      // No esperar otra promesa antes: algunos navegadores pierden el gesto.
      try {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true, applicationServerKey: publicKey(),
        });
      } catch (error) {
        if (permissionState() === 'denied' || error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          showHelp();
          return tell('Si ves un aviso arriba, toca Permitir. Si no aparece, sigue los pasos de abajo.');
        }
        throw error;
      }
    }
    await send(subscription.toJSON());
    help.hidden = true;
    tell('Notificaciones activadas en este dispositivo.');
  }));
  disable.addEventListener('click', () => action(async () => {
    await send({accion: 'quitar', endpoint: subscription.endpoint});
    await subscription.unsubscribe();
    subscription = null;
    tell('Notificaciones desactivadas en este dispositivo.');
  }));

  function withTimeout(promise, milliseconds) {
    let timer;
    return Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Tiempo de espera agotado.')), milliseconds);
      }),
    ]).finally(() => clearTimeout(timer));
  }

  async function init() {
    if (!window.isSecureContext) return tell('Abre la aplicación por HTTPS para activar los avisos en este dispositivo.');
    if (!panel.dataset.key) return tell('Las notificaciones no están disponibles en este momento.');
    if (needsHomeIcon) {
      helpAvailable = true;
      tell('Abre San Carlos desde el ícono de Inicio para recibir avisos.');
      showHelp();
      buttons();
      return;
    }
    if (!('serviceWorker' in navigator)) {
      return tell('Este navegador no ofrece Web Push. En iPhone, agrega la web a Inicio y ábrela desde el ícono.');
    }
    tell('Preparando las notificaciones…');
    try {
      const installed = await withTimeout(navigator.serviceWorker.register(panel.dataset.worker, {
        scope: '/', updateViaCache: 'none',
      }), 10000);
      const active = installed.active ? installed : await withTimeout(navigator.serviceWorker.ready, 10000);
      if (!active.pushManager) {
        return tell('Este navegador no ofrece Web Push. En iPhone, agrega la web a Inicio y ábrela desde el ícono.');
      }
      registration = active;
      if (permissionState() === 'denied') {
        showHelp();
        tell('El teléfono tiene bloqueados los avisos. Sigue los pasos de abajo.');
      } else {
        tell('Toca Activar notificaciones para recibir alertas en este dispositivo.');
      }
      buttons();
      // Consultar una suscripción previa no debe bloquear el botón de activación.
      withTimeout(registration.pushManager.getSubscription(), 5000).then(existing => {
        if (!busy && !subscription && existing) {
          subscription = existing;
          buttons();
        }
      }).catch(() => {});
    } catch (error) {
      registration = null;
      tell('No se pudieron preparar las notificaciones. Recarga la página.');
      console.warn('Web Push: no se pudo iniciar el servicio.', error.name);
    }
  }
  function refreshPermission() {
    if (!registration || busy) return;
    const current = permissionState();
    if (current === lastPermission) return;
    lastPermission = current;
    buttons();
    if (current === 'denied') {
      showHelp();
      tell('El teléfono tiene bloqueados los avisos. Sigue los pasos de abajo.');
    } else {
      help.hidden = true;
      tell('Toca Activar notificaciones para terminar.');
    }
  }
  window.addEventListener('focus', refreshPermission);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refreshPermission();
  });
  init();
})();
