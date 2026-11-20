self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data?.json() || {}; } catch {}
  const path = data.url === '/alertas/' ? '/alertas/' : '/agua/';
  event.waitUntil(self.registration.showNotification(data.title || 'Fundo San Carlos', {
    body: data.body || 'Revisa el nivel del estanque de agua.',
    icon: '/static/img/san-carlos.png',
    tag: data.tag || 'agua',
    data: {path},
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const path = event.notification.data?.path === '/alertas/' ? '/alertas/' : '/agua/';
  event.waitUntil(clients.openWindow(path));
});
