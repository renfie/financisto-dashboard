/* FieLanzen 1.9.34 – no data caching, opt-in per-user Web Push details. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
// No fetch handler: personal finance documents are always requested from server.
self.addEventListener('push', event => {
  let payload = {};
  try { payload = event.data ? event.data.json() : {}; } catch (_) {}
  const tag = typeof payload.tag === 'string' ? payload.tag.slice(0, 130) : 'fielanzen';
  const kind = ['expense','income','test'].includes(payload.kind) ? payload.kind : 'generic';
  const defaults = {expense:'Neue Ausgabe erfasst.',income:'Neue Einnahme erfasst.',test:'Push-Test erfolgreich.',generic:'Neue Buchung erfasst.'};
  const body = typeof payload.body==='string' && payload.body.length<=500 && kind!=='generic'
    ? payload.body : defaults[kind];
  event.waitUntil(self.registration.showNotification('FieLanzen', {
    body,
    icon: '/static/icons/icon-192.png?v=1934',
    badge: '/static/icons/notification-96.png?v=1934',
    tag,
    data: { url: '/' }
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type:'window', includeUncontrolled:true}).then(windows => {
    for (const windowClient of windows) {
      if (new URL(windowClient.url).origin === self.location.origin) {
        return windowClient.focus();
      }
    }
    return self.clients.openWindow('/');
  }));
});
