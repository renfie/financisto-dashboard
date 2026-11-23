/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 René Fieler (RenFie)
 * See LICENSE and NOTICE.md for terms and third-party notices.
 */
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
