(() => {
  'use strict';
  if (!('serviceWorker' in navigator)) return;
  if (!window.isSecureContext) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', {scope: '/', updateViaCache: 'none'}).catch(() => {
      // Installation bleibt optional und darf die Finanzanwendung nie stören.
    });
  });
})();
