/* 1.9.20: Mobile thumb navigation. Uses existing server-generated menu and routes. */
(() => {
 'use strict';
 const more = document.querySelector('.mobile-more');
 const nav = document.getElementById('mobile-nav');
 const toggle = document.querySelector('.mobile-menu-toggle');
 const scrim = document.querySelector('.mobile-nav-scrim');
 if (!more || !nav || !toggle || !scrim) return;
 const compact = window.matchMedia('(max-width:760px)');
 const sync = () => {
   const open = !nav.hidden && compact.matches;
   more.setAttribute('aria-expanded', String(open));
   more.classList.toggle('is-open', open);
   scrim.hidden = !open;
 };
 more.addEventListener('click', () => { toggle.click(); sync(); });
 scrim.addEventListener('click', () => { if (!nav.hidden) toggle.click(); sync(); });
 nav.querySelectorAll('a').forEach(el => el.addEventListener('click', () => requestAnimationFrame(sync)));
 document.addEventListener('keydown', event => {
   if (event.key === 'Escape' && !nav.hidden) requestAnimationFrame(sync);
 });
 new MutationObserver(sync).observe(nav, {attributes:true,attributeFilter:['hidden']});
 compact.addEventListener('change', () => {
   if (!nav.hidden) toggle.click();
   sync();
 });
 sync();
})();
