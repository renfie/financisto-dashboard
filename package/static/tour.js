/* 1.9.42: up-to-date, bilingual, role-aware first-login tour. Fully offline. */
(() => {
  'use strict';
  const body = document.body;
  if (!body || !body.dataset.tourUser) return;
  const role = body.dataset.tourRole;
  const desktop = () => window.matchMedia('(min-width:1081px)').matches;
  // All copy is shipped with the application; no external translation service.
  // Keep UI strings separate from financial records and editable account data.
  const language = document.documentElement.lang === 'en' ? 'en' : 'de';
  const copy = {
    de: {
      overview: ['Dein Finanzüberblick', 'Vergleiche die Einnahmen, Ausgaben und den Saldo zweier Monate. Der Monatssaldo ist nicht mit dem aktuellen Kontostand gleichzusetzen.'],
      filters: ['Zeitraum und Filter', 'Wähle die beiden Vergleichsmonate, Konten, Kategorien und die Währung. Über die Suche kannst du Buchungen gezielt eingrenzen.'],
      balances: ['Kontostände ausklappen', 'Hier siehst du den Gesamtstand und auf Wunsch die einzelnen Kontostände. Die Kontostände sind unabhängig vom eingestellten Berichtszeitraum.'],
      transactions: ['Buchungen prüfen', 'Die Buchungsliste ist aufklappbar; über 1W/1M/3M/6M wählst du den Zeitraum, über die Seitenzahlen springst du direkt zur gewünschten Seite. Der separate Filter durchsucht und sortiert die Liste. Auf kleineren Bildschirmen zeigt ein Fingertipp weitere Details. Gelb gekennzeichnete Buchungen liegen in der Zukunft, beeinflussen den gespeicherten Kontostand aber schon jetzt.'],
      history: ['Historische Auswertung', 'Untersuche Entwicklungen über längere Zeiträume, Durchschnittswerte und die wichtigsten Ausgabenkategorien.'],
      monthly: ['Monatsberichte drucken', 'Die Monatsauswertung bietet druckbare Berichte im A5- oder A4-Format.'],
      booking: ['Neue Buchungen erfassen', 'Erfasse Ausgaben, Einnahmen und Umbuchungen. Der Empfänger steht vor der Kategorie. Du kannst Buchungen bearbeiten oder klonen und auch zukünftige Buchungstage eintragen. Dafür muss die Web-Finanzverwaltung führend sein.'],
      recurring: ['Wiederkehrende Buchungen', 'Vorlagen können pausiert oder manuell ausgeführt werden; Administratoren können auch die Automatik freigeben. Begrenze Regeln bei Bedarf auf eine Anzahl von Ausführungen oder mit einem Enddatum. Das erzeugt Web-Buchungen, keinen Bank-Dauerauftrag.'],
      recurringViewer: ['Wiederkehrende Buchungen ansehen', 'Hier siehst du wiederkehrende Vorlagen, ihre Termine und Grenzen. Neue Buchungen und die automatische Ausführung hängen von Berechtigung und führender Datenquelle ab.'],
      imports: ['Financisto-Import und Datenführung', 'Verwalte manuelle .backup-Importe und den optionalen automatischen SFTP-Import. Die Wahl des führenden Systems entscheidet, wo Buchungen bearbeitet werden; Änderungen sind bewusst geschützt.'],
      settingsAdmin: ['Einstellungen und Sicherheit', 'Hier verwaltest du Benutzer, Rechte, die Finanz-Stammdaten und System- sowie Benachrichtigungseinstellungen. Sicherheitsrelevante Änderungen erfordern eine Bestätigung.'],
      settingsEditor: ['Einstellungen für Bearbeiter', 'Hier kannst du die für deine Rolle freigegebenen Finanz-Stammdaten verwalten. Benutzer, System-Sicherheit und die Datenführung werden vom Administrator gesteuert.'],
      language: ['Deutsch und Englisch', 'Mit DE / EN kannst du die Oberfläche jederzeit umstellen. Die Auswahl gilt für deine aktuelle Browser-Sitzung; Buchungen und persönliche Daten bleiben unverändert.'],
      help: ['Einführung erneut öffnen', 'Über „Hilfe / Einführung“ startest du diesen Rundgang jederzeit wieder. Mit „Überspringen“ kannst du ihn schon jetzt beenden.']
    },
    en: {
      overview: ['Your financial overview', 'Compare income, expenses and the balance of two months. The monthly balance is not the same as your current account balance.'],
      filters: ['Dates and filters', 'Choose the two comparison months, accounts, categories and currency. Use search to narrow down the transactions.'],
      balances: ['Expand account balances', 'See the total and, if needed, individual account balances. Account balances are independent of the selected reporting period.'],
      transactions: ['Review transactions', 'Expand the transaction list, select 1W/1M/3M/6M, and jump straight to a page number. The separate filter searches the list. On smaller screens, tap an entry for more details. Yellow-highlighted transactions have a future date but already affect the stored account balance.'],
      history: ['Historical analysis', 'Explore longer-term trends, averages and the most important expense categories.'],
      monthly: ['Print monthly reports', 'The monthly report offers printable summaries in A5 or A4 format.'],
      booking: ['Enter transactions', 'Record expenses, income and transfers. Payee comes before category. You can edit or clone transactions and enter future transaction dates. The web dashboard must be the authoritative finance system to make changes.'],
      recurring: ['Recurring transactions', 'Rules can be paused or run manually; administrators may also enable automatic posting. Set an end date or a maximum number of executions. This creates web transactions, not bank standing orders.'],
      recurringViewer: ['View recurring transactions', 'Review recurring rules, scheduled dates and limits. Creating transactions and automatic posting depend on permissions and the authoritative data source.'],
      imports: ['Financisto imports and data ownership', 'Manage manual .backup imports and optional automatic SFTP imports. The authoritative data-source setting determines where transactions can be edited; changes have explicit safeguards.'],
      settingsAdmin: ['Settings and security', 'Manage users, access rights, financial master data, system options and notifications. Sensitive changes require confirmation.'],
      settingsEditor: ['Editor settings', 'Manage the financial master data available to your role. Users, system security and the authoritative data source are controlled by an administrator.'],
      language: ['German and English', 'Use DE / EN to switch the interface at any time. Your choice applies to the current browser session; transactions and personal data do not change.'],
      help: ['Restart this introduction', 'Open “Help / introduction” to replay this tour at any time. You can also choose “Skip” to stop it now.']
    }
  };
  const labels = language === 'en'
    ? {skip:'Skip', back:'Back', next:'Next', done:'Finish', step:(current,total)=>`Step ${current} of ${total}`,
       closeMenu:'Close menu', openMenu:'Open menu', saveError:'Could not save the introduction status. Please reload the page later.'}
    : {skip:'Überspringen', back:'Zurück', next:'Weiter', done:'Fertig', step:(current,total)=>`Schritt ${current} von ${total}`,
       closeMenu:'Menü schließen', openMenu:'Menü öffnen', saveError:'Einführungsstatus konnte nicht gespeichert werden. Bitte Seite später neu laden.'};
  const steps = [
    {id:'overview', target:'.month-comparison'},
    {id:'filters', target:'#dashboard-filters > summary'},
    {id:'balances', target:'#dashboard-balances > summary'},
    {id:'transactions', target:'#dashboard-ledger > summary', fallback:'#buchungen'},
    {id:'history', nav:'history'},
    {id:'monthly', nav:'monthly'},
    {id:'booking', nav:'bookings-entry', roles:['admin','editor']},
    {id:role === 'viewer' ? 'recurringViewer' : 'recurring', nav:'recurring'},
    {id:'imports', nav:'import', roles:['admin']},
    {id:role === 'admin' ? 'settingsAdmin' : 'settingsEditor', nav:'settings', roles:['admin','editor']},
    {id:'language', languageTarget:true},
    {id:'help', nav:'help'}
  ].filter(step => !step.roles || step.roles.includes(role));
  const token = document.querySelector('meta[name="tour-csrf"]')?.content;
  let index = 0, running = false, lastFocused = null, raf = 0, shade, halo, card, title, message, count, prev, next, menuWasOpen = false;

  function menu(open) {
    const nav = document.getElementById('mobile-nav');
    const toggle = document.querySelector('.mobile-menu-toggle');
    if (!nav || !toggle) return;
    nav.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? labels.closeMenu : labels.openMenu);
  }
  function locate(step) {
    if (step.languageTarget) {
      if (!desktop()) menu(false);
      return document.querySelector(desktop() ? '.sidebar-language .locale-toggle' : '.topbar .locale-toggle');
    }
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
    const [heading,description] = copy[language][step.id];
    title.textContent = heading;
    message.textContent = description;
    count.textContent = labels.step(index+1, steps.length);
    prev.disabled = index === 0;
    next.textContent = index === steps.length-1 ? labels.done : labels.next;
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
      console.warn(labels.saveError);
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
      <section class="tour-card" data-no-i18n role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-text">
        <div class="tour-counter" aria-live="polite"></div>
        <h2 id="tour-title"></h2><p id="tour-text"></p>
        <div class="tour-actions">
          <button type="button" class="tour-skip"></button>
          <button type="button" class="tour-prev"></button>
          <button type="button" class="tour-next"></button>
        </div>
      </section>`;
    shade=root.children[0]; halo=root.children[1]; card=root.children[2];
    document.body.append(shade,halo,card);
    title=card.querySelector('#tour-title'); message=card.querySelector('#tour-text');
    count=card.querySelector('.tour-counter'); prev=card.querySelector('.tour-prev');
    next=card.querySelector('.tour-next');
    card.querySelector('.tour-skip').textContent = labels.skip;
    prev.textContent = labels.back;
    next.textContent = labels.next;
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
