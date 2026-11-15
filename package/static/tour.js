/* 1.9.12: local, role-aware first-login tour. No external libraries or analytics. */
(() => {
  'use strict';
  const body = document.body;
  if (!body || !body.dataset.tourUser) return;
  const role = body.dataset.tourRole;
  const desktop = () => window.matchMedia('(min-width:1081px)').matches;
  const steps = [
    {id:'overview', target:'.month-comparison', title:'Dein Finanzüberblick', text:'Hier siehst du Einnahmen, Ausgaben und den Saldo der beiden gewählten Monate. Die Karten lassen sich direkt vergleichen.'},
    {id:'filters', target:'#dashboard-filters > summary', title:'Monate und Filter auswählen', text:'Hier wählst du zwei Monate, Konten, Kategorien und Währung. Die Buchungsliste berücksichtigt auch alle Monate dazwischen.'},
    {id:'transactions', target:'#buchungen .section-head', fallback:'#buchungen', title:'Buchungen im Blick', text:'Hier findest du alle Buchungen im gewählten Zeitraum mit Suchfeld, Sortierung, Seitenwechsel und dem Kontostand nach jeder Buchung.'},
    {id:'history', nav:'history', title:'Historische Auswertung', text:'Dieser Menüpunkt zeigt den gesamten Zeitraum zwischen den gewählten Monaten: Trends, Durchschnittswerte und die größten Kategorien.'},
    {id:'booking', nav:'bookings-entry', title:'Neue Buchungen erfassen', text:'Hier trägst du Ausgaben, Einnahmen und Umbuchungen ein und kannst bereits erfasste Web-Buchungen bearbeiten.', roles:['admin','editor']},
    {id:'recurring', nav:'recurring', title:'Wiederkehrende Buchungen', text:'Plane regelmäßige Zahlungen. Jede Regel ist pausiert, manuell oder automatisch. Automatisch bedeutet nur eine Eintragung im Haushaltsbuch.'},
    {id:'monthly', nav:'monthly', title:'Monatsauswertung drucken', text:'Diesen Bericht kannst du für die ausgewählten Monate als übersichtliche A4- oder A5-Auswertung ausdrucken.', roles:['viewer']},
    {id:'imports', nav:'import', title:'Import und Synchronisation', text:'Hier prüfst du die Android-Sicherung und steuerst den manuellen sowie den automatischen Import. Deine bisherigen Daten bleiben geschützt.', roles:['admin']},
    {id:'settings', nav:'settings', title:'Einstellungen und Hilfe', text:'Unter Einstellungen verwaltest du unter anderem Stammdaten und persönliche Vorgaben. Über „Hilfe / Einführung“ kannst du diesen Rundgang jederzeit erneut starten.', roles:['admin','editor']},
    {id:'viewer-help', nav:'help', title:'Einführung erneut starten', text:'Über diesen Menüpunkt kannst du den Rundgang jederzeit wiederholen.', roles:['viewer']}
  ].filter(step => !step.roles || step.roles.includes(role));
  const token = document.querySelector('meta[name="tour-csrf"]')?.content;
  let index = 0, running = false, lastFocused = null, raf = 0, shade, halo, card, title, message, count, prev, next, menuWasOpen = false;

  function menu(open) {
    const nav = document.getElementById('mobile-nav');
    const toggle = document.querySelector('.mobile-menu-toggle');
    if (!nav || !toggle) return;
    nav.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
  }
  function locate(step) {
    if (step.nav) {
      if (!desktop()) menu(true);
      const selector = step.nav === 'help' ? '[data-tour-start]' : `[data-tour-link="${step.nav}"]`;
      const section = document.querySelector(desktop() ? '.app-sidebar' : '#mobile-nav');
      return section?.querySelector(selector) || null;
    }
    if (!desktop()) menu(false);
    return document.querySelector(step.target) || (step.fallback && document.querySelector(step.fallback)) || null;
  }
  function drawPosition() {
    if (!running || !halo || !card) return;
    const target = locate(steps[index]);
    if (!target) return;
    let r = target.getBoundingClientRect();
    const w = window.innerWidth, h = window.innerHeight;
    if (r.bottom < 10 || r.top > h - 10) {
      target.scrollIntoView({block: 'center', behavior: 'instant'});
      r = target.getBoundingClientRect();
    }
    const x = Math.max(5, r.left - 5), y = Math.max(5, r.top - 5);
    const right = Math.min(w - 5, r.right + 5), bottom = Math.min(h - 5, r.bottom + 5);
    Object.assign(halo.style, {left:`${x}px`,top:`${y}px`,width:`${Math.max(2,right-x)}px`,height:`${Math.max(2,bottom-y)}px`});
    const cw = card.offsetWidth, ch = card.offsetHeight;
    let cx = Math.max(12, Math.min(x, w - cw - 12));
    let cy = bottom + 15;
    if (cy + ch > h - 12) cy = y - ch - 15;
    if (cy < 12) cy = Math.max(12, Math.min(h - ch - 12, (h - ch)/2));
    Object.assign(card.style, {left:`${cx}px`,top:`${cy}px`});
  }
  function schedule() {if (!running) return; window.cancelAnimationFrame(raf); raf = requestAnimationFrame(drawPosition);}
  function display() {
    if (!running) return;
    const step = steps[index];
    const target = locate(step);
    if (!target) { // A feature is absent on this installation: skip it, never trap a user.
      if (index < steps.length-1) {index++; display(); return;}
      void finish('finished'); return;
    }
    title.textContent = step.title;
    message.textContent = step.text;
    count.textContent = `Schritt ${index+1} von ${steps.length}`;
    prev.disabled = index === 0;
    next.textContent = index === steps.length-1 ? 'Fertig' : 'Weiter';
    target.scrollIntoView({block:'center', behavior:'instant'});
    next.focus({preventScroll:true});
    schedule();
  }
  function destroy() {
    running = false;
    window.cancelAnimationFrame(raf);
    shade?.remove(); halo?.remove(); card?.remove();
    document.documentElement.classList.remove('tour-running');
    if (!desktop()) menu(menuWasOpen);
    if (lastFocused && lastFocused.isConnected) lastFocused.focus({preventScroll:true});
  }
  async function finish(outcome) {
    if (!running) return;
    destroy();
    if (!token) return;
    try {
      const body = new URLSearchParams({csrf:token, outcome});
      const result = await fetch('/account/tutorial/complete', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:body.toString()
      });
      if (!result.ok) throw new Error(`HTTP ${result.status}`);
      document.body.dataset.tourAuto='0';
    } catch (_) {
      // Do not silently claim server persistence; a fresh visit can offer the tour again.
      console.warn('Einführungsstatus konnte nicht gespeichert werden. Bitte Seite später neu laden.');
    }
  }
  function start() {
    if (running || !steps.length || !document.querySelector('.month-comparison')) return;
    lastFocused = document.activeElement;
    const nav = document.getElementById('mobile-nav');
    menuWasOpen = !!nav && !nav.hidden;
    const root = document.createElement('div');
    root.innerHTML = `
      <div class="tour-shade" aria-hidden="true"></div>
      <div class="tour-halo" aria-hidden="true"></div>
      <section class="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-text">
        <div class="tour-counter" aria-live="polite"></div>
        <h2 id="tour-title"></h2><p id="tour-text"></p>
        <div class="tour-actions">
          <button type="button" class="tour-skip">Überspringen</button>
          <button type="button" class="tour-prev">Zurück</button>
          <button type="button" class="tour-next">Weiter</button>
        </div>
      </section>`;
    shade=root.children[0]; halo=root.children[1]; card=root.children[2];
    document.body.append(shade,halo,card);
    title=card.querySelector('#tour-title'); message=card.querySelector('#tour-text');
    count=card.querySelector('.tour-counter'); prev=card.querySelector('.tour-prev');
    next=card.querySelector('.tour-next');
    card.querySelector('.tour-skip').addEventListener('click', () => void finish('skipped'));
    prev.addEventListener('click', () => {if(index>0){index--;display();}});
    next.addEventListener('click', () => {
      if(index===steps.length-1) {void finish('finished');return;}
      index++;display();
    });
    running = true;
    document.documentElement.classList.add('tour-running');
    index = 0;
    display();
  }
  document.addEventListener('keydown', event => {
    if (!running) return;
    if (event.key === 'Escape') {event.preventDefault();void finish('skipped');return;}
    if (event.key !== 'Tab') return;
    const buttons=Array.from(card.querySelectorAll('button:not(:disabled)'));
    const first=buttons[0], last=buttons[buttons.length-1];
    if (event.shiftKey && document.activeElement===first) {event.preventDefault();last.focus();}
    else if (!event.shiftKey && document.activeElement===last) {event.preventDefault();first.focus();}
  });
  window.addEventListener('resize', schedule, {passive:true});
  window.addEventListener('scroll', schedule, {passive:true, capture:true});

  const url = new URL(window.location.href);
  const manual = url.searchParams.get('tour') === '1';
  if (manual) {
    url.searchParams.delete('tour');
    window.history.replaceState(null, '', url.pathname + url.search + url.hash);
  }
  // A link to the dashboard provides a consistent start regardless of the page.
  if (manual || body.dataset.tourAuto === '1') {
    if (document.querySelector('.month-comparison')) requestAnimationFrame(start);
  }
})();
